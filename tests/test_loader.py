import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import json
import unittest
from unittest.mock import patch

from smarttest_selector.loader import load_testcases_from_browserstack


class BrowserStackLoaderTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_load_testcases_from_browserstack(self, mock_urlopen):
        payload = {
            "test_cases": [
                {
                    "id": "TC-100",
                    "title": "PLP filter",
                    "description": "Filter on PLP",
                    "module": "PLP",
                    "tags": ["plp", "filter"],
                    "steps": ["Open PLP", "Apply filter"],
                }
            ],
            "has_next": False,
        }

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        mock_urlopen.return_value = _Resp()

        cases = load_testcases_from_browserstack(
            project_id="123",
            username="user",
            access_key="key",
            endpoint_template="https://example.com/projects/{project_id}/test-cases",
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].id, "TC-100")
        self.assertEqual(cases[0].module, "PLP")

    @patch("urllib.request.urlopen")
    def test_load_nested_test_case_shape(self, mock_urlopen):
        payload = {
            "data": [
                {
                    "test_case": {
                        "identifier": "PR-18-TC-42",
                        "name": "PLP page filters should apply",
                        "labels": [{"name": "plp"}, {"name": "filters"}],
                        "test_steps": ["Open PLP", "Apply brand filter"],
                    }
                }
            ],
            "next": None,
        }

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        mock_urlopen.return_value = _Resp()

        cases = load_testcases_from_browserstack(
            project_id="PR-18",
            username="user",
            access_key="key",
            endpoint_template="https://example.com/projects/{project_id}/test-cases",
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].id, "PR-18-TC-42")
        self.assertEqual(cases[0].title, "PLP page filters should apply")
        self.assertIn("plp", cases[0].tags)


if __name__ == "__main__":
    unittest.main()
