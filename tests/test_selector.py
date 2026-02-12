import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from smarttest_selector.models import TestCase
from smarttest_selector.selector import SelectorEngine


class SelectorEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.testcases = [
            TestCase(
                id="TC-PLP-1",
                title="PLP filter by color",
                description="Verify filters in product listing",
                module="PLP",
                tags=["plp", "filter"],
            ),
            TestCase(
                id="TC-CHK-1",
                title="Checkout with card",
                description="Payment flow validation",
                module="Checkout",
                tags=["checkout", "payment"],
            ),
        ]

    def test_plp_query_selects_plp_case(self):
        engine = SelectorEngine(self.testcases)
        results = engine.select("PLP page filters", top_k=1, use_llm_rerank=False)
        self.assertEqual(results[0].testcase.id, "TC-PLP-1")


if __name__ == "__main__":
    unittest.main()
