"""Frozen aggregate evaluation for the Base versus V6 confirmation."""
from collections import Counter

from .confirmatory_statistics import paired_summary, text2opt_match, wilson_interval


METHODS = ("Base", "V6")


def _method_summary(private_rows, method):
    planned = len(private_rows)
    unavailable = sum(row["infrastructure"][method] for row in private_rows)
    correct = sum(row["scores"][method] is True for row in private_rows)
    complete = planned - unavailable
    conditional_correct = sum(
        row["scores"][method] is True
        for row in private_rows if not row["infrastructure"][method]
    )
    return {
        "planned_records": planned,
        "infrastructure_unavailable": unavailable,
        "accuracy_all_selected": correct / planned,
        "correct_all_selected": correct,
        "infrastructure_complete_records": complete,
        "accuracy_infrastructure_complete": conditional_correct / complete if complete else None,
        "wilson_95_all_selected": wilson_interval(correct, planned),
    }


def v6_confirmation_gate(report):
    checks = {
        "paired_completion_at_least_99pct": report["paired_completion_rate"] >= 0.99,
        "accuracy_delta_at_least_1pp": report["accuracy_delta"] >= 0.01,
        "at_least_five_corrections": report["corrections"] >= 5,
        "corrections_at_least_four_times_regressions": (
            report["corrections"] >= 4 * max(1, report["regressions"])
        ),
        "one_sided_exact_p_at_most_005": report["paired_one_sided_exact_p"] <= 0.05,
        "positive_in_at_least_two_categories": report["positive_categories"] >= 2,
        "negative_in_at_most_one_category": report["negative_categories"] <= 1,
    }
    return {"checks": checks, "confirmed": all(checks.values())}


def evaluate_v6_confirmation(entries, references):
    if not isinstance(entries, list) or not entries:
        raise ValueError("empty_confirmation_entries")
    if not isinstance(references, dict):
        raise ValueError("invalid_confirmation_references")
    private_rows = []
    counts = Counter()
    for entry in entries:
        problem_id = entry["problem_id"]
        probe = entry["probe"]
        if problem_id not in references or probe.get("problem_id") != problem_id:
            raise ValueError("confirmation_reference_or_probe_binding")
        infrastructure = probe.get("method_infrastructure_unavailable")
        if not isinstance(infrastructure, dict) or set(infrastructure) != set(METHODS):
            raise ValueError("confirmation_infrastructure_schema")
        scores = {}
        for method in METHODS:
            if type(infrastructure[method]) is not bool:
                raise ValueError("confirmation_infrastructure_value")
            scores[method] = text2opt_match(probe.get("solve", {}).get(method), references[problem_id])
            counts[method + (":correct" if scores[method] else ":incorrect")] += 1
            counts[method + ":infrastructure_unavailable"] += infrastructure[method]
        private_rows.append({
            "problem_id": problem_id, "category": entry["category"],
            "scores": scores, "infrastructure": infrastructure,
            "probe_status": probe.get("status"),
            "v6_status": probe.get("reports", {}).get("v6", {}).get("status"),
        })
    paired = [{
        "category": row["category"],
        "candidate": row["scores"]["V6"],
        "comparator": row["scores"]["Base"],
        "candidate_infrastructure_unavailable": row["infrastructure"]["V6"],
        "comparator_infrastructure_unavailable": row["infrastructure"]["Base"],
    } for row in private_rows]
    comparison = paired_summary(paired)
    public = {
        "schema": "text2opt-v6-confirmation-evaluation-v1",
        "records": len(private_rows),
        "categories": len({row["category"] for row in private_rows}),
        "method_summaries": {
            method: _method_summary(private_rows, method) for method in METHODS
        },
        "comparison": comparison,
        "confirmation_gate": v6_confirmation_gate(comparison),
        "counts": dict(counts),
        "claim_guard": (
            "Passing supports a pre-registered external benchmark formulation-accuracy improvement for V6 "
            "over Base. It does not establish universal semantic equivalence or remove public-data contamination."
        ),
    }
    return public, private_rows


__all__ = ["METHODS", "evaluate_v6_confirmation", "v6_confirmation_gate"]
