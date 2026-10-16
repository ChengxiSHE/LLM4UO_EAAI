"""Body-free common-protocol synthesis for the fresh 38-instance endpoint."""

import hashlib
import json
import math
from pathlib import Path
from typing import Any


VERSION = "fresh-common38-common-protocol-synthesis-v1"
OUTPUT_PATH = "experiments/fresh_common38_common_protocol_synthesis_20261015.json"
REPORT_PATH = "docs/FRESH_COMMON38_COMMON_PROTOCOL_SYNTHESIS_20261015.md"
INPUTS = {
    "current": "experiments/fresh_common38_current_native_result_20261015.json",
    "base": "experiments/fresh_common38_base_result_v1_20261015.json",
    "bind": "experiments/fresh_common38_bind_result_v2_20261015.json",
    "coe": "experiments/fresh_common38_coe_current_result_v2_20261015.json",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    values = {}; hashes = {}
    for name, relative in INPUTS.items():
        path = root / relative
        values[name] = json.loads(path.read_text())
        hashes[relative] = _sha(path)
    return values, hashes


def _maps(values: dict[str, Any]) -> tuple[dict[str, dict[str, bool]], dict[str, str]]:
    maps = {
        "current": {row["id"]: bool(row["correct"]) for row in values["current"]["rows"]},
        "base": {row["id"]: bool(row["correct"]) for row in values["base"]["rows"]},
        "bind_round_one": {row["id"]: bool(row["round_one_correct"]) for row in values["bind"]["rows"]},
        "bind_final": {row["id"]: bool(row["final_correct"]) for row in values["bind"]["rows"]},
        "coe_safe": {row["id"]: bool(row["author_exact"]) for row in values["coe"]["rows"]},
    }
    family = {row["id"]: row["family"] for row in values["current"]["rows"]}
    identities = set(family)
    if len(identities) != 38 or any(set(value) != identities for value in maps.values()):
        raise ValueError("common_identity_mismatch")
    return maps, family


def _families(outcomes: dict[str, bool], family: dict[str, str]) -> dict[str, dict[str, int]]:
    result = {}
    for name in ("rcpsp", "vrptw"):
        selected = [problem_id for problem_id in outcomes if family[problem_id] == name]
        result[name] = {"correct": sum(outcomes[i] for i in selected), "planned": len(selected)}
    return result


def _sign_tail(corrections: int, regressions: int) -> float:
    discordant = corrections + regressions
    if not discordant:
        return 1.0
    return math.fsum(
        math.comb(discordant, k) for k in range(corrections, discordant + 1)
    ) / (2 ** discordant)


def _paired(
    label: str, current: dict[str, bool], comparator: dict[str, bool]
) -> dict[str, Any]:
    identities = sorted(current)
    corrections = sum(current[i] and not comparator[i] for i in identities)
    regressions = sum(comparator[i] and not current[i] for i in identities)
    both = sum(current[i] and comparator[i] for i in identities)
    neither = len(identities) - corrections - regressions - both
    return {
        "comparison": label, "planned_pairs": len(identities),
        "corrections": corrections, "regressions": regressions,
        "both_correct": both, "neither_correct": neither,
        "paired_accuracy_delta": (corrections - regressions) / len(identities),
        "discordant_pairs": corrections + regressions,
        "one_sided_exact_sign_p": _sign_tail(corrections, regressions),
    }


def _holm(rows: list[dict[str, Any]], alpha: float = 0.05) -> None:
    ordered = sorted(enumerate(rows), key=lambda item: item[1]["one_sided_exact_sign_p"])
    running = 0.0; count = len(rows)
    for rank, (index, row) in enumerate(ordered):
        adjusted = min(1.0, (count - rank) * row["one_sided_exact_sign_p"])
        running = max(running, adjusted)
        rows[index]["holm_adjusted_p"] = running
        rows[index]["holm_reject_0_05"] = running <= alpha


def build_synthesis(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve(); values, hashes = _load(root); maps, family = _maps(values)
    labels = {
        "current": "Proof-carrying compilation", "base": "Base",
        "bind_round_one": "BIND round 1", "bind_final": "BIND final",
        "coe_safe": "CoE-safe",
    }
    resource = {
        "current": {"max_external_calls_per_identity": 0, "actual_logical_requests": 0, "provider_tokens": 0},
        "base": {"max_external_calls_per_identity": 1, "actual_logical_requests": values["base"]["accounting"]["logical_requests"], "provider_tokens": values["base"]["accounting"]["logical_tokens"]},
        "bind_round_one": {"max_external_calls_per_identity": 1, "actual_logical_requests": None, "provider_tokens": None, "accounting_scope": "shared_with_bind_final_trajectory"},
        "bind_final": {"max_external_calls_per_identity": 3, "actual_logical_requests": values["bind"]["accounting"]["logical_requests"], "provider_tokens": values["bind"]["accounting"]["logical_tokens"]},
        "coe_safe": {"max_external_calls_per_identity": 11, "actual_logical_requests": values["coe"]["accounting"]["logical_requests"], "provider_tokens": values["coe"]["accounting"]["logical_tokens"]},
    }
    order = ("current", "base", "bind_round_one", "bind_final", "coe_safe")
    method_rows = [{
        "method": labels[key], "planned": 38, "correct": sum(maps[key].values()),
        "accuracy": sum(maps[key].values()) / 38,
        "families": _families(maps[key], family), "inference_resources": resource[key],
        "answer_bearing_feedback": key == "bind_final",
    } for key in order]
    pairs = [
        _paired("current_vs_base", maps["current"], maps["base"]),
        _paired("current_vs_bind_round_one", maps["current"], maps["bind_round_one"]),
        _paired("current_vs_bind_final", maps["current"], maps["bind_final"]),
        _paired("current_vs_coe_safe", maps["current"], maps["coe_safe"]),
    ]
    _holm(pairs)
    bind_transition = _paired(
        "bind_final_vs_bind_round_one", maps["bind_final"], maps["bind_round_one"],
    )
    strict_keys = ("current", "bind_round_one", "base")
    strict_rows = [next(row for row in method_rows if row["method"] == labels[key]) for key in strict_keys]
    return {
        "schema": VERSION, "status": "complete", "cohort": {"planned": 38, "rcpsp": 13, "vrptw": 25},
        "input_sha256": hashes, "identity_alignment_verified": True,
        "method_native_rows": method_rows, "paired_against_current": pairs,
        "bind_answer_bearing_transition": bind_transition,
        "sensitivity_views": {
            "answer_blind_at_most_one_external_call": {
                "estimand": "full_denominator_accuracy_under_an_inference_ceiling_of_at_most_one_external_model_call_per_identity",
                "included": strict_rows,
                "excluded": [{
                    "method": "CoE-safe",
                    "reason": "official_protocol_has_no_valid_terminal_artifact_after_one_call",
                }, {
                    "method": "BIND final",
                    "reason": "answer_bearing_repair_can_use_more_than_one_call",
                }],
                "construction_cost_equalized": False,
            },
            "method_native_up_to_eleven_call_ceiling": {
                "estimand": "descriptive_accuracy_when_each_method_uses_its_prespecified_native_trajectory_within_a_common_eleven_call_ceiling",
                "included": method_rows, "consumption_equalized": False,
            },
        },
        "inference": {
            "test": "one_sided_exact_conditional_McNemar_sign_test_on_discordant_pairs",
            "familywise_control": "Holm", "familywise_alpha": 0.05,
            "confirmatory_comparisons": 4,
        },
        "privacy": {
            "contains_credentials": False, "contains_problem_bodies": False,
            "contains_request_bodies": False, "contains_response_bodies": False,
            "contains_objectives": False, "contains_points": False,
            "contains_reference_values": False,
        },
        "claim_boundary": {
            "fixed_fresh_common_endpoint_only": True,
            "broad_benchmark_superiority_supported": False,
            "construction_cost_equalized": False,
            "current_knowledge_acquisition_was_authored": True,
            "component_causality_supported": False,
            "coe_current_repository_license_and_release_package_unverified": True,
            "infrastructure_unavailable_retained_in_full_denominator": True,
        },
    }


def render_markdown(value: dict[str, Any]) -> str:
    lines = [
        "# Fresh common-38 common-protocol synthesis", "",
        "Status: **complete, fixed-endpoint evidence; not broad benchmark superiority**.", "",
        "## Method-native full-denominator results", "",
        "| Method | Correct / 38 | Accuracy | RCPSP | VRPTW | Max external calls / item |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in value["method_native_rows"]:
        lines.append(
            f"| {row['method']} | {row['correct']}/38 | {100*row['accuracy']:.2f}% | "
            f"{row['families']['rcpsp']['correct']}/13 | {row['families']['vrptw']['correct']}/25 | "
            f"{row['inference_resources']['max_external_calls_per_identity']} |"
        )
    lines += ["", "## Paired contrasts against proof-carrying compilation", "",
              "| Comparison | Corrections | Regressions | Delta | Exact one-sided p | Holm p |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in value["paired_against_current"]:
        lines.append(
            f"| {row['comparison']} | {row['corrections']} | {row['regressions']} | "
            f"{100*row['paired_accuracy_delta']:.2f} pp | {row['one_sided_exact_sign_p']:.6g} | "
            f"{row['holm_adjusted_p']:.6g} |"
        )
    lines += [
        "", "All tests retain the 38-instance denominator. Holm correction covers the four prespecified current-method contrasts.",
        "", "## Budget sensitivity", "",
        "Under the answer-blind ceiling of at most one external model call per item, the valid terminal methods are proof-carrying compilation (30/38), BIND round 1 (13/38), and Base (0/38). CoE-safe has no official one-call terminal artifact, while BIND final can use answer-bearing repair and more than one call. This view equalizes the inference-call ceiling, not library construction cost or provider tokens.",
        "", "## Claim boundary", "",
        "The result supports a large, statistically clear advantage on this fixed fresh RCPSP/VRPTW endpoint. It does not establish broad benchmark superiority, automatic knowledge acquisition, or component causality. The current library was authored; G08 acquisition and G09 component experiments remain prospective. CoE is a safe-adapter reproduction from the current official repository snapshot, whose license and complete release package remain unverified.", "",
    ]
    return "\n".join(lines)


__all__ = ["OUTPUT_PATH", "REPORT_PATH", "build_synthesis", "render_markdown"]
