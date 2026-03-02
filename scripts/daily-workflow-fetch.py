#!/usr/bin/env python3
"""
Fetch daily workflow data from Linear and GitHub APIs.

Generates an ACTION-ORIENTED checklist with explicit instructions for each item:
- Linear tickets with investigation/fix commands
- Ready PRs with review status and ping instructions
- Draft PRs with specific fix/test/mark-ready commands

Usage:
    python daily-workflow-fetch.py [--github-user USER] [--output FORMAT]

Environment variables:
    LINEAR_API_KEY - Linear API key
    GITHUB_TOKEN - GitHub personal access token
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


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
    labels: list[str] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        return self.state_type not in ("completed", "canceled")

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
            lines.append("**Note**: No GitHub repos detected - read description carefully")

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
    def needs_evidence(self) -> bool:
        return (
            self.is_draft
            and not self.has_evidence
            and not self.is_content_only
            and self.ci_status != "failure"
        )

    def get_action_instructions(self) -> str:
        """Generate specific action instructions for this PR."""
        lines = []
        repo_short = self.repo.split("/")[-1]

        if not self.is_draft:
            # Ready PR
            if self.is_stale:
                lines.append(f"**Action**: Ping reviewers (stale {self.days_in_ready} days)")
                lines.append("**Status**: Add to summary as 'needs reviewer ping'")
            elif self.has_approvals:
                lines.append("**Action**: None needed - approved and awaiting merge")
            else:
                lines.append("**Action**: None needed - awaiting review")
            return "\n".join(lines)

        # Draft PR
        if self.needs_ci_fix:
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
            lines.append("**Action**: Gather evidence by testing the PR")
            lines.append("**Commands**:")
            lines.append("```bash")
            lines.append(f"cd /tmp && git clone https://github.com/{self.repo}.git {repo_short}")
            lines.append(f"cd /tmp/{repo_short} && git fetch origin {self.head_branch} && git checkout {self.head_branch}")
            lines.append("# Run tests or demo the feature")
            lines.append("# Add ## Evidence section to PR description")
            lines.append("# Then mark ready for review")
            lines.append("```")

        elif self.can_mark_ready:
            lines.append("**Action**: Mark ready for review (all checks pass)")
            lines.append("**Commands**:")
            lines.append("```bash")
            lines.append(f'gh pr ready {self.number} --repo {self.repo}')
            lines.append("```")

        return "\n".join(lines)


@dataclass
class WorkflowChecklist:
    linear_tickets: list[LinearTicket] = field(default_factory=list)
    ready_prs: list[GitHubPR] = field(default_factory=list)
    draft_prs: list[GitHubPR] = field(default_factory=list)
    fetch_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_markdown(self) -> str:
        lines = ["# Daily Workflow - Action Items", ""]
        lines.append(f"*Generated: {self.fetch_time.strftime('%Y-%m-%d %H:%M UTC')}*")
        lines.append("")
        lines.append("Work through each item in order. Execute the commands provided.")
        lines.append("")

        # Phase 1: Linear Tickets
        lines.append("---")
        lines.append("## Phase 1: Linear Tickets")
        lines.append("")
        if not self.linear_tickets:
            lines.append("✅ No open tickets assigned.")
        else:
            # Group by priority
            by_priority: dict[int, list[LinearTicket]] = {}
            for t in self.linear_tickets:
                by_priority.setdefault(t.priority, []).append(t)

            for priority in sorted(by_priority.keys()):
                tickets = by_priority[priority]
                label = tickets[0].priority_label if tickets else "Unknown"
                lines.append(f"### {label} Priority")
                lines.append("")
                for t in tickets:
                    lines.append(f"#### [{t.identifier}]({t.url}): {t.title}")
                    lines.append(f"**State**: {t.state}")
                    lines.append("")
                    lines.append(t.get_action_instructions())
                    lines.append("")

        # Phase 2: Ready PRs
        lines.append("---")
        lines.append("## Phase 2: Ready PRs")
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

        # Phase 3: Draft PRs
        lines.append("---")
        lines.append("## Phase 3: Draft PRs")
        lines.append("")
        if not self.draft_prs:
            lines.append("✅ No draft PRs to work on.")
        else:
            # Order by action type: fix CI first, then evidence, then mark ready
            ordered = sorted(self.draft_prs, key=lambda p: (
                0 if p.needs_ci_fix else (1 if p.unresolved_threads > 0 else (2 if p.needs_evidence else 3))
            ))

            for pr in ordered:
                if pr.needs_ci_fix:
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
        return json.dumps(
            {
                "fetch_time": self.fetch_time.isoformat(),
                "linear_tickets": [
                    {
                        "identifier": t.identifier,
                        "title": t.title,
                        "priority": t.priority,
                        "priority_label": t.priority_label,
                        "state": t.state,
                        "url": t.url,
                        "is_actionable": t.is_actionable,
                        "is_manual_only": t.is_manual_only,
                        "referenced_repos": t.referenced_repos,
                        "action_instructions": t.get_action_instructions(),
                    }
                    for t in self.linear_tickets
                ],
                "ready_prs": [
                    {
                        "repo": pr.repo,
                        "number": pr.number,
                        "title": pr.title,
                        "url": pr.url,
                        "has_approvals": pr.has_approvals,
                        "days_in_ready": pr.days_in_ready,
                        "is_stale": pr.is_stale,
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
                        "unresolved_threads": pr.unresolved_threads,
                        "has_evidence": pr.has_evidence,
                        "needs_ci_fix": pr.needs_ci_fix,
                        "needs_evidence": pr.needs_evidence,
                        "can_mark_ready": pr.can_mark_ready,
                        "action_instructions": pr.get_action_instructions(),
                    }
                    for pr in self.draft_prs
                ],
            },
            indent=2,
        )


def run_gh(args: list[str]) -> dict[str, Any] | list[Any] | str | int:
    """Run gh CLI command and return parsed JSON or raw output."""
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error running gh {' '.join(args)}: {result.stderr}", file=sys.stderr)
        return {}
    output = result.stdout.strip()
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # Return raw string for non-JSON output (like jq scalar results)
        return output


def fetch_linear_tickets(api_key: str) -> list[LinearTicket]:
    """Fetch assigned Linear tickets."""
    import urllib.request

    query = """
    query {
        viewer {
            assignedIssues(first: 100, filter: { state: { type: { nin: ["completed", "canceled"] } } }) {
                nodes {
                    identifier
                    title
                    description
                    priority
                    priorityLabel
                    url
                    state { name type }
                    labels { nodes { name } }
                }
            }
        }
    }
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
        return []

    tickets = []
    nodes = (
        data.get("data", {})
        .get("viewer", {})
        .get("assignedIssues", {})
        .get("nodes", [])
    )
    for node in nodes:
        labels = [l["name"] for l in node.get("labels", {}).get("nodes", [])]
        tickets.append(
            LinearTicket(
                identifier=node["identifier"],
                title=node["title"],
                description=node.get("description", "") or "",
                priority=node.get("priority", 0),
                priority_label=node.get("priorityLabel", "No priority"),
                state=node["state"]["name"],
                state_type=node["state"]["type"],
                url=node["url"],
                labels=labels,
            )
        )

    return sorted(tickets, key=lambda t: (t.priority, t.identifier))


def _build_pr_graphql_fragment(alias: str, owner: str, repo: str, number: int) -> str:
    """Build a GraphQL fragment for fetching a single PR's details."""
    # Use single line format to avoid shell escaping issues
    return (
        f'{alias}: repository(owner: "{owner}", name: "{repo}") {{ '
        f'pullRequest(number: {number}) {{ '
        f'number title url body isDraft createdAt headRefName headRefOid '
        f'files(first: 100) {{ nodes {{ path }} }} '
        f'reviewThreads(first: 100) {{ nodes {{ isResolved comments(first: 1) {{ nodes {{ body }} }} }} }} '
        f'reviews(first: 50) {{ nodes {{ state }} }} '
        f'commits(last: 1) {{ nodes {{ commit {{ statusCheckRollup {{ contexts(first: 50) {{ nodes {{ ... on CheckRun {{ name conclusion }} }} }} }} }} }} }} '
        f'timelineItems(first: 100, itemTypes: [READY_FOR_REVIEW_EVENT]) {{ nodes {{ ... on ReadyForReviewEvent {{ createdAt }} }} }} '
        f'}} }}'
    )


def _parse_pr_from_graphql(repo_name: str, pr_data: dict[str, Any]) -> GitHubPR | None:
    """Parse a PR from GraphQL response data."""
    if not pr_data or not pr_data.get("pullRequest"):
        return None

    pr = pr_data["pullRequest"]
    number = pr["number"]
    pr_body = pr.get("body") or ""

    # Extract changed files
    files_nodes = pr.get("files", {}).get("nodes", [])
    changed_files = [f.get("path", "") for f in files_nodes if f]

    # Detect content-only PRs
    content_extensions = {'.md', '.txt', '.rst', '.json', '.yaml', '.yml', '.toml'}
    content_dirs = {'docs/', 'skills/', '.github/', 'examples/'}
    is_content_only = False
    if changed_files:
        is_content_only = all(
            any(f.endswith(ext) for ext in content_extensions) or
            any(f.startswith(d) for d in content_dirs)
            for f in changed_files
        )

    # Parse CI status from statusCheckRollup
    ci_status = "unknown"
    ci_failures: list[str] = []
    commits = pr.get("commits", {}).get("nodes", [])
    if commits:
        rollup = commits[0].get("commit", {}).get("statusCheckRollup")
        if rollup:
            contexts = rollup.get("contexts", {}).get("nodes", [])
            conclusions = [c.get("conclusion") for c in contexts if c]
            ci_failures = [
                c.get("name", "unknown")
                for c in contexts
                if c and c.get("conclusion") == "FAILURE"
            ]
            if not conclusions:
                ci_status = "pending"
            elif all(c in ("SUCCESS", "SKIPPED", None) for c in conclusions):
                ci_status = "success"
            elif "FAILURE" in conclusions:
                ci_status = "failure"
            else:
                ci_status = "pending"

    # Parse review threads
    unresolved = 0
    unresolved_details: list[str] = []
    threads = pr.get("reviewThreads", {}).get("nodes", [])
    for t in threads:
        if t and not t.get("isResolved", True):
            unresolved += 1
            comments = t.get("comments", {}).get("nodes", [])
            if comments:
                body = comments[0].get("body", "")[:100]
                unresolved_details.append(body)

    # Parse approvals
    reviews = pr.get("reviews", {}).get("nodes", [])
    has_approvals = any(r and r.get("state") == "APPROVED" for r in reviews)

    # Check for evidence
    has_evidence = "## Evidence" in pr_body or "## Testing" in pr_body

    # Parse ready_for_review date
    ready_at = None
    days_in_ready = 0
    is_draft = pr.get("isDraft", False)
    if not is_draft:
        timeline_items = pr.get("timelineItems", {}).get("nodes", [])
        if timeline_items:
            last_ready = timeline_items[-1].get("createdAt", "")
            if last_ready:
                try:
                    ready_at = datetime.fromisoformat(last_ready.replace("Z", "+00:00"))
                    days_in_ready = (datetime.now(timezone.utc) - ready_at).days
                except ValueError:
                    pass

    created_at = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))

    return GitHubPR(
        repo=repo_name,
        number=number,
        title=pr["title"],
        url=pr["url"],
        is_draft=is_draft,
        created_at=created_at,
        head_branch=pr.get("headRefName", ""),
        ready_at=ready_at,
        ci_status=ci_status,
        ci_failures=ci_failures,
        has_approvals=has_approvals,
        unresolved_threads=unresolved,
        unresolved_thread_details=unresolved_details,
        has_evidence=has_evidence,
        days_in_ready=days_in_ready,
        is_content_only=is_content_only,
    )


def _fetch_single_pr_graphql(repo_name: str, number: int) -> GitHubPR | None:
    """Fetch a single PR using GraphQL. Fallback for batches that fail."""
    owner, repo = repo_name.split("/")
    query = "query { " + _build_pr_graphql_fragment("pr", owner, repo, number) + " }"
    result = run_gh(["api", "graphql", "-f", f"query={query}"])

    if not isinstance(result, dict) or "data" not in result:
        return None

    pr_data = result.get("data", {}).get("pr")
    if pr_data:
        return _parse_pr_from_graphql(repo_name, pr_data)
    return None


def fetch_github_prs(user: str) -> tuple[list[GitHubPR], list[GitHubPR]]:
    """Fetch GitHub PRs authored by user using batched GraphQL queries."""
    # Fetch all open PRs (basic info only)
    prs_data = run_gh(
        [
            "search",
            "prs",
            "--author",
            user,
            "--state",
            "open",
            "--json",
            "repository,number",
            "--limit",
            "100",
        ]
    )

    if not isinstance(prs_data, list):
        return [], []

    ready_prs: list[GitHubPR] = []
    draft_prs: list[GitHubPR] = []

    # Build batched GraphQL query for all PRs
    # Use smaller batches (10) to reduce impact of permission errors
    batch_size = 10
    for batch_start in range(0, len(prs_data), batch_size):
        batch = prs_data[batch_start:batch_start + batch_size]

        # Build query fragments for this batch
        fragments = []
        pr_map: dict[str, tuple[str, int]] = {}  # alias -> (repo_name, number)
        for i, pr_info in enumerate(batch):
            repo_name = pr_info["repository"]["nameWithOwner"]
            number = pr_info["number"]
            owner, repo = repo_name.split("/")
            alias = f"pr_{i}"
            pr_map[alias] = (repo_name, number)
            fragments.append(_build_pr_graphql_fragment(alias, owner, repo, number))
            print(f"  Processing {repo_name}#{number}...", file=sys.stderr)

        # Execute batched query
        query = "query { " + " ".join(fragments) + " }"
        result = run_gh(["api", "graphql", "-f", f"query={query}"])

        if isinstance(result, dict) and "data" in result:
            # Parse results from successful batch
            data = result["data"]
            for alias, (repo_name, _) in pr_map.items():
                pr_data = data.get(alias)
                if pr_data:
                    pr = _parse_pr_from_graphql(repo_name, pr_data)
                    if pr:
                        if pr.is_draft:
                            draft_prs.append(pr)
                        else:
                            ready_prs.append(pr)
        else:
            # Batch failed - fall back to individual queries
            print(f"  Batch failed, fetching individually...", file=sys.stderr)
            for alias, (repo_name, number) in pr_map.items():
                pr = _fetch_single_pr_graphql(repo_name, number)
                if pr:
                    if pr.is_draft:
                        draft_prs.append(pr)
                    else:
                        ready_prs.append(pr)

    # Sort by repo name and PR number for consistent output
    ready_prs.sort(key=lambda p: (p.repo, p.number))
    draft_prs.sort(key=lambda p: (p.repo, p.number))

    return ready_prs, draft_prs


def main():
    parser = argparse.ArgumentParser(description="Fetch daily workflow data")
    parser.add_argument("--github-user", default="neubig", help="GitHub username")
    parser.add_argument(
        "--output",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument("--skip-linear", action="store_true", help="Skip Linear fetch")
    parser.add_argument("--skip-github", action="store_true", help="Skip GitHub fetch")
    args = parser.parse_args()

    checklist = WorkflowChecklist()

    # Fetch Linear tickets
    if not args.skip_linear:
        linear_key = os.environ.get("LINEAR_API_KEY")
        if linear_key:
            print("Fetching Linear tickets...", file=sys.stderr)
            checklist.linear_tickets = fetch_linear_tickets(linear_key)
            print(f"  Found {len(checklist.linear_tickets)} tickets", file=sys.stderr)
        else:
            print("LINEAR_API_KEY not set, skipping Linear", file=sys.stderr)

    # Fetch GitHub PRs
    if not args.skip_github:
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            print(f"Fetching GitHub PRs for {args.github_user}...", file=sys.stderr)
            checklist.ready_prs, checklist.draft_prs = fetch_github_prs(
                args.github_user
            )
            print(
                f"  Found {len(checklist.ready_prs)} ready, "
                f"{len(checklist.draft_prs)} draft",
                file=sys.stderr,
            )
        else:
            print("GITHUB_TOKEN not set, skipping GitHub", file=sys.stderr)

    # Output
    if args.output == "json":
        print(checklist.to_json())
    else:
        print(checklist.to_markdown())


if __name__ == "__main__":
    main()
