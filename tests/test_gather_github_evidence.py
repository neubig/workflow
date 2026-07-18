import importlib.util
import pathlib
import unittest
from unittest import mock


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "skills"
    / "daily-workflow"
    / "scripts"
    / "gather_github_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("gather_github_evidence", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class EvidenceSummaryTests(unittest.TestCase):
    def test_empty_evidence_heading_is_declared_but_not_genuine(self):
        summary = MODULE.evidence_summary("## Evidence\n\n## Checklist\n- [ ] Done")

        self.assertTrue(summary["heading_present"])
        self.assertFalse(summary["likely_genuine"])

    def test_live_evidence_with_runtime_output_is_genuine(self):
        body = """## Live evidence — local server
```bash
$ curl http://localhost:8000/health
output: success
```
"""
        summary = MODULE.evidence_summary(body)

        self.assertTrue(summary["heading_present"])
        self.assertTrue(summary["has_command_output"])
        self.assertTrue(summary["likely_genuine"])

    def test_blocked_evidence_is_not_genuine(self):
        summary = MODULE.evidence_summary(
            "## Evidence\nBrowser verification is blocked pending credentials."
        )

        self.assertTrue(summary["blocked_or_incomplete"])
        self.assertFalse(summary["likely_genuine"])


class CheckSummaryTests(unittest.TestCase):
    def test_failure_takes_precedence_over_pending_checks(self):
        pr = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "state": "FAILURE",
                                "contexts": {
                                    "pageInfo": {"hasNextPage": False},
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "unit",
                                            "status": "COMPLETED",
                                            "conclusion": "FAILURE",
                                        },
                                        {
                                            "__typename": "CheckRun",
                                            "name": "integration",
                                            "status": "IN_PROGRESS",
                                            "conclusion": None,
                                        },
                                    ],
                                },
                            }
                        }
                    }
                ]
            }
        }

        summary, warnings = MODULE.summarize_checks(pr)

        self.assertEqual(summary["summary"], "failing")
        self.assertEqual([check["name"] for check in summary["failing"]], ["unit"])
        self.assertEqual(warnings, [])


class GatherTests(unittest.TestCase):
    def test_both_queues_are_collected_in_one_request(self):
        review_pr = {
            "number": 1,
            "title": "Review me",
            "url": "https://github.com/example/repo/pull/1",
            "updatedAt": "2026-07-18T01:00:00Z",
            "repository": {"nameWithOwner": "example/repo"},
            "author": {"login": "contributor"},
        }
        authored_pr = {
            "number": 2,
            "title": "My change",
            "url": "https://github.com/example/repo/pull/2",
            "updatedAt": "2026-07-18T02:00:00Z",
            "repository": {"nameWithOwner": "example/repo"},
            "author": {"login": "octocat"},
        }
        response = {
            "data": {
                "viewer": {"login": "octocat"},
                "rateLimit": {"cost": 10, "remaining": 4990},
                "reviewRequested": {
                    "issueCount": 1,
                    "pageInfo": {"hasNextPage": False, "endCursor": "review"},
                    "nodes": [review_pr],
                },
                "authored": {
                    "issueCount": 1,
                    "pageInfo": {"hasNextPage": False, "endCursor": "authored"},
                    "nodes": [authored_pr],
                },
            }
        }

        with mock.patch.object(MODULE, "run_graphql", return_value=response) as run:
            snapshot = MODULE.gather("@me", "@me", 100, False)

        run.assert_called_once()
        self.assertEqual(snapshot["api_requests"], 1)
        self.assertEqual(snapshot["viewer"], "octocat")
        self.assertEqual(len(snapshot["prs_awaiting_review"]), 1)
        self.assertEqual(len(snapshot["authored_open_prs"]), 1)
        self.assertEqual(snapshot["warnings"], [])


if __name__ == "__main__":
    unittest.main()
