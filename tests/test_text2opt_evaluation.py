import unittest

from llm4or.text2opt_evaluation import evaluate_confirmation


def probe(pid, base, v6, full, *, category="unused"):
    def solved(correct):
        return {"status": "optimal", "objective": 10.0 if correct else 11.0}
    return {
        "problem_id": pid,
        "status": "completed",
        "solve": {
            "Base": solved(base), "V6": solved(v6),
            "DualLedger": solved(full), "FullV7": solved(full),
        },
        "method_infrastructure_unavailable": {
            "Base": False, "V6": False, "DualLedger": False, "FullV7": False,
        },
        "reports": {"dual_ledger": {"status": "accepted"}},
    }


class Text2OptEvaluationTests(unittest.TestCase):
    def test_aggregate_keeps_private_identifiers_out_of_public_report(self):
        entries = []
        references = {}
        categories = ["ra", "transportation", "disaster", "jssp", "vrptw", "rcpsp", "facility"]
        for index in range(431):
            pid = f"p{index:03d}"
            category = categories[index % 7]
            correction = index < 21
            regression = index == 430
            entries.append({
                "problem_id": pid, "category": category,
                "probe": probe(pid, regression, regression, correction),
            })
            references[pid] = {"solver_status": 2, "theoretical_optimum": 10.0}
        public, private = evaluate_confirmation(entries, references)
        self.assertEqual(public["records"], 431)
        self.assertEqual(public["categories"], 7)
        self.assertTrue(public["joint_confirmation_gate"]["confirmed"])
        self.assertNotIn("problem_id", str(public))
        self.assertEqual(len(private), 431)


if __name__ == "__main__":
    unittest.main()
