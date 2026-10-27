#!/usr/bin/env python3
"""Check read-only access to one or more Linear API connections.

The script performs a minimal ``viewer`` query for every configured key and
reports only connection status and the authenticated user's identity. Keys are
read from ``LINEAR_API_KEY`` or comma-separated ``LINEAR_API_KEYS`` and are
never included in output.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

LINEAR_API_URL = "https://api.linear.app/graphql"
VIEWER_QUERY = "query { viewer { id name email } }"


@dataclass(frozen=True)
class AccessResult:
    connection: int
    ok: bool
    status: int | None = None
    identity: str | None = None
    error: str | None = None


def parse_api_keys(single: str | None, multiple: str | None) -> list[str]:
    """Return non-empty, trimmed keys, preferring the singular variable."""
    value = single if single and single.strip() else multiple
    if not value:
        return []
    return list(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))


def check_key(api_key: str, connection: int, timeout: float) -> AccessResult:
    """Run the minimal viewer query for one key without exposing it."""
    payload = json.dumps({"query": VIEWER_QUERY}).encode("utf-8")
    request = urllib.request.Request(
        LINEAR_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
            "User-Agent": "daily-workflow-linear-access-check",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        return AccessResult(connection, False, exc.code, error=f"HTTP {exc.code}")
    except urllib.error.URLError as exc:
        return AccessResult(connection, False, error=f"network error: {exc.reason}")
    except TimeoutError:
        return AccessResult(connection, False, error="request timed out")
    except (json.JSONDecodeError, ValueError):
        return AccessResult(connection, False, error="invalid JSON response")
    except OSError as exc:
        return AccessResult(connection, False, error=f"request error: {exc}")

    errors = body.get("errors") or []
    viewer = body.get("data", {}).get("viewer") if isinstance(body.get("data"), dict) else None
    if errors or not isinstance(viewer, dict):
        message = errors[0].get("message", "GraphQL query failed") if errors else "viewer missing"
        return AccessResult(connection, False, status, error=message)

    identity = viewer.get("email") or viewer.get("name") or viewer.get("id") or "authenticated user"
    return AccessResult(connection, True, status, identity=identity)


def render(results: list[AccessResult], json_output: bool) -> str:
    if json_output:
        return json.dumps({"ok": all(result.ok for result in results), "connections": [asdict(result) for result in results]}, indent=2)
    lines = []
    for result in results:
        if result.ok:
            lines.append(f"connection {result.connection}: OK ({result.identity})")
        else:
            detail = f"{result.error} (HTTP {result.status})" if result.status and result.error else (result.error or "access denied")
            lines.append(f"connection {result.connection}: FAILED ({detail})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--timeout", type=float, default=15.0, help="request timeout in seconds (default: 15)")
    args = parser.parse_args(argv)

    keys = parse_api_keys(os.environ.get("LINEAR_API_KEY"), os.environ.get("LINEAR_API_KEYS"))
    if not keys:
        print("No Linear credentials found; set LINEAR_API_KEY or LINEAR_API_KEYS.", file=sys.stderr)
        return 2

    results = [check_key(key, index, args.timeout) for index, key in enumerate(keys, start=1)]
    print(render(results, args.json))
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
