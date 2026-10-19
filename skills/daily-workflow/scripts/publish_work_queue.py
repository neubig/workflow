"""Publish a prepared snapshot to an installed, snapshot-backed Canvas app."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlparse


SECTIONS = ("review", "align", "slack", "linear", "actions")
PREFIX = "const DATA = "


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Snapshot must be an object")
    for name in ("generated", "source", "today", "githubUser"):
        if not isinstance(data.get(name), str) or not data[name]:
            raise ValueError(f"Missing snapshot metadata: {name}")
    for name in SECTIONS:
        if not isinstance(data.get(name), list):
            raise ValueError(f"Missing snapshot section: {name}")
    fields = {
        "review": ("pr", "author", "ci", "review", "action", "reviewRequested", "liveState"),
        "align": ("pr", "issue", "assigned", "linear", "action"),
        "slack": ("source", "ticket", "destination", "reason", "awaiting"),
        "linear": ("id", "title", "url", "priority", "priorityNum", "workspace", "pr", "ci", "review", "evidence", "context"),
        "actions": ("item", "needed"),
    }
    links = {"review": ("pr",), "align": ("pr", "issue", "linear"), "slack": ("source",), "linear": ("pr",), "actions": ("item",)}
    for section in SECTIONS:
        for row in data[section]:
            if not isinstance(row, dict) or any(key not in row for key in fields[section]):
                raise ValueError(f"Invalid row in {section}")
            for key in links[section]:
                value = row[key]
                if not isinstance(value, dict) or not isinstance(value.get("label"), str) or "url" not in value:
                    raise ValueError(f"Invalid link: {section}.{key}")
            if section == "review" and (row["reviewRequested"] is not True or row["liveState"] != "OPEN"):
                raise ValueError("Review queue must contain only open, still-requested PRs")

    recommendations = data.get("recommendations", {})
    if not isinstance(recommendations, dict):
        raise ValueError("Recommendations must be a URL-keyed object")
    for url, recommendation in recommendations.items():
        if urlparse(url).scheme != "https" or not urlparse(url).netloc:
            raise ValueError("Recommendation target must be an HTTPS URL")
        if not isinstance(recommendation, dict) or any(
            not isinstance(recommendation.get(key), str) or not recommendation[key].strip()
            for key in ("summary", "rationale", "assessedAt")
        ):
            raise ValueError("Invalid recommendation")
        refs = recommendation.get("links", [])
        if not isinstance(refs, list):
            raise ValueError("Recommendation links must be an array")
        for ref in refs:
            if (not isinstance(ref, dict) or not isinstance(ref.get("label"), str)
                    or not isinstance(ref.get("url"), str)
                    or urlparse(ref["url"]).scheme != "https" or not urlparse(ref["url"]).netloc):
                raise ValueError("Invalid recommendation evidence link")


def embedded(source):
    if not source.startswith(PREFIX):
        raise ValueError("Unsupported app bundle; expected leading const DATA assignment")
    data, end = json.JSONDecoder().raw_decode(source[len(PREFIX):])
    suffix = source[len(PREFIX) + end:]
    if not suffix.startswith(";"):
        raise ValueError("Unsupported app bundle; missing DATA terminator")
    return data, suffix


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".work-queue-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def publish(app_dir, data, check_only=False):
    validate(data)
    bundle = app_dir / "extension.js"
    snapshot = app_dir / "src" / "data.json"
    if not snapshot.parent.is_dir():
        raise ValueError("App src directory not found")
    _, suffix = embedded(bundle.read_text())
    encoded = json.dumps(data, ensure_ascii=True, indent=2)
    updated = PREFIX + encoded + suffix
    # Check the actual replacement module, without executing any app code.
    result = subprocess.run(["node", "--input-type=module", "--check"], input=updated, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f"Updated bundle did not parse: {result.stderr}")
    if check_only:
        return
    atomic_write(snapshot, encoded + "\n")
    atomic_write(bundle, updated)
    if json.loads(snapshot.read_text()) != data or embedded(bundle.read_text())[0] != data:
        raise ValueError("Published snapshot read-back mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--app-dir", type=Path, required=True, help="Actual installed app path, not only its source checkout")
    parser.add_argument("--check", action="store_true", help="Validate without writing")
    args = parser.parse_args()
    data = json.loads(args.snapshot.read_text())
    publish(args.app_dir, data, args.check)
    print(json.dumps({"status": "validated" if args.check else "published", "app_dir": str(args.app_dir), "generated": data["generated"], "counts": {key: len(data[key]) for key in SECTIONS}}))


if __name__ == "__main__":
    main()
