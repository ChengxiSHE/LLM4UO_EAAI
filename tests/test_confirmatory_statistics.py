import unittest

from llm4or.confirmatory_statistics import (
    conditional_exact_delta_interval, confirmation_gate, exact_one_sided_mcnemar,
    holm_adjust, paired_summary, text2opt_match, wilson_interval,
)


class ConfirmatoryStatisticsTests(unittest.TestCase):
    def test_text2opt_match_uses_pinned_evaluator_tolerance(self):
        reference = {"solver_status": 2, "theoretical_optimum": 1000.0}
        self.assertTrue(text2opt_match({"status": "optimal", "objective": 1000.009}, reference))
        self.assertFalse(text2opt_match({"status": "optimal", "objective": 1000.02}, reference))
        self.assertFalse(text2opt_match({"status": "limit", "objective": 1000.0}, reference))

    def test_exact_tests_intervals_and_holm(self):
        self.assertEqual(exact_one_sided_mcnemar(6, 0), 0.015625)
        self.assertEqual(exact_one_sided_mcnemar(0, 0), 1.0)
        self.assertEqual(holm_adjust({"a": 0.01, "b": 0.04}), {"a": 0.02, "b": 0.04})
        low, high = wilson_interval(50, 100)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)
        low, high = conditional_exact_delta_interval(8, 1, 100)
        self.assertLess(low, 0.07)
        self.assertGreater(high, 0.07)

    def test_paired_summary_excludes_only_explicit_infrastructure(self):
        rows = [
            {"category": "a", "candidate": True, "comparator": False},
            {"category": "a", "candidate": False, "comparator": False},
            {"category": "b", "candidate": False, "comparator": True},
            {"category": "b", "candidate": False, "comparator": False,
             "candidate_infrastructure_unavailable": True},
        ]
        report = paired_summary(rows)
        self.assertEqual(report["n"], 3)
        self.assertEqual(report["corrections"], 1)
        self.assertEqual(report["regressions"], 1)
        self.assertEqual(report["paired_infrastructure_unavailable"], 1)

    def test_joint_gate_requires_effect_significance_and_category_spread(self):
        rows = []
        categories = ["a", "b", "c", "d", "e", "f", "g"]
        for index in range(431):
            rows.append({"category": categories[index % 7], "candidate": False, "comparator": False})
        # Twenty-one distributed corrections and one regression: +4.64 pp,
        # positive in all categories, and highly significant.
        for index in range(21):
            rows[index]["candidate"] = True
        rows[-1].update(candidate=False, comparator=True)
        report = paired_summary(rows)
        gate = confirmation_gate(report, report)
        self.assertTrue(gate["confirmed"])
        self.assertLessEqual(gate["holm_adjusted_p"]["versus_base"], 0.05)


if __name__ == "__main__":
    unittest.main()
