"""Post-hoc label-blind robustness replication of the RetailOpt comparison."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .formal_gateway import VERSION as GATEWAY_VERSION, wire_body
from .formal_provider import BASE_URL, MODEL, check_profile_metadata
from .formulationbench_same_knowledge import PREPARATION_PYTHON, _runtime_metadata
from .retailopt190_experiment import build_full_material
from .retailopt190_knowledge import library_sha256
from .schema import canonical, digest


VERSION = "retailopt190-label-blind-v1"
PLAN_PATH = "experiments/retailopt190_label_blind_plan_20261017.json"
AUTH_PATH = "experiments/retailopt190_label_blind_authorization_20261017.json"
AUDIT_PATH = "experiments/retailopt190_label_blind_audit_20261017.json"
EXECUTION_PATH = "experiments/retailopt190_label_blind_execution_20261017.json"
EVALUATION_PATH = "experiments/retailopt190_label_blind_evaluation_20261017.json"
REQUEST_ROOT = "results/private/retailopt190_label_blind_requests_20261017"
RUN_DIRECTORY = "results/private/retailopt190_label_blind_20261017"


def _sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def _bytes(value: Any) -> bytes: return (canonical(value) + "\n").encode()
def _file_sha(path: str | Path) -> str: return _sha(Path(path).read_bytes())


def build_material(source_root: str | Path, ledger_path: str | Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    base, original = build_full_material(source_root, ledger_path)
    entries: dict[str, bytes] = {}
    cells = json.loads(canonical(base["cells"])); public_inputs = {}
    for path, raw in original.items():
        if not path.startswith("requests/"):
            entries[path] = raw; continue
        cell_id = Path(path).stem; payload = json.loads(raw)
        payload["version"] = VERSION
        payload["view"].pop("arm")
        payload["view"]["schema"] = "llm4or-retailopt190-short-decision-request-v2"
        payload["context"] = {
            "opaque_archetype_id": cells[cell_id]["opaque_archetype_id"],
            "selected_skill_ids": cells[cell_id]["selected_skill_ids"],
        }
        rendered = _bytes(payload); entries[path] = rendered
        cells[cell_id]["request_sha256"] = _sha(rendered); cells[cell_id]["request_bytes"] = len(rendered)
        public_inputs[cell_id] = digest(payload)
    request_values = [json.loads(raw) for path, raw in entries.items() if path.startswith("requests/")]
    return {
        "cells": dict(sorted(cells.items())), "public_inputs": dict(sorted(public_inputs.items())),
        "entries_sha256": digest({path: _sha(raw) for path, raw in sorted(entries.items())}),
        "max_request_bytes": max(len(_bytes(value)) for value in request_values),
        "max_wire_bytes": max(len(canonical(wire_body(value, 512)).encode()) for value in request_values),
        "max_evidence_bytes": base["max_evidence_bytes"],
        "private_archetype_ledger_sha256": _sha(entries["private/archetype_ledger.json"]),
    }, dict(sorted(entries.items()))


def build_plan(root: str | Path, source_root: str | Path, ledger_path: str | Path, capacity_result: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
    if capacity_result.get("capacity_gate", {}).get("passed") is not True: raise ValueError("capacity_not_passed")
    check_profile_metadata(); root = Path(root).resolve(); material, entries = build_material(source_root, ledger_path)
    reserve = material["max_wire_bytes"] + 8_192 + 512
    frozen = [
        "llm4or/formal_gateway.py", "llm4or/formal_provider.py", "llm4or/formulationbench_same_knowledge.py",
        "llm4or/openai_httpx_worker.py", "llm4or/retailopt190_blind_replication.py",
        "llm4or/retailopt190_compiler.py", "llm4or/retailopt190_endpoint.py", "llm4or/retailopt190_evaluation.py",
        "llm4or/retailopt190_experiment.py", "llm4or/retailopt190_knowledge.py", "llm4or/schema.py",
        "scripts/evaluate_retailopt190_short_full.py", "scripts/freeze_retailopt190_label_blind.py",
        "scripts/openai_httpx_transport_worker.py", "scripts/run_retailopt190_label_blind.py",
    ]
    plan = {
        "schema": VERSION + "-plan", "status": "frozen_ready_for_posthoc_robustness", "kind": "fresh_common_external",
        "endpoint": BASE_URL, "model": MODEL, "runtime_version": VERSION, "gateway_version": GATEWAY_VERSION,
        "replicates": [0], "public_inputs": material["public_inputs"], "cells": material["cells"],
        "token_cap": reserve + 1, "trajectory_token_caps": [reserve + 1],
        "limits": {"max_requests": 228, "max_total_reserved_or_reported_tokens": 228 * reserve, "max_completion_tokens": 512,
                   "max_input_bytes": max(32_768, material["max_wire_bytes"] + 4_096), "max_output_bytes": 16_384,
                   "token_overhead_reserve": 8_192, "request_seconds": 150, "max_run_seconds": 21_600,
                   "minimum_free_disk_bytes": 5_000_000_000},
        "resilience": {"max_attempts_per_request": 3, "backoff_seconds": [2, 5], "circuit_breaker_consecutive_failures": 8,
                       "retryable_local_errors": ["invalid_json_response"], "max_concurrent_requests": 5},
        "transport": {"kind": "openai_httpx_single_attempt_v1", "python": str(PREPARATION_PYTHON),
                      "python_sha256": _file_sha(PREPARATION_PYTHON), "worker": "scripts/openai_httpx_transport_worker.py"},
        "runtime": {"controller_python": __import__('platform').python_version(), "controller_machine": __import__('platform').machine(), "transport_runtime": _runtime_metadata()},
        "frozen_files": {path: _file_sha(root / path) for path in frozen}, "skill_library_sha256": library_sha256(),
        "private_request_bundle_sha256": material["entries_sha256"], "private_archetype_ledger_sha256": material["private_archetype_ledger_sha256"],
        "authorization_schema": VERSION + "-authorization", "authorization_path": AUTH_PATH,
        "external_method": {"name": "RetailOptShortDecisionBlind", "paper_label": "label-blind-posthoc-robustness", "scope_stage": "retailblind", "max_calls": 1},
        "source": {"commit": "d809c6bbeb42cb99b0564c41bfb8f331f0156b9d", "records": 190, "archetypes": 38, "variants_per_archetype": 5},
        "population": {"archetypes": 38, "variants": 190, "arms": ["base_short", "knowledge_short"], "logical_requests": 76, "solver_evaluations": 380},
        "matrix": {"inference_cells": 76, "logical_requests": 76}, "run_directory": RUN_DIRECTORY, "private_request_root": REQUEST_ROOT,
        "output": {"public_execution": EXECUTION_PATH, "public_evaluation": EVALUATION_PATH},
        "capacity_gate": {"plan_sha256": capacity_result["plan_sha256"], "result_sha256": digest(capacity_result), "passed": True},
        "rate_limit_policy": {"max_logical_starts": 40, "window_seconds": 60, "safety_seconds": 1.0, "observed_provider_limit": 60},
        "evidence_budget": {"maximum_cards": 3, "maximum_evidence_bytes": material["max_evidence_bytes"], "decision_completion_tokens": 512},
        "matched_design": {"same_model": True, "same_public_task": True, "same_question_set": True, "same_output_contract": True,
                           "same_compiler": True, "same_solver": True, "arm_label_model_visible": False,
                           "only_model_visible_difference": "selected obligation and counterexample evidence"},
        "study_role": "posthoc_label_blind_robustness_after_primary_result_opened",
        "privacy": {"reference_values_available_to_inference": False, "request_bodies_public": False, "response_bodies_public": False},
        "claim_boundary": "Post-hoc same-benchmark robustness to removing informative arm labels; it is not a second independent confirmation.",
    }
    return plan, entries


def audit(plan: Mapping[str, Any], entries: Mapping[str, bytes]) -> dict[str, Any]:
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for cell_id, descriptor in plan["cells"].items():
        payload = json.loads(entries[f"requests/{cell_id}.json"])
        grouped.setdefault(descriptor["opaque_archetype_id"], []).append((descriptor, payload))
    pair_checks = []
    for rows in grouped.values():
        if len(rows) != 2: pair_checks.append(False); continue
        normalized=[]
        for _descriptor,payload in rows:
            value=json.loads(canonical(payload)); value["view"]["evidence"]=[]; normalized.append(value)
        pair_checks.append(normalized[0] == normalized[1])
    checks = {
        "thirty_eight_pairs": len(grouped) == 38 and all(len(rows) == 2 for rows in grouped.values()),
        "model_visible_difference_only_evidence": all(pair_checks),
        "arm_label_absent": all("arm" not in payload["view"] and "arm" not in payload["context"] for rows in grouped.values() for _,payload in rows),
        "two_arms_internal": all({descriptor["arm"] for descriptor,_ in rows} == {"base_short","knowledge_short"} for rows in grouped.values()),
        "concurrency_five": plan["resilience"]["max_concurrent_requests"] == 5,
        "rate_gate": plan["rate_limit_policy"]["max_logical_starts"] == 40,
    }
    return {"schema": VERSION + "-audit", "status": "passed" if all(checks.values()) else "failed", "plan_sha256": digest(plan),
            "checks": checks, "execution": {"api_calls": 0, "model_calls": 0, "solver_calls": 0}, "claim_boundary": plan["claim_boundary"]}


__all__ = ["AUDIT_PATH","AUTH_PATH","EVALUATION_PATH","EXECUTION_PATH","PLAN_PATH","REQUEST_ROOT","RUN_DIRECTORY","VERSION","audit","build_material","build_plan"]
