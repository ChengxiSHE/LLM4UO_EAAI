import unittest

from llm4or.source_indexed_evaluation import (
    evaluate_source_indexed_development, final_development_gate, stage1_gate,
)


def solve(correct):
    return {"status": "optimal", "objective": 10 if correct else 11}


def entries(n=70, corrections=6, regressions=1):
    categories = ["ra", "transport", "disaster", "jssp", "vrptw", "rcpsp", "facility"]
    values, references = [], {}
    for index in range(n):
        problem_id = f"p{index:03d}"
        base = not (index < corrections)
        full = False if corrections <= index < corrections + regressions else True
        values.append({
            "problem_id": problem_id, "category": categories[index % len(categories)],
            "probe": {
                "solve": {"Base": solve(base), "SourceIndexed": solve(full), "FullV8": solve(full)},
                "method_infrastructure_unavailable": {"Base": False, "SourceIndexed": False, "FullV8": False},
                "reports": {"full_gate": {"accepted": True}},
            },
        })
        references[problem_id] = {"solver_status": 2, "theoretical_optimum": 10}
    return values, references


class SourceIndexedEvaluationTests(unittest.TestCase):
    def test_final_gate_passes_clear_multicategory_gain(self):
        values, references = entries()
        report, private = evaluate_source_indexed_development(values, references)
        self.assertTrue(final_development_gate(report)["passed"])
        self.assertEqual(report["comparison"]["corrections"], 6)
        self.assertEqual(report["comparison"]["regressions"], 1)
        self.assertEqual(len(private), 70)

    def test_stage1_gate_rejects_zero_actionability(self):
        values, references = entries(n=10, corrections=0, regressions=0)
        for value in values:
            value["probe"]["reports"]["full_gate"]["accepted"] = False
        report, _ = evaluate_source_indexed_development(values, references)
        self.assertFalse(stage1_gate(report)["passed"])


if __name__ == "__main__":
    unittest.main()
