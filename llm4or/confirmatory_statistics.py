"""Frozen statistical primitives for external benchmark confirmation.

The primary endpoint is binary benchmark formulation accuracy: an internally
solved model must be optimal and its objective must match Text2Opt's published
solver outcome.  Model/parse/contract failures are false.  True transport
interruptions are tracked separately and may only be removed pairwise under
the protocol's completeness guard.
"""
from collections import defaultdict
import math

from scipy.stats import beta


TEXT2OPT_REL_TOL = 1e-5
TEXT2OPT_ABS_TOL = 1e-6
GUROBI_OPTIMAL = 2


def text2opt_match(solve, reference):
    """Match the pinned upstream evaluator without executing upstream code."""
    if not isinstance(reference, dict) or set(reference) != {
        "solver_status", "theoretical_optimum"
    }:
        raise ValueError("invalid_text2opt_reference")
    status = reference["solver_status"]
    optimum = reference["theoretical_optimum"]
    if status != GUROBI_OPTIMAL or type(optimum) not in (int, float) or not math.isfinite(optimum):
        raise ValueError("unsupported_text2opt_reference")
    if not isinstance(solve, dict) or solve.get("status") != "optimal":
        return False
    objective = solve.get("objective")
    return (
        type(objective) in (int, float)
        and math.isfinite(objective)
        and math.isclose(
            float(objective), float(optimum),
            rel_tol=TEXT2OPT_REL_TOL, abs_tol=TEXT2OPT_ABS_TOL,
        )
    )


def exact_one_sided_mcnemar(corrections, regressions):
    """P(X >= corrections), X~Binomial(discordant, .5)."""
    if type(corrections) is not int or type(regressions) is not int or min(corrections, regressions) < 0:
        raise ValueError("invalid_discordance_counts")
    discordant = corrections + regressions
    if discordant == 0:
        return 1.0
    return sum(math.comb(discordant, k) for k in range(corrections, discordant + 1)) / 2**discordant


def wilson_interval(successes, n, alpha=0.05):
    if type(successes) is not int or type(n) is not int or not 0 <= successes <= n or n <= 0:
        raise ValueError("invalid_binomial_counts")
    if not 0 < alpha < 1:
        raise ValueError("invalid_alpha")
    # 1.959963984540054 is Phi^-1(.975); confirmation fixes alpha=.05.
    if not math.isclose(alpha, 0.05):
        raise ValueError("only_frozen_alpha_supported")
    z = 1.959963984540054
    p = successes / n
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return [max(0.0, center-radius), min(1.0, center+radius)]


def conditional_exact_delta_interval(corrections, regressions, n, alpha=0.05):
    """Exact conditional CI for paired accuracy delta with discordance fixed."""
    if type(n) is not int or n <= 0 or corrections + regressions > n:
        raise ValueError("invalid_paired_counts")
    if min(corrections, regressions) < 0:
        raise ValueError("invalid_paired_counts")
    m = corrections + regressions
    if m == 0:
        return [0.0, 0.0]
    lower = 0.0 if corrections == 0 else float(beta.ppf(alpha/2, corrections, m-corrections+1))
    upper = 1.0 if corrections == m else float(beta.ppf(1-alpha/2, corrections+1, m-corrections))
    scale = m / n
    return [(2*lower-1)*scale, (2*upper-1)*scale]


def holm_adjust(raw):
    """Holm family-wise adjustment with monotonic adjusted p-values."""
    if not isinstance(raw, dict) or not raw or any(
        not isinstance(name, str) or type(value) not in (int, float) or not 0 <= value <= 1
        for name, value in raw.items()
    ):
        raise ValueError("invalid_p_values")
    ordered = sorted(raw.items(), key=lambda item: (item[1], item[0]))
    adjusted = {}
    running = 0.0
    total = len(ordered)
    for index, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, (total-index)*float(value)))
        adjusted[name] = running
    return adjusted


def _binary(value):
    if type(value) is not bool:
        raise ValueError("nonbinary_accuracy_value")
    return value


def paired_summary(rows, candidate="candidate", comparator="comparator"):
    """Aggregate one frozen paired comparison without exposing identifiers."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty_paired_rows")
    complete = []
    by_category = defaultdict(list)
    unavailable = 0
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("category"), str):
            raise ValueError("invalid_paired_row")
        candidate_infra = row.get(candidate + "_infrastructure_unavailable") is True
        comparator_infra = row.get(comparator + "_infrastructure_unavailable") is True
        if candidate_infra or comparator_infra:
            unavailable += 1
            continue
        pair = (_binary(row[candidate]), _binary(row[comparator]))
        complete.append(pair)
        by_category[row["category"]].append(pair)
    if not complete:
        raise ValueError("no_complete_pairs")

    def counts(pairs):
        candidate_correct = sum(a for a, _ in pairs)
        comparator_correct = sum(b for _, b in pairs)
        corrections = sum(a and not b for a, b in pairs)
        regressions = sum(b and not a for a, b in pairs)
        n = len(pairs)
        return {
            "n": n,
            "candidate_correct": candidate_correct,
            "comparator_correct": comparator_correct,
            "candidate_accuracy": candidate_correct/n,
            "comparator_accuracy": comparator_correct/n,
            "accuracy_delta": (corrections-regressions)/n,
            "corrections": corrections,
            "regressions": regressions,
            "both_correct": sum(a and b for a, b in pairs),
            "both_incorrect": sum(not a and not b for a, b in pairs),
            "paired_one_sided_exact_p": exact_one_sided_mcnemar(corrections, regressions),
            "candidate_wilson_95": wilson_interval(candidate_correct, n),
            "comparator_wilson_95": wilson_interval(comparator_correct, n),
            "conditional_exact_delta_95": conditional_exact_delta_interval(corrections, regressions, n),
        }

    category = {name: counts(pairs) for name, pairs in sorted(by_category.items())}
    deltas = [value["accuracy_delta"] for value in category.values()]
    return {
        **counts(complete),
        "planned_records": len(rows),
        "paired_infrastructure_unavailable": unavailable,
        "paired_completion_rate": len(complete)/len(rows),
        "categories": category,
        "category_macro_accuracy_delta": sum(deltas)/len(deltas),
        "positive_categories": sum(value > 0 for value in deltas),
        "negative_categories": sum(value < 0 for value in deltas),
        "tied_categories": sum(value == 0 for value in deltas),
    }


def confirmation_gate(vs_base, vs_v6, *, alpha=0.05):
    """Pre-registered joint gate; both comparisons must satisfy every rule."""
    if not math.isclose(alpha, 0.05):
        raise ValueError("only_frozen_alpha_supported")
    reports = {"versus_base": vs_base, "versus_v6": vs_v6}
    adjusted = holm_adjust({
        name: report["paired_one_sided_exact_p"] for name, report in reports.items()
    })
    checks = {}
    for name, report in reports.items():
        checks[name] = {
            "paired_completion_at_least_99pct": report["paired_completion_rate"] >= 0.99,
            "accuracy_delta_at_least_2pp": report["accuracy_delta"] >= 0.02,
            "corrections_at_least_twice_regressions": (
                report["corrections"] >= 2*max(1, report["regressions"])
            ),
            "holm_adjusted_one_sided_p_at_most_005": adjusted[name] <= alpha,
            "positive_in_at_least_four_categories": report["positive_categories"] >= 4,
            "negative_in_at_most_one_category": report["negative_categories"] <= 1,
        }
    return {
        "holm_adjusted_p": adjusted,
        "checks": checks,
        "confirmed": all(all(value.values()) for value in checks.values()),
    }


__all__ = [
    "TEXT2OPT_ABS_TOL", "TEXT2OPT_REL_TOL", "conditional_exact_delta_interval",
    "confirmation_gate", "exact_one_sided_mcnemar", "holm_adjust", "paired_summary",
    "text2opt_match", "wilson_interval",
]
