"""Anytime-valid promotion rules for versioned harness candidates.

This module does not assess natural-language semantics.  It consumes one
precommitted incumbent/candidate binary pair per independently reviewed family.
Freshness, candidate freezing, and family review belong to the persistent
ledger that calls this pure statistical rule.
"""

import math


VERSION = "verified-harness-promotion-v1"


def alpha_spend(generation: int, total_alpha: float = 0.05) -> float:
    """Return an alpha-spending sequence whose infinite sum is total_alpha."""
    if type(generation) is not int or generation < 1 or not 0 < total_alpha < 1:
        raise ValueError("invalid_alpha_spend")
    return total_alpha / (generation * (generation + 1))


def _binomial_cdf(k: int, n: int, probability: float) -> float:
    return sum(
        math.comb(n, j) * probability**j * (1.0 - probability) ** (n - j)
        for j in range(k + 1)
    )


def clopper_pearson_upper(successes: int, trials: int, alpha: float) -> float:
    """Exact one-sided upper confidence bound for a binomial probability."""
    if (
        type(successes) is not int or type(trials) is not int
        or trials < 1 or successes < 0 or successes > trials
        or not 0 < alpha < 1
    ):
        raise ValueError("invalid_binomial_bound")
    if successes == trials:
        return 1.0
    low, high = 0.0, 1.0
    # CDF(successes; trials, p) decreases in p.  Solve CDF = alpha.
    for _ in range(90):
        mid = (low + high) / 2.0
        if _binomial_cdf(successes, trials, mid) > alpha:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def one_sided_mcnemar(plus: int, minus: int) -> float:
    """Exact p-value for candidate corrections exceeding regressions."""
    if type(plus) is not int or type(minus) is not int or min(plus, minus) < 0:
        raise ValueError("invalid_paired_counts")
    discordant = plus + minus
    if discordant == 0:
        return 1.0
    return sum(math.comb(discordant, j) for j in range(plus, discordant + 1)) / 2**discordant


def minimum_zero_regression_trials(maximum_rate: float, alpha: float) -> int:
    """Trials needed for a zero-event exact upper bound at ``maximum_rate``."""
    if not 0 < maximum_rate < 1 or not 0 < alpha < 1:
        raise ValueError("invalid_zero_event_design")
    return math.ceil(math.log(alpha) / math.log(1.0 - maximum_rate))


def promotion_decision(
    pairs,
    generation: int,
    *,
    total_alpha: float = 0.05,
    maximum_regression_rate: float = 0.05,
    minimum_net_corrections: int = 1,
):
    """Test positive paired gain and a bounded family-level regression rate.

    The generation's alpha is split equally between the gain and regression
    conditions.  Summing over all generations and both conditions is therefore
    bounded by ``total_alpha`` through a union bound.
    """
    if (
        not pairs or not 0 < maximum_regression_rate < 1
        or type(minimum_net_corrections) is not int or minimum_net_corrections < 1
    ):
        raise ValueError("invalid_promotion_inputs")
    if any(len(pair) != 2 or any(type(value) is not bool for value in pair) for pair in pairs):
        raise ValueError("one_binary_pair_per_reviewed_family_required")
    generation_alpha = alpha_spend(generation, total_alpha)
    condition_alpha = generation_alpha / 2.0
    plus = sum(not incumbent and candidate for incumbent, candidate in pairs)
    minus = sum(incumbent and not candidate for incumbent, candidate in pairs)
    gain_pvalue = one_sided_mcnemar(plus, minus)
    regression_upper = clopper_pearson_upper(minus, len(pairs), condition_alpha)
    net = plus - minus
    gain_pass = gain_pvalue <= condition_alpha and net >= minimum_net_corrections
    regression_pass = regression_upper <= maximum_regression_rate
    return {
        "schema": "verified-harness-promotion-decision-v1",
        "version": VERSION,
        "generation": generation,
        "reviewed_families": len(pairs),
        "corrections": plus,
        "regressions": minus,
        "net_corrections": net,
        "total_alpha": total_alpha,
        "generation_alpha": generation_alpha,
        "condition_alpha": condition_alpha,
        "gain_pvalue": gain_pvalue,
        "gain_pass": gain_pass,
        "maximum_regression_rate": maximum_regression_rate,
        "regression_rate_upper_bound": regression_upper,
        "regression_pass": regression_pass,
        "accept": gain_pass and regression_pass,
        "assumptions_enforced_by_this_function": False,
        "assumptions": [
            "one precommitted pair per independently reviewed family",
            "candidate frozen before outcomes are opened",
            "fresh promotion families are never reused across generations",
            "families represent the stated target distribution",
        ],
    }


__all__ = [
    "VERSION", "alpha_spend", "clopper_pearson_upper",
    "minimum_zero_regression_trials", "one_sided_mcnemar", "promotion_decision",
]
