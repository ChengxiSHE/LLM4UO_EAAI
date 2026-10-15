import unittest

from llm4or.text2opt_v9_evaluation import evaluate_v9_confirmation, v9_confirmation_gate


class Text2OptV9Tests(unittest.TestCase):
    def test_evaluation_counts_paired_corrections(self):
        entries = []
        references = {}
        for index in range(20):
            problem_id = f"case_{index}"
            references[problem_id] = {"solver_status": 2, "theoretical_optimum": 10.0}
            entries.append({
                "problem_id": problem_id, "category": f"family_{index % 5}",
                "probe": {
                    "problem_id": problem_id, "status": "completed",
                    "solve": {
                        "Base": {"status": "optimal", "objective": 11.0},
                        "V9": {"status": "optimal", "objective": 10.0},
                    },
                    "method_infrastructure_unavailable": {"Base": False, "V9": False},
                    "reports": {"compiler": {"status": "optimal", "adopted": True}},
                },
            })
        public, private = evaluate_v9_confirmation(entries, references)
        self.assertEqual(len(private), 20)
        self.assertEqual(public["comparison"]["corrections"], 20)
        self.assertEqual(public["comparison"]["regressions"], 0)
        self.assertTrue(public["confirmation_gate"]["confirmed"])

    def test_gate_rejects_small_effect(self):
        report = {
            "paired_completion_rate": 1.0, "accuracy_delta": 0.01,
            "corrections": 10, "regressions": 0, "paired_one_sided_exact_p": 0.001,
            "positive_categories": 5, "negative_categories": 0,
        }
        self.assertFalse(v9_confirmation_gate(report)["confirmed"])


if __name__ == "__main__":
    unittest.main()
