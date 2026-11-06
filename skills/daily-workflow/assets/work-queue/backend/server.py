#!/usr/bin/env python3
"""Read-only managed Work Queue backend; requires host-provided python3."""

import argparse
import json
import os
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import threading
import time
import urllib.request


ENDPOINT = "https://api.linear.app/graphql"
ROOT = Path(__file__).resolve().parent
CLOSED = {"completed", "canceled", "duplicate"}
PRIORITIES = ("No priority", "Urgent", "High", "Medium", "Low")
QUERY = """
query WorkQueue($after: String) {
  organization { id name urlKey }
  viewer {
    assignedIssues(first: 10, after: $after, includeArchived: false,
      filter: {state: {type: {nin: ["completed", "canceled", "duplicate"]}}}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        id identifier title url priority archivedAt dueDate
        state { name type }
        cycle { startsAt endsAt name number }
        labels(first: 20) { nodes { name } pageInfo { hasNextPage endCursor } }
        inverseRelations(first: 20) {
          nodes { type issue { archivedAt state { type } } }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  }
}
"""


class Unavailable(Exception):
    pass


def connection(value):
    if not isinstance(value, dict) or not isinstance(value.get("nodes"), list):
        raise Unavailable()
    info = value.get("pageInfo")
    if not isinstance(info, dict) or type(info.get("hasNextPage")) is not bool:
        raise Unavailable()
    return value["nodes"], info


def complete_nodes(value):
    nodes, info = connection(value)
    if info["hasNextPage"]:
        raise Unavailable()
    return nodes


def day(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise Unavailable()
    try:
        if len(value) == 10:
            return date.fromisoformat(value).isoformat()
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        raise Unavailable() from None


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise Unavailable()
    return value


def row(node, workspace):
    state = text(node["state"]["type"])
    if node["archivedAt"] or state in CLOSED or state == "blocked":
        return None
    labels = complete_nodes(node["labels"])
    relations = complete_nodes(node["inverseRelations"])
    if any(text(label["name"]).strip().lower() == "blocked" for label in labels):
        return None
    # An inverse blocks edge points from its source issue (the blocker) to this issue.
    for rel in relations:
        if text(rel["type"]) == "blocks":
            blocker = rel["issue"]
            if not blocker["archivedAt"] and text(blocker["state"]["type"]) not in CLOSED:
                return None
    priority = node["priority"]
    if type(priority) is not int or not 0 <= priority <= 4:
        raise Unavailable()
    url = text(node["url"])
    if not re.fullmatch(r"https://linear\.app/[^\s]+", url):
        raise Unavailable()
    cycle = node["cycle"]
    cycle_end = day(cycle["endsAt"]) if cycle else ""
    if cycle:
        day(cycle["startsAt"])
    identifier = text(node["identifier"])
    return {
        "id": identifier, "identifier": identifier, "issueId": text(node["id"]),
        "title": text(node["title"]), "url": url, "workspace": workspace,
        "priorityNum": priority, "priority": PRIORITIES[priority],
        "due": day(node["dueDate"]), "cycleEnd": cycle_end,
        "pr": {"label": "Not fetched", "url": ""},
        "ci": "unknown — not fetched", "review": "Not verified",
        "evidence": "Not verified", "context": text(node["state"]["name"]),
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Unavailable()


class LinearClient:
    def __init__(self, keys, *, _endpoint=ENDPOINT, timeout=10, max_pages=100,
                 budget=150):
        # _endpoint is an internal local-HTTP test seam, not a CLI/env option.
        self.keys = tuple(dict.fromkeys(key.strip() for key in keys if key.strip()))
        self.endpoint = _endpoint
        self.timeout = timeout
        self.max_pages = max_pages
        self.budget = budget
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect())

    def fetch(self):
        if not self.keys:
            raise Unavailable()
        deadline = time.monotonic() + self.budget
        rows, sources = {}, {}
        try:
            for key in self.keys:
                after, seen, organization_id = None, set(), None
                for _ in range(self.max_pages):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise Unavailable()
                    request = urllib.request.Request(
                        self.endpoint,
                        data=json.dumps({"query": QUERY, "variables": {"after": after}}).encode(),
                        headers={"Content-Type": "application/json", "Authorization": key},
                        method="POST")
                    with self.opener.open(request, timeout=min(self.timeout, remaining)) as response:
                        payload = response.read(4 * 1024 * 1024 + 1)
                    if len(payload) > 4 * 1024 * 1024:
                        raise Unavailable()
                    result = json.loads(payload)
                    if result.get("errors"):
                        raise Unavailable()
                    data = result["data"]
                    org = data["organization"]
                    identity = {field: text(org[field]) for field in ("id", "name", "urlKey")}
                    if organization_id and organization_id != identity["id"]:
                        raise Unavailable()
                    organization_id = identity["id"]
                    sources[organization_id] = identity
                    nodes, info = connection(data["viewer"]["assignedIssues"])
                    for node in nodes:
                        item = row(node, identity["name"])
                        if item:
                            rows[(organization_id, item["issueId"])] = item
                    if not info["hasNextPage"]:
                        break
                    after = text(info.get("endCursor"))
                    if not nodes or after in seen:
                        raise Unavailable()
                    seen.add(after)
                else:
                    raise Unavailable()
            return {"issues": sorted(rows.values(), key=lambda r: (
                r["priorityNum"], min(filter(None, (r["due"], r["cycleEnd"])), default="9999"),
                r["workspace"], r["id"])), "sources": list(sources.values())}
        except Exception:
            # Upstream errors can contain credentials or private query data.
            raise Unavailable() from None


class WorkQueueServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, client, *, static_root=ROOT):
        self.client = client
        self.static_root = Path(static_root).resolve()
        self.fetch_lock = threading.Lock()
        super().__init__(address, Handler)

    def handle_error(self, request, client_address):
        pass


class Handler(BaseHTTPRequestHandler):
    server_version = "WorkQueue"
    sys_version = ""

    def log_message(self, *args):
        pass

    def reply(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self.reply(200, b'{"status":"ok"}')
        elif path == "/api/linear":
            if not self.server.fetch_lock.acquire(blocking=False):
                self.reply(503, b'{"error":"Linear refresh already running"}')
                return
            try:
                result = self.server.client.fetch()
                self.reply(200, json.dumps(result).encode())
            except Unavailable:
                self.reply(503, b'{"error":"Linear unavailable; no partial results returned"}')
            finally:
                self.server.fetch_lock.release()
        elif path in ("/", "/index.html", "/extension.js"):
            filename = "extension.js" if path == "/extension.js" else "index.html"
            file = self.server.static_root / filename
            if file.is_file() and not file.is_symlink():
                self.reply(200, file.read_bytes(),
                           "text/javascript; charset=utf-8" if filename.endswith(".js")
                           else "text/html; charset=utf-8")
            else:
                self.reply(404, b'{"error":"UI not packaged"}')
        else:
            self.reply(404, b'{"error":"Not found"}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1", "localhost"))
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    # No queue/credential persistence: data-dir is accepted for the managed launcher.
    server = WorkQueueServer((args.host, args.port),
                             LinearClient(os.environ.get("LINEAR_API_KEYS", "").split(",")))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
