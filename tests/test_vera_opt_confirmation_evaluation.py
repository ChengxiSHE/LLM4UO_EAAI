import unittest

from llm4or.vera_opt_confirmation_evaluation import evaluate_confirmation


class VeraOptConfirmationEvaluationTests(unittest.TestCase):
    def test_frozen_gate_passes_with_broad_zero_regression_gain(self):
        entries = []; references = {}
        for index in range(110):
            problem_id = f"p{index}"; references[problem_id] = 1.0
            # Eight corrections distributed over eight size groups.
            base_correct = index % 10 != 0 or index >= 80
            entries.append({"problem_id": problem_id,
                "category": f"size_{20 + index // 10}",
                "probe": {"problem_id": problem_id,
                    "solve": {
                        "Base": {"status": "optimal", "objective": 1.0 if base_correct else 0.0},
                        "VERA": {"status": "optimal", "objective": 1.0}},
                    "reports": {"skill": {"adopted": True}},
                    "method_infrastructure_unavailable": {"Base": False, "VERA": False},
                    "status": "completed"}})
        public, _ = evaluate_confirmation(entries, references)
        self.assertEqual(public["comparison"]["corrections"], 8)
        self.assertTrue(public["confirmation_gate"]["confirmed"])


if __name__ == "__main__":
    unittest.main()
