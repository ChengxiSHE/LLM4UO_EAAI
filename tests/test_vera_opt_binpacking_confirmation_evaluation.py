import unittest

from llm4or.vera_opt_binpacking_confirmation_evaluation import evaluate_confirmation


class VeraOptBinPackingConfirmationEvaluationTests(unittest.TestCase):
    @staticmethod
    def entries(correction_groups):
        entries = []
        references = {}
        for index in range(150):
            problem_id = f"bp{index}"
            group = index // 10
            references[problem_id] = 1.0
            base_correct = not (group in correction_groups and index % 10 == 0)
            entries.append({
                "problem_id": problem_id,
                "category": f"size_{26 + group}",
                "probe": {
                    "problem_id": problem_id,
                    "solve": {
                        "Base": {"status": "optimal", "objective": 1.0 if base_correct else 0.0},
                        "VERA": {"status": "optimal", "objective": 1.0},
                    },
                    "reports": {"skill": {"adopted": True}},
                    "method_infrastructure_unavailable": {"Base": False, "VERA": False},
                    "status": "completed",
                },
            })
        return entries, references

    def test_strict_confirmation_gate_passes_with_ten_groups(self):
        entries, references = self.entries(set(range(10)))
        public, _ = evaluate_confirmation(entries, references, alpha=0.003125)
        self.assertEqual(public["comparison"]["corrections"], 10)
        self.assertEqual(public["comparison"]["positive_categories"], 10)
        self.assertTrue(public["confirmation_gate"]["confirmed"])

    def test_requires_eight_positive_size_groups(self):
        entries, references = self.entries(set(range(7)))
        public, _ = evaluate_confirmation(entries, references, alpha=0.003125)
        self.assertFalse(public["confirmation_gate"]["checks"][
            "positive_in_at_least_eight_size_groups"
        ])
        self.assertFalse(public["confirmation_gate"]["confirmed"])


if __name__ == "__main__":
    unittest.main()
