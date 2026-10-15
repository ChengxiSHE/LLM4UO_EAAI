import json
from pathlib import Path
import unittest

from llm4or.fresh_common38_native_audit import build_audit


ROOT = Path(__file__).resolve().parents[1]


class FreshCommon38NativeAuditTests(unittest.TestCase):
    def test_terminal_run_reconstructs_without_public_values(self):
        audit = build_audit(ROOT)
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["checks"]["private_checkpoints_verified"], 38)
        self.assertEqual(audit["checks"]["endpoint_scores_recomputed"], 38)
        self.assertEqual(audit["checks"]["aggregate"]["correct"], 30)
        rendered = json.dumps(audit, sort_keys=True)
        for prohibited in ('"objective"', '"point"', '"optimum"', '"public_payload"'):
            self.assertNotIn(prohibited, rendered)


if __name__ == "__main__":
    unittest.main()
