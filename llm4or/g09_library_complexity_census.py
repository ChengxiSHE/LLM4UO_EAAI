"""Exact finite census isolating library-level complexity control for G09."""

from __future__ import annotations

from collections import Counter
import hashlib
from itertools import product
from pathlib import Path
from typing import Any

from .g09_component_census import _envelope_population
from .schema import canonical, digest


VERSION = "g09-library-complexity-census-v1"
OUTPUT_PATH = "experiments/g09_library_complexity_census_20261015.json"
REPORT_PATH = "docs/G09_LIBRARY_COMPLEXITY_CENSUS_20261015.md"
SOURCE_PATHS = (
    "experiments/prospective_research_program_decision_20261015.json",
    "docs/KNOWLEDGE_EVOLUTION_THEORETICAL_FRAMEWORK_20261015.md",
    "manuscript/SUPPLEMENTARY_THEORY.md",
    "llm4or/g09_component_census.py",
    "llm4or/g09_library_complexity_census.py",
)
WITNESS_SHIFTS = (
    "empty",
    "unrelated",
    "new_family",
    "rcpsp_missing_budget",
    "vrptw_renamed_customer_coordinates",
    "union_exact",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rules(envelopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_shift = {row["shift"]: row for row in envelopes}
    if set(WITNESS_SHIFTS) - set(by_shift):
        raise ValueError("witness_shift_population")
    rules = []
    for index, shift in enumerate(WITNESS_SHIFTS):
        row = by_shift[shift]
        if row["multiplicity"] == "unique":
            raise ValueError("witness_must_require_fallback")
        payload = {
            "schema": "g09-optional-shadow-guard-v1",
            "envelope_id": row["envelope_id"],
            "forced_action": "rcpsp" if index % 2 == 0 else "vrptw",
        }
        rules.append({
            **payload,
            "rule_id": digest(payload),
            "shift_class": shift,
            "payload_bits": 8 * len(canonical(payload).encode("utf-8")),
        })
    if len({row["rule_id"] for row in rules}) != len(WITNESS_SHIFTS):
        raise ValueError("rule_identity")
    return rules


def _candidates(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for membership in product((0, 1), repeat=len(rules)):
        active = [rules[index] for index, bit in enumerate(membership) if bit]
        identity = {
            "schema": "g09-library-candidate-v1",
            "base_policy": "exactly_one_else_fallback",
            "optional_rule_ids": [row["rule_id"] for row in active],
        }
        rows.append({
            "candidate_id": digest(identity),
            "membership": "".join(str(bit) for bit in membership),
            "optional_rules": len(active),
            "code_length_bits": len(rules) + sum(row["payload_bits"] for row in active),
            "incorrect_envelope_ids": [row["envelope_id"] for row in active],
        })
    if len(rows) != 64 or len({row["candidate_id"] for row in rows}) != 64:
        raise ValueError("candidate_population")
    return rows


def _episodes(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for membership in product((0, 1), repeat=len(rules)):
        calibrated = [rules[index]["envelope_id"]
                      for index, bit in enumerate(membership) if bit]
        rows.append({
            "episode_id": digest({"calibration_envelope_ids": calibrated}),
            "calibration_membership": "".join(str(bit) for bit in membership),
            "calibration_envelope_ids": calibrated,
        })
    if len(rows) != 64 or len({row["episode_id"] for row in rows}) != 64:
        raise ValueError("episode_population")
    return rows


def _select(
    candidates: list[dict[str, Any]],
    calibration: set[str],
    arm: str,
) -> tuple[dict[str, Any], int]:
    admitted = [row for row in candidates
                if not calibration.intersection(row["incorrect_envelope_ids"])]
    if not admitted:
        raise ValueError("empty_admitted_pool")
    if arm == "proof_constrained_mdl":
        key = lambda row: (row["code_length_bits"], row["candidate_id"])
    elif arm == "proof_only_frozen_hash":
        key = lambda row: (row["candidate_id"],)
    else:
        raise ValueError("arm")
    return min(admitted, key=key), len(admitted)


def build_census(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    envelopes = _envelope_population()
    rules = _rules(envelopes)
    candidates = _candidates(rules)
    episodes = _episodes(rules)
    arm_names = ("proof_constrained_mdl", "proof_only_frozen_hash")
    rows = []
    totals = {name: {"fully_correct_libraries": 0, "routing_decisions_correct": 0,
                     "selected_optional_rules": 0} for name in arm_names}
    paired = {
        "mdl_only_fully_correct": 0,
        "control_only_fully_correct": 0,
        "both_fully_correct": 0,
        "neither_fully_correct": 0,
        "mdl_routing_corrections": 0,
        "mdl_routing_regressions": 0,
        "same_routing_decision_correctness": 0,
    }
    for episode in episodes:
        selected = {}
        admitted_count = None
        for arm in arm_names:
            choice, current_count = _select(
                candidates, set(episode["calibration_envelope_ids"]), arm)
            if admitted_count is None:
                admitted_count = current_count
            elif admitted_count != current_count:
                raise ValueError("arm_pool_mismatch")
            correct = len(envelopes) - choice["optional_rules"]
            fully_correct = choice["optional_rules"] == 0
            selected[arm] = {
                "candidate_id": choice["candidate_id"],
                "code_length_bits": choice["code_length_bits"],
                "optional_rules": choice["optional_rules"],
                "fully_correct": fully_correct,
                "routing_decisions_correct": correct,
            }
            totals[arm]["fully_correct_libraries"] += int(fully_correct)
            totals[arm]["routing_decisions_correct"] += correct
            totals[arm]["selected_optional_rules"] += choice["optional_rules"]
        mdl = selected["proof_constrained_mdl"]
        control = selected["proof_only_frozen_hash"]
        if mdl["fully_correct"] and control["fully_correct"]:
            paired["both_fully_correct"] += 1
        elif mdl["fully_correct"]:
            paired["mdl_only_fully_correct"] += 1
        elif control["fully_correct"]:
            paired["control_only_fully_correct"] += 1
        else:
            paired["neither_fully_correct"] += 1
        paired["mdl_routing_corrections"] += max(
            0, mdl["routing_decisions_correct"] - control["routing_decisions_correct"])
        paired["mdl_routing_regressions"] += max(
            0, control["routing_decisions_correct"] - mdl["routing_decisions_correct"])
        paired["same_routing_decision_correctness"] += min(
            mdl["routing_decisions_correct"], control["routing_decisions_correct"])
        rows.append({
            "episode_id": episode["episode_id"],
            "calibration_membership": episode["calibration_membership"],
            "calibration_envelopes": len(episode["calibration_envelope_ids"]),
            "admitted_candidates": admitted_count,
            "selected": selected,
        })
    arms = [{
        "arm": name,
        "episodes": len(episodes),
        "fully_correct_libraries": totals[name]["fully_correct_libraries"],
        "routing_decisions_planned": len(episodes) * len(envelopes),
        "routing_decisions_correct": totals[name]["routing_decisions_correct"],
        "selected_optional_rules": totals[name]["selected_optional_rules"],
    } for name in arm_names]
    return {
        "schema": VERSION,
        "status": "complete_exact_finite_population_census",
        "input_sha256": {relative: _sha(root / relative) for relative in SOURCE_PATHS},
        "population": {
            "population_definition": "complete_authored_six_shadow_guard_library_and_calibration_subset_grammar",
            "optional_shadow_guards": len(rules),
            "candidate_libraries": len(candidates),
            "calibration_episodes": len(episodes),
            "routing_envelopes": len(envelopes),
            "unique_candidate_hashes": len({row["candidate_id"] for row in candidates}),
            "unique_episode_hashes": len({row["episode_id"] for row in episodes}),
            "same_candidate_pool_every_episode": True,
            "code_frozen_before_episode_labels": True,
        },
        "prefix_code": {
            "membership_header_bits": len(rules),
            "decoder": "fixed_membership_header_followed_by_the_predeclared_payload_for_each_active_rule",
            "prefix_free": True,
            "label_independent": True,
            "common_base_payload_omitted_as_an_arm_invariant": True,
            "rule_payload_bits": {row["rule_id"]: row["payload_bits"] for row in rules},
        },
        "rules": [{key: row[key] for key in (
            "rule_id", "shift_class", "envelope_id", "forced_action", "payload_bits"
        )} for row in rules],
        "candidate_library_hashes": [row["candidate_id"] for row in candidates],
        "arms": arms,
        "paired": paired,
        "selected_optional_rule_distribution": {
            name: dict(sorted(Counter(
                row["selected"][name]["optional_rules"] for row in rows
            ).items())) for name in arm_names
        },
        "episodes": rows,
        "inference": {
            "sampling_based_p_value": False,
            "reason": "complete_deterministic_census_of_the_frozen_library_and_calibration_episode_grammar",
        },
        "claim_boundary": {
            "bounded_complexity_effect_identified": True,
            "exact_only_for_authored_shadow_guard_grammar": True,
            "natural_library_distribution_generalization": False,
            "current_authored_library_length_measured": False,
            "benchmark_accuracy_claimed": False,
            "library_promoted": False,
        },
        "privacy": {
            "contains_credentials": False,
            "contains_problem_bodies": False,
            "contains_request_bodies": False,
            "contains_response_bodies": False,
            "contains_reference_answers": False,
            "contains_evaluator_only_answers": False,
        },
        "execution": {
            "api_calls": 0,
            "credentials_read": False,
            "model_calls": 0,
            "native_calls": 0,
            "solver_calls": 0,
            "vm_calls": 0,
        },
    }


def render_markdown(value: dict[str, Any]) -> str:
    arms = {row["arm"]: row for row in value["arms"]}
    mdl = arms["proof_constrained_mdl"]
    control = arms["proof_only_frozen_hash"]
    paired = value["paired"]
    return f"""# G09 library-complexity census

Status: **complete for the frozen finite library-selection population**.

## Design

The common pool contains all 64 libraries induced by six optional shadow guards on top of the already verified exactly-one-or-fallback router. Each optional branch overrides one public zero- or multiple-match envelope and is therefore an overfitting branch: it can fit any calibration subset that omits its witness but fails that witness in the full 69-envelope endpoint. The complete episode population contains all 64 calibration subsets. Both arms see the same admitted candidate pool in every episode. The treatment chooses the shortest candidate under a label-independent prefix code and the control uses a frozen content-hash tie-break only.

The six-bit membership header declares the suffix payloads, so the code is self-delimiting and prefix-free. Code lengths, candidate identities, the pool, calibration subsets and endpoint were frozen independently of episode labels.

## Exact result

| Selector | Fully correct libraries | Correct routing decisions | Selected optional branches |
|---|---:|---:|---:|
| Proof-constrained MDL | {mdl['fully_correct_libraries']}/64 | {mdl['routing_decisions_correct']}/{mdl['routing_decisions_planned']} | {mdl['selected_optional_rules']} |
| Proof-only frozen hash | {control['fully_correct_libraries']}/64 | {control['routing_decisions_correct']}/{control['routing_decisions_planned']} | {control['selected_optional_rules']} |

The paired census contains **{paired['mdl_only_fully_correct']} fully correct library selections** unique to MDL, {paired['control_only_fully_correct']} unique to control, {paired['both_fully_correct']} correct under both and {paired['neither_fully_correct']} under neither. At the routing-decision level, MDL produces {paired['mdl_routing_corrections']} corrections and {paired['mdl_routing_regressions']} regressions relative to the frozen hash control.

## Boundary

This is an exact causal contrast over the complete authored shadow-guard grammar, not a sample from natural library evolution. It identifies why a label-independent complexity preference can reject gratuitous branches after proof constraints, but it does not measure the description length of the current authored TSP/OR libraries, establish behavior under a natural proposer distribution, add benchmark-accuracy evidence or perform promotion. No sampling p-value is attached. No API, model, solver, native evaluator, VM, credential, problem body, request body, response body or reference answer was used.
"""


__all__ = ["OUTPUT_PATH", "REPORT_PATH", "build_census", "render_markdown"]
