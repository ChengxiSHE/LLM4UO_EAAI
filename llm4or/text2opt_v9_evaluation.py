"""Frozen aggregate-only scoring for Base versus V9 confirmation."""
from collections import Counter

from .confirmatory_statistics import paired_summary, text2opt_match, wilson_interval


METHODS = ("Base", "V9")


def _method_summary(rows, method):
    planned = len(rows); unavailable = sum(row["infrastructure"][method] for row in rows)
    correct = sum(row["scores"][method] for row in rows); complete = planned-unavailable
    conditional = sum(row["scores"][method] for row in rows if not row["infrastructure"][method])
    return {"planned_records": planned, "infrastructure_unavailable": unavailable,
            "correct_all_selected": correct, "accuracy_all_selected": correct/planned,
            "infrastructure_complete_records": complete,
            "accuracy_infrastructure_complete": conditional/complete if complete else None,
            "wilson_95_all_selected": wilson_interval(correct, planned)}


def v9_confirmation_gate(report):
    checks = {
        "paired_completion_at_least_99pct": report["paired_completion_rate"] >= 0.99,
        "accuracy_delta_at_least_5pp": report["accuracy_delta"] >= 0.05,
        "at_least_ten_corrections": report["corrections"] >= 10,
        "corrections_at_least_four_times_regressions": report["corrections"] >= 4*max(1, report["regressions"]),
        "one_sided_exact_p_at_most_005": report["paired_one_sided_exact_p"] <= 0.05,
        "positive_in_at_least_four_categories": report["positive_categories"] >= 4,
        "negative_in_at_most_one_category": report["negative_categories"] <= 1,
    }
    return {"checks": checks, "confirmed": all(checks.values())}


def evaluate_v9_confirmation(entries, references):
    if not isinstance(entries, list) or not entries or not isinstance(references, dict):
        raise ValueError("invalid_v9_confirmation_inputs")
    private = []; counts = Counter()
    for entry in entries:
        problem_id = entry["problem_id"]; probe = entry["probe"]
        if problem_id not in references or probe.get("problem_id") != problem_id:
            raise ValueError("v9_confirmation_binding")
        infrastructure = probe.get("method_infrastructure_unavailable")
        if not isinstance(infrastructure, dict) or set(infrastructure) != set(METHODS):
            raise ValueError("v9_infrastructure_schema")
        scores = {method: text2opt_match(probe.get("solve", {}).get(method), references[problem_id])
                  for method in METHODS}
        for method in METHODS:
            if type(infrastructure[method]) is not bool:
                raise ValueError("v9_infrastructure_value")
            counts[method + (":correct" if scores[method] else ":incorrect")] += 1
            counts[method + ":infrastructure_unavailable"] += infrastructure[method]
        compiler = probe.get("reports", {}).get("compiler", {})
        private.append({"problem_id": problem_id, "category": entry["category"],
                        "scores": scores, "infrastructure": infrastructure,
                        "probe_status": probe.get("status"),
                        "compiler_status": compiler.get("status"),
                        "compiler_adopted": compiler.get("adopted") is True})
    paired_rows = [{
        "category": row["category"], "candidate": row["scores"]["V9"],
        "comparator": row["scores"]["Base"],
        "candidate_infrastructure_unavailable": row["infrastructure"]["V9"],
        "comparator_infrastructure_unavailable": row["infrastructure"]["Base"],
    } for row in private]
    comparison = paired_summary(paired_rows)
    public = {
        "schema": "text2opt-v9-confirmation-evaluation-v1",
        "records": len(private), "categories": len({row["category"] for row in private}),
        "method_summaries": {method: _method_summary(private, method) for method in METHODS},
        "comparison": comparison, "confirmation_gate": v9_confirmation_gate(comparison),
        "compiler": {"adopted": sum(row["compiler_adopted"] for row in private),
                     "not_adopted": sum(not row["compiler_adopted"] for row in private)},
        "counts": dict(counts),
        "claim_guard": (
            "Passing supports a preregistered Text2Opt benchmark formulation-accuracy improvement over Base. "
            "It does not establish universal semantic equivalence or eliminate public-benchmark contamination."
        ),
    }
    return public, private


__all__ = ["METHODS", "evaluate_v9_confirmation", "v9_confirmation_gate"]
