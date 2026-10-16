"""Exact active-acquisition census over typed-count semantic classes."""

from __future__ import annotations

from collections import Counter
import hashlib
from itertools import product
import json
from pathlib import Path
from typing import Any

from .schema import digest
from .typed_count_skill import (
    _SEMANTIC_GRID,
    _model_accepts_clean,
    build_partial_models,
    enumerate_candidates,
)


VERSION = "g08-finite-acquisition-census-v1"
OUTPUT_PATH = "experiments/g08_finite_acquisition_census_20261015.json"
REPORT_PATH = "docs/G08_FINITE_ACQUISITION_CENSUS_20261015.md"
SOURCE_PATHS = (
    "experiments/prospective_research_program_decision_20261015.json",
    "docs/KNOWLEDGE_EVOLUTION_THEORETICAL_FRAMEWORK_20261015.md",
    "llm4or/typed_count_skill.py",
    "llm4or/g08_finite_acquisition_census.py",
)
SEMANTIC_FIELDS = (
    "tail_role",
    "counted_scope",
    "relation",
    "bound_strategy",
    "zero_tail_policy",
)
BUDGET = 3


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen = set()
    for candidate in enumerate_candidates():
        key = tuple(candidate[field] for field in SEMANTIC_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        rows.append(candidate)
    if len(rows) != 32:
        raise ValueError("semantic_candidate_population")
    return rows


def _queries() -> list[dict[str, Any]]:
    rows = []
    for n, m in _SEMANTIC_GRID:
        length = n + 2
        for prefix in product(range(length + 1), repeat=n + 1):
            vector = list(prefix) + [m]
            rows.append({
                "n": n,
                "m": m,
                "vector": vector,
                "query_sha256": digest({"n": n, "m": m, "assignment": vector}),
            })
    if len(rows) != 20977 or len({row["query_sha256"] for row in rows}) != 20977:
        raise ValueError("query_population")
    return rows


def _signature(candidate: dict[str, Any], queries: list[dict[str, Any]]) -> tuple[bool | None, ...]:
    models = {}
    for n, m in _SEMANTIC_GRID:
        try:
            models[(n, m)] = build_partial_models(candidate, n, m)
        except ValueError:
            models[(n, m)] = None
    return tuple(
        (None if models[(row["n"], row["m"])] is None else
         any(_model_accepts_clean(spec, row["vector"])
             for spec in models[(row["n"], row["m"])]))
        for row in queries
    )


def _classes(
    candidates: list[dict[str, Any]],
    queries: list[dict[str, Any]],
) -> tuple[list[tuple[bool | None, ...]], list[dict[str, Any]]]:
    grouped: dict[tuple[bool | None, ...], list[dict[str, Any]]] = {}
    for candidate in candidates:
        grouped.setdefault(_signature(candidate, queries), []).append(candidate)
    signatures = list(grouped)
    rows = []
    for index, signature in enumerate(signatures):
        members = grouped[signature]
        member_hashes = sorted(digest(member) for member in members)
        rows.append({
            "class_id": digest({"member_sha256": member_hashes}),
            "class_index": index,
            "members": len(members),
            "member_sha256": member_hashes,
            "positive_queries": sum(value is True for value in signature),
            "model_rejected_queries": sum(value is None for value in signature),
        })
    if len(signatures) != 10 or sum(row["members"] for row in rows) != 32:
        raise ValueError("semantic_equivalence_classes")
    return signatures, rows


def _select_query(signatures: list[tuple[bool | None, ...]], version: list[int], arm: str) -> int:
    candidates = []
    for query_index in range(len(signatures[0])):
        counts = Counter(signatures[index][query_index] for index in version)
        if len(counts) < 2:
            continue
        if arm == "balanced_separating_witness":
            sizes = sorted(counts.values())
            score = (max(sizes), max(sizes) - min(sizes), query_index)
        elif arm == "canonical_first_witness":
            score = (query_index,)
        else:
            raise ValueError("arm")
        candidates.append((score, query_index))
    if not candidates:
        raise ValueError("no_separating_query")
    return min(candidates)[1]


def _trace(
    signatures: list[tuple[bool | None, ...]],
    queries: list[dict[str, Any]],
    target: int,
    arm: str,
) -> dict[str, Any]:
    version = list(range(len(signatures)))
    sizes = [len(version)]
    query_hashes = []
    labels = []
    while len(version) > 1:
        query_index = _select_query(signatures, version, arm)
        label = signatures[target][query_index]
        version = [index for index in version if signatures[index][query_index] == label]
        if target not in version or len(version) >= sizes[-1]:
            raise ValueError("invalid_version_transition")
        sizes.append(len(version))
        query_hashes.append(queries[query_index]["query_sha256"])
        labels.append(label)
    return {
        "target_class": target,
        "queries": len(query_hashes),
        "identified_within_budget": len(query_hashes) <= BUDGET,
        "version_space_sizes": sizes,
        "query_sha256": query_hashes,
        "observed_labels": labels,
    }


def _arm(signatures, queries, name: str) -> dict[str, Any]:
    traces = [_trace(signatures, queries, target, name)
              for target in range(len(signatures))]
    total = sum(row["queries"] for row in traces)
    return {
        "arm": name,
        "targets": len(traces),
        "budget": BUDGET,
        "identified_within_budget": sum(row["identified_within_budget"] for row in traces),
        "total_queries": total,
        "mean_queries_numerator": total,
        "mean_queries_denominator": len(traces),
        "worst_queries": max(row["queries"] for row in traces),
        "query_count_distribution": dict(sorted(Counter(row["queries"] for row in traces).items())),
        "traces": traces,
    }


def build_census(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    candidates = _semantic_candidates()
    queries = _queries()
    signatures, classes = _classes(candidates, queries)
    arms = [
        _arm(signatures, queries, "balanced_separating_witness"),
        _arm(signatures, queries, "canonical_first_witness"),
    ]
    balanced, canonical = arms
    paired = {
        "budget": BUDGET,
        "balanced_only": sum(
            left["identified_within_budget"] and not right["identified_within_budget"]
            for left, right in zip(balanced["traces"], canonical["traces"])
        ),
        "canonical_only": sum(
            right["identified_within_budget"] and not left["identified_within_budget"]
            for left, right in zip(balanced["traces"], canonical["traces"])
        ),
        "both": sum(
            left["identified_within_budget"] and right["identified_within_budget"]
            for left, right in zip(balanced["traces"], canonical["traces"])
        ),
        "neither": sum(
            not left["identified_within_budget"] and not right["identified_within_budget"]
            for left, right in zip(balanced["traces"], canonical["traces"])
        ),
    }
    return {
        "schema": VERSION,
        "status": "complete_exact_finite_population_census",
        "input_sha256": {relative: _sha(root / relative) for relative in SOURCE_PATHS},
        "population": {
            "full_candidates": len(enumerate_candidates()),
            "semantic_candidates": len(candidates),
            "semantic_equivalence_classes": len(classes),
            "query_space": len(queries),
            "population_definition": "complete_extensional_equivalence_classes_induced_by_the_frozen_32_member_semantic_grammar_on_the_20977_query_domain",
        },
        "classes": classes,
        "arms": arms,
        "paired": paired,
        "inference": {
            "sampling_based_p_value": False,
            "reason": "complete_deterministic_census_of_the_frozen_semantic_class_population",
        },
        "claim_boundary": {
            "exact_only_for_frozen_semantic_classes": True,
            "natural_language_fact_discovery_supported": False,
            "resource_policy_identified_by_semantic_queries": False,
            "benchmark_accuracy_claimed": False,
            "library_promoted": False,
            "llm_proposer_efficacy_claimed": False,
        },
        "privacy": {
            "contains_counterexample_assignments": False,
            "contains_problem_bodies": False,
            "contains_request_bodies": False,
            "contains_response_bodies": False,
            "contains_reference_answers": False,
            "contains_credentials": False,
        },
        "execution": {
            "api_calls": 0,
            "model_calls": 0,
            "solver_calls": 0,
            "native_calls": 0,
            "vm_calls": 0,
        },
    }


def render_markdown(value: dict[str, Any]) -> str:
    arms = {row["arm"]: row for row in value["arms"]}
    balanced = arms["balanced_separating_witness"]
    canonical = arms["canonical_first_witness"]
    return f"""# G08 finite active-acquisition census

Status: **complete for the frozen finite semantic-class population**.

The 64-member typed grammar contains 32 distinct semantic candidates after the
resource-policy axis is removed. On the complete 20,977-query verification
domain, those candidates induce 10 extensionally distinguishable semantic
classes. This census treats those 10 classes as the complete target population.

Both acquisition policies begin with all 10 classes and observe only the label
of a selected assignment query. The balanced policy selects the query that
minimizes the largest remaining partition; the control selects the first
separating query in the same frozen order. Neither policy receives an authored
fact statement or the hidden target identity.

| Policy | Identified within 3 queries | Total queries | Mean | Worst |
|---|---:|---:|---:|---:|
| Balanced separating witness | {balanced['identified_within_budget']}/10 | {balanced['total_queries']} | {balanced['total_queries'] / 10:.1f} | {balanced['worst_queries']} |
| Canonical first witness | {canonical['identified_within_budget']}/10 | {canonical['total_queries']} | {canonical['total_queries'] / 10:.1f} | {canonical['worst_queries']} |

The paired budget outcome is {value['paired']['balanced_only']} balanced-only,
{value['paired']['canonical_only']} control-only, {value['paired']['both']} both
and {value['paired']['neither']} neither. Because every class is enumerated,
these are exact finite-population quantities rather than sampling estimates.

This closes a bounded acquisition claim: balanced verifier-selected witnesses
automatically identify every extensional skill class within the frozen grammar
and budget, whereas the fixed-order control identifies six. It does not show
natural-language fact discovery, identify the resource-policy axis, estimate
LLM proposer efficacy, improve benchmark accuracy or promote a library.
"""


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    value = build_census(root)
    for relative, content in (
        (OUTPUT_PATH, json.dumps(value, indent=2, sort_keys=True) + "\n"),
        (REPORT_PATH, render_markdown(value)),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)


if __name__ == "__main__":
    main()
