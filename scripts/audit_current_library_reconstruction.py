#!/usr/bin/env python3
"""Verify current manifests against body-free direct and mixed identities."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.content_addressed_manifests import operational_description_length_bits
from llm4or.current_library_manifests import (
    build_current_manifest_set,
    publish_current_manifest_set,
)
from scripts.audit_mixed_skill_confirmation import audit_identity


MANIFEST_DIRECTORY = Path("artifacts/knowledge_manifests/current")
OUTPUT = Path("experiments/current_library_manifest_reconstruction_audit_20261015.json")
PUBLIC_INPUTS = {
    "bundle": (
        Path("experiments/public_projections/mixed_skill_confirmation_bundle_projection_20261015.json"),
        "da9a35dcb6b76e2289a7a9f0613384661dac80f6e96b8c3ed41ba1f5538fee65",
    ),
    "mixed": (
        Path("results/public_projections/mixed_skill_confirmation_outputs_projection_20261015.json"),
        "5f7b5860f4e50e5ce37b85e49fbd9e3b96488429bf08e779fe17c503ded1ad70",
    ),
    "or_debug_direct": (
        Path("results/public_projections/or_debug_confirmation_method_outputs_projection_20261015.json"),
        "d714e72bb9207ba7ca7146f43a196f9b6599e1e43b5ea94446fe9a60bfbbcf46",
    ),
    "tsp_direct": (
        Path("results/public_projections/tsp_constraint_confirmation_candidates_projection_20261015.json"),
        "bbd4e31ddf317df76dc7e84ce00be143ec078f159663f57fa443226610a27e23",
    ),
}
EXISTING_AUDIT = (
    Path("results/mixed_skill_confirmation_public_audit_v3_20261015.json"),
    "3c9b8700639cfe5599fc76b18cca4318b14d4b0865fb5bd343f5c0d26fead08f",
)
ENDPOINT_PATHS = {
    "or_debug_corrected_primary": Path(
        "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json"
    ),
    "tsp_constraint_confirmation": Path(
        "results/tsp_constraint_confirmation_root_closure_20261014.json"
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_bound_json(root: Path, relative: Path, expected: str) -> dict[str, Any]:
    path = root / relative
    if _sha256(path) != expected:
        raise ValueError(f"reconstruction_input_hash_mismatch:{relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"reconstruction_input_mapping:{relative}")
    return value


def build_reconstruction_audit(root: Path) -> dict[str, Any]:
    """Rebuild identity claims from content manifests and public projections."""

    root = Path(root).resolve()
    materialized = publish_current_manifest_set(
        root, MANIFEST_DIRECTORY, check=True
    )
    manifest_set = build_current_manifest_set(
        root, MANIFEST_DIRECTORY / "skills"
    )
    payloads = {
        label: _read_bound_json(root, relative, expected)
        for label, (relative, expected) in PUBLIC_INPUTS.items()
    }
    identity = audit_identity(
        payloads["bundle"]["records"],
        payloads["mixed"]["records"],
        payloads["tsp_direct"]["skill_records"],
        payloads["or_debug_direct"]["records"],
    )
    if not identity["exact_identity_pass"]:
        raise ValueError("manifest_reconstruction_identity_failed")

    existing_path, existing_sha = EXISTING_AUDIT
    existing = _read_bound_json(root, existing_path, existing_sha)
    equivalence_fields = [
        "exact_identity_pass",
        "families",
        "route_counts",
        "status_counts",
        "totals",
    ]
    equivalence = {
        field: identity[field] == existing[field] for field in equivalence_fields
    }
    if not all(equivalence.values()):
        raise ValueError("existing_public_audit_drift")

    declared_endpoints = {
        item["endpoint_id"]: item for item in manifest_set["library"]["endpoint_identities"]
    }
    endpoint_checks = {}
    for endpoint_id, relative in ENDPOINT_PATHS.items():
        observed = _sha256(root / relative)
        declared = declared_endpoints[endpoint_id]["evidence_sha256"]
        endpoint_checks[endpoint_id] = {
            "path": relative.as_posix(),
            "declared_sha256": declared,
            "observed_sha256": observed,
            "passed": declared == observed,
        }
    if not all(item["passed"] for item in endpoint_checks.values()):
        raise ValueError("manifest_endpoint_binding_failed")

    return {
        "schema": "llm4or-current-library-manifest-reconstruction-audit-v1",
        "audited_at_local_date": "2026-10-15",
        "status": "passed_body_free_identity_reconstruction",
        "manifest_validation": {
            "passed": True,
            "library_path": materialized["library_path"],
            "library_sha256": materialized["library_sha256"],
            "skill_paths": materialized["skill_paths"],
            "skill_sha256": materialized["skill_sha256"],
            "operational_description_length_bits": operational_description_length_bits(
                list(manifest_set["skills"].values()), manifest_set["library"]["router"]
            ),
        },
        "public_input_sha256": {
            label: expected for label, (_relative, expected) in sorted(PUBLIC_INPUTS.items())
        },
        "endpoint_bindings": endpoint_checks,
        "mixed_identity": identity,
        "existing_audit_equivalence": {
            "path": existing_path.as_posix(),
            "sha256": existing_sha,
            "field_equal": equivalence,
            "passed": all(equivalence.values()),
        },
        "claim_boundary": {
            "accuracy_recomputed": False,
            "runtime_reexecuted": False,
            "complexity_effect_reestimated": False,
            "new_generalization_claimed": False,
            "allowed_claim": "One content-addressed library manifest reconstructs the already sealed public direct-family and mixed output identities.",
        },
        "safety": {
            "api_or_model_calls": 0,
            "solver_calls": 0,
            "native_evaluator_calls": 0,
            "vm_calls": 0,
            "restricted_bodies_read": False,
            "evaluator_only_answers_read": False,
            "credentials_read": False,
        },
    }


def _render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    raw = _render(build_reconstruction_audit(ROOT))
    if arguments.check:
        if output.read_bytes() != raw:
            raise ValueError("reconstruction_audit_check_mismatch")
    else:
        _write_exclusive(output, raw)
    print(
        json.dumps(
            {
                "mode": "check" if arguments.check else "write",
                "output": str(output.relative_to(ROOT)),
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
