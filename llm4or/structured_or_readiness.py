"""Body-free readiness evidence for the fresh common-38 typed skills."""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path

from .fresh_common38 import build_private_bundle
from .schema import canonical
from .structured_or_skills import RESOURCE_CAPS, VERSION, compile_and_admit


SCHEMA = "fresh-common38-structured-skills-readiness-v1"
PACKET_READINESS = "experiments/fresh_common38_packet_readiness_20261015.json"
SKILL_SOURCE = "llm4or/structured_or_skills.py"


def require(ok, code):
    if not ok:
        raise ValueError(code)


def _raw(path):
    return Path(path).read_bytes()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build_audit(root):
    root = Path(root).resolve()
    packet_path = root / PACKET_READINESS
    packet_raw = _raw(packet_path)
    packet_manifest = json.loads(packet_raw)
    bundle = build_private_bundle(root)
    packet_by_id = {row["id"]: row for row in packet_manifest["packet_bindings"]}
    require(len(packet_by_id) == 38, "packet_binding_count")

    bindings = []
    routes = Counter()
    maxima = {key: 0 for key in RESOURCE_CAPS}
    exact = 0
    for row in bundle["records"]:
        require(row["id"] in packet_by_id, "packet_binding_missing")
        public_binding = packet_by_id[row["id"]]
        require(public_binding["public_payload_sha256"] == row["public_payload_sha256"]
                and public_binding["family"] == row["family"], "packet_binding_mismatch")
        admitted = compile_and_admit(row["public_payload"])
        metrics = admitted["metrics"]
        count_match = (
            metrics["variables"] == row["non_outcome_metadata"]["num_vars"]
            and metrics["constraints"] == row["non_outcome_metadata"]["num_constraints"]
        )
        exact += int(count_match)
        routes[admitted["route"]] += 1
        for key, value in metrics.items():
            maxima[key] = max(maxima[key], value)
        bindings.append({
            "id": row["id"],
            "family": row["family"],
            "public_payload_sha256": row["public_payload_sha256"],
            "model_sha256": admitted["model_sha256"],
            "metrics": metrics,
            "source_expected_variable_count": row["non_outcome_metadata"]["num_vars"],
            "source_expected_constraint_count": row["non_outcome_metadata"]["num_constraints"],
            "source_counts_match": count_match,
        })
    require(len(bindings) == 38 and exact == 38, "structured_readiness_incomplete")
    require(routes == {"rcpsp": 13, "vrptw": 25}, "structured_route_counts")

    skill_raw = _raw(root / SKILL_SOURCE)
    return {
        "schema": SCHEMA,
        "status": "typed_skills_ready_dispatch_controls_open",
        "common_packet_readiness_sha256": _sha(packet_raw),
        "source_revision": bundle["source_revision"],
        "skill": {
            "version": VERSION,
            "source_path": SKILL_SOURCE,
            "source_sha256": _sha(skill_raw),
            "typed_routes": ["rcpsp", "vrptw"],
            "resource_caps": dict(RESOURCE_CAPS),
        },
        "aggregate": {
            "planned": 38,
            "compiled_and_admitted": 38,
            "exact_source_count_matches": exact,
            "routes": dict(sorted(routes.items())),
            "maximum_resources": maxima,
        },
        "model_bindings": bindings,
        "execution": {
            "api_calls": 0,
            "solver_calls": 0,
            "model_calls": 0,
        },
        "claim_boundary": {
            "packet_bodies_included": False,
            "evaluator_answers_used": False,
            "upstream_model_annotations_used": False,
            "skills_are_authored_from_public_benchmark_semantics": True,
            "automatic_acquisition_demonstrated": False,
            "exact_count_agreement_is_not_semantic_equivalence_proof": True,
            "solver_accuracy_measured": False,
        },
        "decision": {
            "common_atomic_fact_packet_ready": True,
            "typed_skills_ready": True,
            "routing_and_resource_admission_ready": True,
            "external_serializers_ready": False,
            "native_and_equal_budget_caps_ready": False,
            "outcome_blind_custody_ready": False,
            "ready_to_dispatch": False,
        },
    }


def publish(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o644)
    except FileExistsError as exc:
        raise ValueError("output_exists") from exc
    raw = (canonical(value) + "\n").encode("utf-8")
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(fd, raw[offset:])
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


__all__ = ["build_audit", "publish"]
