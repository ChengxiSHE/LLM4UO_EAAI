"""Frozen final evaluation for VERA-Opt generation-two confirmation."""

from __future__ import annotations

from .confirmatory_statistics import paired_summary, wilson_interval
from .vera_opt_promotion_evaluation import objective_match, zero_failure_upper


VERSION = "vera-opt-generation2-confirmation-evaluation-v1"
METHODS = ("Base", "VERA")


def evaluate_confirmation(entries, references, *, alpha=0.0125):
    if not isinstance(entries, list) or not entries or not isinstance(references, dict):
        raise ValueError("invalid_confirmation_inputs")
    private = []
    for entry in entries:
        problem_id = entry["problem_id"]; probe = entry["probe"]
        if problem_id not in references or probe.get("problem_id") != problem_id:
            raise ValueError("confirmation_binding")
        infrastructure = probe.get("method_infrastructure_unavailable")
        if not isinstance(infrastructure, dict) or set(infrastructure) != set(METHODS):
            raise ValueError("confirmation_infrastructure_schema")
        scores = {method: objective_match(probe.get("solve", {}).get(method), references[problem_id])
                  for method in METHODS}
        private.append({
            "problem_id": problem_id, "category": entry["category"], "scores": scores,
            "infrastructure": infrastructure,
            "skill_adopted": probe.get("reports", {}).get("skill", {}).get("adopted") is True,
            "probe_status": probe.get("status"),
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
        "candidate_exact_on_all_confirmation_records": paired["candidate_correct"] == len(private),
        "candidate_adopted_on_all_confirmation_records": sum(
            row["skill_adopted"] for row in private) == len(private),
        "accuracy_delta_at_least_5pp": paired["accuracy_delta"] >= 0.05,
        "zero_regressions": paired["regressions"] == 0,
        "one_sided_exact_p_within_alpha_spend": paired["paired_one_sided_exact_p"] <= alpha,
        "zero_regression_upper_bound_at_most_5pct": upper <= 0.05,
        "positive_in_at_least_five_size_groups": paired["positive_categories"] >= 5,
        "negative_in_no_size_group": paired["negative_categories"] == 0,
    }
    public = {
        "schema": "vera-opt-generation2-confirmation-evaluation-v1", "version": VERSION,
        "records": len(private), "size_groups": len({row["category"] for row in private}),
        "method_summaries": {method: {
            "correct": sum(row["scores"][method] for row in private),
            "accuracy": sum(row["scores"][method] for row in private) / len(private),
            "wilson_95": wilson_interval(sum(row["scores"][method] for row in private), len(private)),
            "infrastructure_unavailable": sum(row["infrastructure"][method] for row in private),
        } for method in METHODS},
        "comparison": paired,
        "skill": {"adopted": sum(row["skill_adopted"] for row in private),
                  "abstained": sum(not row["skill_adopted"] for row in private)},
        "alpha_spend": alpha, "zero_regression_one_sided_upper": upper,
        "confirmation_gate": {"checks": checks, "confirmed": all(checks.values())},
        "claim_guard": (
            "Passing supports a preregistered OPT-Engine canonical Knapsack size-extrapolation "
            "benchmark formulation-accuracy improvement over the same-model Base. It does not "
            "establish universal semantic equivalence or arbitrary-prose generalization."
        ),
    }
    return public, private


__all__ = ["METHODS", "VERSION", "evaluate_confirmation"]
