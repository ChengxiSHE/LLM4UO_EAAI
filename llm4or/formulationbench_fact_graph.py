"""Canonical same-fact representations for FormulationBench inference pairs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping


class FactGraphError(ValueError):
    """An inference pair or serialized view violates the same-fact contract."""


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FactGraphError("not_canonical_json") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in sorted(value.items()):
            if not isinstance(key, str):
                raise FactGraphError("non_string_key")
            result[key] = _normalize(child)
        return result
    if isinstance(value, list):
        return [_normalize(child) for child in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        _canonical_json(value)
        return value
    raise FactGraphError("invalid_fact_value")


_SENSITIVE_KEYS = frozenset(
    {"answer", "code", "label", "metadata", "proof", "solution", "valid"}
)


def _reject_sensitive_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = "_".join(
                part for part in key.lower().replace("-", "_").split("_") if part
            )
            if normalized in _SENSITIVE_KEYS:
                raise FactGraphError("sensitive_input_key")
            _reject_sensitive_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive_keys(child)


@dataclass(frozen=True)
class Fact:
    kind: str
    scope: str
    key: str
    value: Any
    fact_sha256: str

    def payload(self) -> dict[str, Any]:
        return {
            "fact_sha256": self.fact_sha256,
            "key": self.key,
            "kind": self.kind,
            "scope": self.scope,
            "value": self.value,
        }


@dataclass(frozen=True)
class FactGraph:
    opaque_id: str
    facts: tuple[Fact, ...]
    graph_sha256: str


@dataclass(frozen=True)
class View:
    representation: str
    graph_sha256: str
    fact_hashes: tuple[str, ...]
    guidance_sha256: str
    body: bytes


_FORMULATION_KEYS = frozenset(
    {"assumptions", "constraints", "definitions", "objective", "parameters", "variables"}
)
_MAP_KEYS = frozenset({"definitions", "parameters"})

_GUIDANCE = (
    (
        "parameter_compatibility",
        "Check parameter domains, types, shapes, and the supplied bidirectional map.",
    ),
    (
        "forward_feasibility",
        "Check whether every feasible formulation-A assignment maps to formulation B.",
    ),
    (
        "backward_feasibility",
        "Check whether every feasible formulation-B assignment maps to formulation A.",
    ),
    (
        "integrality_and_bounds",
        "Check variable domains, integrality, dimensions, and bounds in both directions.",
    ),
    (
        "index_quantifier_coverage",
        "Check index domains, quantifier coverage, definitions, and scope alignment.",
    ),
    (
        "objective_preservation",
        "Check objective sense, expression, and value preservation under the map.",
    ),
)


def _fact(kind: str, scope: str, key: str, value: Any) -> Fact:
    normalized = _normalize(value)
    core = {"key": key, "kind": kind, "scope": scope, "value": normalized}
    return Fact(
        kind=kind,
        scope=scope,
        key=key,
        value=normalized,
        fact_sha256=_sha256(_canonical_json(core)),
    )


def _mapping_facts(
    value: Any, *, kind: str, scope: str
) -> list[Fact]:
    if not isinstance(value, Mapping):
        raise FactGraphError("semantic_container_not_mapping")
    return [_fact(kind, scope, key, child) for key, child in sorted(value.items())]


def _sequence_facts(
    value: Any, *, kind: str, scope: str
) -> list[Fact]:
    if not isinstance(value, list):
        raise FactGraphError("semantic_container_not_array")
    normalized = sorted((_normalize(child) for child in value), key=_canonical_json)
    return [
        _fact(kind, scope, f"{index:06d}", child)
        for index, child in enumerate(normalized)
    ]


def _formulation_facts(value: Any, scope: str) -> list[Fact]:
    if not isinstance(value, Mapping) or set(value) - _FORMULATION_KEYS:
        raise FactGraphError("formulation_schema")
    required = {"assumptions", "constraints", "objective", "parameters", "variables"}
    if not required.issubset(value):
        raise FactGraphError("formulation_schema")
    facts: list[Fact] = []
    facts.extend(_sequence_facts(value["assumptions"], kind="assumption", scope=scope))
    facts.extend(_sequence_facts(value["constraints"], kind="constraint", scope=scope))
    facts.extend(_mapping_facts(value.get("definitions", {}), kind="definition", scope=scope))
    facts.extend(_mapping_facts(value["parameters"], kind="parameter", scope=scope))
    facts.extend(_mapping_facts(value["variables"], kind="variable", scope=scope))
    if not isinstance(value["objective"], Mapping):
        raise FactGraphError("objective_not_mapping")
    facts.append(_fact("objective", scope, "objective", value["objective"]))
    return facts


def parse_fact_graph(pair: Mapping[str, Any]) -> FactGraph:
    """Parse one custody inference record into typed, content-addressed facts."""

    if not isinstance(pair, Mapping):
        raise FactGraphError("pair_not_mapping")
    expected = {
        "formulation_a",
        "formulation_b",
        "opaque_id",
        "parameter_map",
        "problem",
        "problem_description",
        "schema",
        "source_commit",
        "source_tree",
    }
    if set(pair) != expected or pair.get("schema") != "llm4or-formulationbench-inference-pair-v1":
        raise FactGraphError("pair_schema")
    opaque_id = pair.get("opaque_id")
    if not isinstance(opaque_id, str) or len(opaque_id) != 64 or any(
        character not in "0123456789abcdef" for character in opaque_id
    ):
        raise FactGraphError("opaque_identity")
    for key in ("source_commit", "source_tree"):
        value = pair.get(key)
        if not isinstance(value, str) or len(value) != 40 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise FactGraphError("source_identity")
    _reject_sensitive_keys(pair)

    description = pair["problem_description"]
    if not isinstance(description, str) or not description.strip():
        raise FactGraphError("problem_description")
    problem = pair["problem"]
    if not isinstance(problem, Mapping) or not isinstance(
        problem.get("parameters"), Mapping
    ):
        raise FactGraphError("problem_schema")

    facts = [_fact("problem_description", "problem", "description", description)]
    facts.extend(
        _mapping_facts(
            problem["parameters"], kind="parameter", scope="problem"
        )
    )
    for key, value in sorted(problem.items()):
        if key != "parameters":
            facts.append(_fact("problem_attribute", "problem", key, value))
    facts.extend(_formulation_facts(pair["formulation_a"], "formulation_a"))
    facts.extend(_formulation_facts(pair["formulation_b"], "formulation_b"))

    parameter_map = pair["parameter_map"]
    if not isinstance(parameter_map, Mapping) or set(parameter_map) - _MAP_KEYS:
        raise FactGraphError("parameter_map_schema")
    if not isinstance(parameter_map.get("parameters"), Mapping):
        raise FactGraphError("parameter_map_schema")
    facts.extend(
        _mapping_facts(
            parameter_map["parameters"],
            kind="parameter_mapping",
            scope="parameter_map",
        )
    )
    facts.extend(
        _mapping_facts(
            parameter_map.get("definitions", {}),
            kind="mapping_definition",
            scope="parameter_map",
        )
    )
    ordered = tuple(
        sorted(
            facts,
            key=lambda fact: (
                fact.kind,
                fact.scope,
                fact.key,
                fact.fact_sha256,
            ),
        )
    )
    hashes = sorted(fact.fact_sha256 for fact in ordered)
    graph_sha256 = _sha256(
        _canonical_json(
            {
                "schema": "llm4or-formulationbench-fact-multiset-v1",
                "fact_sha256": hashes,
            }
        )
    )
    return FactGraph(
        opaque_id=opaque_id,
        facts=ordered,
        graph_sha256=graph_sha256,
    )


def _guidance_payload() -> list[dict[str, str]]:
    return [
        {"id": identifier, "instruction": instruction}
        for identifier, instruction in _GUIDANCE
    ]


def _guidance_sha256() -> str:
    return _sha256(_canonical_json(_guidance_payload()))


def serialize_flat(graph: FactGraph) -> View:
    """Serialize every fact once in a canonical flat inventory."""

    hashes = tuple(sorted(fact.fact_sha256 for fact in graph.facts))
    body = _canonical_json(
        {
            "schema": "llm4or-formulationbench-view-v1",
            "representation": "flat-k",
            "opaque_id": graph.opaque_id,
            "graph_sha256": graph.graph_sha256,
            "checks": _guidance_payload(),
            "facts": [fact.payload() for fact in graph.facts],
        }
    )
    return View(
        representation="flat-k",
        graph_sha256=graph.graph_sha256,
        fact_hashes=hashes,
        guidance_sha256=_guidance_sha256(),
        body=body,
    )


def _obligation_for(fact: Fact) -> str:
    if fact.kind in {
        "parameter",
        "parameter_mapping",
        "problem_attribute",
        "problem_description",
    }:
        return "parameter_compatibility"
    if fact.kind in {"assumption", "constraint"}:
        return (
            "forward_feasibility"
            if fact.scope == "formulation_a"
            else "backward_feasibility"
        )
    if fact.kind == "variable":
        return "integrality_and_bounds"
    if fact.kind in {"definition", "mapping_definition"}:
        return "index_quantifier_coverage"
    if fact.kind == "objective":
        return "objective_preservation"
    raise FactGraphError("unroutable_fact_kind")


def serialize_pck(graph: FactGraph) -> View:
    """Serialize the identical facts under typed proof obligations."""

    grouped: dict[str, list[Fact]] = {identifier: [] for identifier, _ in _GUIDANCE}
    for fact in graph.facts:
        grouped[_obligation_for(fact)].append(fact)
    obligations = []
    for identifier, instruction in _GUIDANCE:
        obligations.append(
            {
                "id": identifier,
                "instruction": instruction,
                "facts": [fact.payload() for fact in grouped[identifier]],
            }
        )
    hashes = tuple(sorted(fact.fact_sha256 for fact in graph.facts))
    body = _canonical_json(
        {
            "schema": "llm4or-formulationbench-view-v1",
            "representation": "pck-k",
            "opaque_id": graph.opaque_id,
            "graph_sha256": graph.graph_sha256,
            "obligations": obligations,
        }
    )
    return View(
        representation="pck-k",
        graph_sha256=graph.graph_sha256,
        fact_hashes=hashes,
        guidance_sha256=_guidance_sha256(),
        body=body,
    )


def _load_view(view: View) -> tuple[list[str], list[dict[str, str]]]:
    try:
        payload = json.loads(view.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise FactGraphError("invalid_view_json") from exc
    if not isinstance(payload, dict) or payload.get("schema") != "llm4or-formulationbench-view-v1":
        raise FactGraphError("view_schema")
    if payload.get("representation") != view.representation:
        raise FactGraphError("view_representation")
    if payload.get("graph_sha256") != view.graph_sha256:
        raise FactGraphError("view_graph_identity")

    if view.representation == "flat-k":
        if set(payload) != {
            "checks",
            "facts",
            "graph_sha256",
            "opaque_id",
            "representation",
            "schema",
        } or not isinstance(payload["facts"], list):
            raise FactGraphError("flat_view_schema")
        facts = payload["facts"]
        guidance = payload["checks"]
    elif view.representation == "pck-k":
        if set(payload) != {
            "graph_sha256",
            "obligations",
            "opaque_id",
            "representation",
            "schema",
        } or not isinstance(payload["obligations"], list):
            raise FactGraphError("pck_view_schema")
        guidance = []
        facts = []
        for obligation in payload["obligations"]:
            if not isinstance(obligation, dict) or set(obligation) != {
                "facts",
                "id",
                "instruction",
            } or not isinstance(obligation["facts"], list):
                raise FactGraphError("pck_obligation_schema")
            guidance.append(
                {"id": obligation["id"], "instruction": obligation["instruction"]}
            )
            facts.extend(obligation["facts"])
    else:
        raise FactGraphError("view_representation")

    expected_guidance = _guidance_payload()
    if guidance != expected_guidance:
        raise FactGraphError("guidance_mismatch")
    if _sha256(_canonical_json(guidance)) != view.guidance_sha256:
        raise FactGraphError("guidance_hash_mismatch")

    hashes: list[str] = []
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) != {
            "fact_sha256",
            "key",
            "kind",
            "scope",
            "value",
        }:
            raise FactGraphError("view_fact_schema")
        core = {
            "key": fact["key"],
            "kind": fact["kind"],
            "scope": fact["scope"],
            "value": fact["value"],
        }
        observed = _sha256(_canonical_json(core))
        if fact["fact_sha256"] != observed:
            raise FactGraphError("fact_hash_mismatch")
        hashes.append(observed)
    if tuple(sorted(hashes)) != view.fact_hashes:
        raise FactGraphError("view_fact_multiset_mismatch")
    graph_sha256 = _sha256(
        _canonical_json(
            {
                "schema": "llm4or-formulationbench-fact-multiset-v1",
                "fact_sha256": sorted(hashes),
            }
        )
    )
    if graph_sha256 != view.graph_sha256:
        raise FactGraphError("view_graph_hash_mismatch")
    return hashes, guidance


def verify_same_facts(flat: View, pck: View) -> None:
    """Fail closed unless both views carry the same facts and guidance."""

    if flat.representation != "flat-k" or pck.representation != "pck-k":
        raise FactGraphError("view_pair_roles")
    flat_hashes, flat_guidance = _load_view(flat)
    pck_hashes, pck_guidance = _load_view(pck)
    if Counter(flat_hashes) != Counter(pck_hashes):
        raise FactGraphError("cross_view_fact_mismatch")
    if flat_guidance != pck_guidance:
        raise FactGraphError("cross_view_guidance_mismatch")
    if flat.graph_sha256 != pck.graph_sha256:
        raise FactGraphError("cross_view_graph_mismatch")


def audit_inference_root(
    root: Path,
    *,
    source_commit: str,
    source_tree: str,
    expected_pairs: int,
) -> dict[str, Any]:
    """Audit every inference record without accessing evaluator custody."""

    root = Path(root)
    try:
        root_info = root.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise FactGraphError("inference_root_missing") from exc
    if not stat.S_ISDIR(root_info.st_mode):
        raise FactGraphError("inference_root_unsafe")
    try:
        pair_directories = sorted(
            os.scandir(root), key=lambda entry: entry.name.encode("utf-8")
        )
    except OSError as exc:
        raise FactGraphError("inference_root_unsafe") from exc
    if len(pair_directories) != expected_pairs:
        raise FactGraphError("inference_pair_count")

    descriptors = []
    fact_counts = []
    flat_sizes = []
    guidance_hashes = set()
    pck_sizes = []
    for entry in pair_directories:
        if (
            entry.is_symlink()
            or not entry.is_dir(follow_symlinks=False)
            or len(entry.name) != 64
            or any(character not in "0123456789abcdef" for character in entry.name)
        ):
            raise FactGraphError("inference_pair_directory")
        directory = Path(entry.path)
        try:
            children = list(os.scandir(directory))
        except OSError as exc:
            raise FactGraphError("inference_pair_directory") from exc
        if (
            len(children) != 1
            or children[0].name != "pair.json"
            or children[0].is_symlink()
            or not children[0].is_file(follow_symlinks=False)
        ):
            raise FactGraphError("inference_pair_shape")
        path = Path(children[0].path)
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                raw = b""
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk:
                        break
                    raw += chunk
            finally:
                os.close(descriptor)
            pair = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FactGraphError("inference_pair_json") from exc
        if not isinstance(pair, dict):
            raise FactGraphError("inference_pair_json")
        if (
            pair.get("opaque_id") != entry.name
            or pair.get("source_commit") != source_commit
            or pair.get("source_tree") != source_tree
        ):
            raise FactGraphError("inference_pair_identity")
        graph = parse_fact_graph(pair)
        flat = serialize_flat(graph)
        pck = serialize_pck(graph)
        verify_same_facts(flat, pck)
        fact_counts.append(len(graph.facts))
        flat_sizes.append(len(flat.body))
        pck_sizes.append(len(pck.body))
        guidance_hashes.add(flat.guidance_sha256)
        descriptors.append(
            {
                "opaque_id": graph.opaque_id,
                "graph_sha256": graph.graph_sha256,
                "facts": len(graph.facts),
                "flat_sha256": _sha256(flat.body),
                "pck_sha256": _sha256(pck.body),
            }
        )
    if len(guidance_hashes) != 1:
        raise FactGraphError("guidance_population_drift")
    return {
        "schema": "llm4or-formulationbench-same-fact-audit-v1",
        "status": "passed_full_inference_population_same_fact_verification",
        "source": {"commit": source_commit, "dataset_tree": source_tree},
        "counts": {
            "pairs": len(descriptors),
            "verified_pairs": len(descriptors),
            "facts_total": sum(fact_counts),
            "facts_minimum": min(fact_counts),
            "facts_maximum": max(fact_counts),
            "flat_bytes_total": sum(flat_sizes),
            "flat_bytes_minimum": min(flat_sizes),
            "flat_bytes_maximum": max(flat_sizes),
            "pck_bytes_total": sum(pck_sizes),
            "pck_bytes_minimum": min(pck_sizes),
            "pck_bytes_maximum": max(pck_sizes),
            "unique_graphs": len({row["graph_sha256"] for row in descriptors}),
            "guidance_variants": len(guidance_hashes),
            "fact_multiset_mismatches": 0,
            "guidance_mismatches": 0,
        },
        "guidance_sha256": next(iter(guidance_hashes)),
        "population_descriptor_sha256": _sha256(_canonical_json(descriptors)),
        "privacy": {
            "contains_code_bodies": False,
            "contains_data_values": False,
            "contains_pair_labels": False,
            "contains_problem_bodies": False,
            "contains_proof_bodies": False,
            "contains_solutions": False,
        },
        "execution": {
            "api_calls": 0,
            "credentials_read": False,
            "lean_calls": 0,
            "model_calls": 0,
            "solver_calls": 0,
            "vm_calls": 0,
        },
        "claim_boundary": (
            "This audit proves exact fact and fixed-guidance identity between "
            "Flat-K and PCK-K. It does not report model behavior or accuracy."
        ),
    }
