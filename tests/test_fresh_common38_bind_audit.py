import json
from pathlib import Path
import unittest

from llm4or.fresh_common38_bind_audit import build_audit


ROOT = Path(__file__).resolve().parents[1]


class FreshCommon38BindAuditTests(unittest.TestCase):
    def test_terminal_result_reconstructs_without_api_or_public_bodies(self):
        audit = build_audit(ROOT)
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["checks"]["private_terminal_cells"], 38)
        self.assertEqual(audit["checks"]["round_one"]["correct"], 13)
        self.assertEqual(audit["checks"]["final"]["correct"], 13)
        self.assertEqual(audit["execution"]["new_api_calls"], 0)
        rendered = json.dumps(audit, sort_keys=True)
        for prohibited in (
            '"objective"', '"point"', '"optimum"', '"code"', '"text"',
            '"request_body"', '"response_body"', '"api_key"',
        ):
            self.assertNotIn(prohibited, rendered)


if __name__ == "__main__":
    unittest.main()
