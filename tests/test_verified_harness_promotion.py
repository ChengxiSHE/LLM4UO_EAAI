import unittest

from llm4or.verified_harness_promotion import (
    alpha_spend, clopper_pearson_upper, minimum_zero_regression_trials,
    promotion_decision,
)


class VerifiedHarnessPromotionTests(unittest.TestCase):
    def test_alpha_spending_is_globally_bounded(self):
        spent = sum(alpha_spend(generation) for generation in range(1, 100000))
        self.assertLess(spent, 0.05)
        self.assertGreater(spent, 0.04999)

    def test_zero_regression_bound_matches_closed_form(self):
        alpha = 0.01
        bound = clopper_pearson_upper(0, 100, alpha)
        self.assertAlmostEqual(bound, 1 - alpha ** (1 / 100), places=12)

    def test_zero_regression_sample_size_design(self):
        # Generation 1 spends .025 and splits it equally across two conditions.
        required = minimum_zero_regression_trials(0.05, 0.0125)
        self.assertEqual(required, 86)
        self.assertLessEqual(clopper_pearson_upper(0, required, 0.0125), 0.05)
        self.assertGreater(clopper_pearson_upper(0, required - 1, 0.0125), 0.05)

    def test_small_perfect_batch_is_not_enough_for_risk_claim(self):
        decision = promotion_decision(
            [(False, True)] * 8,
            1,
            maximum_regression_rate=0.05,
        )
        self.assertTrue(decision["gain_pass"])
        self.assertFalse(decision["regression_pass"])
        self.assertFalse(decision["accept"])

    def test_large_correction_only_batch_can_pass_both_conditions(self):
        decision = promotion_decision(
            [(False, True)] * 200,
            1,
            maximum_regression_rate=0.05,
        )
        self.assertTrue(decision["gain_pass"])
        self.assertTrue(decision["regression_pass"])
        self.assertTrue(decision["accept"])

    def test_observed_regressions_can_block_significant_gain(self):
        pairs = [(False, True)] * 80 + [(True, False)] * 5 + [(True, True)] * 115
        decision = promotion_decision(pairs, 1, maximum_regression_rate=0.03)
        self.assertTrue(decision["gain_pass"])
        self.assertFalse(decision["regression_pass"])
        self.assertFalse(decision["accept"])


if __name__ == "__main__":
    unittest.main()
