"""Exact finite-population component censuses for G09."""

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .schema import digest
from .structured_or_skills import RCPSP_KEYS, VRPTW_KEYS, route_instance
from .typed_count_skill import enumerate_candidates, measure_candidate_components


VERSION = "g09-finite-component-census-v2"
OUTPUT_PATH = "experiments/g09_finite_component_census_v2_20261015.json"
REPORT_PATH = "docs/G09_FINITE_COMPONENT_CENSUS_V2_20261015.md"
PLAN_PATH = "docs/superpowers/plans/2026-10-15-g09-finite-component-census.md"
SOURCE_PATHS = (
    PLAN_PATH,
    "experiments/prospective_research_program_decision_20261015.json",
    "llm4or/typed_count_skill.py",
    "llm4or/structured_or_skills.py",
    "results/dcp_typed_count_repair_input_20261014.json",
    "results/dcp_count_public_binding_preview_20261014.json",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _public_cases(root: Path) -> list[dict[str, int]]:
    repair = json.loads((root / "results/dcp_typed_count_repair_input_20261014.json").read_text())
    preview = json.loads((root / "results/dcp_count_public_binding_preview_20261014.json").read_text())
    expected = repair["public_cases_sha256"]
    rows = preview.get("rows")
    cases = sorted(
        [row["instance"] for row in rows or []
         if row.get("contract_kind_for_analysis_only") == "partial_fixed_tail"],
        key=lambda row: (row["n"], row["m"]),
    )
    if not cases or digest(cases) != expected:
        raise ValueError("public_case_binding")
    return cases


def _admission_census(root: Path) -> dict[str, Any]:
    cases = _public_cases(root); rows = []
    for candidate in enumerate_candidates():
        verification = measure_candidate_components(candidate, cases)
        semantic = bool(verification["semantic"]["passed"])
        resource = bool(verification["resources"]["passed"])
        safe = semantic and resource
        decisions = {"full": safe, "no_semantic": resource, "no_resource": semantic}
        rows.append({
            "candidate_sha256": verification["candidate_sha256"],
            "semantic_passed": semantic, "resource_passed": resource,
            "safe_admission": safe,
            "semantic_failure_code": verification["semantic_failure_code"],
            "resource_failure_code": verification["resource_failure_code"],
            "decisions": decisions,
        })
    if len(rows) != 64 or len({row["candidate_sha256"] for row in rows}) != 64:
        raise ValueError("candidate_population")
    arms = []
    for arm in ("full", "no_semantic", "no_resource"):
        admitted = sum(row["decisions"][arm] for row in rows)
        unsafe = sum(row["decisions"][arm] and not row["safe_admission"] for row in rows)
        false_reject = sum(not row["decisions"][arm] and row["safe_admission"] for row in rows)
        arms.append({
            "arm": arm, "admitted": admitted, "unsafe_admissions": unsafe,
            "safe_admissions_rejected": false_reject,
            "correct_admission_decisions": len(rows) - unsafe - false_reject,
        })
    no_semantic = next(row for row in arms if row["arm"] == "no_semantic")
    no_resource = next(row for row in arms if row["arm"] == "no_resource")
    return {
        "population": len(rows), "unique_candidate_hashes": len(rows),
        "population_definition": "complete_frozen_64_member_typed_count_grammar",
        "semantic_failure_code_counts": dict(sorted(Counter(
            row["semantic_failure_code"] or "accepted" for row in rows
        ).items())),
        "resource_failure_code_counts": dict(sorted(Counter(
            row["resource_failure_code"] or "accepted" for row in rows
        ).items())),
        "semantic_resource_cells": {
            f"semantic_{int(semantic)}_resource_{int(resource)}": count
            for (semantic, resource), count in sorted(Counter(
                (row["semantic_passed"], row["resource_passed"]) for row in rows
            ).items())
        },
        "arms": arms,
        "paired_full_vs_no_semantic": {
            "full_prevents_unsafe_admission": no_semantic["unsafe_admissions"],
            "no_semantic_prevents_safe_admission": no_semantic["safe_admissions_rejected"],
            "same_decision": len(rows) - no_semantic["unsafe_admissions"] - no_semantic["safe_admissions_rejected"],
        },
        "paired_full_vs_no_resource": {
            "full_prevents_unsafe_admission": no_resource["unsafe_admissions"],
            "no_resource_prevents_safe_admission": no_resource["safe_admissions_rejected"],
            "same_decision": len(rows) - no_resource["unsafe_admissions"] - no_resource["safe_admissions_rejected"],
        },
        "semantic_identifiability": "identified_non_nested_complete_finite_grammar",
        "rows": rows,
    }


def _envelope_population() -> list[dict[str, Any]]:
    families = {"rcpsp": set(RCPSP_KEYS), "vrptw": set(VRPTW_KEYS)}
    rows: list[tuple[str, str, set[str]]] = [
        ("zero", "empty", set()),
        ("zero", "unrelated", {"unrelated_a", "unrelated_b"}),
        ("zero", "new_family", {"graph", "nodes", "edges", "weights"}),
    ]
    for family, keys in families.items():
        for key in sorted(keys):
            rows.append(("zero", f"{family}_missing_{key}", keys - {key}))
            rows.append(("zero", f"{family}_renamed_{key}",
                         (keys - {key}) | {"shift_" + hashlib.sha256(key.encode()).hexdigest()[:12]}))
    for family, keys in families.items():
        other = "vrptw" if family == "rcpsp" else "rcpsp"
        rows.append(("unique", f"{family}_exact", set(keys)))
        rows.append(("unique", f"{family}_additive", set(keys) | {"unknown_extension"}))
        for missing in sorted(families[other]):
            rows.append(("unique", f"{family}_partial_{other}_without_{missing}",
                         set(keys) | (families[other] - {missing})))
    union = families["rcpsp"] | families["vrptw"]
    rows.extend([
        ("multiple", "union_exact", union),
        ("multiple", "union_additive", union | {"unknown_extension"}),
    ])
    output = []
    for multiplicity, shift, keys in rows:
        value = {key: None for key in keys}
        matches = [name for name, required in families.items() if required <= keys]
        observed = "zero" if not matches else "unique" if len(matches) == 1 else "multiple"
        if observed != multiplicity:
            raise ValueError("envelope_multiplicity")
        output.append({
            "envelope_id": digest({"multiplicity": multiplicity, "shift": shift, "keys": sorted(keys)}),
            "multiplicity": multiplicity, "shift": shift, "data": value,
            "matches": sorted(matches),
        })
    if len(output) != 69 or len({row["envelope_id"] for row in output}) != 69:
        raise ValueError("envelope_population")
    return output


def _policy_action(row: dict[str, Any], policy: str) -> str:
    matches = row["matches"]
    if policy == "exactly_one":
        try:
            return route_instance(row["data"])
        except ValueError:
            return "fallback"
    if policy == "forced_first":
        return matches[0] if matches else "rcpsp"
    if policy == "relaxed_multiple":
        return matches[0] if matches else "fallback"
    raise ValueError("policy")


def _routing_census() -> dict[str, Any]:
    population = _envelope_population(); policies = []; correctness = {}
    for policy in ("exactly_one", "forced_first", "relaxed_multiple"):
        values = {}
        for row in population:
            expected = row["matches"][0] if row["multiplicity"] == "unique" else "fallback"
            values[row["envelope_id"]] = _policy_action(row, policy) == expected
        correctness[policy] = values
        policies.append({
            "policy": policy, "planned": len(population), "correct": sum(values.values()),
            "incorrect": len(population) - sum(values.values()),
        })
    exact, forced = correctness["exactly_one"], correctness["forced_first"]
    return {
        "population": len(population),
        "population_definition": "complete_frozen_key_transformation_envelope_grammar",
        "multiplicity_counts": dict(sorted(Counter(row["multiplicity"] for row in population).items())),
        "shift_counts": dict(sorted(Counter(
            "missing" if "_missing_" in row["shift"] else
            "renamed" if "_renamed_" in row["shift"] else
            "partial_cross_family" if "_partial_" in row["shift"] else
            "other" for row in population
        ).items())),
        "policies": policies,
        "paired_exactly_one_vs_forced_first": {
            "corrections": sum(exact[key] and not forced[key] for key in exact),
            "regressions": sum(forced[key] and not exact[key] for key in exact),
            "same": sum(exact[key] == forced[key] for key in exact),
        },
        "rows": [{
            "envelope_id": row["envelope_id"], "multiplicity": row["multiplicity"],
            "shift": row["shift"], "expected_action": row["matches"][0] if row["multiplicity"] == "unique" else "fallback",
            "actions": {policy: _policy_action(row, policy) for policy in correctness},
        } for row in population],
    }


def build_census(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    inputs = {relative: _sha(root / relative) for relative in SOURCE_PATHS}
    return {
        "schema": VERSION, "status": "complete_exact_finite_population_census",
        "input_sha256": inputs, "admission_census": _admission_census(root),
        "routing_census": _routing_census(),
        "complexity_control": {
            "empirical_status": "not_estimated", "independent_library_selection_episodes": 0,
            "retained_role": "prefix_code_and_MDL_theory_protocol_component",
        },
        "inference": {
            "sampling_based_p_values": False, "holm_applied": False,
            "reason": "complete_deterministic_censuses_have_no_sampling_uncertainty_for_their_frozen_populations",
        },
        "execution": {
            "api_calls": 0, "credentials_read": False, "model_calls": 0,
            "native_calls": 0, "solver_calls": 0, "vm_calls": 0,
        },
        "privacy": {
            "contains_credentials": False, "contains_problem_bodies": False,
            "contains_request_bodies": False, "contains_response_bodies": False,
            "contains_reference_answers": False, "contains_counterexamples": False,
        },
        "claim_boundary": {
            "exact_only_for_frozen_finite_populations": True,
            "proposer_distribution_generalization": False,
            "unrestricted_shift_robustness": False,
            "semantic_gate_effect_identified_in_typed_count_grammar": True,
            "resource_gate_effect_identified_in_typed_count_grammar": True,
            "exactly_one_routing_effect_identified_in_envelope_grammar": True,
            "complexity_control_causal_effect_identified": False,
            "library_changed_or_promoted": False,
        },
    }


def render_markdown(value: dict[str, Any]) -> str:
    admission = {row["arm"]: row for row in value["admission_census"]["arms"]}
    routing = {row["policy"]: row for row in value["routing_census"]["policies"]}
    return f"""# G09 finite component census

Status: **complete for the two frozen finite populations; broader component causality remains bounded**.

## Admission census

All 64 members of the frozen typed-count grammar were enumerated, and the semantic and resource gates were measured independently rather than short-circuited. The census contains all four semantic/resource cells: 47 fail both gates, 11 fail only semantics, 5 fail only resources, and 1 passes both. Full admission accepts 1/64 with 0 unsafe admissions. Removing the semantic gate accepts 12/64 and creates 11 unsafe admissions; removing the resource gate accepts 6/64 and creates 5 unsafe admissions. The full policy prevents all sixteen unsafe admissions without rejecting the one safe candidate.

| Arm | Admitted | Unsafe admissions | Correct admission decisions |
|---|---:|---:|---:|
| Full | {admission['full']['admitted']} | {admission['full']['unsafe_admissions']} | {admission['full']['correct_admission_decisions']}/64 |
| No semantic gate | {admission['no_semantic']['admitted']} | {admission['no_semantic']['unsafe_admissions']} | {admission['no_semantic']['correct_admission_decisions']}/64 |
| No resource gate | {admission['no_resource']['admitted']} | {admission['no_resource']['unsafe_admissions']} | {admission['no_resource']['correct_admission_decisions']}/64 |

## Routing census

The frozen envelope grammar contains 69 unique key patterns: 43 zero-match, 24 unique-match and 2 multiple-match cases, including missing-key, renamed-key, additive, partial cross-family, unrelated and new-family shifts. Exactly-one routing is correct on all 69. Forced-first routing is correct on 24/69; exactly-one fallback corrects 45 cases with 0 regressions. A policy that falls back only on zero matches but forces ambiguous multiple matches reaches 67/69.

| Policy | Correct |
|---|---:|
| Exactly one, otherwise fallback | {routing['exactly_one']['correct']}/69 |
| Forced first match/default | {routing['forced_first']['correct']}/69 |
| Fallback on zero, force multiple | {routing['relaxed_multiple']['correct']}/69 |

## Complexity and inference boundary

No empirical complexity-control effect is reported because there are no independent common-pool library-selection episodes. Prefix-code/MDL control remains a theoretical and prospective protocol component. These are complete deterministic censuses, so sampling p-values and Holm correction are inapplicable to the frozen populations. The results do not generalize automatically to a proposer distribution or unrestricted schema shift. No API, solver, native evaluator, credential, request body, response body, or reference answer was used.
"""


__all__ = ["OUTPUT_PATH", "REPORT_PATH", "build_census", "render_markdown"]
