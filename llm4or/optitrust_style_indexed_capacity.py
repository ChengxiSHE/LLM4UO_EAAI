"""Worst-shape, answer-blind transport gate for indexed MILP IR generation."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
from typing import Any, Callable

from .benchmark_inputs import payload_sha256
from .formal_gateway import RequestUnavailable, VERSION as GATEWAY_VERSION
from .formal_provider import BASE_URL, MODEL
from .fresh_common38 import SOURCE_RELATIVE, build_private_bundle
from .gateway import Stopped
from .indexed_milp_ir import IRCompileError, compile_ir, validate_ir_surface
from .optitrust_style_indexed_runtime import VERSION as RUNTIME_VERSION, stage_payload
from .run_interruption import RunInterrupted
from .schema import canonical, digest


VERSION = "optitrust-style-indexed-capacity-gate-v4"
PLAN_PATH = "experiments/optitrust_style_indexed_capacity_plan_v4_20261016.json"
AUTH_PATH = "experiments/optitrust_style_indexed_capacity_authorization_v4_20261016.json"
RESULT_PATH = "experiments/optitrust_style_indexed_capacity_result_v4_20261016.json"
AUDIT_PATH = "experiments/optitrust_style_indexed_capacity_audit_v4_20261016.json"
RUN_DIRECTORY = "results/private/optitrust_style_indexed_capacity_v4_20261016"
PREPARATION_PYTHON = Path("/Users/chengxi-nju/Desktop/LLM4UO/.venv-preparation/bin/python")
CODE_PATHS = (
    "llm4or/optitrust_style_indexed_capacity.py",
    "llm4or/optitrust_style_indexed_runtime.py",
    "llm4or/indexed_milp_ir.py",
    "llm4or/formal_gateway.py",
    "llm4or/formal_provider.py",
    "llm4or/openai_httpx_worker.py",
    "llm4or/milp_schema.py",
    "llm4or/schema.py",
    "scripts/openai_httpx_transport_worker.py",
    "scripts/freeze_optitrust_style_indexed_capacity.py",
    "scripts/run_optitrust_style_indexed_capacity.py",
    "scripts/audit_optitrust_style_indexed_capacity.py",
)
RESOURCE_LIMITS = {
    "variables": 2_000, "constraints": 10_000, "nonzeros": 100_000,
    "serialized_bytes": 4_000_000, "expansion_steps": 1_000_000,
}
TERMINAL = frozenset({"completed", "method_failure", "infrastructure_unavailable"})


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _shape_metrics(value: Any) -> tuple[int, int]:
    nodes, maximum = 1, 0
    if isinstance(value, dict):
        for child in value.values():
            child_nodes, child_maximum = _shape_metrics(child)
            nodes += child_nodes
            maximum = max(maximum, child_maximum)
    elif isinstance(value, list):
        maximum = len(value)
        for child in value:
            child_nodes, child_maximum = _shape_metrics(child)
            nodes += child_nodes
            maximum = max(maximum, child_maximum)
    return nodes, maximum


def selected_cases(root: str | Path) -> list[dict[str, Any]]:
    """Union of per-family public-size extrema; no reference or outcome access."""
    bundle = build_private_bundle(Path(root).resolve())
    enriched = []
    for row in bundle["records"]:
        public = row["public_payload"]
        data = public["instances"][0]["input"]["instance_data"]
        nodes, maximum = _shape_metrics(data)
        enriched.append({
            "id": row["id"], "family": row["family"], "public": public,
            "public_input_sha256": row["public_payload_sha256"],
            "public_bytes": len(canonical(public).encode()),
            "recursive_nodes": nodes, "max_list_length": maximum,
        })
    selected: dict[str, dict[str, Any]] = {}
    for family in sorted({row["family"] for row in enriched}):
        cohort = [row for row in enriched if row["family"] == family]
        for field, reason in (
            ("public_bytes", "max_public_bytes"),
            ("recursive_nodes", "max_recursive_nodes"),
            ("max_list_length", "max_list_length"),
        ):
            winner = max(cohort, key=lambda row: (row[field], row["id"]))
            if winner["id"] not in selected:
                selected[winner["id"]] = {**winner, "selection_reasons": []}
            selected[winner["id"]]["selection_reasons"].append(reason)
    return [selected[key] for key in sorted(selected)]


def _preparation_runtime() -> dict[str, Any]:
    require(PREPARATION_PYTHON.is_file(), "preparation_python_missing")
    code = (
        "import importlib.metadata as m,json,platform,ssl,openai,httpx;"
        "names=('openai','httpx','httpcore','requests','certifi');"
        "print(json.dumps({'python':platform.python_version(),"
        "'openssl':ssl.OPENSSL_VERSION,'packages':{n:m.version(n) for n in names},"
        "'module_paths':{'openai':openai.__file__,'httpx':httpx.__file__}},sort_keys=True))"
    )
    completed = subprocess.run(
        [str(PREPARATION_PYTHON), "-c", code], capture_output=True,
        text=True, check=True, timeout=20,
        env={"HOME": str(Path.home()), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
    )
    value = json.loads(completed.stdout)
    require(set(value) == {"python", "openssl", "packages", "module_paths"}, "preparation_runtime")
    return value


def build_plan(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    cases = selected_cases(root)
    require(len(cases) == 3, "capacity_selection_count")
    frozen_files = {path: _sha(root / path) for path in CODE_PATHS}
    bundle_rows = {row["id"]: row for row in build_private_bundle(root)["records"]}
    for case in cases:
        source = bundle_rows[case["id"]]
        source_path = f"{SOURCE_RELATIVE}/{source['source_file']}"
        require(_sha(root / source_path) == source["source_file_sha256"], "source_binding")
        frozen_files[source_path] = source["source_file_sha256"]
    maximum_reservation = 262_144 + 8_192 + 3_072
    max_requests = len(cases) * 3
    limits = {
        "max_requests": max_requests,
        "max_total_reserved_or_reported_tokens": max_requests * maximum_reservation,
        "max_completion_tokens": 3_072, "max_input_bytes": 262_144,
        "max_output_bytes": 32_768, "token_overhead_reserve": 8_192,
        "request_seconds": 150, "max_run_seconds": 2 * 3600,
        "minimum_free_disk_bytes": 5_000_000_000,
    }
    token_cap = maximum_reservation + 1
    return {
        "schema": VERSION + "-plan",
        "status": "frozen_ready_for_authorized_antchat_capacity_gate",
        "authorization": "standing_user_approval_no_reconfirmation_20261016",
        "authorization_schema": VERSION + "-authorization",
        "authorization_path": AUTH_PATH,
        "kind": "fresh_common_external", "endpoint": BASE_URL, "model": MODEL,
        "runtime_version": RUNTIME_VERSION, "gateway_version": GATEWAY_VERSION,
        "external_method": {
            "name": "OptiTrustStyleIndexedCapacity",
            "paper_label": "OptiTrust-style-indexed-sidecar-capacity-gate",
            "scope_stage": "optitrustindexedcapacity", "max_calls": 1,
            "stage_slots": [{"stage": "canonical_indexed_ir", "modeling_language": None}],
        },
        "replicates": [0],
        "public_inputs": {row["id"]: row["public_input_sha256"] for row in cases},
        "selection": [{key: row[key] for key in (
            "id", "family", "public_input_sha256", "selection_reasons",
            "public_bytes", "recursive_nodes", "max_list_length",
        )} for row in cases],
        "selection_rule": "per_family_union_of_argmax_public_bytes_recursive_nodes_max_list_length_tie_id",
        "resource_limits": dict(RESOURCE_LIMITS),
        "token_cap": token_cap, "trajectory_token_caps": [token_cap], "limits": limits,
        "resilience": {
            "max_attempts_per_request": 3, "backoff_seconds": [2, 5],
            "circuit_breaker_consecutive_failures": 8,
            "retryable_local_errors": ["invalid_json_response"],
            "max_concurrent_requests": 3,
        },
        "matrix": {"capacity_cells": 3, "logical_requests": 3},
        "progress_stage": "optitrustindexedcapacity", "run_directory": RUN_DIRECTORY,
        "output": {"public_result": RESULT_PATH, "public_audit": AUDIT_PATH},
        "transport": {
            "kind": "openai_httpx_single_attempt_v1",
            "python": str(PREPARATION_PYTHON),
            "python_sha256": _sha(PREPARATION_PYTHON),
            "worker": "scripts/openai_httpx_transport_worker.py",
        },
        "runtime": {
            "controller_python": platform.python_version(),
            "controller_machine": platform.machine(),
            "transport_runtime": _preparation_runtime(),
        },
        "frozen_files": dict(sorted(frozen_files.items())),
        "capacity_gate": {
            "terminal_cells": 3, "infrastructure_unavailable": 0,
            "logical_slots": 3, "received_candidates": 3,
            "maximum_completion_tokens": 3_072,
            "maximum_candidate_bytes": 32_768,
            "max_attempt_ordinal": 3, "restart_new_items": 0,
        },
        "claim_boundary": {
            "benchmark_public_inputs_used_for_transport_gate": True,
            "reference_or_answer_loaded": False, "solver_called": False,
            "benchmark_accuracy_estimated": False,
            "capacity_gate_only": True, "official_optitrust_reproduction": False,
            "common38_responses_reused": False,
            "v1_2048_token_gate_failed_by_length": True,
            "v2_complete_candidates_failed_strict_compilation": True,
            "v3_malformed_json_exposed_missing_local_retry": True,
            "candidate_compilation_is_diagnostic_not_capacity_gate": True,
        },
    }


def authorization(root: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    return {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "endpoint": BASE_URL, "model": MODEL,
        "run_directory": str(root / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": "Standing autonomous approval reaffirmed 2026-10-16.",
    }


def publish_new(path: str | Path, value: dict[str, Any]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    raw = (canonical(value) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _cell_path(directory: str | Path, problem_id: str) -> Path:
    return Path(directory) / "cells" / (hashlib.sha256(problem_id.encode()).hexdigest() + ".json")


def _load_cell(path: Path, problem_id: str, plan_sha: str) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(
        value.get("schema") == VERSION + "-private-cell"
        and value.get("plan_sha256") == plan_sha and value.get("id") == problem_id
        and value.get("status") in TERMINAL,
        "checkpoint_binding",
    )
    return value


def _scope(problem_id: str) -> str:
    return f"optitrustindexedcapacity:OptiTrustStyleIndexedCapacity:0:{problem_id}"


def _hash_state() -> dict[str, str]:
    return {
        "slot_0_components": digest({"capacity_gate": "components"}),
        "slot_1_components": digest({"capacity_gate": "components_reflection"}),
        "slot_2_formulation": digest({"capacity_gate": "formulation"}),
        "slot_3_formulation": digest({"capacity_gate": "formulation_reflection"}),
    }


def capacity_payload(public: dict[str, Any]) -> dict[str, Any]:
    payload = stage_payload(public, 4, {"analysis_hashes": _hash_state()})
    payload["context"]["method"] = "OptiTrust-style-indexed-capacity-gate"
    payload["context"]["step"] = 0
    return payload


def _instance_data(public: dict[str, Any]) -> Any:
    return public["instances"][0]["input"]["instance_data"]


def run_plan(
    root: str | Path, plan: dict[str, Any], directory: str | Path, gateway: Any,
    *, workers: int = 3,
) -> dict[str, Any]:
    root = Path(root).resolve(); directory = Path(directory)
    require(canonical(plan) == canonical(build_plan(root)), "plan_reconstruction")
    require(workers == plan["resilience"]["max_concurrent_requests"] == 3, "worker_binding")
    cases = {row["id"]: row for row in selected_cases(root)}
    plan_sha = digest(plan)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def one(problem_id: str):
        path = _cell_path(directory, problem_id)
        if path.exists():
            return _load_cell(path, problem_id, plan_sha), False
        public = cases[problem_id]["public"]
        require(payload_sha256(public) == plan["public_inputs"][problem_id], "public_changed")
        scope = _scope(problem_id); gateway.work_started(scope)
        try:
            gateway.register(scope, 1, plan["token_cap"])
            payload = capacity_payload(public)
            prefix = digest({"problem": public, "version": VERSION, "payload": payload})
            response = gateway.request(scope, payload, prefix, 0, 0)
            candidate = json.loads(response["text"])
            surface = validate_ir_surface(candidate)
            try:
                admission = compile_ir(_instance_data(public), candidate, plan["resource_limits"])
            except IRCompileError as exc:
                compile_admitted = False
                compile_error = str(exc).split(":", 1)[0]
                model_sha256 = None
                metrics = None
            else:
                compile_admitted = True
                compile_error = None
                model_sha256 = admission["model_sha256"]
                metrics = admission["metrics"]
            record = {
                "status": "received", "ir_sha256": surface["ir_sha256"],
                "model_sha256": model_sha256, "metrics": metrics,
                "compile_admitted": compile_admitted, "compile_error": compile_error,
                "candidate_bytes": len(canonical(candidate).encode()),
                "completion_tokens": response["completion_tokens"],
            }
            status, error = "completed", None
            gateway.work_finished(scope, "complete", None)
        except RequestUnavailable as exc:
            record, status = None, "infrastructure_unavailable"
            error = str(exc).split(":", 1)[-1][:160]
            gateway.work_finished(scope, "unavailable", error)
        except RunInterrupted:
            raise
        except Stopped as exc:
            halt = gateway.halt_reason() if hasattr(gateway, "halt_reason") else None
            if halt:
                raise RunInterrupted("global_halt:" + halt) from exc
            record, status, error = None, "method_failure", str(exc).split(":", 1)[-1][:160]
            gateway.work_finished(scope, "complete", error)
        except Exception as exc:
            record, status, error = None, "method_failure", type(exc).__name__
            gateway.work_finished(scope, "complete", error)
        cell = {
            "schema": VERSION + "-private-cell", "plan_sha256": plan_sha,
            "id": problem_id, "status": status, "error": error, "record": record,
        }
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        publish_new(path, cell)
        return cell, True

    cells, new_items = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, problem_id) for problem_id in sorted(cases)]
        for future in as_completed(futures):
            cell, created = future.result(); cells.append(cell); new_items += int(created)
    return {
        "terminal": len(cells), "new_items": new_items,
        "status_counts": dict(sorted(Counter(row["status"] for row in cells).items())),
        "gateway": gateway.summary(),
    }


def _ledger(directory: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{directory / 'requests.sqlite3'}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        totals = connection.execute("SELECT * FROM totals WHERE id=1").fetchone()
        slots = connection.execute("SELECT count(*) n,count(DISTINCT scope) scopes FROM slots").fetchone()
        per_scope = connection.execute("SELECT scope,count(*) n,min(slot) lo,max(slot) hi FROM slots GROUP BY scope").fetchall()
        retry_max = connection.execute("SELECT coalesce(max(ordinal),1) FROM retry_attempts").fetchone()[0]
        halt = connection.execute("SELECT reason FROM halt WHERE id=1").fetchone()
        attempts = list(connection.execute("SELECT status,response FROM attempts"))
        config = json.loads(connection.execute("SELECT config FROM metadata WHERE id=1").fetchone()[0])
    finally:
        connection.close()
    completions = []
    for row in attempts:
        if row["response"]:
            response = json.loads(row["response"])
            if type(response.get("completion_tokens")) is int:
                completions.append(response["completion_tokens"])
    return {
        "physical_attempts": totals["physical_calls"],
        "logical_slots": slots["n"], "distinct_scopes": slots["scopes"],
        "all_scope_slots_contiguous": len(per_scope) == 3 and all(
            row["n"] == 1 and row["lo"] == row["hi"] == 0 for row in per_scope
        ),
        "max_attempt_ordinal": retry_max,
        "attempt_status_counts": dict(sorted(Counter(row["status"] for row in attempts).items())),
        "maximum_completion_tokens": max(completions, default=0),
        "halt": halt[0] if halt else None, "offline": config["offline"],
    }


def _cells(plan: dict[str, Any], directory: Path) -> list[dict[str, Any]]:
    plan_sha = digest(plan)
    return [
        _load_cell(_cell_path(directory, problem_id), problem_id, plan_sha)
        for problem_id in sorted(plan["public_inputs"])
    ]


def score_run(plan: dict[str, Any], directory: str | Path, *, restart_new_items: int) -> dict[str, Any]:
    directory = Path(directory); cells = _cells(plan, directory); ledger = _ledger(directory)
    statuses = Counter(row["status"] for row in cells)
    received = sum((row.get("record") or {}).get("status") == "received" for row in cells)
    admitted = sum((row.get("record") or {}).get("compile_admitted") is True for row in cells)
    maximum_candidate_bytes = max(
        ((row.get("record") or {}).get("candidate_bytes", 0) for row in cells), default=0,
    )
    observed = {
        "terminal_cells": len(cells),
        "infrastructure_unavailable": statuses["infrastructure_unavailable"],
        "logical_slots": ledger["logical_slots"], "received_candidates": received,
        "admitted_candidates": admitted,
        "maximum_completion_tokens": ledger["maximum_completion_tokens"],
        "maximum_candidate_bytes": maximum_candidate_bytes,
        "max_attempt_ordinal": ledger["max_attempt_ordinal"],
        "restart_new_items": restart_new_items,
    }
    required = plan["capacity_gate"]
    checks = {
        "terminal_cells": observed["terminal_cells"] == required["terminal_cells"],
        "infrastructure_unavailable": observed["infrastructure_unavailable"] == 0,
        "logical_slots": observed["logical_slots"] == required["logical_slots"] and ledger["all_scope_slots_contiguous"],
        "received_candidates": observed["received_candidates"] == required["received_candidates"],
        "completion_limit": observed["maximum_completion_tokens"] <= required["maximum_completion_tokens"],
        "candidate_byte_limit": observed["maximum_candidate_bytes"] <= required["maximum_candidate_bytes"],
        "attempt_cap": observed["max_attempt_ordinal"] <= required["max_attempt_ordinal"],
        "restart": observed["restart_new_items"] == required["restart_new_items"],
        "no_global_halt": ledger["halt"] is None,
    }
    return {
        "schema": VERSION + "-public-result", "status": "complete",
        "method": "OptiTrust-style-indexed-sidecar-capacity-gate",
        "plan_sha256": digest(plan),
        "capacity_gate": {**observed, "passed": all(checks.values()), "checks": checks},
        "rows": [{
            "id": row["id"], "status": row["status"],
            "received": (row.get("record") or {}).get("status") == "received",
            "compile_admitted": (row.get("record") or {}).get("compile_admitted") is True,
        } for row in cells],
        "ledger": ledger,
        "claim_boundary": plan["claim_boundary"],
    }


def build_audit_from(
    root: str | Path, plan: dict[str, Any], plan_path: str | Path,
    directory: str | Path, result_path: str | Path, *, expected_offline: bool,
) -> dict[str, Any]:
    root = Path(root).resolve(); directory = Path(directory)
    loaded_plan = json.loads(Path(plan_path).read_text())
    result = json.loads(Path(result_path).read_text())
    reconstruction = canonical(plan) == canonical(build_plan(root)) == canonical(loaded_plan)
    files = all(_sha(root / path) == sha for path, sha in plan["frozen_files"].items())
    cells = _cells(plan, directory); ledger = _ledger(directory)
    checks = {
        "plan_reconstruction": reconstruction,
        "frozen_files": files,
        "three_terminal_cells": len(cells) == 3 and all(row["status"] in TERMINAL for row in cells),
        "result_binding": result.get("plan_sha256") == digest(plan),
        "capacity_gate_passed": result.get("capacity_gate", {}).get("passed") is True,
        "offline_mode": ledger["offline"] is expected_offline,
        "no_reference_or_solver": plan["claim_boundary"]["reference_or_answer_loaded"] is False
        and plan["claim_boundary"]["solver_called"] is False,
    }
    return {
        "schema": VERSION + "-audit", "status": "passed" if all(checks.values()) else "failed",
        "plan_sha256": digest(plan), "result_sha256": _sha(result_path),
        "checks": checks, "ledger": ledger,
        "execution": {"new_provider_calls": 0, "new_solver_calls": 0},
    }
