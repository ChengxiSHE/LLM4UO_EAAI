"""Aggregate-only Text2Opt confirmation scoring after the run is frozen."""
from collections import Counter

from .confirmatory_statistics import confirmation_gate, paired_summary, text2opt_match, wilson_interval


METHODS = ("Base", "V6", "DualLedger", "FullV7")


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
        "accuracy_all_selected": correct/planned,
        "correct_all_selected": correct,
        "infrastructure_complete_records": complete,
        "accuracy_infrastructure_complete": conditional_correct/complete if complete else None,
        "wilson_95_all_selected": wilson_interval(correct, planned),
    }


def evaluate_confirmation(entries, references):
    """Score private records and return public aggregate plus private rows."""
    if not isinstance(entries, list) or not entries:
        raise ValueError("empty_confirmation_entries")
    if not isinstance(references, dict):
        raise ValueError("invalid_confirmation_references")
    private_rows = []
    counts = Counter()
    for entry in entries:
        pid = entry["problem_id"]
        category = entry["category"]
        probe = entry["probe"]
        if pid not in references or probe.get("problem_id") != pid:
            raise ValueError("confirmation_reference_or_probe_binding")
        infrastructure = probe.get("method_infrastructure_unavailable")
        if not isinstance(infrastructure, dict) or set(infrastructure) != set(METHODS):
            raise ValueError("confirmation_infrastructure_schema")
        scores = {}
        for method in METHODS:
            if type(infrastructure[method]) is not bool:
                raise ValueError("confirmation_infrastructure_value")
            scores[method] = text2opt_match(probe.get("solve", {}).get(method), references[pid])
            counts[method + (":correct" if scores[method] else ":incorrect")] += 1
            counts[method + ":infrastructure_unavailable"] += infrastructure[method]
        private_rows.append({
            "problem_id": pid,
            "category": category,
            "scores": scores,
            "infrastructure": infrastructure,
            "probe_status": probe.get("status"),
            "dual_status": probe.get("reports", {}).get("dual_ledger", {}).get("status"),
        })

    comparisons = {}
    for comparator in ("Base", "V6"):
        paired = [{
            "category": row["category"],
            "candidate": row["scores"]["FullV7"],
            "comparator": row["scores"][comparator],
            "candidate_infrastructure_unavailable": row["infrastructure"]["FullV7"],
            "comparator_infrastructure_unavailable": row["infrastructure"][comparator],
        } for row in private_rows]
        comparisons["FullV7_vs_" + comparator] = paired_summary(paired)
    gate = confirmation_gate(
        comparisons["FullV7_vs_Base"], comparisons["FullV7_vs_V6"]
    )
    public = {
        "schema": "text2opt-confirmation-evaluation-v1",
        "records": len(private_rows),
        "categories": len({row["category"] for row in private_rows}),
        "method_summaries": {method: _method_summary(private_rows, method) for method in METHODS},
        "comparisons": comparisons,
        "joint_confirmation_gate": gate,
        "counts": dict(counts),
        "claim_guard": (
            "A confirmed result requires the frozen joint gate. Semantic equivalence and public-data "
            "contamination remain separate limitations."
        ),
    }
    return public, private_rows


__all__ = ["METHODS", "evaluate_confirmation"]
