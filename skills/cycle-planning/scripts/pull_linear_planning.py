#!/usr/bin/env python3
"""Pull incomplete planning data from all configured Linear connections.

Examples:
  LINEAR_API_KEYS=key1,key2 python3 pull_linear_planning.py
  ... pull_linear_planning.py --team 'OSS Team' --label oss-release

The JSON snapshot is intended to remain local. Credentials are never printed.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

API_URL = "https://api.linear.app/graphql"
ISSUES_QUERY = '''
query PlanningIssues($after: String) {
  issues(first: 100, after: $after, filter: {state: {type: {nin: ["completed", "canceled", "duplicate"]}}}) {
    nodes {
      id identifier title description url priority priorityLabel dueDate createdAt updatedAt
      state { id name type }
      team { id name key }
      cycle { id number name startsAt endsAt }
      project { id name url }
      assignee { id name email }
      labels { nodes { id name } }
      parent { id identifier title url }
      relations { nodes { type relatedIssue { id identifier title url state { type } } } }
      inverseRelations { nodes { type relatedIssue { id identifier title url state { type } } } }
    }
    pageInfo { hasNextPage endCursor }
  }
}
'''
CYCLES_QUERY = '''
query PlanningCycles($after: String) {
  teams(first: 100, after: $after) {
    nodes { id name key cycles(first: 100) { nodes { id number name startsAt endsAt completedAt } } }
    pageInfo { hasNextPage endCursor }
  }
}
'''


def parse_keys(value: str | None) -> list[str]:
    """Parse and deduplicate comma-separated keys without logging them."""
    if not value:
        return []
    return list(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))


def graphql(api_key: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    if payload.get("errors"):
        raise RuntimeError("; ".join(str(error.get("message", "GraphQL error")) for error in payload["errors"]))
    return payload.get("data", {})


def paginate(api_key: str, query: str, root: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        connection = graphql(api_key, query, {"after": after}).get(root, {})
        nodes.extend(connection.get("nodes", []))
        page_info = connection.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            return nodes
        after = page_info.get("endCursor")
        if not after:
            raise RuntimeError(f"Linear returned no cursor for paginated {root}")


def fetch_connection(api_key: str) -> dict[str, Any]:
    return {"issues": paginate(api_key, ISSUES_QUERY, "issues"), "teams": paginate(api_key, CYCLES_QUERY, "teams")}


def matches(issue: dict[str, Any], teams: set[str], labels: set[str]) -> bool:
    team = issue.get("team") or {}
    issue_labels = {item.get("name", "").casefold() for item in (issue.get("labels") or {}).get("nodes", [])}
    return (
        (not teams or team.get("name", "").casefold() in teams or team.get("key", "").casefold() in teams)
        and (not labels or bool(issue_labels & labels))
    )


def merge(snapshots: list[dict[str, Any]], teams: set[str], labels: set[str]) -> dict[str, Any]:
    issues: dict[str, dict[str, Any]] = {}
    cycles: dict[str, dict[str, Any]] = {}
    for snapshot in snapshots:
        for issue in snapshot["issues"]:
            if matches(issue, teams, labels):
                issues.setdefault(issue["id"], issue)
        for team in snapshot["teams"]:
            for cycle in (team.get("cycles") or {}).get("nodes", []):
                item = dict(cycle)
                item["team"] = {key: team.get(key) for key in ("id", "name", "key")}
                cycles.setdefault(cycle["id"], item)
    return {
        "issues": sorted(issues.values(), key=lambda item: (item.get("team", {}).get("name", ""), item.get("identifier", ""))),
        "cycles": sorted(cycles.values(), key=lambda item: (item.get("startsAt") or "", item.get("team", {}).get("name", ""))),
        "connections": len(snapshots),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", action="append", default=[], help="Team name or key; repeatable")
    parser.add_argument("--label", action="append", default=[], help="Label; repeatable")
    parser.add_argument("--output", choices=("json", "pretty"), default="pretty")
    args = parser.parse_args()
    keys = parse_keys(os.environ.get("LINEAR_API_KEYS"))
    if not keys:
        parser.error("LINEAR_API_KEYS is not set or contains no keys")

    snapshots: list[dict[str, Any]] = []
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(keys)) as executor:
        for future in [executor.submit(fetch_connection, key) for key in keys]:
            try:
                snapshots.append(future.result())
            except (OSError, urllib.error.URLError, RuntimeError, ValueError) as error:
                failures += 1
                print(f"warning: one Linear connection failed: {error}", file=sys.stderr)
    if not snapshots:
        print("error: all Linear connections failed", file=sys.stderr)
        return 1
    result = merge(snapshots, {item.casefold() for item in args.team}, {item.casefold() for item in args.label})
    result["filters"] = {"teams": args.team, "labels": args.label, "incompleteOnly": True}
    result["failedConnections"] = failures
    print(json.dumps(result, indent=2 if args.output == "pretty" else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
