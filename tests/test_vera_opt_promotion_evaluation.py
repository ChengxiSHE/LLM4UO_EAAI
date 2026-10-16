import unittest

from llm4or.vera_opt_promotion_evaluation import (
    evaluate_promotion, objective_match, zero_failure_upper,
)


class VeraOptPromotionEvaluationTests(unittest.TestCase):
    def test_objective_match(self):
        self.assertTrue(objective_match({"status": "optimal", "objective": 12.0}, 12))
        self.assertFalse(objective_match({"status": "error", "objective": 12}, 12))

    def test_zero_failure_bound_for_ninety_is_below_five_percent(self):
        self.assertLessEqual(zero_failure_upper(90, 0.0125), 0.05)

    def test_strict_promotion_gate(self):
        entries = []
        references = {}
        for index in range(90):
            problem_id = f"p{index}"
            references[problem_id] = 1.0
            base = {"status": "optimal", "objective": 1.0} if index >= 8 else {
                "status": "optimal", "objective": 0.0,
            }
            entries.append({
                "problem_id": problem_id, "category": f"size_{11 + index // 10}",
                "probe": {
                    "problem_id": problem_id,
                    "solve": {"Base": base, "VERA": {"status": "optimal", "objective": 1.0}},
                    "reports": {"skill": {"adopted": True}},
                    "method_infrastructure_unavailable": {"Base": False, "VERA": False},
                    "status": "completed",
                },
            })
        public, private = evaluate_promotion(entries, references)
        self.assertEqual(len(private), 90)
        self.assertEqual(public["comparison"]["corrections"], 8)
        self.assertTrue(public["promotion_gate"]["promoted"])


if __name__ == "__main__":
    unittest.main()
