import importlib.util
import pathlib
import unittest
from unittest import mock


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "skills"
    / "daily-workflow"
    / "scripts"
    / "daily-workflow-fetch.py"
)
SPEC = importlib.util.spec_from_file_location("daily_workflow_fetch", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class LinearTicketActionTests(unittest.TestCase):
    def test_ticket_with_linked_pull_request_points_to_github(self):
        ticket = MODULE.LinearTicket(
            identifier="ALL-1",
            title="Example",
            description="Tracked on GitHub",
            priority=2,
            priority_label="High",
            state="In Progress",
            state_type="started",
            url="https://linear.app/example/issue/ALL-1",
            external_links=[
                MODULE.ExternalLink(
                    title="PR: Example implementation",
                    url="https://github.com/OpenHands/example/pull/123",
                )
            ],
        )

        instructions = ticket.get_action_instructions()
        self.assertIn("Continue through linked GitHub PR(s) already in progress", instructions)
        self.assertIn("https://github.com/OpenHands/example/pull/123", instructions)
        self.assertNotIn("git clone", instructions)


class LinearTicketOrderingTests(unittest.TestCase):
    def make_ticket(self, identifier, priority, due_date):
        return MODULE.LinearTicket(
            identifier=identifier,
            title="Example",
            description="",
            priority=priority,
            priority_label="High" if priority == 2 else "Medium",
            state="Todo",
            state_type="unstarted",
            url=f"https://linear.app/example/issue/{identifier}",
            due_date=due_date,
        )

    def test_same_priority_uses_earlier_due_date_first(self):
        tickets = [
            self.make_ticket("ALL-3", 2, None),
            self.make_ticket("ALL-2", 2, "2026-08-11"),
            self.make_ticket("ALL-1", 2, "2026-07-20"),
            self.make_ticket("ALL-4", 3, "2026-07-01"),
        ]

        ordered = sorted(tickets, key=MODULE.linear_ticket_sort_key)

        self.assertEqual(
            [ticket.identifier for ticket in ordered],
            ["ALL-1", "ALL-2", "ALL-3", "ALL-4"],
        )


class LinearBlockedIssueTests(unittest.TestCase):
    def test_blocked_state_omits_issue(self):
        node = {
            "state": {"type": "blocked"},
            "labels": {"nodes": []},
            "inverseRelations": {"nodes": []},
        }

        self.assertTrue(MODULE.linear_node_is_blocked(node))

    def test_blocked_label_omits_issue(self):
        node = {
            "state": {"type": "unstarted"},
            "labels": {"nodes": [{"name": "Blocked"}]},
            "inverseRelations": {"nodes": []},
        }

        self.assertTrue(MODULE.linear_node_is_blocked(node))

    def test_active_blocker_omits_issue(self):
        node = {
            "state": {"type": "unstarted"},
            "labels": {"nodes": []},
            "inverseRelations": {
                "nodes": [
                    {
                        "type": "blocks",
                        "relatedIssue": {"state": {"type": "started"}},
                    }
                ]
            },
        }

        self.assertTrue(MODULE.linear_node_is_blocked(node))

    def test_completed_blocker_does_not_omit_issue(self):
        node = {
            "state": {"type": "unstarted"},
            "labels": {"nodes": []},
            "inverseRelations": {
                "nodes": [
                    {
                        "type": "blocks",
                        "relatedIssue": {"state": {"type": "completed"}},
                    }
                ]
            },
        }

        self.assertFalse(MODULE.linear_node_is_blocked(node))


class BatchedGitHubContextTests(unittest.TestCase):
    def test_report_uses_shared_collector_for_both_pr_queues(self):
        collector = mock.Mock()
        collector.gather.return_value = {
            "viewer": "octocat",
            "profile": "report",
            "api_requests": 5,
            "warnings": [],
            "prs_awaiting_review": [
                {
                    "repository": "example/repo",
                    "number": 1,
                    "title": "Review me",
                    "url": "https://github.com/example/repo/pull/1",
                    "is_draft": False,
                    "created_at": "2026-07-18T01:00:00Z",
                    "ci": {"summary": "passing", "failing": []},
                    "review_summary": "awaiting review",
                    "live_evidence": {"likely_genuine": True},
                    "unresolved_review_threads": [],
                    "closing_issues": [],
                }
            ],
            "authored_open_prs": [
                {
                    "repository": "example/repo",
                    "number": 2,
                    "title": "My draft",
                    "url": "https://github.com/example/repo/pull/2",
                    "is_draft": True,
                    "created_at": "2026-07-18T02:00:00Z",
                    "ci": {"summary": "passing", "failing": []},
                    "review_summary": "unknown",
                    "live_evidence": {"likely_genuine": False},
                    "unresolved_review_threads": [],
                    "closing_issues": [],
                }
            ],
        }

        with mock.patch.object(MODULE, "_load_github_collector", return_value=collector):
            review, ready, draft, metadata = MODULE.fetch_github_context("octocat")

        collector.gather.assert_called_once_with(
            "octocat", "octocat", 100, False, "report"
        )
        self.assertEqual([pr.number for pr in review], [1])
        self.assertEqual(ready, [])
        self.assertEqual([pr.number for pr in draft], [2])
        self.assertEqual(metadata["api_requests"], 5)
        self.assertTrue(review[0].awaiting_user_review)


class ActionItemReportTests(unittest.TestCase):
    def test_action_limit_keeps_review_requests_first(self):
        review = MODULE.GitHubPR(
            repo="example/repo",
            number=1,
            title="Review me",
            url="https://github.com/example/repo/pull/1",
            is_draft=False,
            created_at=MODULE.datetime.now(MODULE.timezone.utc),
            awaiting_user_review=True,
        )
        ticket = MODULE.LinearTicket(
            identifier="ALL-1",
            title="Next ticket",
            description="",
            priority=1,
            priority_label="Urgent",
            state="Todo",
            state_type="unstarted",
            url="https://linear.app/example/issue/ALL-1",
        )
        checklist = MODULE.WorkflowChecklist(
            review_requests=[review],
            linear_tickets=[ticket],
            action_limit=1,
        )

        self.assertEqual(
            checklist.action_items(),
            [
                {
                    "kind": "review_request",
                    "title": "example/repo#1 — Review me",
                    "url": "https://github.com/example/repo/pull/1",
                    "summary": "Review now and verify live evidence with the author",
                    "related_issues": [],
                }
            ],
        )

    def test_draft_conflicts_are_rendered_before_other_draft_actions(self):
        created_at = MODULE.datetime.now(MODULE.timezone.utc)
        evidence_pr = MODULE.GitHubPR(
            repo="example/repo",
            number=2,
            title="Needs evidence",
            url="https://github.com/example/repo/pull/2",
            is_draft=True,
            created_at=created_at,
        )
        conflict_pr = MODULE.GitHubPR(
            repo="example/repo",
            number=3,
            title="Has conflicts",
            url="https://github.com/example/repo/pull/3",
            is_draft=True,
            created_at=created_at,
            mergeable="CONFLICTING",
        )

        report = MODULE.WorkflowChecklist(
            draft_prs=[evidence_pr, conflict_pr]
        ).to_markdown()

        self.assertLess(report.index("Has conflicts"), report.index("Needs evidence"))


if __name__ == "__main__":
    unittest.main()
