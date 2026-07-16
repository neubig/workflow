import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "public-daily-workflow-example"
SPEC = importlib.util.spec_from_file_location("public_daily_workflow_demo", EXAMPLE / "demo.py")
assert SPEC and SPEC.loader
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


class PublicDailyWorkflowDataTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads((EXAMPLE / "data" / "intake.json").read_text(encoding="utf-8"))

    def test_committed_bundle_passes_boundary(self):
        DEMO.validate_bundle(self.bundle)

    def test_non_openhands_repository_is_rejected(self):
        altered = copy.deepcopy(self.bundle)
        altered["github"][0]["repository"] = "example/agent-canvas"
        with self.assertRaisesRegex(DEMO.DataBoundaryError, r"OpenHands/\*"):
            DEMO.validate_bundle(altered)

    def test_private_style_github_url_is_rejected(self):
        altered = copy.deepcopy(self.bundle)
        altered["github"][0]["source_url"] = "https://github.example/OpenHands/agent-canvas/pull/1822"
        with self.assertRaisesRegex(DEMO.DataBoundaryError, "outside the allowlist"):
            DEMO.validate_bundle(altered)

    def test_unlabeled_slack_fixture_is_rejected(self):
        altered = copy.deepcopy(self.bundle)
        altered["slack"][0]["display_text"] = "Please publish this message."
        with self.assertRaisesRegex(DEMO.DataBoundaryError, "visibly labeled"):
            DEMO.validate_bundle(altered)

    def test_real_slack_without_approval_is_rejected(self):
        altered = copy.deepcopy(self.bundle)
        altered["slack"][0]["type"] = "slack"
        with self.assertRaisesRegex(DEMO.DataBoundaryError, "lacks approval"):
            DEMO.validate_bundle(altered)

    def test_token_like_content_is_rejected(self):
        altered = copy.deepcopy(self.bundle)
        altered["slack"][0]["display_text"] += " xoxb-not-a-real-token-value"
        with self.assertRaisesRegex(DEMO.DataBoundaryError, "forbidden credential"):
            DEMO.validate_bundle(altered)


class PublicDailyWorkflowReplayTests(unittest.TestCase):
    def test_scripted_recovery_path(self):
        result = subprocess.run(
            [
                sys.executable,
                str(EXAMPLE / "demo.py"),
                "--answers",
                "y,r,2,y,n,y",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CORRECTION  Human context overrides", result.stdout)
        self.assertIn("AGENT EXECUTION  Evidence checklist prepared", result.stdout)
        self.assertIn("RECOVERY  Evidence rejected", result.stdout)
        self.assertIn("External writes = 0", result.stdout)
        self.assertIn("fixture-backed development replay", result.stdout)


if __name__ == "__main__":
    unittest.main()
