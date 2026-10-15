"""Frozen, resumable current-snapshot CoE-safe fresh common-38 evaluation."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
from typing import Any, Callable

from .benchmark_inputs import payload_sha256, validate_public_input
from .bind_runtime import bind_reference_projection
from .coe_official_adapter import CoEPromptSource
from .coe_runtime import (
    PROMPT_VERSION, VERSION as COE_RUNTIME_VERSION, run_coe_forward,
)
from .formal_gateway import RequestUnavailable, VERSION as GATEWAY_VERSION
from .formal_provider import BASE_URL, MODEL
from .fresh_common38 import SOURCE_RELATIVE, build_private_bundle
from .gateway import Stopped
from .gurobi_cli_solver import (
    DEFAULT_BINARY, VERSION as SOLVER_VERSION, execute as gurobi_execute,
)
from .run_interruption import RunInterrupted
from .schema import canonical, digest


VERSION = "fresh-common38-coe-current-v2"
PLAN_PATH = "experiments/fresh_common38_coe_current_plan_v2_20261015.json"
AUTH_PATH = "experiments/fresh_common38_coe_current_authorization_v2_20261015.json"
RESULT_PATH = "experiments/fresh_common38_coe_current_result_v2_20261015.json"
AUDIT_PATH = "experiments/fresh_common38_coe_current_audit_v2_20261015.json"
RUN_DIRECTORY = "results/private/fresh_common38_coe_current_v2"
COE_UPSTREAM = "data/raw/xzymustbexzy__Chain-of-Experts_20261003"
PACKET_READINESS = "experiments/fresh_common38_packet_readiness_20261015.json"
SKELETON = '''def solve_problem():
    """Solve the exact numeric optimization instance in the description.

    Returns:
        objective_value: the optimal objective value as a single int or float
    """
    objective_value = 0
    return objective_value
'''
CODE_PATHS = (
    "llm4or/fresh_common38_coe.py",
    "llm4or/fresh_common38.py",
    "llm4or/coe_runtime.py",
    "llm4or/coe_official_adapter.py",
    "llm4or/external_code_adapter.py",
    "llm4or/restricted_gurobi.py",
    "llm4or/formal_gateway.py",
    "llm4or/formal_provider.py",
    "llm4or/gurobi_cli_solver.py",
    "llm4or/milp_solver.py",
    "scripts/freeze_fresh_common38_coe.py",
    "scripts/run_fresh_common38_coe.py",
    "scripts/score_fresh_common38_coe.py",
)
TERMINAL = frozenset({"completed", "method_failure", "infrastructure_unavailable"})


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _binary_version(binary: str) -> str:
    completed = subprocess.run(
        [binary, "--version"], capture_output=True, text=True,
        check=True, timeout=10,
    )
    version = completed.stdout.splitlines()[0].strip()
    require(bool(version), "solver_version")
    return version


def coe_public_projection(packet: dict[str, Any]) -> dict[str, Any]:
    packet = validate_public_input(packet)
    return validate_public_input({
        "id": packet["id"], "profile": "description_parameters_v1",
        "text": packet["text"], "parameters": [], "instances": [],
    })


def build_plan(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    bundle = build_private_bundle(root)
    source_root = root / SOURCE_RELATIVE
    prompts = CoEPromptSource.load(root / COE_UPSTREAM, "current")
    bindings = []
    frozen_files = {path: _sha(root / path) for path in CODE_PATHS}
    frozen_files[PACKET_READINESS] = _sha(root / PACKET_READINESS)
    for row in bundle["records"]:
        source_path = source_root / row["source_file"]
        require(_sha(source_path) == row["source_file_sha256"], "source_binding")
        public = coe_public_projection(row["public_payload"])
        bindings.append({
            "id": row["id"], "family": row["family"],
            "packet_public_input_sha256": row["public_payload_sha256"],
            "coe_public_input_sha256": payload_sha256(public),
            "public_text_sha256": row["public_text_sha256"],
            "source_file": f"{SOURCE_RELATIVE}/{row['source_file']}",
            "source_file_sha256": row["source_file_sha256"],
        })
        frozen_files[f"{SOURCE_RELATIVE}/{row['source_file']}"] = row["source_file_sha256"]
    binary = str(Path(DEFAULT_BINARY).resolve())
    maximum_reservation = 524_288 + 8_192 + 8_192
    token_cap = 11 * maximum_reservation + 1
    limits = {
        "max_requests": 38 * 11 * 3,
        "max_total_reserved_or_reported_tokens": 38 * 11 * 3 * maximum_reservation,
        "max_completion_tokens": 8_192,
        "max_input_bytes": 524_288,
        "max_output_bytes": 256_000,
        "token_overhead_reserve": 8_192,
        "request_seconds": 600,
        "max_run_seconds": 7 * 24 * 3600,
        "minimum_free_disk_bytes": 5_000_000_000,
    }
    return {
        "schema": VERSION + "-plan",
        "status": "frozen_ready_for_authorized_antchat_run",
        "authorization": "approved_scheme_A_G07_G09_and_standing_no_reconfirmation",
        "authorization_schema": VERSION + "-authorization",
        "authorization_path": AUTH_PATH,
        "kind": "fresh_common_external",
        "source_revision": bundle["source_revision"],
        "packet_readiness_sha256": frozen_files[PACKET_READINESS],
        "endpoint": BASE_URL, "model": MODEL,
        "runtime_version": PROMPT_VERSION,
        "coe_runtime_version": COE_RUNTIME_VERSION,
        "gateway_version": GATEWAY_VERSION,
        "external_method": {
            "name": "CoE", "scope_stage": "freshcoe", "max_calls": 11,
            "snapshot": "current", "max_collaborations": 5,
            "reflection": False, "rng_seed": 0,
        },
        "upstream": {
            "commit": prompts.commit,
            "source_adapter_snapshot": prompts.snapshot,
            "license": "not_found_in_official_repository_recheck_20261015",
        },
        "replicates": [0],
        "public_inputs": {row["id"]: row["coe_public_input_sha256"] for row in bindings},
        "bindings": bindings,
        "code_example_sha256": hashlib.sha256(SKELETON.encode()).hexdigest(),
        "token_cap": token_cap,
        "trajectory_token_caps": [token_cap],
        "limits": limits,
        "resilience": {
            "max_attempts_per_request": 3,
            "backoff_seconds": [2, 5],
            "circuit_breaker_consecutive_failures": 8,
            "max_concurrent_requests": 5,
        },
        "matrix": {"inference_cells": 38},
        "progress_stage": "freshcoe",
        "run_directory": RUN_DIRECTORY,
        "output": {"public_result": RESULT_PATH, "public_audit": AUDIT_PATH},
        "solver": {
            "backend": SOLVER_VERSION, "binary": binary,
            "binary_sha256": _sha(binary), "version_line": _binary_version(binary),
            "threads": 1, "solve_seconds": 20, "wall_seconds": 30,
        },
        "runtime": {
            "python": platform.python_version(), "machine": platform.machine(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "psutil", "certifi")
            },
        },
        "frozen_files": dict(sorted(frozen_files.items())),
        "information_regime": {
            "official_method_input": "public prose including numeric annex plus generic no-answer skeleton",
            "structured_instance_data": False,
            "reference_loaded_after_durable_reducer": True,
            "transport_json_object_policy": "unwrap exact text wrapper; otherwise preserve the complete JSON object bytes as the official response",
        },
        "claim_boundary": {
            "official_current_snapshot_forward_only": True,
            "reflection": False,
            "generated_python_executed": False,
            "restricted_translation_and_trusted_solver_only": True,
            "full_denominator": 38,
            "baseline_prompt_tuning": False,
            "broad_superiority_supported": False,
            "upstream_license_verified": False,
        },
    }


def authorization(root: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    return {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "endpoint": BASE_URL, "model": MODEL,
        "run_directory": str(root / plan["run_directory"]),
        "limits": plan["limits"],
        "user_confirmation": "Scheme A approved 2026-10-15; AntChat runs need no repeated confirmation.",
    }


def _write_new(path: str | Path, value: dict[str, Any]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ValueError("output_exists") from exc
    raw = (canonical(value) + "\n").encode()
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


def publish_new(path: str | Path, value: dict[str, Any]) -> None:
    _write_new(path, value)


def _cell_path(directory: str | Path, problem_id: str) -> Path:
    return Path(directory) / "cells" / (hashlib.sha256(problem_id.encode()).hexdigest() + ".json")


def _load_cell(path: str | Path, binding: dict[str, Any], plan_sha: str) -> dict[str, Any]:
    cell = json.loads(Path(path).read_text())
    require(
        cell.get("schema") == VERSION + "-private-cell"
        and cell.get("plan_sha256") == plan_sha
        and cell.get("id") == binding["id"]
        and cell.get("family") == binding["family"]
        and cell.get("status") in TERMINAL,
        "checkpoint_binding",
    )
    return cell


def _scope(problem_id: str) -> str:
    return f"freshcoe:CoE:0:{problem_id}"


def _terminal_cell(
    plan_sha: str, binding: dict[str, Any], status: str,
    record: dict[str, Any] | None, error: str | None,
) -> dict[str, Any]:
    return {
        "schema": VERSION + "-private-cell", "plan_sha256": plan_sha,
        "id": binding["id"], "family": binding["family"],
        "coe_public_input_sha256": binding["coe_public_input_sha256"],
        "status": status, "error": error, "record": record,
    }


def run_plan(
    root: str | Path, plan: dict[str, Any], directory: str | Path, gateway: Any,
    *, runner: Callable[..., dict[str, Any]] = run_coe_forward,
    solver: Callable[..., dict[str, Any]] = gurobi_execute,
    workers: int = 5,
) -> dict[str, Any]:
    root = Path(root).resolve(); directory = Path(directory)
    require(canonical(plan) == canonical(build_plan(root)), "plan_reconstruction")
    require(workers == plan["resilience"]["max_concurrent_requests"] == 5, "worker_binding")
    plan_sha = digest(plan)
    rows = {row["id"]: row for row in build_private_bundle(root)["records"]}
    prompts = CoEPromptSource.load(root / COE_UPSTREAM, "current")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def one(binding: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        cell_path = _cell_path(directory, binding["id"])
        if cell_path.exists():
            return _load_cell(cell_path, binding, plan_sha), False
        row = rows[binding["id"]]
        source_path = root / binding["source_file"]
        require(_sha(source_path) == binding["source_file_sha256"], "source_changed")
        source = json.loads(source_path.read_text())
        public = coe_public_projection(row["public_payload"])
        require(payload_sha256(public) == binding["coe_public_input_sha256"], "public_changed")
        scope = _scope(binding["id"])
        gateway.work_started(scope)
        runtime_checkpoint = directory / "inference" / (digest(scope) + ".json")
        runtime_checkpoint.parent.mkdir(parents=True, exist_ok=True)

        def reference_loader() -> list[dict[str, Any]]:
            reference = bind_reference_projection(source)
            return [{"input": {}, "output": [reference["optimum"]]}]

        try:
            record = runner(
                public, {"description": public["text"], "code_example": SKELETON},
                "solve_problem", gateway, scope, 0, plan["token_cap"], prompts,
                reference_loader, max_collaborations=5, rng_seed=0,
                solver=solver, checkpoint_path=runtime_checkpoint,
            )
            cell = _terminal_cell(plan_sha, binding, "completed", record, None)
            gateway.work_finished(scope, "complete")
        except RequestUnavailable as exc:
            cell = _terminal_cell(
                plan_sha, binding, "infrastructure_unavailable", None,
                str(exc).split(":", 1)[-1][:160],
            )
            gateway.work_finished(scope, "unavailable", cell["error"])
        except RunInterrupted:
            raise
        except Stopped as exc:
            halt = gateway.halt_reason() if hasattr(gateway, "halt_reason") else None
            if halt:
                raise RunInterrupted("global_halt:" + halt) from exc
            cell = _terminal_cell(plan_sha, binding, "method_failure", None,
                                  str(exc).split(":", 1)[-1][:160])
            gateway.work_finished(scope, "complete", cell["error"])
        except Exception as exc:
            cell = _terminal_cell(plan_sha, binding, "method_failure", None, type(exc).__name__)
            gateway.work_finished(scope, "complete", cell["error"])
        _write_new(cell_path, cell)
        return cell, True

    cells = []; new_items = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, binding) for binding in plan["bindings"]]
        for future in as_completed(futures):
            cell, created = future.result()
            cells.append(cell); new_items += int(created)
    counts = Counter(cell["status"] for cell in cells)
    return {
        "terminal": len(cells), "new_items": new_items,
        "status_counts": dict(sorted(counts.items())), "gateway": gateway.summary(),
    }


def load_cells(plan: dict[str, Any], directory: str | Path) -> list[dict[str, Any]]:
    plan_sha = digest(plan)
    return [_load_cell(_cell_path(directory, row["id"]), row, plan_sha)
            for row in plan["bindings"]]


def ledger_summary(directory: str | Path) -> dict[str, Any]:
    path = Path(directory) / "requests.sqlite3"
    require(path.is_file(), "ledger_missing")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        total = connection.execute(
            "SELECT physical_calls,physical_tokens,logical_calls,logical_tokens FROM totals WHERE id=1"
        ).fetchone()
        halt = connection.execute("SELECT reason FROM halt WHERE id=1").fetchone()
        retries = connection.execute(
            "SELECT count(*) FROM retry_attempts WHERE ordinal>1"
        ).fetchone()[0]
        failed = connection.execute(
            "SELECT count(*) FROM retry_attempts WHERE status='failed'"
        ).fetchone()[0]
        failed += connection.execute(
            "SELECT count(*) FROM attempts a WHERE status IN ('failed','exhausted') "
            "AND NOT EXISTS (SELECT 1 FROM retry_attempts r WHERE r.key=a.key AND r.ordinal=1)"
        ).fetchone()[0]
    finally:
        connection.close()
    return {
        "physical_attempts": total[0], "reserved_or_reported_tokens": total[1],
        "logical_requests": total[2], "logical_tokens": total[3],
        "retry_attempts": retries, "failed_physical_attempts": failed,
        "halt": halt[0] if halt else None,
    }


def score_cells(
    plan: dict[str, Any], cells: list[dict[str, Any]], accounting: dict[str, Any],
) -> dict[str, Any]:
    by_id = {cell["id"]: cell for cell in cells}
    require(len(by_id) == len(cells) == len(plan["bindings"]) == 38, "score_denominator")
    total = Counter(); tolerance = Counter(); families = {name: Counter() for name in ("rcpsp", "vrptw")}
    rows = []
    for binding in plan["bindings"]:
        cell = by_id[binding["id"]]
        record = cell.get("record") if cell["status"] == "completed" else None
        correct = bool(record and record.get("author_accept"))
        tolerant = bool(record and record.get("tolerance_accept"))
        supported = bool(record and record.get("adapter_supported"))
        if cell["status"] == "infrastructure_unavailable":
            disposition = "infrastructure_unavailable"
        elif cell["status"] == "method_failure":
            disposition = "method_failure"
        else:
            disposition = "correct" if correct else "incorrect"
        total[disposition] += 1; families[binding["family"]][disposition] += 1
        tolerance["correct" if tolerant else disposition if disposition != "correct" else "incorrect"] += 1
        rows.append({
            "id": binding["id"], "family": binding["family"],
            "status": cell["status"], "author_exact": correct,
            "tolerance_match": tolerant, "adapter_supported": supported,
            "disposition": disposition,
        })
    for counter in (total, tolerance, *families.values()):
        for key in ("correct", "incorrect", "method_failure", "infrastructure_unavailable"):
            counter[key] += 0
    return {
        "schema": VERSION + "-public-result", "status": "complete",
        "plan_sha256": digest(plan),
        "aggregate": {"planned": 38, **dict(sorted(total.items())),
                      "accuracy": total["correct"] / 38},
        "tolerance_secondary": {"planned": 38, **dict(sorted(tolerance.items())),
                                "accuracy": tolerance["correct"] / 38},
        "families": {name: {"planned": sum(value.values()), **dict(sorted(value.items()))}
                     for name, value in sorted(families.items())},
        "rows": rows,
        "accounting": {key: accounting.get(key) for key in (
            "physical_attempts", "retry_attempts", "failed_physical_attempts",
            "reserved_or_reported_tokens", "logical_requests", "logical_tokens", "halt",
        )},
        "privacy": {
            "contains_request_bodies": False, "contains_response_bodies": False,
            "contains_generated_code": False, "contains_objectives": False,
            "contains_points": False, "contains_reference_values": False,
            "contains_credentials": False,
        },
        "information_regime": plan["information_regime"],
        "claim_boundary": plan["claim_boundary"],
    }


__all__ = [
    "authorization", "build_plan", "coe_public_projection", "ledger_summary",
    "load_cells", "publish_new", "run_plan", "score_cells",
]
