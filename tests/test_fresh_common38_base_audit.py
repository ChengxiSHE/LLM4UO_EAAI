import json
from pathlib import Path
import unittest

from llm4or.fresh_common38_base_audit import build_audit


ROOT = Path(__file__).resolve().parents[1]


class FreshCommon38BaseAuditTests(unittest.TestCase):
    def test_terminal_result_reconstructs_and_normalizes_zero_count(self):
        audit = build_audit(ROOT)
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["checks"]["private_terminal_cells"], 38)
        self.assertEqual(audit["checks"]["aggregate"]["planned"], 38)
        self.assertEqual(audit["checks"]["aggregate"]["correct"], 0)
        self.assertEqual(audit["checks"]["ledger"]["logical_slots"], 38)
        self.assertEqual(audit["execution"], {"new_api_calls": 0, "new_solver_calls": 0})
        rendered = json.dumps(audit, sort_keys=True)
        for prohibited in (
            '"objective"', '"point"', '"optimum"', '"text"',
            '"request_body"', '"response_body"', '"api_key"',
        ):
            self.assertNotIn(prohibited, rendered)


if __name__ == "__main__":
    unittest.main()
