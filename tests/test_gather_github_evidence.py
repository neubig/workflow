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

    def test_human_tested_evidence_with_results_is_genuine(self):
        summary = MODULE.evidence_summary(
            "- [x] A human has tested this change\n\n"
            "## Evidence\nThe updated flow matched expectations."
        )

        self.assertTrue(summary["human_tested"])
        self.assertTrue(summary["likely_genuine"])


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
    def test_both_queues_are_collected_in_one_pipelined_report(self):
        review_pr = {
            "node_id": "PR_review",
            "number": 1,
            "title": "Review me",
            "html_url": "https://github.com/example/repo/pull/1",
            "state": "open",
            "draft": False,
            "created_at": "2026-07-17T01:00:00Z",
            "updated_at": "2026-07-18T01:00:00Z",
            "body": "",
            "repository_url": "https://api.github.com/repos/example/repo",
            "user": {"login": "contributor"},
        }
        authored_pr = {
            "node_id": "PR_authored",
            "number": 2,
            "title": "My change",
            "html_url": "https://github.com/example/repo/pull/2",
            "state": "open",
            "draft": True,
            "created_at": "2026-07-17T02:00:00Z",
            "updated_at": "2026-07-18T02:00:00Z",
            "body": "## Evidence\n$ run\noutput: success",
            "repository_url": "https://api.github.com/repos/example/repo",
            "user": {"login": "octocat"},
        }

        def search(query, _max_prs):
            item = review_pr if "review-requested" in query else authored_pr
            return 1, [item], 1

        def graphql(variables, query):
            nodes = [{"id": node_id} for node_id in variables["ids"]]
            data = {"nodes": nodes}
            if query == MODULE.REPORT_STATUS_QUERY:
                data.update(
                    {
                        "viewer": {"login": "octocat"},
                        "rateLimit": {"cost": 1, "remaining": 4990},
                    }
                )
            return {"data": data}

        with (
            mock.patch.object(MODULE, "run_search", side_effect=search) as run_search,
            mock.patch.object(MODULE, "run_graphql", side_effect=graphql) as run_graphql,
        ):
            snapshot = MODULE.gather("@me", "@me", 100, False, "report")

        self.assertEqual(run_search.call_count, 2)
        self.assertEqual(run_graphql.call_count, 6)
        self.assertEqual(snapshot["api_requests"], 8)
        self.assertEqual(snapshot["viewer"], "octocat")
        self.assertEqual(len(snapshot["prs_awaiting_review"]), 1)
        self.assertEqual(len(snapshot["authored_open_prs"]), 1)
        self.assertEqual(snapshot["warnings"], [])


if __name__ == "__main__":
    unittest.main()
