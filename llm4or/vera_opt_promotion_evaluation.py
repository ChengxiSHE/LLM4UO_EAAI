"""Frozen aggregate evaluation for VERA-Opt generation-one promotion."""

from __future__ import annotations

import math

from .confirmatory_statistics import exact_one_sided_mcnemar, paired_summary, wilson_interval


VERSION = "vera-opt-generation1-promotion-evaluation-v1"
METHODS = ("Base", "VERA")


def objective_match(result, reference, *, rel_tol=1e-7, abs_tol=1e-6):
    return (
        isinstance(result, dict) and result.get("status") == "optimal"
        and type(result.get("objective")) in (int, float)
        and math.isfinite(result["objective"])
        and type(reference) in (int, float) and math.isfinite(reference)
        and math.isclose(float(result["objective"]), float(reference),
                         rel_tol=rel_tol, abs_tol=abs_tol)
    )


def zero_failure_upper(n: int, alpha: float) -> float:
    if type(n) is not int or n <= 0 or not 0 < alpha < 1:
        raise ValueError("invalid_zero_failure_bound")
    return 1 - alpha ** (1 / n)


def evaluate_promotion(entries, references, *, alpha=0.0125):
    if not isinstance(entries, list) or not entries or not isinstance(references, dict):
        raise ValueError("invalid_promotion_inputs")
    private = []
    for entry in entries:
        problem_id = entry["problem_id"]; probe = entry["probe"]
        if problem_id not in references or probe.get("problem_id") != problem_id:
            raise ValueError("promotion_binding")
        infrastructure = probe.get("method_infrastructure_unavailable")
        if not isinstance(infrastructure, dict) or set(infrastructure) != set(METHODS):
            raise ValueError("promotion_infrastructure_schema")
        scores = {
            method: objective_match(probe.get("solve", {}).get(method), references[problem_id])
            for method in METHODS
        }
        adopted = probe.get("reports", {}).get("skill", {}).get("adopted") is True
        private.append({
            "problem_id": problem_id, "category": entry["category"],
            "scores": scores, "infrastructure": infrastructure,
            "skill_adopted": adopted, "probe_status": probe.get("status"),
        })
    paired = paired_summary([{
        "category": row["category"], "candidate": row["scores"]["VERA"],
        "comparator": row["scores"]["Base"],
        "candidate_infrastructure_unavailable": row["infrastructure"]["VERA"],
        "comparator_infrastructure_unavailable": row["infrastructure"]["Base"],
    } for row in private])
    upper = zero_failure_upper(paired["n"], alpha) if paired["regressions"] == 0 else 1.0
    checks = {
        "all_pairs_complete": paired["paired_completion_rate"] == 1.0,
        "candidate_exact_on_all_promotion_records": paired["candidate_correct"] == len(private),
        "candidate_adopted_on_all_promotion_records": sum(
            row["skill_adopted"] for row in private
        ) == len(private),
        "zero_regressions": paired["regressions"] == 0,
        "at_least_one_correction": paired["corrections"] >= 1,
        "one_sided_exact_p_within_alpha_spend": paired["paired_one_sided_exact_p"] <= alpha,
        "zero_regression_upper_bound_at_most_5pct": upper <= 0.05,
    }
    public = {
        "schema": "vera-opt-generation1-promotion-evaluation-v1",
        "version": VERSION,
        "records": len(private),
        "size_groups": len({row["category"] for row in private}),
        "method_summaries": {
            method: {
                "correct": sum(row["scores"][method] for row in private),
                "accuracy": sum(row["scores"][method] for row in private) / len(private),
                "wilson_95": wilson_interval(
                    sum(row["scores"][method] for row in private), len(private),
                ),
                "infrastructure_unavailable": sum(
                    row["infrastructure"][method] for row in private
                ),
            } for method in METHODS
        },
        "comparison": paired,
        "skill": {
            "adopted": sum(row["skill_adopted"] for row in private),
            "abstained": sum(not row["skill_adopted"] for row in private),
        },
        "alpha_spend": alpha,
        "zero_regression_one_sided_upper": upper,
        "promotion_gate": {"checks": checks, "promoted": all(checks.values())},
        "claim_guard": (
            "Promotion is an internal hidden gate for one Knapsack size-extrapolation cohort; "
            "it is not the final confirmation claim."
        ),
    }
    return public, private


__all__ = [
    "METHODS", "VERSION", "evaluate_promotion", "objective_match", "zero_failure_upper",
]
