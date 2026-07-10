import importlib.util
import pathlib
import unittest
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "daily-workflow-fetch.py"
SPEC = importlib.util.spec_from_file_location("daily_workflow_fetch", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class EvidenceParsingTests(unittest.TestCase):
    def test_extract_markdown_section_returns_evidence_content(self):
        body = """## Summary\nSummary text\n\n## Evidence\n```bash\n$ python app.py\noutput: success\n```\n\n## Checklist\n- [x] Done\n"""
        self.assertEqual(
            MODULE.extract_markdown_section(body, "Evidence"),
            "```bash\n$ python app.py\noutput: success\n```",
        )

    def test_evidence_section_accepts_screenshot(self):
        evidence = "Validated in the browser. ![Screenshot](https://example.com/run.png)"
        self.assertTrue(MODULE.evidence_section_has_live_run(evidence))

    def test_evidence_section_accepts_fenced_command_output(self):
        evidence = """```bash\n$ python app.py\noutput: success\n```"""
        self.assertTrue(MODULE.evidence_section_has_live_run(evidence))

    def test_evidence_section_rejects_blocked_manual_verification(self):
        evidence = "Live verification is blocked pending credentials and still requires manual verification."
        self.assertFalse(MODULE.evidence_section_has_live_run(evidence))

    def test_evidence_section_rejects_plain_summary_without_live_run(self):
        evidence = "Ran through the changes conceptually and described the expected behavior."
        self.assertFalse(MODULE.evidence_section_has_live_run(evidence))


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


class GitHubIdentityTests(unittest.TestCase):
    def test_resolves_authenticated_github_user(self):
        with mock.patch.object(MODULE, "run_gh", return_value="octocat") as run_gh:
            self.assertEqual(MODULE.resolve_github_username(), "octocat")

        run_gh.assert_called_once_with(["api", "user", "--jq", ".login"])

    def test_returns_none_when_authenticated_user_is_unavailable(self):
        with mock.patch.object(MODULE, "run_gh", return_value={}):
            self.assertIsNone(MODULE.resolve_github_username())


if __name__ == "__main__":
    unittest.main()
