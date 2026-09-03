import importlib.util
import json
import pathlib
import unittest
from unittest import mock


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "skills"
    / "daily-workflow"
    / "scripts"
    / "check_linear_access.py"
)
SPEC = importlib.util.spec_from_file_location("check_linear_access", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ParseCredentialTests(unittest.TestCase):
    def test_prefers_single_key_and_deduplicates_multiple_keys(self):
        self.assertEqual(MODULE.parse_api_keys(" single ", "first, second, first"), ["single"])
        self.assertEqual(MODULE.parse_api_keys(None, " first, second, first, "), ["first", "second"])


class CheckKeyTests(unittest.TestCase):
    def response(self, payload, status=200):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = status
        response.read.return_value = json.dumps(payload).encode()
        return response

    def test_success_reports_identity_without_key(self):
        response = self.response({"data": {"viewer": {"id": "user-1", "email": "graham@example.com"}}})
        with mock.patch.object(MODULE.urllib.request, "urlopen", return_value=response) as urlopen:
            result = MODULE.check_key("secret-token", 1, 1)

        self.assertTrue(result.ok)
        self.assertEqual(result.identity, "graham@example.com")
        self.assertNotIn("secret-token", MODULE.render([result], False))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "secret-token")

    def test_graphql_error_is_failure(self):
        response = self.response({"errors": [{"message": "Authentication required"}]})
        with mock.patch.object(MODULE.urllib.request, "urlopen", return_value=response):
            result = MODULE.check_key("bad-token", 1, 1)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Authentication required")

    def test_json_output_is_machine_readable(self):
        result = MODULE.AccessResult(1, False, 401, error="HTTP 401")
        payload = json.loads(MODULE.render([result], True))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["connections"][0]["status"], 401)


if __name__ == "__main__":
    unittest.main()
