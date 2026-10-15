"""Development-only evaluation for the V8 source-indexed mechanism."""
from collections import defaultdict

from .confirmatory_statistics import paired_summary, text2opt_match


def evaluate_source_indexed_development(entries, references):
    rows = []
    private = []
    accepted = 0
    accepted_by_category = defaultdict(int)
    corrections_by_category = defaultdict(int)
    for entry in entries:
        problem_id = entry["problem_id"]
        category = entry["category"]
        probe = entry["probe"]
        reference = references[problem_id]
        base = text2opt_match(probe["solve"].get("Base"), reference)
        full = text2opt_match(probe["solve"].get("FullV8"), reference)
        source_indexed = text2opt_match(probe["solve"].get("SourceIndexed"), reference)
        base_unavailable = probe["method_infrastructure_unavailable"].get("Base") is True
        full_unavailable = probe["method_infrastructure_unavailable"].get("FullV8") is True
        adopted = probe.get("reports", {}).get("full_gate", {}).get("accepted") is True
        accepted += int(adopted)
        accepted_by_category[category] += int(adopted)
        corrections_by_category[category] += int(full and not base)
        rows.append({
            "category": category,
            "candidate": full, "comparator": base,
            "candidate_infrastructure_unavailable": full_unavailable,
            "comparator_infrastructure_unavailable": base_unavailable,
        })
        private.append({
            "problem_id": problem_id, "category": category, "base": base,
            "source_indexed": source_indexed, "full_v8": full, "adopted": adopted,
            "base_infrastructure_unavailable": base_unavailable,
            "full_v8_infrastructure_unavailable": full_unavailable,
        })
    comparison = paired_summary(rows)
    correcting_categories = sum(value > 0 for value in corrections_by_category.values())
    report = {
        "schema": "source-indexed-development-evaluation-v1",
        "records": len(entries),
        "comparison": comparison,
        "source_indexed_accepted": accepted,
        "source_indexed_acceptance_rate": accepted / len(entries),
        "accepted_by_category": dict(sorted(accepted_by_category.items())),
        "correcting_categories": correcting_categories,
    }
    return report, private


def stage1_gate(report):
    comparison = report["comparison"]
    checks = {
        "paired_completion_at_least_90pct": comparison["paired_completion_rate"] >= 0.90,
        "source_indexed_accepted_at_least_five": report["source_indexed_accepted"] >= 5,
        "corrections_at_least_two": comparison["corrections"] >= 2,
        "regressions_at_most_one": comparison["regressions"] <= 1,
        "net_corrections_at_least_one": comparison["corrections"] - comparison["regressions"] >= 1,
        "at_least_one_correcting_category": report["correcting_categories"] >= 1,
    }
    return {"checks": checks, "passed": all(checks.values())}


def final_development_gate(report):
    comparison = report["comparison"]
    checks = {
        "paired_completion_at_least_95pct": comparison["paired_completion_rate"] >= 0.95,
        "source_indexed_acceptance_rate_at_least_50pct": report["source_indexed_acceptance_rate"] >= 0.50,
        "accuracy_delta_at_least_3pp": comparison["accuracy_delta"] >= 0.03,
        "corrections_at_least_five": comparison["corrections"] >= 5,
        "regressions_at_most_two": comparison["regressions"] <= 2,
        "corrections_at_least_twice_regressions": comparison["corrections"] >= 2*max(1, comparison["regressions"]),
        "one_sided_exact_p_at_most_010": comparison["paired_one_sided_exact_p"] <= 0.10,
        "positive_in_at_least_two_categories": comparison["positive_categories"] >= 2,
        "negative_in_at_most_one_category": comparison["negative_categories"] <= 1,
    }
    return {"checks": checks, "passed": all(checks.values())}


__all__ = ["evaluate_source_indexed_development", "final_development_gate", "stage1_gate"]
