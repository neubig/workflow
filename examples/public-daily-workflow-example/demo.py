#!/usr/bin/env python3
"""Public, fixture-backed daily-workflow demo.

The program intentionally displays only allowlisted fields from public OpenHands
GitHub records and a synthetic Slack fixture. It performs no remote mutations.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "data" / "intake.json"
PRIORITIES = {"Urgent", "High", "Medium", "Low"}
GITHUB_TYPES = {"issue": "issues", "pull_request": "pull"}
SENSITIVE_PATTERNS = (
    re.compile(r"(?:github_pat_|gh[opsu]_|xox[baprs]-)[A-Za-z0-9_-]{8,}"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"https://[^\s/]*slack\.com/archives/", re.IGNORECASE),
)


class DataBoundaryError(ValueError):
    """Raised when demo input crosses the public-data boundary."""


def load_bundle(path: Path = DEFAULT_DATA) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        bundle = json.load(stream)
    validate_bundle(bundle)
    return bundle


def _all_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _all_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_strings(child)


def _validate_priority(item: dict[str, Any]) -> None:
    if item.get("priority") not in PRIORITIES:
        raise DataBoundaryError(f"{item.get('id')}: invalid priority")
    score = item.get("priority_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise DataBoundaryError(f"{item.get('id')}: priority_score must be 0..100")
    if not item.get("triage_rationale"):
        raise DataBoundaryError(f"{item.get('id')}: triage rationale is required")


def _validate_github_item(item: dict[str, Any]) -> None:
    item_type = item.get("type")
    if item_type not in GITHUB_TYPES:
        raise DataBoundaryError(f"{item.get('id')}: unsupported GitHub type")

    repository = item.get("repository", "")
    parts = repository.split("/")
    if len(parts) != 2 or parts[0] != "OpenHands" or not parts[1]:
        raise DataBoundaryError(f"{item.get('id')}: repository must be OpenHands/*")

    number = item.get("number")
    if not isinstance(number, int) or number <= 0:
        raise DataBoundaryError(f"{item.get('id')}: invalid GitHub number")

    source_url = item.get("source_url", "")
    parsed = urlparse(source_url)
    expected_kind = GITHUB_TYPES[item_type]
    expected_path = f"/OpenHands/{parts[1]}/{expected_kind}/{number}"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise DataBoundaryError(f"{item.get('id')}: source URL is outside the allowlist")

    if not item.get("title") or item.get("state") not in {"open", "closed"}:
        raise DataBoundaryError(f"{item.get('id')}: snapshot title/state is required")
    if not isinstance(item.get("labels"), list):
        raise DataBoundaryError(f"{item.get('id')}: labels must be a list")
    _validate_priority(item)


def _validate_slack_item(item: dict[str, Any]) -> None:
    disclosure = item.get("disclosure", {})
    item_type = item.get("type")

    if item_type == "slack_fixture":
        if not item.get("display_text", "").startswith("[SYNTHETIC FIXTURE]"):
            raise DataBoundaryError(f"{item.get('id')}: fixture must be visibly labeled")
        if disclosure != {
            "status": "synthetic_fixture",
            "approved_for_public_demo": True,
            "contains_real_slack_content": False,
        }:
            raise DataBoundaryError(f"{item.get('id')}: invalid fixture disclosure gate")
        if not item.get("source_ref", "").startswith("fixture://"):
            raise DataBoundaryError(f"{item.get('id')}: invalid fixture reference")
    elif item_type == "slack":
        required = {
            "status": "approved_public",
            "approved_for_public_demo": True,
            "contains_real_slack_content": True,
        }
        if any(disclosure.get(key) != value for key, value in required.items()):
            raise DataBoundaryError(f"{item.get('id')}: real Slack input lacks approval")
        if not disclosure.get("approval_reference") or not disclosure.get("reviewed_on"):
            raise DataBoundaryError(f"{item.get('id')}: approval evidence is required")
        if not item.get("source_ref", "").startswith("slack-safe://OpenHands/"):
            raise DataBoundaryError(f"{item.get('id')}: use a disclosure-safe reference")
    else:
        raise DataBoundaryError(f"{item.get('id')}: unsupported Slack type")

    if not item.get("display_text") or not item.get("channel_reference"):
        raise DataBoundaryError(f"{item.get('id')}: Slack display fields are required")
    _validate_priority(item)


def validate_bundle(bundle: dict[str, Any]) -> None:
    if bundle.get("schema_version") != 1:
        raise DataBoundaryError("unsupported schema version")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", bundle.get("snapshot_date", "")):
        raise DataBoundaryError("snapshot_date must use YYYY-MM-DD")

    github = bundle.get("github")
    slack = bundle.get("slack")
    if not isinstance(github, list) or not github:
        raise DataBoundaryError("at least one GitHub item is required")
    if not isinstance(slack, list) or not slack:
        raise DataBoundaryError("at least one Slack item is required")

    ids: set[str] = set()
    for item in github:
        _validate_github_item(item)
        if not item.get("id") or item["id"] in ids:
            raise DataBoundaryError("every item needs a unique id")
        ids.add(item["id"])
    for item in slack:
        _validate_slack_item(item)
        if not item.get("id") or item["id"] in ids:
            raise DataBoundaryError("every item needs a unique id")
        ids.add(item["id"])

    for value in _all_strings(bundle):
        if any(pattern.search(value) for pattern in SENSITIVE_PATTERNS):
            raise DataBoundaryError("input contains a forbidden credential/identity pattern")


def _github_api(path: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "public-daily-workflow-example",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def verify_public_github(bundle: dict[str, Any]) -> list[str]:
    """Verify live existence, ownership, visibility, and URL; tolerate snapshot drift."""
    results: list[str] = []
    repositories: dict[str, dict[str, Any]] = {}
    for item in bundle["github"]:
        repository = item["repository"]
        if repository not in repositories:
            repositories[repository] = _github_api(f"/repos/{repository}")
        repo_data = repositories[repository]
        if repo_data.get("private") is not False:
            raise DataBoundaryError(f"{repository}: repository is not public")
        if repo_data.get("owner", {}).get("login") != "OpenHands":
            raise DataBoundaryError(f"{repository}: owner is not OpenHands")

        endpoint = "issues" if item["type"] == "issue" else "pulls"
        live = _github_api(f"/repos/{repository}/{endpoint}/{item['number']}")
        if live.get("html_url") != item["source_url"]:
            raise DataBoundaryError(f"{item['id']}: live URL does not match source map")
        drift = []
        if live.get("title") != item["title"]:
            drift.append("title")
        if live.get("state") != item["state"]:
            drift.append("state")
        suffix = f"; snapshot drift: {', '.join(drift)}" if drift else ""
        results.append(f"{item['id']}: public OpenHands source verified{suffix}")
    return results


class Demo:
    def __init__(self, bundle: dict[str, Any], answers: list[str], pace: float, live: bool):
        self.bundle = bundle
        self.answers = answers
        self.pace = pace
        self.live = live
        self.live_results: list[str] = []
        self.decisions: list[dict[str, str]] = []

    def say(self, text: str = "") -> None:
        print(text, flush=True)
        if self.pace:
            time.sleep(self.pace)

    def ask(self, prompt: str) -> str:
        print(prompt, end="", flush=True)
        if self.answers:
            answer = self.answers.pop(0)
            print(answer, flush=True)
            if self.pace:
                time.sleep(self.pace)
            return answer.strip()
        return input().strip()

    def run(self) -> dict[str, Any]:
        self.say("PUBLIC DAILY WORKFLOW — HUMAN-IN-THE-LOOP REPLAY")
        self.say("Boundary: public OpenHands GitHub + disclosure-safe Slack only")
        self.say("Remote mutations: disabled")
        if self.answers:
            self.say("Replay mode: recorded human choices are echoed; omit --answers for live input.")
        self.say()

        self.say("[1/5] Privacy gate")
        self.say("PASS  Local schema and credential/identity-pattern checks")
        if self.live:
            self.say("Running live GitHub visibility checks...")
            self.live_results = verify_public_github(self.bundle)
            for result in self.live_results:
                self.say(f"PASS  {result}")
        else:
            self.say("NOTE  Live GitHub verification skipped (use --verify-live)")
        fixture_count = sum(item["type"] == "slack_fixture" for item in self.bundle["slack"])
        self.say(f"PASS  Slack gate: {fixture_count} visibly labeled synthetic fixture(s)")
        if self.ask("Human: approve sanitized intake for triage? [y/N] ").lower() != "y":
            raise RuntimeError("human rejected intake")
        self.decisions.append({"checkpoint": "intake", "decision": "approved"})
        self.say()

        self.say("[2/5] Priority-aware intake")
        items = sorted(self.bundle["github"] + self.bundle["slack"], key=lambda x: -x["priority_score"])
        for index, item in enumerate(items, 1):
            if item["type"] in GITHUB_TYPES:
                kind = "GitHub PR" if item["type"] == "pull_request" else "GitHub issue"
                source = item["source_url"]
                title = item["title"]
            else:
                kind = "Slack fixture"
                source = item["source_ref"]
                title = item["display_text"]
            self.say(f"{index}. [{item['priority']} / {item['priority_score']}] {kind}")
            self.say(f"   {title}")
            self.say(f"   source: {source}")

        recommendation = items[0]
        self.say()
        self.say(f"Agent recommendation: #{1} — {recommendation['triage_rationale']}")
        choice = self.ask("Human: [a]pprove recommendation or [r]edirect? ").lower()
        if choice == "r":
            selected_text = self.ask(f"Human: choose item [1-{len(items)}]: ")
            if not selected_text.isdigit() or not 1 <= int(selected_text) <= len(items):
                raise RuntimeError("invalid redirect selection")
            selected = items[int(selected_text) - 1]
            self.say("CORRECTION  Human context overrides the score-only recommendation.")
            self.decisions.append({"checkpoint": "priority", "decision": f"redirected to {selected['id']}"})
        elif choice == "a":
            selected = recommendation
            self.decisions.append({"checkpoint": "priority", "decision": f"approved {selected['id']}"})
        else:
            raise RuntimeError("human stopped at priority decision")
        self.say()

        self.say("[3/5] Consequential action approval")
        self.say(f"Selected: {selected['id']}")
        self.say("Proposed action: prepare a read-only execution/evidence checklist; mutate no remote item.")
        if self.ask("Human: approve this bounded action? [y/N] ").lower() != "y":
            raise RuntimeError("human rejected action")
        self.decisions.append({"checkpoint": "execution", "decision": "approved read-only action"})
        selected_source = selected.get("source_url", selected.get("source_ref"))
        self.say("AGENT EXECUTION  Evidence checklist prepared")
        self.say(f"- inspect selected source: {selected_source}")
        self.say("- preserve the human redirect in the decision record")
        self.say("- require live public-source and disclosure-label evidence")
        self.say("DONE  External writes = 0")
        self.say()

        self.say("[4/5] Evidence review")
        self.say(f"Evidence: {len(self.bundle['github'])}/{len(self.bundle['github'])} GitHub records passed the local allowlist")
        if self.live:
            self.say(f"Evidence: {len(self.live_results)}/{len(self.bundle['github'])} GitHub records verified live as public")
        self.say(f"Evidence: Slack input is synthetic ({fixture_count}/{len(self.bundle['slack'])})")
        publish_real = self.ask("Human: publish this as a real-Slack demo? [y/N] ").lower()
        if publish_real == "y" and fixture_count:
            self.say("RECOVERY  Policy guard refused: synthetic input cannot be presented as real Slack.")
            self.decisions.append({"checkpoint": "evidence", "decision": "unsafe label blocked"})
        elif publish_real != "y" and fixture_count:
            self.say("RECOVERY  Evidence rejected for a real-Slack claim; relabeling fixture-backed.")
            self.decisions.append({"checkpoint": "evidence", "decision": "real-Slack claim rejected"})
        else:
            self.decisions.append({"checkpoint": "evidence", "decision": "approved"})

        if fixture_count:
            if self.ask("Human: approve the corrected fixture-backed evidence package? [y/N] ").lower() != "y":
                raise RuntimeError("human rejected corrected evidence")
            self.decisions.append({"checkpoint": "recovery", "decision": "fixture-backed package approved"})
        self.say()

        self.say("[5/5] Result")
        self.say("PASS  Publishable as a clearly labeled fixture-backed development replay")
        if fixture_count:
            self.say("BLOCKER  A real-Slack recording still requires an authorized disclosure-safe source.")
        self.say("PASS  Human inspection, redirect, action approval, evidence review, and recovery are recorded")
        return {
            "result": "fixture-backed" if fixture_count else "disclosure-approved",
            "selected_item": selected["id"],
            "external_writes": 0,
            "decisions": self.decisions,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verify-live", action="store_true")
    parser.add_argument("--answers", help="comma-separated replay answers")
    parser.add_argument("--pace", type=float, default=0.0, help="seconds between display steps")
    parser.add_argument("--report", type=Path, help="optional local-only JSON decision report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        bundle = load_bundle(args.data)
        if args.validate_only:
            print(f"PASS: {args.data} satisfies the public-data boundary")
            if args.verify_live:
                for result in verify_public_github(bundle):
                    print(f"PASS: {result}")
            return 0
        answers = args.answers.split(",") if args.answers else []
        report = Demo(bundle, answers, args.pace, args.verify_live).run()
        if args.report:
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(f"Local decision report: {args.report}")
        return 0
    except (DataBoundaryError, RuntimeError, urllib.error.URLError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
