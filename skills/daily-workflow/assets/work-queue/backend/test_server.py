import copy
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import socket
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from server import LinearClient, QUERY, WorkQueueServer


def connection(nodes, more=False, cursor=None):
    return {"nodes": nodes, "pageInfo": {"hasNextPage": more, "endCursor": cursor}}


def issue(identifier="EX-1", **changes):
    node = {
        "id": identifier, "identifier": identifier, "title": "Example ticket",
        "url": "https://linear.app/example/issue/" + identifier,
        "priority": 0, "archivedAt": None, "dueDate": None,
        "state": {"name": "Todo", "type": "unstarted"}, "cycle": None,
        "labels": connection([]), "inverseRelations": connection([]),
    }
    node.update(changes)
    return node


def page(nodes, more=False, cursor=None, org="example"):
    return {"data": {"organization": {"id": org, "name": org, "urlKey": org},
                     "viewer": {"assignedIssues": connection(nodes, more, cursor)}}}


@contextmanager
def running(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class Upstream(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.calls.append((self.headers["Authorization"], request))
        response = self.server.responses.pop(0)
        if isinstance(response, float):
            time.sleep(response)
            response = page([])
        if response == "redirect":
            self.send_response(302)
            self.send_header("Location", self.server.redirect)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        try:
            self.wfile.write(json.dumps(response).encode())
        except BrokenPipeError:
            pass


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        self.upstream.responses = []
        self.upstream.calls = []
        self.context = running(self.upstream)
        self.endpoint = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)

    def fetch_http(self, responses, keys=("test-key",), **options):
        self.upstream.responses = copy.deepcopy(responses)
        client = LinearClient(keys, _endpoint=self.endpoint, **options)
        with running(WorkQueueServer(("127.0.0.1", 0), client)) as base:
            try:
                response = urllib.request.urlopen(base + "/api/linear")
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, json.load(response)

    def test_pagination_workspaces_priority_dates_schema(self):
        cycle = {"startsAt": "2026-10-01T12:00:00Z", "endsAt": "2026-11-01T12:00:00Z",
                 "name": "Example", "number": 1}
        status, data = self.fetch_http([
            page([issue("EX-1", priority=1)], True, "next"),
            page([issue("EX-2", dueDate="2026-12-01", cycle=cycle)]),
            page([issue("EX-3", dueDate="2026-10-30T00:00:00Z")], org="other"),
        ], keys=(" test-key ", "other-key", "test-key"))
        self.assertEqual(status, 200)
        self.assertEqual([r["id"] for r in data["issues"]], ["EX-3", "EX-2", "EX-1"])
        self.assertEqual(len(data["sources"]), 2)
        self.assertEqual(data["issues"][1]["cycleEnd"], "2026-11-01")
        self.assertEqual(data["issues"][0]["due"], "2026-10-30")
        self.assertEqual(data["issues"][0]["priority"], "No priority")
        for row in data["issues"]:
            self.assertEqual(row["ci"], "unknown — not fetched")
            self.assertEqual(row["pr"]["url"], "")
        self.assertEqual([c[1]["variables"]["after"] for c in self.upstream.calls],
                         [None, "next", None])
        self.assertNotIn("test-key", json.dumps(data))
        self.assertIn("issue { archivedAt state { type } }", QUERY)
        self.assertNotIn("mutation", QUERY)

    def test_blocker_direction_closed_archived_and_label_filters(self):
        def relation(state, archived=None):
            return connection([{"type": "blocks", "issue": {
                "archivedAt": archived, "state": {"type": state}}}])
        nodes = [issue("ACTIVE", inverseRelations=relation("started")),
                 issue("DONE", inverseRelations=relation("completed")),
                 issue("CANCELED", inverseRelations=relation("canceled")),
                 issue("OLD", inverseRelations=relation("started", "2026-01-01")),
                 issue("LABEL", labels=connection([{"name": " Blocked "}])),
                 issue("ARCHIVED", archivedAt="2026-01-01"),
                 issue("CLOSED", state={"name": "Done", "type": "completed"}),
                 issue("BLOCKED", state={"name": "Blocked", "type": "blocked"}),
                 issue("RELATED", inverseRelations=connection([{"type": "related"}]))]
        status, data = self.fetch_http([page(nodes)])
        self.assertEqual(status, 200)
        self.assertEqual({r["id"] for r in data["issues"]},
                         {"DONE", "CANCELED", "OLD", "RELATED"})

    def test_fail_closed_incomplete_or_invalid_responses(self):
        variants = [
            {"errors": [{"message": "test-key must never escape"}]}, {"data": None},
            page([issue(labels=connection([], True, "more"))]),
            page([issue(inverseRelations=connection([], True, "more"))]),
            page([issue(inverseRelations=connection([{"type": "blocks", "issue": None}]))]),
            page([issue(priority=True)]), page([issue(dueDate="bad-date")]),
            page([issue(url="javascript:alert(1)")]),
            page([issue()], True, None), page([], True, "more"),
        ]
        bad_info = page([])
        del bad_info["data"]["viewer"]["assignedIssues"]["pageInfo"]
        variants.append(bad_info)
        for response in variants:
            with self.subTest(response=response):
                status, data = self.fetch_http([response])
                self.assertEqual(status, 503)
                self.assertNotIn("issues", data)
                self.assertNotIn("test-key", json.dumps(data))

    def test_no_partial_results_later_page_key_or_cursor_failure(self):
        for responses, keys in [
            ([page([issue()], True, "next"), {"errors": ["private"]}], ("a",)),
            ([page([issue()]), {"errors": ["private"]}], ("a", "b")),
            ([page([issue()], True, "same"), page([issue()], True, "same")], ("a",)),
            ([page([issue()], True, "next"), page([], org="changed")], ("a",)),
        ]:
            self.assertEqual(self.fetch_http(responses, keys=keys)[0], 503)

    def test_limits_missing_keys_timeout_redirect(self):
        self.assertEqual(self.fetch_http([], keys=())[0], 503)
        self.assertEqual(self.fetch_http([page([issue()], True, "next")], max_pages=1)[0], 503)
        self.assertEqual(self.fetch_http([], budget=0)[0], 503)
        self.assertEqual(self.fetch_http([0.15], timeout=0.02)[0], 503)
        self.upstream.redirect = self.endpoint + "/must-not-follow"
        before = len(self.upstream.calls)
        self.assertEqual(self.fetch_http(["redirect"])[0], 503)
        self.assertEqual(len(self.upstream.calls), before + 1)

    def test_health_static_allowlist_and_no_cors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text("<main>Example</main>")
            (root / "extension.js").write_text("export const example = true;")
            (root / "private.txt").write_text("not served")
            server = WorkQueueServer(("127.0.0.1", 0), LinearClient([]), static_root=root)
            with running(server) as base:
                for path in ("/health", "/", "/extension.js"):
                    with urllib.request.urlopen(base + path) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers["Cache-Control"], "no-store")
                        self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))
                for path in ("/private.txt", "/../server.py", "/server.py", "/%2e%2e/private.txt"):
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(base + path)
                    self.assertEqual(error.exception.code, 404)
                (root / "extension.js").unlink()
                (root / "extension.js").symlink_to(root / "private.txt")
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(base + "/extension.js")

    def test_busy_refresh_does_not_block_health(self):
        server = WorkQueueServer(("127.0.0.1", 0), LinearClient([]))
        server.fetch_lock.acquire()
        with running(server) as base:
            with urllib.request.urlopen(base + "/health") as response:
                self.assertEqual(response.status, 200)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + "/api/linear")
            self.assertEqual(error.exception.code, 503)
        server.fetch_lock.release()

    def test_same_workspace_keys_deduplicate(self):
        status, data = self.fetch_http([page([issue()]), page([issue()])], keys=("a", "b"))
        self.assertEqual(status, 200)
        self.assertEqual(len(data["issues"]), 1)
        self.assertEqual(len(data["sources"]), 1)

    def test_executable_cli_without_credentials(self):
        root = Path(__file__).resolve().parent
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.Popen([
                str(root / "server.py"), "--host=127.0.0.1", "--port=" + str(port),
                "--data-dir=" + directory,
            ], env={"PATH": os.environ["PATH"]}, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen("http://127.0.0.1:" + str(port) + "/health",
                                                    timeout=0.1) as response:
                            self.assertEqual(json.load(response), {"status": "ok"})
                        break
                    except urllib.error.URLError:
                        if process.poll() is not None:
                            self.fail("CLI terminated unexpectedly")
                        time.sleep(0.02)
                else:
                    self.fail("CLI failed to start")
                self.assertEqual(list(Path(directory).iterdir()), [])
            finally:
                process.terminate()
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(stdout, b"")
                self.assertEqual(stderr, b"")

    def test_build_reproducible_and_executable(self):
        root = Path(__file__).resolve().parent
        command = [sys.executable, str(root / "build-backend.py")]
        subprocess.run(command, check=True, capture_output=True)
        first = (root / "linux-amd64.tar.gz").read_bytes()
        subprocess.run(command, check=True, capture_output=True)
        self.assertEqual(first, (root / "linux-amd64.tar.gz").read_bytes())
        self.assertEqual(first, (root / "linux-arm64.tar.gz").read_bytes())
        with tarfile.open(fileobj=io.BytesIO(first), mode="r:gz") as archive:
            member = archive.getmember("server.py")
            self.assertEqual(member.mode, 0o755)
            self.assertTrue(archive.extractfile(member).read().startswith(b"#!/usr/bin/env python3\n"))
            self.assertNotIn("test_server.py", archive.getnames())


if __name__ == "__main__":
    unittest.main()
