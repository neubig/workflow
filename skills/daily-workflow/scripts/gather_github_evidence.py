#!/usr/bin/env python3
"""Gather GitHub evidence for the daily workflow in batched GraphQL reads."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_THREADS_QUERY = r"""
query($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on PullRequest {
      id
      reviewThreads(first: 50) {
        pageInfo { hasNextPage }
        nodes { id isResolved isOutdated path line startLine }
      }
      files(first: 100) {
        pageInfo { hasNextPage }
        nodes { path }
      }
    }
  }
}
"""


REPORT_ISSUES_QUERY = r"""
query($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on PullRequest {
      id
      closingIssuesReferences(first: 20) {
        pageInfo { hasNextPage }
        nodes {
          number
          title
          url
          state
          repository { nameWithOwner }
          assignees(first: 10) {
            pageInfo { hasNextPage }
            nodes { login }
          }
        }
      }
    }
  }
}
"""


REPORT_STATUS_QUERY = r"""
query($ids: [ID!]!) {
  viewer { login }
  rateLimit { cost remaining resetAt }
  nodes(ids: $ids) {
    ... on PullRequest {
      id
      baseRefName
      baseRefOid
      headRefName
      headRefOid
      mergeable
      mergeStateStatus
      reviewDecision
      headRepository { nameWithOwner }
      reviewRequests(first: 20) {
        pageInfo { hasNextPage }
        nodes {
          requestedReviewer {
            ... on User { login }
            ... on Team { name slug }
          }
        }
      }
      commits(last: 1) {
        nodes {
          commit {
            oid
            committedDate
            statusCheckRollup { state }
          }
        }
      }
      timelineItems(last: 1, itemTypes: [READY_FOR_REVIEW_EVENT]) {
        nodes { ... on ReadyForReviewEvent { createdAt } }
      }
    }
  }
}
"""


FULL_QUERY = r"""
query(
  $reviewQuery: String!
  $authoredQuery: String!
  $reviewCursor: String
  $authoredCursor: String
  $pageSize: Int!
) {
  viewer { login }
  rateLimit { cost remaining resetAt }
  reviewRequested: search(
    query: $reviewQuery
    type: ISSUE
    first: $pageSize
    after: $reviewCursor
  ) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes { ...PullRequestEvidence }
  }
  authored: search(
    query: $authoredQuery
    type: ISSUE
    first: $pageSize
    after: $authoredCursor
  ) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes { ...PullRequestEvidence }
  }
}

fragment PullRequestEvidence on PullRequest {
  id
  number
  title
  url
  state
  isDraft
  createdAt
  updatedAt
  body
  additions
  deletions
  changedFiles
  baseRefName
  baseRefOid
  headRefName
  headRefOid
  mergeable
  mergeStateStatus
  reviewDecision
  author { login }
  repository { nameWithOwner url }
  headRepository { nameWithOwner }
  reviewRequests(first: 20) {
    pageInfo { hasNextPage }
    nodes {
      requestedReviewer {
        ... on User { login }
        ... on Team { name slug }
      }
    }
  }
  latestReviews(first: 20) {
    pageInfo { hasNextPage }
    nodes {
      state
      body
      submittedAt
      author { login }
    }
  }
  comments(last: 10) {
    nodes {
      body
      createdAt
      url
      author { login }
    }
  }
  reviewThreads(first: 50) {
    pageInfo { hasNextPage }
    nodes {
      id
      isResolved
      isOutdated
      path
      line
      startLine
      comments(first: 10) {
        pageInfo { hasNextPage }
        nodes {
          body
          createdAt
          url
          author { login }
        }
      }
    }
  }
  closingIssuesReferences(first: 20) {
    pageInfo { hasNextPage }
    nodes {
      number
      title
      url
      state
      repository { nameWithOwner }
      assignees(first: 10) {
        pageInfo { hasNextPage }
        nodes { login }
      }
    }
  }
  files(first: 100) {
    pageInfo { hasNextPage }
    nodes { path additions deletions }
  }
  commits(last: 1) {
    nodes {
      commit {
        oid
        committedDate
        statusCheckRollup {
          state
          contexts(first: 100) {
            pageInfo { hasNextPage }
            nodes {
              __typename
              ... on CheckRun {
                name
                status
                conclusion
                detailsUrl
              }
              ... on StatusContext {
                context
                state
                targetUrl
              }
            }
          }
        }
      }
    }
  }
  timelineItems(last: 1, itemTypes: [READY_FOR_REVIEW_EVENT]) {
    nodes { ... on ReadyForReviewEvent { createdAt } }
  }
}
"""


FAILURE_VALUES = {
    "ACTION_REQUIRED",
    "CANCELLED",
    "ERROR",
    "FAILURE",
    "STARTUP_FAILURE",
    "TIMED_OUT",
}
PENDING_VALUES = {
    "EXPECTED",
    "IN_PROGRESS",
    "PENDING",
    "QUEUED",
    "REQUESTED",
    "WAITING",
}
PASS_VALUES = {"SUCCESS"}
SKIP_VALUES = {"NEUTRAL", "SKIPPED", "STALE"}

ISSUE_URL_RE = re.compile(
    r"https://github\.com/([^/\s)]+/[^/\s)]+)/issues/(\d+)", re.I
)
PR_URL_RE = re.compile(
    r"https://github\.com/([^/\s)]+/[^/\s)]+)/pull/(\d+)", re.I
)
LINEAR_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")
EVIDENCE_HEADING_RE = re.compile(
    r"(?im)^#{1,3}\s+(?:live(?:[- ]code)?\s+)?evidence"
    r"(?:\s*[:\-\u2013\u2014].*)?\s*#*\s*$"
)
HUMAN_CHECK_RE = re.compile(
    r"(?im)^\s*-\s*\[([ xX])\]\s*A human has tested"
)
RUNTIME_SIGNAL_RE = re.compile(
    r"(?i)\b(browser|curl|database|docker|endpoint|gif|http|live process|"
    r"production|rendered|runtime|screenshot|server|service|workflow dispatch)\b"
)
BLOCKED_EVIDENCE_RE = re.compile(
    r"(?i)\b(blocked|could not|manual verification|not run|not tested|pending manual|"
    r"unable to|unavailable)\b"
)
CONTENT_EXTENSIONS = {".md", ".rst", ".txt"}
CONTENT_PREFIXES = {"docs/", "skills/"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline the GitHub portion of the daily workflow with REST discovery "
            "and concurrent GraphQL detail reads. The collector is read-only."
        )
    )
    parser.add_argument(
        "--author", default="@me", help="GitHub login for authored PRs"
    )
    parser.add_argument(
        "--reviewer", default="@me", help="GitHub login for review requests"
    )
    parser.add_argument(
        "--max-prs",
        type=int,
        default=100,
        help="Maximum PRs per category (maximum 1000)",
    )
    parser.add_argument(
        "--format", choices=("json", "markdown"), default="json"
    )
    parser.add_argument(
        "--profile",
        choices=("report", "full"),
        default="report",
        help=(
            "report fetches only action-ranking context; full also fetches check, "
            "review, and comment details"
        ),
    )
    parser.add_argument(
        "--include-body", action="store_true", help="Include complete PR bodies"
    )
    parser.add_argument("--output", default="-", help="Output path, or - for stdout")
    return parser.parse_args()


def require_gh() -> None:
    if shutil.which("gh") is None:
        raise RuntimeError("gh is not installed")
    result = subprocess.run(
        ["gh", "auth", "status"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError("gh is not authenticated; run gh auth login")


def run_graphql(variables: dict[str, Any], query: str = FULL_QUERY) -> dict[str, Any]:
    command = ["gh", "api", "graphql", "-F", "query=@-"]
    for key, value in variables.items():
        if value is not None:
            if isinstance(value, list):
                for item in value:
                    command.extend(["-F", f"{key}[]={item}"])
            else:
                command.extend(["-F", f"{key}={value}"])
    result = subprocess.run(
        command,
        input=query,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message or "gh api graphql failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GitHub returned invalid JSON: {exc}") from exc
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], indent=2))
    return payload


def run_search(query: str, max_prs: int) -> tuple[int, list[dict[str, Any]], int]:
    """Fetch a PR search through REST, preserving bodies and GraphQL node IDs."""
    items: list[dict[str, Any]] = []
    total = 0
    requests = 0
    page = 1
    while len(items) < max_prs:
        page_size = min(100, max_prs - len(items))
        command = [
            "gh",
            "api",
            "-X",
            "GET",
            "/search/issues",
            "-f",
            f"q={query}",
            "-F",
            f"per_page={page_size}",
            "-F",
            f"page={page}",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(message or "GitHub PR search failed")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"GitHub search returned invalid JSON: {exc}") from exc
        requests += 1
        total = payload.get("total_count", total)
        page_items = payload.get("items") or []
        items.extend(page_items)
        if len(page_items) < page_size or len(items) >= total:
            break
        page += 1
    return total, items[:max_prs], requests


def normalize_search_item(item: dict[str, Any]) -> dict[str, Any]:
    repository_api_url = item.get("repository_url") or ""
    marker = "/repos/"
    repository = (
        repository_api_url.split(marker, 1)[1]
        if marker in repository_api_url
        else None
    )
    return {
        "id": item.get("node_id"),
        "number": item.get("number"),
        "title": item.get("title"),
        "url": item.get("html_url"),
        "state": str(item.get("state") or "").upper(),
        "isDraft": item.get("draft", False),
        "createdAt": item.get("created_at"),
        "updatedAt": item.get("updated_at"),
        "body": item.get("body") or "",
        "author": {"login": (item.get("user") or {}).get("login")},
        "repository": {
            "nameWithOwner": repository,
            "url": f"https://github.com/{repository}" if repository else None,
        },
    }


def requested_reviewer(node: dict[str, Any]) -> str | None:
    reviewer = node.get("requestedReviewer") or {}
    return reviewer.get("login") or reviewer.get("slug") or reviewer.get("name")


def compact_comment(node: dict[str, Any], limit: int = 800) -> dict[str, Any]:
    return {
        "author": (node.get("author") or {}).get("login"),
        "created_at": node.get("createdAt"),
        "url": node.get("url"),
        "body": (node.get("body") or "")[:limit],
    }


def summarize_checks(pr: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    commit_nodes = (pr.get("commits") or {}).get("nodes") or []
    commit = (commit_nodes[-1].get("commit") if commit_nodes else None) or {}
    rollup = commit.get("statusCheckRollup") or {}
    contexts = rollup.get("contexts") or {}
    if (contexts.get("pageInfo") or {}).get("hasNextPage"):
        warnings.append("checks truncated at 100")

    checks: list[dict[str, Any]] = []
    buckets: dict[str, list[dict[str, Any]]] = {
        "failing": [],
        "pending": [],
        "passing": [],
        "skipped": [],
    }
    for raw in contexts.get("nodes") or []:
        status = raw.get("status") or raw.get("state")
        conclusion = raw.get("conclusion") or raw.get("state")
        value = str(conclusion or status or "").upper()
        status_value = str(status or "").upper()
        if value in FAILURE_VALUES or status_value in FAILURE_VALUES:
            bucket = "failing"
        elif value in PENDING_VALUES or status_value in PENDING_VALUES or not value:
            bucket = "pending"
        elif value in PASS_VALUES:
            bucket = "passing"
        elif value in SKIP_VALUES:
            bucket = "skipped"
        else:
            bucket = "pending"
        item = {
            "name": raw.get("name") or raw.get("context") or "unnamed check",
            "type": raw.get("__typename"),
            "status": status,
            "conclusion": conclusion,
            "url": raw.get("detailsUrl") or raw.get("targetUrl"),
        }
        checks.append(item)
        buckets[bucket].append(item)

    rollup_state = str(rollup.get("state") or "").upper()
    if buckets["failing"] or (not checks and rollup_state in FAILURE_VALUES):
        summary = "failing"
    elif buckets["pending"] or (not checks and rollup_state in PENDING_VALUES):
        summary = "pending"
    elif checks or rollup_state in PASS_VALUES:
        summary = "passing"
    else:
        summary = "missing"
    return {
        "summary": summary,
        "rollup_state": rollup.get("state"),
        "total": len(checks),
        **buckets,
    }, warnings


def extract_evidence_section(body: str) -> tuple[bool, str]:
    match = EVIDENCE_HEADING_RE.search(body)
    if not match:
        return False, ""
    tail = body[match.end() :]
    next_heading = re.search(r"(?m)^#{1,3}\s+", tail)
    section = tail[: next_heading.start()] if next_heading else tail
    return True, section.strip()


def evidence_summary(body: str) -> dict[str, Any]:
    heading_present, section = extract_evidence_section(body)
    runtime_signals = sorted(
        {match.lower() for match in RUNTIME_SIGNAL_RE.findall(section)}
    )
    human_match = HUMAN_CHECK_RE.search(body)
    human_tested = (
        None if not human_match else human_match.group(1).lower() == "x"
    )
    lowered = section.lower()
    has_screenshot = "![" in section or "<img" in lowered
    has_prompt = bool(re.search(r"(?m)^\s*(?:\$|>)\s+\S", section))
    has_fenced_output = "```" in section and any(
        value in lowered for value in ("output:", "result:", "success", "passed", "✓", "✅")
    )
    blocked = bool(BLOCKED_EVIDENCE_RE.search(section))
    return {
        "heading_present": heading_present,
        "runtime_signals": runtime_signals,
        "has_screenshot": has_screenshot,
        "has_command_output": has_prompt or has_fenced_output,
        "blocked_or_incomplete": blocked,
        "likely_genuine": heading_present
        and not blocked
        and bool(
            runtime_signals
            or has_screenshot
            or has_prompt
            or has_fenced_output
            or (human_tested and section)
        ),
        "human_tested": human_tested,
        "section_excerpt": section[:1200],
    }


def likely_content_only(file_nodes: list[dict[str, Any]]) -> bool:
    paths = [node.get("path", "") for node in file_nodes]
    return bool(paths) and all(
        Path(path).suffix.lower() in CONTENT_EXTENSIONS
        or any(path.startswith(prefix) for prefix in CONTENT_PREFIXES)
        for path in paths
    )


def summarize_pr(
    pr: dict[str, Any], assignment_login: str, include_body: bool
) -> dict[str, Any]:
    body = pr.get("body") or ""
    warnings: list[str] = []
    checks, check_warnings = summarize_checks(pr)
    warnings.extend(check_warnings)

    review_threads = pr.get("reviewThreads") or {}
    if (review_threads.get("pageInfo") or {}).get("hasNextPage"):
        warnings.append("review threads truncated at 50")
    unresolved_threads = []
    for thread in review_threads.get("nodes") or []:
        comments = thread.get("comments") or {}
        if (comments.get("pageInfo") or {}).get("hasNextPage"):
            warnings.append(f"thread {thread.get('id')} comments truncated at 10")
        if not thread.get("isResolved") and not thread.get("isOutdated"):
            unresolved_threads.append(
                {
                    "id": thread.get("id"),
                    "path": thread.get("path"),
                    "line": thread.get("line"),
                    "start_line": thread.get("startLine"),
                    "comments": [
                        compact_comment(comment)
                        for comment in comments.get("nodes") or []
                    ],
                }
            )

    closing = pr.get("closingIssuesReferences") or {}
    if (closing.get("pageInfo") or {}).get("hasNextPage"):
        warnings.append("closing issues truncated at 20")
    closing_issues = []
    for issue in closing.get("nodes") or []:
        assignees = issue.get("assignees") or {}
        if (assignees.get("pageInfo") or {}).get("hasNextPage"):
            warnings.append(f"issue {issue.get('url')} assignees truncated at 10")
        logins = [node.get("login") for node in assignees.get("nodes") or []]
        closing_issues.append(
            {
                "repository": (issue.get("repository") or {}).get("nameWithOwner"),
                "number": issue.get("number"),
                "title": issue.get("title"),
                "url": issue.get("url"),
                "state": issue.get("state"),
                "assignees": logins,
                "assigned_to_target": assignment_login in logins,
            }
        )

    files = pr.get("files") or {}
    file_nodes = files.get("nodes") or []
    if (files.get("pageInfo") or {}).get("hasNextPage"):
        warnings.append("changed files truncated at 100")

    reviews = pr.get("latestReviews") or {}
    if (reviews.get("pageInfo") or {}).get("hasNextPage"):
        warnings.append("latest reviews truncated at 20")
    requests = pr.get("reviewRequests") or {}
    if (requests.get("pageInfo") or {}).get("hasNextPage"):
        warnings.append("review requests truncated at 20")

    evidence = evidence_summary(body)
    issue_urls = sorted(
        {f"{repo}#{number}" for repo, number in ISSUE_URL_RE.findall(body)}
    )
    pr_urls = sorted(
        {f"{repo}#{number}" for repo, number in PR_URL_RE.findall(body)}
    )
    remediation_reasons = []
    if pr.get("mergeable") == "CONFLICTING" or pr.get("mergeStateStatus") == "DIRTY":
        remediation_reasons.append("merge_conflict")
    if checks["summary"] == "failing":
        remediation_reasons.append("failing_ci")
    if unresolved_threads:
        remediation_reasons.append("unresolved_review_threads")
    if not evidence["heading_present"]:
        remediation_reasons.append("missing_live_evidence_declaration")
    elif not evidence["likely_genuine"]:
        remediation_reasons.append("live_evidence_needs_inspection")

    review_decision = pr.get("reviewDecision")
    if unresolved_threads or review_decision == "CHANGES_REQUESTED":
        review_summary = "changes requested"
    elif review_decision == "APPROVED":
        review_summary = "approved"
    elif review_decision == "REVIEW_REQUIRED":
        review_summary = "awaiting review"
    else:
        review_summary = "unknown"

    ready_nodes = (pr.get("timelineItems") or {}).get("nodes") or []
    ready_at = ready_nodes[-1].get("createdAt") if ready_nodes else None

    result = {
        "repository": (pr.get("repository") or {}).get("nameWithOwner"),
        "number": pr.get("number"),
        "title": pr.get("title"),
        "url": pr.get("url"),
        "state": pr.get("state"),
        "is_draft": pr.get("isDraft"),
        "author": (pr.get("author") or {}).get("login"),
        "created_at": pr.get("createdAt"),
        "updated_at": pr.get("updatedAt"),
        "ready_at": ready_at,
        "base_ref": pr.get("baseRefName"),
        "base_oid": pr.get("baseRefOid"),
        "head_ref": pr.get("headRefName"),
        "head_oid": pr.get("headRefOid"),
        "head_repository": (pr.get("headRepository") or {}).get("nameWithOwner"),
        "mergeable": pr.get("mergeable"),
        "merge_state_status": pr.get("mergeStateStatus"),
        "review_decision": review_decision,
        "review_summary": review_summary,
        "review_requests": [
            reviewer
            for reviewer in (
                requested_reviewer(node) for node in requests.get("nodes") or []
            )
            if reviewer
        ],
        "latest_reviews": [
            {
                "author": (review.get("author") or {}).get("login"),
                "state": review.get("state"),
                "submitted_at": review.get("submittedAt"),
                "body": (review.get("body") or "")[:800],
            }
            for review in reviews.get("nodes") or []
        ],
        "unresolved_review_threads": unresolved_threads,
        "recent_comments": [
            compact_comment(comment)
            for comment in (pr.get("comments") or {}).get("nodes") or []
        ],
        "ci": checks,
        "closing_issues": closing_issues,
        "issue_urls_in_body": issue_urls,
        "pr_urls_in_body": pr_urls,
        "linear_ids_in_body": sorted(set(LINEAR_RE.findall(body))),
        "has_issue_reference": bool(closing_issues or issue_urls),
        "closing_issues_assigned_to_target": bool(closing_issues)
        and all(issue["assigned_to_target"] for issue in closing_issues),
        "live_evidence": evidence,
        "content_only_likely": likely_content_only(file_nodes),
        "diff": {
            "additions": pr.get("additions"),
            "deletions": pr.get("deletions"),
            "changed_files": pr.get("changedFiles"),
            "files": file_nodes,
        },
        "remediation_candidate_reasons": remediation_reasons,
        "warnings": sorted(set(warnings)),
    }
    if include_body:
        result["body"] = body
    return result


def gather(
    author: str,
    reviewer: str,
    max_prs: int,
    include_body: bool,
    profile: str = "report",
) -> dict[str, Any]:
    page_size = min(100, max_prs)
    review_query = f"is:pr is:open review-requested:{reviewer} sort:updated-desc"
    authored_query = f"is:pr is:open author:{author} sort:updated-desc"
    review_cursor = authored_cursor = None
    review_done = authored_done = False
    review_raw: dict[str, dict[str, Any]] = {}
    authored_raw: dict[str, dict[str, Any]] = {}
    review_total = authored_total = 0
    viewer_login = ""
    rate_limit = None
    api_requests = 0
    global_warnings: set[str] = set()

    if profile == "report":
        queue_nodes: dict[str, list[dict[str, Any]]] = {}
        details_by_id: dict[str, dict[str, Any]] = {}
        report_queries = (
            REPORT_THREADS_QUERY,
            REPORT_ISSUES_QUERY,
            REPORT_STATUS_QUERY,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            search_futures = {
                executor.submit(run_search, review_query, max_prs): "review",
                executor.submit(run_search, authored_query, max_prs): "authored",
            }
            detail_futures: dict[concurrent.futures.Future[Any], bool] = {}
            for future in concurrent.futures.as_completed(search_futures):
                queue_name = search_futures[future]
                total, items, request_count = future.result()
                api_requests += request_count
                nodes = [normalize_search_item(item) for item in items]
                queue_nodes[queue_name] = nodes
                if queue_name == "review":
                    review_total = total
                else:
                    authored_total = total
                for node in nodes:
                    if node.get("id"):
                        details_by_id.setdefault(node["id"], {}).update(node)
                ids = [node["id"] for node in nodes if node.get("id")]
                for start in range(0, len(ids), 100):
                    variables = {"ids": ids[start : start + 100]}
                    for query in report_queries:
                        detail_futures[
                            executor.submit(run_graphql, variables, query)
                        ] = query == REPORT_STATUS_QUERY

            for future in concurrent.futures.as_completed(detail_futures):
                payload = future.result()
                api_requests += 1
                data = payload["data"]
                if detail_futures[future]:
                    viewer_login = data["viewer"]["login"]
                    rate_limit = data.get("rateLimit")
                for node in data.get("nodes") or []:
                    if node and node.get("id"):
                        details_by_id.setdefault(node["id"], {}).update(node)

        review_raw = {
            node["url"]: details_by_id[node["id"]]
            for node in queue_nodes.get("review", [])
            if node.get("url") and node.get("id") in details_by_id
        }
        authored_raw = {
            node["url"]: details_by_id[node["id"]]
            for node in queue_nodes.get("authored", [])
            if node.get("url") and node.get("id") in details_by_id
        }
    else:
        while not (review_done and authored_done):
            payload = run_graphql(
                {
                    "reviewQuery": review_query,
                    "authoredQuery": authored_query,
                    "reviewCursor": review_cursor,
                    "authoredCursor": authored_cursor,
                    "pageSize": page_size,
                },
                FULL_QUERY,
            )
            api_requests += 1
            data = payload["data"]
            viewer_login = data["viewer"]["login"]
            rate_limit = data.get("rateLimit")
            review_total = data["reviewRequested"].get("issueCount", review_total)
            authored_total = data["authored"].get("issueCount", authored_total)
            for key, target in (
                ("reviewRequested", review_raw),
                ("authored", authored_raw),
            ):
                for node in data[key].get("nodes") or []:
                    if node and node.get("url"):
                        target[node["url"]] = node

            review_page = data["reviewRequested"]["pageInfo"]
            authored_page = data["authored"]["pageInfo"]
            review_cursor = review_page.get("endCursor") or review_cursor
            authored_cursor = authored_page.get("endCursor") or authored_cursor
            review_done = (
                not review_page.get("hasNextPage") or len(review_raw) >= max_prs
            )
            authored_done = (
                not authored_page.get("hasNextPage") or len(authored_raw) >= max_prs
            )

    assignment_login = viewer_login if author == "@me" else author.lstrip("@")
    review_items = [
        summarize_pr(node, assignment_login, include_body)
        for node in list(review_raw.values())[:max_prs]
    ]
    authored_items = [
        summarize_pr(node, assignment_login, include_body)
        for node in list(authored_raw.values())[:max_prs]
    ]
    review_items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    authored_items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    warnings = global_warnings | {
        f"{item['repository']}#{item['number']}: {warning}"
        for item in review_items + authored_items
        for warning in item["warnings"]
    }
    if review_total > max_prs:
        warnings.add(f"review-requested results truncated at {max_prs} of {review_total}")
    if authored_total > max_prs:
        warnings.add(f"authored results truncated at {max_prs} of {authored_total}")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "viewer": viewer_login,
        "author_query": author,
        "reviewer_query": reviewer,
        "profile": profile,
        "api_requests": api_requests,
        "rate_limit": rate_limit,
        "prs_awaiting_review": review_items,
        "authored_open_prs": authored_items,
        "warnings": sorted(warnings),
        "notes": [
            "The report profile omits expensive detail; use --profile full or a targeted read before remediation.",
            "Live-evidence classification is heuristic; inspect the section before acting.",
            "Content-only and housekeeping exemptions require human judgment.",
            "Re-fetch a target PR before any mutation or recommendation.",
            "Linear and Slack are intentionally outside this GitHub-only snapshot.",
            "Keep generated reports local because they may contain private work data.",
        ],
    }


def markdown_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def issue_cell(pr: dict[str, Any]) -> str:
    if pr["closing_issues"]:
        return ", ".join(
            f"[#{issue['number']}]({issue['url']})" for issue in pr["closing_issues"]
        )
    if pr["issue_urls_in_body"]:
        return ", ".join(pr["issue_urls_in_body"])
    if pr["pr_urls_in_body"]:
        return "Upstream PR reference"
    return "Missing"


def render_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# Daily Workflow GitHub Snapshot",
        "",
        f"Generated: {snapshot['generated_at']}  ",
        f"Viewer: `{snapshot['viewer']}`  ",
        f"GitHub API requests: {snapshot['api_requests']}",
        "",
        "## PRs Awaiting Review",
        "",
        "| PR | Author | Draft | CI | Review | Threads | Merge |",
        "|---|---|---:|---|---|---:|---|",
    ]
    for pr in snapshot["prs_awaiting_review"]:
        lines.append(
            "| [{repo}#{number} — {title}]({url}) | {author} | {draft} | {ci} | "
            "{review} | {threads} | {merge} |".format(
                repo=markdown_escape(pr["repository"]),
                number=pr["number"],
                title=markdown_escape(pr["title"]),
                url=pr["url"],
                author=markdown_escape(pr["author"]),
                draft="Yes" if pr["is_draft"] else "No",
                ci=pr["ci"]["summary"],
                review=pr["review_summary"],
                threads=len(pr["unresolved_review_threads"]),
                merge=pr["mergeable"],
            )
        )
    if not snapshot["prs_awaiting_review"]:
        lines.append("| None |  |  |  |  |  |  |")

    lines.extend(
        [
            "",
            "## Authored Open PRs",
            "",
            "| PR | Draft | Merge | CI | Review | Threads | Issue | Evidence | Candidate reasons |",
            "|---|---:|---|---|---|---:|---|---|---|",
        ]
    )
    for pr in snapshot["authored_open_prs"]:
        evidence = pr["live_evidence"]
        if evidence["likely_genuine"]:
            evidence_cell = "Declared; live signals"
        elif evidence["heading_present"]:
            evidence_cell = "Declared; inspect manually"
        else:
            evidence_cell = "Missing declaration"
        lines.append(
            "| [{repo}#{number} — {title}]({url}) | {draft} | {merge} | {ci} | "
            "{review} | {threads} | {issue} | {evidence} | {reasons} |".format(
                repo=markdown_escape(pr["repository"]),
                number=pr["number"],
                title=markdown_escape(pr["title"]),
                url=pr["url"],
                draft="Yes" if pr["is_draft"] else "No",
                merge=pr["mergeable"],
                ci=pr["ci"]["summary"],
                review=pr["review_summary"],
                threads=len(pr["unresolved_review_threads"]),
                issue=issue_cell(pr),
                evidence=evidence_cell,
                reasons=", ".join(pr["remediation_candidate_reasons"]) or "None",
            )
        )
    if not snapshot["authored_open_prs"]:
        lines.append("| None |  |  |  |  |  |  |  |  |")
    if snapshot["warnings"]:
        lines.extend(["", "## Truncation Warnings", ""])
        lines.extend(f"- {warning}" for warning in snapshot["warnings"])
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in snapshot["notes"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    if not 1 <= args.max_prs <= 1000:
        print("error: --max-prs must be between 1 and 1000", file=sys.stderr)
        return 2
    try:
        require_gh()
        snapshot = gather(
            args.author,
            args.reviewer,
            args.max_prs,
            args.include_body,
            args.profile,
        )
    except (KeyError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = (
        render_markdown(snapshot)
        if args.format == "markdown"
        else json.dumps(snapshot, indent=2) + "\n"
    )
    if args.output == "-":
        sys.stdout.write(output)
    else:
        Path(args.output).write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
