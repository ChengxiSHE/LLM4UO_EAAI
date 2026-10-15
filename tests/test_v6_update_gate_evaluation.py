import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evaluate_v6_update_gate", ROOT / "scripts/evaluate_v6_update_gate.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class V6UpdateGateEvaluationTests(unittest.TestCase):
    def test_exact_sign_probability(self):
        self.assertEqual(MODULE.exact_one_sided_sign_probability(0, 0), 1.0)
        self.assertEqual(MODULE.exact_one_sided_sign_probability(5, 0), 0.03125)
        self.assertEqual(MODULE.exact_one_sided_sign_probability(4, 0), 0.0625)

    def test_classification(self):
        self.assertEqual(MODULE.classify(False, True), "correction")
        self.assertEqual(MODULE.classify(True, False), "regression")
        self.assertEqual(MODULE.classify(True, True), "both_match")
        self.assertEqual(MODULE.classify(False, False), "neither_match")
        self.assertEqual(MODULE.classify(None, True), "unknown")


if __name__ == "__main__":
    unittest.main()
