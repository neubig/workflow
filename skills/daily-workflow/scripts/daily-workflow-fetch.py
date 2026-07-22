#!/usr/bin/env python3
"""
Fetch daily workflow data from Linear and GitHub APIs.

Generates an ACTION-ORIENTED checklist with explicit instructions for each item:
- PRs awaiting the current user's review
- Linear tickets with investigation/fix commands
- Ready PRs with review status and ping instructions
- Draft PRs with specific fix/test/mark-ready commands

Usage:
    python daily-workflow-fetch.py [--github-user USER] [--output FORMAT]

When --github-user is omitted, the script uses the authenticated GitHub CLI
user. The generated report may contain private work data; keep it local.

Environment variables:
    LINEAR_API_KEYS - Comma-separated Linear API keys
    GITHUB_TOKEN - GitHub personal access token
"""

import argparse
import concurrent.futures
import importlib.util
import json
import os
import pathlib
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


NON_ACTIONABLE_LINEAR_STATE_TYPES = ("completed", "canceled", "duplicate")


@dataclass(frozen=True)
class ExternalLink:
    title: str
    url: str


@dataclass
class LinearTicket:
    identifier: str
    title: str
    description: str
    priority: int
    priority_label: str
    state: str
    state_type: str
    url: str
    due_date: str | None = None
    labels: list[str] = field(default_factory=list)
    external_links: list[ExternalLink] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        return self.state_type not in NON_ACTIONABLE_LINEAR_STATE_TYPES

    @property
    def referenced_repos(self) -> list[str]:
        """Extract GitHub repo references from title and description."""
        repos = []
        # Match patterns like: OpenHands/repo, github.com/owner/repo
        pattern = r'(?:github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)'
        for match in re.finditer(pattern, f"{self.title} {self.description}"):
            repo = match.group(1)
            if not repo.startswith(('http', 'www')):
                repos.append(repo)
        return list(set(repos))

    @property
    def github_links(self) -> list[ExternalLink]:
        return [link for link in self.external_links if "github.com/" in link.url]

    @property
    def linked_pull_requests(self) -> list[ExternalLink]:
        return [link for link in self.github_links if "/pull/" in link.url]

    @property
    def linked_issues(self) -> list[ExternalLink]:
        return [link for link in self.github_links if "/issues/" in link.url]

    @property
    def is_bug(self) -> bool:
        text = f"{self.title} {self.description}".lower()
        return any(kw in text for kw in ['bug', 'error', 'fix', 'crash', 'fail'])

    @property
    def is_manual_only(self) -> bool:
        """Check if ticket requires only manual action (Slack, email, meetings)."""
        text = f"{self.title} {self.description}".lower()
        manual_keywords = ['slack', 'email', 'contact', 'meeting', 'discuss', 'call', 'ping']
        code_keywords = ['github', 'repo', 'pr', 'code', 'fix', 'implement', 'bug', 'error']
        has_manual = any(kw in text for kw in manual_keywords)
        has_code = any(kw in text for kw in code_keywords)
        return has_manual and not has_code

    def get_action_instructions(self) -> str:
        """Generate specific action instructions for this ticket."""
        lines = []

        if self.is_manual_only:
            lines.append("**Action**: Manual - requires human communication")
            lines.append("**Status**: Add to summary as manual action item")
            return "\n".join(lines)

        if self.linked_pull_requests:
            lines.append("**Action**: Continue through linked GitHub PR(s) already in progress")
            lines.append("**Linked GitHub PRs**:")
            for link in self.linked_pull_requests:
                title = link.title or link.url.rsplit('/', 1)[-1]
                lines.append(f"- [{title}]({link.url})")
            if self.linked_issues:
                lines.append("**Linked GitHub issues**:")
                for link in self.linked_issues:
                    title = link.title or link.url.rsplit('/', 1)[-1]
                    lines.append(f"- [{title}]({link.url})")
            lines.append("**Status**: Follow the linked PR workflow; no separate Linear-only action needed")
            return "\n".join(lines)

        if self.linked_issues:
            lines.append("**Action**: Follow linked GitHub work already in progress")
            lines.append("**Linked GitHub items**:")
            for link in self.linked_issues:
                title = link.title or link.url.rsplit('/', 1)[-1]
                lines.append(f"- [{title}]({link.url})")
            lines.append("**Status**: Track implementation through the linked GitHub issue/PR rather than duplicating work in Linear")
            return "\n".join(lines)

        repos = self.referenced_repos
        if repos:
            lines.append(f"**Action**: Investigate and fix in {', '.join(repos)}")
            lines.append("**Commands**:")
            lines.append("```bash")
            for repo in repos[:1]:  # Primary repo
                lines.append(f"cd /tmp && git clone https://github.com/{repo}.git")
                if self.is_bug:
                    # Search for error-related terms
                    search_terms = []
                    for term in ['error', 'exception', 'fail']:
                        if term in self.title.lower():
                            search_terms.append(term)
                    if search_terms:
                        lines.append(f"grep -rn '{search_terms[0]}' /tmp/{repo.split('/')[-1]}/")
            lines.append("```")
        else:
            lines.append("**Action**: Investigate ticket description for actionable items")
            lines.append("**Note**: No GitHub repos or PR links detected - read description carefully")

        return "\n".join(lines)


@dataclass
class GitHubPR:
    repo: str
    number: int
    title: str
    url: str
    is_draft: bool
    created_at: datetime
    head_branch: str = ""
    ready_at: datetime | None = None
    ci_status: str = "unknown"  # success, failure, pending, unknown
    ci_failures: list[str] = field(default_factory=list)
    has_approvals: bool = False
    unresolved_threads: int = 0
    unresolved_thread_details: list[str] = field(default_factory=list)
    has_evidence: bool = False
    days_in_ready: int = 0
    is_content_only: bool = False  # docs, skills, config files
    mergeable: str = "UNKNOWN"
    merge_state_status: str = "UNKNOWN"
    review_summary: str = "unknown"
    awaiting_user_review: bool = False
    linked_issues: list[ExternalLink] = field(default_factory=list)

    @property
    def is_stale(self) -> bool:
        return not self.is_draft and self.days_in_ready > 2 and not self.has_approvals

    @property
    def can_mark_ready(self) -> bool:
        # Content-only PRs don't need evidence
        evidence_ok = self.has_evidence or self.is_content_only
        return (
            self.is_draft
            and self.ci_status == "success"
            and self.unresolved_threads == 0
            and evidence_ok
        )

    @property
    def needs_ci_fix(self) -> bool:
        return self.is_draft and self.ci_status == "failure"

    @property
    def needs_conflict_fix(self) -> bool:
        return self.mergeable == "CONFLICTING" or self.merge_state_status == "DIRTY"

    @property
    def needs_evidence(self) -> bool:
        return (
            self.is_draft
            and not self.has_evidence
            and not self.is_content_only
            and self.ci_status != "failure"
        )

    @property
    def requires_action(self) -> bool:
        if self.awaiting_user_review:
            return not self.is_draft
        if not self.is_draft:
            return self.has_approvals or self.is_stale
        return bool(
            self.needs_conflict_fix
            or self.needs_ci_fix
            or self.unresolved_threads
            or self.needs_evidence
            or self.can_mark_ready
        )

    def get_action_instructions(self) -> str:
        """Generate specific action instructions for this PR."""
        lines = []
        repo_short = self.repo.split("/")[-1]

        if self.awaiting_user_review:
            if self.is_draft:
                lines.append("**Action**: Wait for the author to mark this PR ready")
            elif self.ci_status == "failure":
                lines.append("**Action**: Ask the author to fix failing CI before review")
            elif self.needs_conflict_fix:
                lines.append("**Action**: Ask the author to resolve merge conflicts before review")
            elif not self.has_evidence and not self.is_content_only:
                lines.append("**Action**: Review now and verify live evidence with the author")
            else:
                lines.append("**Action**: Review now")
            return "\n".join(lines)

        if not self.is_draft:
            # Ready PR
            if self.is_stale:
                lines.append(f"**Action**: Ping reviewers (stale {self.days_in_ready} days)")
                lines.append("**Status**: Add to summary as 'needs reviewer ping'")
            elif self.has_approvals:
                lines.append("**Action**: Merge the approved PR")
            else:
                lines.append("**Action**: None needed - awaiting review")
            return "\n".join(lines)

        # Draft PR
        if self.needs_conflict_fix:
            lines.append("**Action**: Resolve merge conflicts")
            lines.append("**Commands**:")
            lines.append("```bash")
            lines.append(f"gh pr checkout {self.number} --repo {self.repo}")
            lines.append("# Merge or rebase the current base branch, resolve conflicts, and push")
            lines.append("```")

        elif self.needs_ci_fix:
            lines.append("**Action**: Fix failing CI/tests")
            lines.append("**Commands**:")
            lines.append("```bash")
            lines.append(f"cd /tmp && git clone https://github.com/{self.repo}.git {repo_short}")
            lines.append(f"cd /tmp/{repo_short} && git fetch origin {self.head_branch} && git checkout {self.head_branch}")
            if self.ci_failures:
                lines.append(f"# Failing checks: {', '.join(self.ci_failures[:3])}")
            lines.append("# Run tests locally, fix failures, commit and push")
            lines.append("```")

        elif self.unresolved_threads > 0:
            lines.append(f"**Action**: Resolve {self.unresolved_threads} review thread(s)")
            lines.append("**Commands**:")
            lines.append("```bash")
            lines.append(f"cd /tmp && git clone https://github.com/{self.repo}.git {repo_short}")
            lines.append(f"cd /tmp/{repo_short} && git fetch origin {self.head_branch} && git checkout {self.head_branch}")
            lines.append("# Address review comments, commit and push")
            lines.append(f"gh pr view {self.number} --repo {self.repo} --comments")
            lines.append("```")
            if self.unresolved_thread_details:
                lines.append("**Review comments**:")
                for detail in self.unresolved_thread_details[:3]:
                    lines.append(f"- {detail}")

        elif self.needs_evidence:
            lines.append("**Action**: Gather live evidence by testing the PR")
            lines.append("**Commands**:")
            lines.append("```bash")
            lines.append(f"cd /tmp && git clone https://github.com/{self.repo}.git {repo_short}")
            lines.append(f"cd /tmp/{repo_short} && git fetch origin {self.head_branch} && git checkout {self.head_branch}")
            lines.append("# Run or demo the feature end-to-end")
            lines.append("# Add/update ## Evidence with a screenshot or fenced command input/output")
            lines.append("# A ## Testing section or an empty ## Evidence heading is not enough")
            lines.append("# If live evidence is blocked, keep the PR in draft")
            lines.append("```")

        elif self.can_mark_ready:
            lines.append("**Action**: Mark ready for review (all checks pass)")
            lines.append("**Commands**:")
            lines.append("```bash")
            lines.append(f'gh pr ready {self.number} --repo {self.repo}')
            lines.append("```")

        return "\n".join(lines)


def linear_ticket_sort_key(ticket: LinearTicket) -> tuple[int, int, str, str]:
    """Sort by Linear priority, then put the earliest due date first."""
    priority_rank = ticket.priority if ticket.priority > 0 else 99
    due_date_rank = 0 if ticket.due_date else 1
    return (
        priority_rank,
        due_date_rank,
        ticket.due_date or "9999-12-31",
        ticket.identifier,
    )


def draft_pr_sort_key(pr: GitHubPR) -> tuple[int, str, int]:
    """Put draft PRs with the most immediate unblock action first."""
    rank = (
        0
        if pr.needs_conflict_fix
        else 1
        if pr.needs_ci_fix
        else 2
        if pr.unresolved_threads > 0
        else 3
        if pr.needs_evidence
        else 4
    )
    return rank, pr.repo, pr.number


@dataclass
class WorkflowChecklist:
    linear_tickets: list[LinearTicket] = field(default_factory=list)
    review_requests: list[GitHubPR] = field(default_factory=list)
    ready_prs: list[GitHubPR] = field(default_factory=list)
    draft_prs: list[GitHubPR] = field(default_factory=list)
    github_metadata: dict[str, Any] = field(default_factory=dict)
    fetch_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def highest_priority_linear_tickets(self) -> list[LinearTicket]:
        """Return every actionable ticket tied at the highest active priority."""
        tickets = sorted(
            (ticket for ticket in self.linear_tickets if ticket.is_actionable),
            key=linear_ticket_sort_key,
        )
        if not tickets:
            return []
        highest_rank = linear_ticket_sort_key(tickets[0])[0]
        return [
            ticket
            for ticket in tickets
            if linear_ticket_sort_key(ticket)[0] == highest_rank
        ]

    def action_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for pr in self.review_requests:
            if pr.requires_action:
                items.append(
                    {
                        "kind": "review_request",
                        "title": f"{pr.repo}#{pr.number} — {pr.title}",
                        "url": pr.url,
                        "priority": None,
                        "priority_label": None,
                        "summary": pr.get_action_instructions().splitlines()[0]
                        .removeprefix("**Action**: "),
                        "related_issues": [
                            {"title": issue.title, "url": issue.url}
                            for issue in pr.linked_issues
                        ],
                    }
                )
        for ticket in self.highest_priority_linear_tickets():
            items.append(
                {
                    "kind": "linear",
                    "title": f"{ticket.identifier} — {ticket.title}",
                    "url": ticket.url,
                    "priority": ticket.priority,
                    "priority_label": ticket.priority_label,
                    "summary": ticket.get_action_instructions().splitlines()[0]
                    .removeprefix("**Action**: "),
                    "related_issues": [
                        {"title": link.title, "url": link.url}
                        for link in ticket.github_links
                    ],
                }
            )
        for pr in self.ready_prs + sorted(self.draft_prs, key=draft_pr_sort_key):
            if pr.requires_action:
                items.append(
                    {
                        "kind": "authored_pr",
                        "title": f"{pr.repo}#{pr.number} — {pr.title}",
                        "url": pr.url,
                        "priority": None,
                        "priority_label": None,
                        "summary": pr.get_action_instructions().splitlines()[0]
                        .removeprefix("**Action**: "),
                        "related_issues": [
                            {"title": issue.title, "url": issue.url}
                            for issue in pr.linked_issues
                        ],
                    }
                )
        return items

    def to_markdown(self) -> str:
        lines = ["# Daily Workflow - Action Items", ""]
        lines.append(f"*Generated: {self.fetch_time.strftime('%Y-%m-%d %H:%M UTC')}*")
        lines.append("")
        lines.append(
            "This report lists the current actionable GitHub work and every Linear "
            "ticket tied at the highest active priority."
        )
        lines.append("")
        lines.append("## Action Items")
        lines.append("")
        actions = self.action_items()
        if not actions:
            lines.append("✅ No current action items.")
        else:
            for index, item in enumerate(actions, start=1):
                lines.append(
                    f"{index}. [{item['title']}]({item['url']})"
                    + (
                        f" — {item['priority_label']} ({item['priority']})"
                        if item["kind"] == "linear"
                        else ""
                    )
                    + f" — {item['summary']}"
                )
                if item["related_issues"]:
                    related = ", ".join(
                        f"[{issue['title'] or issue['url']}]({issue['url']})"
                        for issue in item["related_issues"]
                    )
                    lines.append(f"   Related: {related}")
        lines.append("")

        # Phase 1: PRs awaiting the user's review
        lines.append("---")
        lines.append("## Phase 1: PRs Awaiting Review")
        lines.append("")
        if not self.review_requests:
            lines.append("✅ No PRs are waiting for your review.")
        else:
            for pr in self.review_requests:
                lines.append(f"#### [{pr.repo}#{pr.number}]({pr.url}): {pr.title}")
                lines.append("")
                lines.append(pr.get_action_instructions())
                lines.append("")

        # Phase 2: Highest-priority Linear ticket cohort
        highest_priority_tickets = self.highest_priority_linear_tickets()
        lines.append("---")
        lines.append("## Phase 2: Highest-Priority Linear Tickets")
        lines.append("")
        if not highest_priority_tickets:
            lines.append("✅ No open tickets assigned.")
        else:
            label = highest_priority_tickets[0].priority_label
            value = highest_priority_tickets[0].priority
            lines.append(f"### {label} Priority ({value})")
            lines.append("")
            for t in highest_priority_tickets:
                lines.append(f"#### [{t.identifier}]({t.url}): {t.title}")
                lines.append(f"**State**: {t.state}")
                lines.append(f"**Due**: {t.due_date or 'No due date'}")
                lines.append("")
                lines.append(t.get_action_instructions())
                lines.append("")

        # Phase 3: Ready PRs
        lines.append("---")
        lines.append("## Phase 3: Ready PRs")
        lines.append("")
        if not self.ready_prs:
            lines.append("✅ No ready PRs to manage.")
        else:
            for pr in self.ready_prs:
                status_icon = "⚠️" if pr.is_stale else ("✅" if pr.has_approvals else "⏳")
                lines.append(f"#### {status_icon} [{pr.repo}#{pr.number}]({pr.url}): {pr.title}")
                lines.append("")
                lines.append(pr.get_action_instructions())
                lines.append("")

        # Phase 4: Draft PRs
        lines.append("---")
        lines.append("## Phase 4: Draft PRs")
        lines.append("")
        if not self.draft_prs:
            lines.append("✅ No draft PRs to work on.")
        else:
            # Order by action type: conflicts, CI, review threads, evidence, ready.
            ordered = sorted(self.draft_prs, key=draft_pr_sort_key)

            for pr in ordered:
                if pr.needs_conflict_fix:
                    icon = "💥"
                elif pr.needs_ci_fix:
                    icon = "🔴"
                elif pr.unresolved_threads > 0:
                    icon = "🟠"
                elif pr.needs_evidence:
                    icon = "🟡"
                else:
                    icon = "🟢"

                lines.append(f"#### {icon} [{pr.repo}#{pr.number}]({pr.url}): {pr.title}")
                lines.append("")
                lines.append(pr.get_action_instructions())
                lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        highest_priority_tickets = self.highest_priority_linear_tickets()
        return json.dumps(
            {
                "fetch_time": self.fetch_time.isoformat(),
                "github_metadata": self.github_metadata,
                "highest_linear_priority": (
                    {
                        "value": highest_priority_tickets[0].priority,
                        "label": highest_priority_tickets[0].priority_label,
                    }
                    if highest_priority_tickets
                    else None
                ),
                "action_items": self.action_items(),
                "review_requests": [
                    {
                        "repo": pr.repo,
                        "number": pr.number,
                        "title": pr.title,
                        "url": pr.url,
                        "is_draft": pr.is_draft,
                        "ci_status": pr.ci_status,
                        "mergeable": pr.mergeable,
                        "merge_state_status": pr.merge_state_status,
                        "review_summary": pr.review_summary,
                        "has_evidence": pr.has_evidence,
                        "linked_issues": [
                            {"title": issue.title, "url": issue.url}
                            for issue in pr.linked_issues
                        ],
                        "action_instructions": pr.get_action_instructions(),
                    }
                    for pr in self.review_requests
                ],
                "linear_tickets": [
                    {
                        "identifier": t.identifier,
                        "title": t.title,
                        "priority": t.priority,
                        "priority_label": t.priority_label,
                        "state": t.state,
                        "due_date": t.due_date,
                        "url": t.url,
                        "is_actionable": t.is_actionable,
                        "is_manual_only": t.is_manual_only,
                        "referenced_repos": t.referenced_repos,
                        "external_links": [
                            {"title": link.title, "url": link.url}
                            for link in t.external_links
                        ],
                        "action_instructions": t.get_action_instructions(),
                    }
                    for t in highest_priority_tickets
                ],
                "ready_prs": [
                    {
                        "repo": pr.repo,
                        "number": pr.number,
                        "title": pr.title,
                        "url": pr.url,
                        "ci_status": pr.ci_status,
                        "mergeable": pr.mergeable,
                        "merge_state_status": pr.merge_state_status,
                        "review_summary": pr.review_summary,
                        "has_evidence": pr.has_evidence,
                        "unresolved_threads": pr.unresolved_threads,
                        "has_approvals": pr.has_approvals,
                        "days_in_ready": pr.days_in_ready,
                        "is_stale": pr.is_stale,
                        "linked_issues": [
                            {"title": issue.title, "url": issue.url}
                            for issue in pr.linked_issues
                        ],
                        "action_instructions": pr.get_action_instructions(),
                    }
                    for pr in self.ready_prs
                ],
                "draft_prs": [
                    {
                        "repo": pr.repo,
                        "number": pr.number,
                        "title": pr.title,
                        "url": pr.url,
                        "ci_status": pr.ci_status,
                        "ci_failures": pr.ci_failures,
                        "mergeable": pr.mergeable,
                        "merge_state_status": pr.merge_state_status,
                        "review_summary": pr.review_summary,
                        "unresolved_threads": pr.unresolved_threads,
                        "has_evidence": pr.has_evidence,
                        "needs_ci_fix": pr.needs_ci_fix,
                        "needs_evidence": pr.needs_evidence,
                        "can_mark_ready": pr.can_mark_ready,
                        "linked_issues": [
                            {"title": issue.title, "url": issue.url}
                            for issue in pr.linked_issues
                        ],
                        "action_instructions": pr.get_action_instructions(),
                    }
                    for pr in self.draft_prs
                ],
            },
            indent=2,
        )


def linear_node_is_blocked(node: dict[str, Any]) -> bool:
    """Return True when a Linear issue should be omitted from daily workflow."""
    state_type = node.get("state", {}).get("type")
    if state_type == "blocked":
        return True

    labels = [l["name"] for l in node.get("labels", {}).get("nodes", [])]
    normalized_labels = {label.strip().lower() for label in labels}
    if "blocked" in normalized_labels:
        return True

    inverse_relations = node.get("inverseRelations", {}).get("nodes", [])
    return any(
        rel.get("type") == "blocks"
        and rel.get("relatedIssue", {}).get("state", {}).get("type")
        not in NON_ACTIONABLE_LINEAR_STATE_TYPES
        for rel in inverse_relations
    )


def fetch_linear_tickets(api_key: str) -> list[LinearTicket]:
    """Fetch assigned Linear tickets that are not blocked."""
    import urllib.request

    # Fetch in batches to avoid Linear's query complexity limit
    # inverseRelations adds significant complexity per issue
    batch_size = 50
    all_tickets: list[LinearTicket] = []
    has_more = True
    cursor = None

    while has_more:
        after_clause = f', after: "{cursor}"' if cursor else ""
        query = f"""
        query {{
            viewer {{
                assignedIssues(first: {batch_size}{after_clause}, filter: {{ state: {{ type: {{ nin: ["completed", "canceled", "duplicate"] }} }} }}) {{
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    nodes {{
                        identifier
                        title
                        description
                        priority
                        priorityLabel
                        dueDate
                        url
                        state {{ name type }}
                        labels {{ nodes {{ name }} }}
                        attachments {{
                            nodes {{
                                title
                                url
                            }}
                        }}
                        inverseRelations {{
                            nodes {{
                                type
                                relatedIssue {{
                                    state {{ type }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """

        req = urllib.request.Request(
            "https://api.linear.app/graphql",
            data=json.dumps({"query": query}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": api_key,
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"Error fetching Linear tickets: {e}", file=sys.stderr)
            break

        assigned_issues = (
            data.get("data", {}).get("viewer", {}).get("assignedIssues", {})
        )
        nodes = assigned_issues.get("nodes", [])
        page_info = assigned_issues.get("pageInfo", {})

        for node in nodes:
            if linear_node_is_blocked(node):
                continue

            labels = [l["name"] for l in node.get("labels", {}).get("nodes", [])]
            attachments = node.get("attachments", {}).get("nodes", [])
            external_links = [
                ExternalLink(
                    title=(attachment.get("title") or "").strip(),
                    url=attachment.get("url", ""),
                )
                for attachment in attachments
                if attachment and attachment.get("url")
            ]

            all_tickets.append(
                LinearTicket(
                    identifier=node["identifier"],
                    title=node["title"],
                    description=node.get("description", "") or "",
                    priority=node.get("priority", 0),
                    priority_label=node.get("priorityLabel", "No priority"),
                    state=node["state"]["name"],
                    state_type=node["state"]["type"],
                    url=node["url"],
                    due_date=node.get("dueDate"),
                    labels=labels,
                    external_links=external_links,
                )
            )

        has_more = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")

    tickets = all_tickets

    return sorted(tickets, key=linear_ticket_sort_key)


def parse_linear_api_keys(value: str | None) -> list[str]:
    """Parse and deduplicate comma-separated Linear API keys."""
    if not value:
        return []

    return list(dict.fromkeys(key.strip() for key in value.split(",") if key.strip()))


def fetch_linear_tickets_for_keys(api_keys: list[str]) -> list[LinearTicket]:
    """Fetch and merge assigned tickets from every configured Linear key."""
    if not api_keys:
        return []

    tickets_by_url: dict[str, LinearTicket] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(api_keys)) as executor:
        futures = [executor.submit(fetch_linear_tickets, key) for key in api_keys]
        for future in futures:
            for ticket in future.result():
                tickets_by_url.setdefault(ticket.url, ticket)

    return sorted(tickets_by_url.values(), key=linear_ticket_sort_key)


def _load_github_collector() -> Any:
    path = pathlib.Path(__file__).with_name("gather_github_evidence.py")
    spec = importlib.util.spec_from_file_location("daily_workflow_github", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load GitHub collector from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_github_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _github_pr_from_snapshot(
    item: dict[str, Any], *, awaiting_user_review: bool = False
) -> GitHubPR:
    ready_at_value = item.get("ready_at")
    ready_at = _parse_github_datetime(ready_at_value) if ready_at_value else None
    days_in_ready = (
        max(0, (datetime.now(timezone.utc) - ready_at).days) if ready_at else 0
    )
    ci_map = {
        "passing": "success",
        "failing": "failure",
        "pending": "pending",
        "missing": "unknown",
    }
    unresolved_threads = item.get("unresolved_review_threads") or []
    linked_issues = [
        ExternalLink(title=issue.get("title") or "", url=issue.get("url") or "")
        for issue in item.get("closing_issues") or []
        if issue.get("url")
    ]
    return GitHubPR(
        repo=item.get("repository") or "unknown/unknown",
        number=item.get("number") or 0,
        title=item.get("title") or "Untitled PR",
        url=item.get("url") or "",
        is_draft=bool(item.get("is_draft")),
        created_at=_parse_github_datetime(item.get("created_at")),
        head_branch=item.get("head_ref") or "",
        ready_at=ready_at,
        ci_status=ci_map.get((item.get("ci") or {}).get("summary"), "unknown"),
        ci_failures=[
            check.get("name") or "unknown"
            for check in (item.get("ci") or {}).get("failing") or []
        ],
        has_approvals=item.get("review_summary") == "approved",
        unresolved_threads=len(unresolved_threads),
        unresolved_thread_details=[
            (thread.get("comments") or [{}])[0].get("body", "")[:100]
            for thread in unresolved_threads
            if thread.get("comments")
        ],
        has_evidence=bool((item.get("live_evidence") or {}).get("likely_genuine")),
        days_in_ready=days_in_ready,
        is_content_only=bool(item.get("content_only_likely")),
        mergeable=item.get("mergeable") or "UNKNOWN",
        merge_state_status=item.get("merge_state_status") or "UNKNOWN",
        review_summary=item.get("review_summary") or "unknown",
        awaiting_user_review=awaiting_user_review,
        linked_issues=linked_issues,
    )


def fetch_github_context(
    user: str,
) -> tuple[list[GitHubPR], list[GitHubPR], list[GitHubPR], dict[str, Any]]:
    collector = _load_github_collector()
    snapshot = collector.gather(user, user, 100, False, "report")
    review_requests = [
        _github_pr_from_snapshot(item, awaiting_user_review=True)
        for item in snapshot["prs_awaiting_review"]
    ]
    authored = [
        _github_pr_from_snapshot(item) for item in snapshot["authored_open_prs"]
    ]
    ready_prs = [pr for pr in authored if not pr.is_draft]
    draft_prs = [pr for pr in authored if pr.is_draft]
    ready_prs.sort(key=lambda pr: (pr.repo, pr.number))
    draft_prs.sort(key=draft_pr_sort_key)
    metadata = {
        "viewer": snapshot.get("viewer"),
        "profile": snapshot.get("profile"),
        "api_requests": snapshot.get("api_requests"),
        "warnings": snapshot.get("warnings") or [],
    }
    return review_requests, ready_prs, draft_prs, metadata


def fetch_github_prs(user: str) -> tuple[list[GitHubPR], list[GitHubPR]]:
    """Compatibility wrapper around the shared batched report collector."""
    _, ready_prs, draft_prs, _ = fetch_github_context(user)
    return ready_prs, draft_prs


def main():
    parser = argparse.ArgumentParser(description="Fetch daily workflow data")
    parser.add_argument(
        "--github-user",
        help="GitHub username (defaults to the authenticated gh CLI user)",
    )
    parser.add_argument(
        "--output",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument("--skip-github", action="store_true", help="Skip GitHub fetch")
    args = parser.parse_args()

    checklist = WorkflowChecklist()
    linear_keys = parse_linear_api_keys(os.environ.get("LINEAR_API_KEYS"))
    if not linear_keys:
        print("LINEAR_API_KEYS not set, skipping Linear", file=sys.stderr)

    tasks: dict[str, concurrent.futures.Future[Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        if linear_keys:
            print(
                f"Fetching Linear tickets from {len(linear_keys)} connection(s)...",
                file=sys.stderr,
            )
            tasks["linear"] = executor.submit(
                fetch_linear_tickets_for_keys, linear_keys
            )
        if not args.skip_github:
            github_user = args.github_user or "@me"
            print(f"Fetching GitHub report context for {github_user}...", file=sys.stderr)
            tasks["github"] = executor.submit(fetch_github_context, github_user)

        if "linear" in tasks:
            checklist.linear_tickets = tasks["linear"].result()
            print(f"  Found {len(checklist.linear_tickets)} tickets", file=sys.stderr)
        if "github" in tasks:
            (
                checklist.review_requests,
                checklist.ready_prs,
                checklist.draft_prs,
                checklist.github_metadata,
            ) = tasks["github"].result()
            print(
                f"  Found {len(checklist.review_requests)} review requests, "
                f"{len(checklist.ready_prs)} ready, "
                f"{len(checklist.draft_prs)} draft",
                file=sys.stderr,
            )

    # Output
    if args.output == "json":
        print(checklist.to_json())
    else:
        print(checklist.to_markdown())


if __name__ == "__main__":
    main()
