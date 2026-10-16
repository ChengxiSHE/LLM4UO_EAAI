import math
import unittest

from llm4or.retailopt190_endpoint import readme_strict_correct, relative_objective_error, reloop_code_correct


class RetailOptEndpointTests(unittest.TestCase):
    def test_policies_diverge_inside_one_percent(self):
        record = {"reference_status": "OPTIMAL", "reference_objective": 100.0, "archetype": "moq_binary"}
        result = {"status": "OPTIMAL", "objective": 100.5}
        self.assertFalse(readme_strict_correct(record, result))
        self.assertTrue(reloop_code_correct(record, result))

    def test_relaxed_readme_archetypes_and_status_strengthening(self):
        record = {"reference_status": "OPTIMAL (TL)", "reference_objective": 100.0, "archetype": "pack_size_integer"}
        result = {"status": "OPTIMAL", "objective": 100.5}
        self.assertTrue(readme_strict_correct(record, result))

    def test_one_percent_boundary_is_strict_for_reloop(self):
        record = {"reference_status": "OPTIMAL", "reference_objective": 100.0, "archetype": "moq_binary"}
        self.assertFalse(reloop_code_correct(record, {"status": "OPTIMAL", "objective": 101.0}))

    def test_nonfinite_rejected_and_zero_defined(self):
        self.assertEqual(relative_objective_error(0.0, 0.0), 0.0)
        self.assertEqual(relative_objective_error(1.0, 0.0), math.inf)
        with self.assertRaisesRegex(ValueError, "objective_nonfinite"):
            relative_objective_error(float("nan"), 1.0)


if __name__ == "__main__":
    unittest.main()
