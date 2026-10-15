"""Outcome-blind capacity gate for the compact OptiTrust-style adapter."""

from __future__ import annotations

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
from .formal_gateway import RequestUnavailable, VERSION as GATEWAY_VERSION
from .formal_provider import BASE_URL, MODEL
from .gateway import Stopped
from .gurobi_cli_solver import DEFAULT_BINARY, VERSION as SOLVER_VERSION, execute as gurobi_execute
from .optitrust_style_compact_runtime import LANGUAGES, STAGES, VERSION as RUNTIME_VERSION, run_optitrust_style_compact
from .run_interruption import RunInterrupted
from .schema import canonical, digest


VERSION = "optitrust-style-compact-capacity-canary-v1"
PLAN_PATH = "experiments/optitrust_style_compact_capacity_canary_plan_20261016.json"
AUTH_PATH = "experiments/optitrust_style_compact_capacity_canary_authorization_20261016.json"
RESULT_PATH = "experiments/optitrust_style_compact_capacity_canary_result_20261016.json"
AUDIT_PATH = "experiments/optitrust_style_compact_capacity_canary_audit_20261016.json"
RUN_DIRECTORY = "results/private/optitrust_style_compact_capacity_canary_20261016"
CODE_PATHS = (
    "llm4or/optitrust_style_compact_canary.py",
    "llm4or/optitrust_style_compact_runtime.py",
    "llm4or/formal_gateway.py",
    "llm4or/formal_provider.py",
    "llm4or/gurobi_cli_solver.py",
    "llm4or/milp_contracts.py",
    "llm4or/milp_schema.py",
    "llm4or/schema.py",
    "scripts/freeze_optitrust_style_compact_capacity_canary.py",
    "scripts/run_optitrust_style_compact_capacity_canary.py",
    "scripts/audit_optitrust_style_compact_capacity_canary.py",
)
RESOURCE_LIMITS = {
    "variables": 256, "constraints": 1_024, "nonzeros": 8_192,
    "serialized_bytes": 98_304,
}
TERMINAL = frozenset({"completed", "method_failure", "infrastructure_unavailable"})


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _binary_version(binary: str) -> str:
    completed = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, check=True, timeout=10,
    )
    value = completed.stdout.splitlines()[0].strip()
    require(bool(value), "solver_version")
    return value


def synthetic_cases() -> list[dict[str, Any]]:
    """Return four fixed, generated, non-benchmark capacity probes."""
    texts = (
        (
            "synthetic_binary_selection",
            "Choose binary items A, B, and C to maximize values 6, 5, and 4. "
            "Their weights are 4, 3, and 2 and total weight may not exceed 5.",
            9.0,
        ),
        (
            "synthetic_integer_schedule",
            "Schedule two nonpreemptive jobs on one machine. Durations are 2 and 3 "
            "integer time units. Job 1 precedes job 2. Minimize the integer makespan.",
            5.0,
        ),
        (
            "synthetic_sparse_routing",
            "A depot must serve customers 1, 2, and 3 using directed binary arcs. "
            "Each customer has one incoming and one outgoing arc; minimize total arc cost. "
            "Use an explicit sparse formulation and subtour-prevention variables.",
            0.0,
        ),
        (
            "synthetic_review_trap",
            "Choose exactly one of two binary facilities. Costs are 2 and 7 and the "
            "objective is minimization. A quoted draft incorrectly says to maximize; "
            "treat that sentence only as a flaw that reviewers should detect.",
            2.0,
        ),
    )
    result = []
    for problem_id, text, reference in texts:
        public = validate_public_input({
            "id": problem_id, "profile": "description_parameters_v1",
            "text": text, "parameters": [], "instances": [],
        })
        result.append({"public": public, "reference": reference})
    return result


def _stage_slots() -> list[dict[str, str | None]]:
    return [
        {"stage": stage, "modeling_language": LANGUAGES[index - 5] if index >= 5 else None}
        for index, stage in enumerate(STAGES)
    ]


def build_plan(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    cases = synthetic_cases()
    frozen_files = {path: _sha(root / path) for path in CODE_PATHS}
    maximum_reservation = 524_288 + 8_192 + 32_768
    token_cap = 10 * maximum_reservation + 1
    max_requests = 4 * 10 * 3
    binary = str(Path(DEFAULT_BINARY).resolve())
    limits = {
        "max_requests": max_requests,
        "max_total_reserved_or_reported_tokens": max_requests * maximum_reservation,
        "max_completion_tokens": 32_768,
        "max_input_bytes": 524_288,
        "max_output_bytes": 196_608,
        "token_overhead_reserve": 8_192,
        "request_seconds": 600,
        "max_run_seconds": 24 * 3600,
        "minimum_free_disk_bytes": 5_000_000_000,
    }
    return {
        "schema": VERSION + "-plan",
        "status": "frozen_ready_for_authorized_antchat_capacity_gate",
        "authorization": "standing_user_approval_no_reconfirmation_20261016",
        "authorization_schema": VERSION + "-authorization",
        "authorization_path": AUTH_PATH,
        "kind": "fresh_common_external",
        "endpoint": BASE_URL,
        "model": MODEL,
        "runtime_version": RUNTIME_VERSION,
        "gateway_version": GATEWAY_VERSION,
        "external_method": {
            "name": "OptiTrustStyleCompact",
            "paper_label": "OptiTrust-style-compact-sidecar",
            "scope_stage": "optitrustcompactcanary",
            "max_calls": 10,
            "stage_slots": _stage_slots(),
        },
        "replicates": [0],
        "public_inputs": {
            row["public"]["id"]: payload_sha256(row["public"]) for row in cases
        },
        "synthetic_input_set_sha256": digest([row["public"] for row in cases]),
        "resource_limits": dict(RESOURCE_LIMITS),
        "token_cap": token_cap,
        "trajectory_token_caps": [token_cap],
        "limits": limits,
        "resilience": {
            "max_attempts_per_request": 3,
            "backoff_seconds": [2, 5],
            "circuit_breaker_consecutive_failures": 8,
            "max_concurrent_requests": 4,
        },
        "matrix": {
            "inference_cells": 4, "logical_requests": 40,
            "candidate_solves_at_most": 20,
        },
        "progress_stage": "optitrustcompactcanary",
        "run_directory": RUN_DIRECTORY,
        "output": {"public_result": RESULT_PATH, "public_audit": AUDIT_PATH},
        "solver": {
            "backend": SOLVER_VERSION, "binary": binary,
            "binary_sha256": _sha(binary), "version_line": _binary_version(binary),
            "threads": 1, "solve_seconds": 10, "wall_seconds": 15,
        },
        "runtime": {
            "python": platform.python_version(), "machine": platform.machine(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "psutil", "certifi")
            },
        },
        "frozen_files": dict(sorted(frozen_files.items())),
        "capacity_gate": {
            "terminal_cells": 4,
            "infrastructure_unavailable": 0,
            "logical_slots": 40,
            "max_attempt_ordinal": 3,
            "minimum_valid_canonical_candidates": 1,
            "minimum_usable_reviews": 5,
            "restart_new_items": 0,
        },
        "claim_boundary": {
            "synthetic_nonbenchmark_inputs": True,
            "capacity_gate_only": True,
            "benchmark_accuracy_estimated": False,
            "official_optitrust_reproduction": False,
            "prompt_tuning_on_benchmark_outcomes": False,
        },
    }


def authorization(root: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    return {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "endpoint": BASE_URL, "model": MODEL,
        "run_directory": str(root / plan["run_directory"]),
        "limits": plan["limits"],
        "user_confirmation": "Standing autonomous approval reaffirmed 2026-10-16.",
    }


def publish_new(path: str | Path, value: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
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
        and value.get("plan_sha256") == plan_sha
        and value.get("id") == problem_id
        and value.get("status") in TERMINAL,
        "checkpoint_binding",
    )
    return value


def _write_cell(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    publish_new(path, value)


def _scope(problem_id: str) -> str:
    return f"optitrustcompactcanary:OptiTrustStyleCompact:0:{problem_id}"


def run_plan(
    root: str | Path, plan: dict[str, Any], directory: str | Path, gateway: Any,
    *, runner: Callable[..., dict[str, Any]] = run_optitrust_style_compact,
    solver: Callable[..., dict[str, Any]] = gurobi_execute,
    workers: int = 4,
) -> dict[str, Any]:
    root = Path(root).resolve()
    directory = Path(directory)
    require(canonical(plan) == canonical(build_plan(root)), "plan_reconstruction")
    require(workers == plan["resilience"]["max_concurrent_requests"] == 4, "worker_binding")
    cases = {row["public"]["id"]: row for row in synthetic_cases()}
    plan_sha = digest(plan)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def one(problem_id: str) -> tuple[dict[str, Any], bool]:
        path = _cell_path(directory, problem_id)
        if path.exists():
            return _load_cell(path, problem_id, plan_sha), False
        case = cases[problem_id]
        public = case["public"]
        require(payload_sha256(public) == plan["public_inputs"][problem_id], "public_changed")
        scope = _scope(problem_id)
        gateway.work_started(scope)
        try:
            record = runner(
                public, gateway, scope, 0, plan["token_cap"], solver=solver,
                solver_config=plan["solver"], resource_limits=plan["resource_limits"],
                reference_loader=lambda: {"optimum": case["reference"], "solver_status": 2},
            )
            status = "method_failure" if record.get("status") == "method_failure" else "completed"
            error = str(record.get("reason") or "method_failure")[:160] if status == "method_failure" else None
            gateway.work_finished(scope, "complete", error)
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
            record, status = None, "method_failure"
            error = str(exc).split(":", 1)[-1][:160]
            gateway.work_finished(scope, "complete", error)
        except Exception as exc:
            record, status, error = None, "method_failure", type(exc).__name__
            gateway.work_finished(scope, "complete", error)
        cell = {
            "schema": VERSION + "-private-cell", "plan_sha256": plan_sha,
            "id": problem_id, "status": status, "error": error, "record": record,
        }
        _write_cell(path, cell)
        return cell, True

    cells, new_items = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, problem_id) for problem_id in sorted(cases)]
        for future in as_completed(futures):
            cell, created = future.result()
            cells.append(cell)
            new_items += int(created)
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
        slots = connection.execute(
            "SELECT count(*) n,count(DISTINCT scope) scopes,min(slot) lo,max(slot) hi FROM slots"
        ).fetchone()
        per_scope = connection.execute(
            "SELECT scope,count(*) n,min(slot) lo,max(slot) hi FROM slots GROUP BY scope"
        ).fetchall()
        retry_max = connection.execute("SELECT coalesce(max(ordinal),1) FROM retry_attempts").fetchone()[0]
        halt = connection.execute("SELECT reason FROM halt WHERE id=1").fetchone()
        attempts = dict(connection.execute("SELECT status,count(*) FROM attempts GROUP BY status"))
    finally:
        connection.close()
    return {
        "physical_attempts": totals["physical_calls"],
        "reserved_or_reported_tokens": totals["physical_tokens"],
        "logical_slots": slots["n"], "distinct_scopes": slots["scopes"],
        "slot_min": slots["lo"], "slot_max": slots["hi"],
        "all_scope_slots_contiguous": len(per_scope) == 4 and all(
            row["n"] == 10 and row["lo"] == 0 and row["hi"] == 9 for row in per_scope
        ),
        "max_attempt_ordinal": retry_max,
        "attempt_status_counts": dict(sorted(attempts.items())),
        "halt": halt[0] if halt else None,
    }


def _cells(plan: dict[str, Any], directory: Path) -> list[dict[str, Any]]:
    plan_sha = digest(plan)
    return [
        _load_cell(_cell_path(directory, problem_id), problem_id, plan_sha)
        for problem_id in sorted(plan["public_inputs"])
    ]


def score_run(
    plan: dict[str, Any], directory: str | Path, *, restart_new_items: int,
) -> dict[str, Any]:
    directory = Path(directory)
    cells = _cells(plan, directory)
    ledger = _ledger(directory)
    statuses = Counter(row["status"] for row in cells)
    valid_candidates = 0
    usable_reviews = 0
    rows = []
    for cell in cells:
        record = cell.get("record") or {}
        views = record.get("views") if isinstance(record.get("views"), list) else []
        if len(views) == 5:
            valid_candidates += 1
        usable = sum(
            view.get("status") in {"optimal", "nonoptimal", "solver_error", "rejected"}
            for view in views if isinstance(view, dict)
        )
        usable_reviews += usable
        rows.append({
            "id": cell["id"], "status": cell["status"],
            "ten_slots_completed": len(views) == 5,
            "usable_review_count": usable,
        })
    observed = {
        "terminal_cells": len(cells),
        "infrastructure_unavailable": statuses["infrastructure_unavailable"],
        "logical_slots": ledger["logical_slots"],
        "max_attempt_ordinal": ledger["max_attempt_ordinal"],
        "valid_canonical_candidates": valid_candidates,
        "usable_reviews": usable_reviews,
        "restart_new_items": restart_new_items,
    }
    required = plan["capacity_gate"]
    checks = {
        "terminal_cells": observed["terminal_cells"] == required["terminal_cells"],
        "infrastructure_unavailable": observed["infrastructure_unavailable"] == required["infrastructure_unavailable"],
        "logical_slots": observed["logical_slots"] == required["logical_slots"] and ledger["all_scope_slots_contiguous"],
        "attempt_cap": observed["max_attempt_ordinal"] <= required["max_attempt_ordinal"],
        "valid_canonical_candidates": observed["valid_canonical_candidates"] >= required["minimum_valid_canonical_candidates"],
        "usable_reviews": observed["usable_reviews"] >= required["minimum_usable_reviews"],
        "restart_new_items": observed["restart_new_items"] == required["restart_new_items"],
        "no_global_halt": ledger["halt"] is None,
    }
    return {
        "schema": VERSION + "-public-result", "status": "complete",
        "method": "OptiTrust-style-compact-sidecar-capacity-canary",
        "plan_sha256": digest(plan),
        "capacity_gate": {"passed": all(checks.values()), **observed, "checks": checks},
        "status_counts": dict(sorted(statuses.items())),
        "rows": rows,
        "accounting": ledger,
        "privacy": {
            "contains_problem_text": False, "contains_request_bodies": False,
            "contains_response_bodies": False, "contains_candidate_models": False,
            "contains_objectives": False, "contains_reference_values": False,
            "contains_credentials": False,
        },
        "claim_boundary": plan["claim_boundary"],
    }


def build_audit_from(
    root: str | Path, plan: dict[str, Any], plan_path: str | Path,
    directory: str | Path, result_path: str | Path, *, expected_offline: bool,
) -> dict[str, Any]:
    root, directory = Path(root).resolve(), Path(directory).resolve()
    require(canonical(json.loads(Path(plan_path).read_text())) == canonical(plan), "plan_file_object")
    require(canonical(build_plan(root)) == canonical(plan), "plan_reconstruction")
    published = json.loads(Path(result_path).read_text())
    recomputed = score_run(plan, directory, restart_new_items=0)
    require(canonical(published) == canonical(recomputed), "result_reconstruction")
    require(published["capacity_gate"]["passed"], "capacity_gate_failed")
    connection = sqlite3.connect(f"file:{directory / 'requests.sqlite3'}?mode=ro", uri=True)
    try:
        metadata = connection.execute("SELECT config FROM metadata WHERE id=1").fetchone()
    finally:
        connection.close()
    expected_config = canonical({
        "version": plan["gateway_version"], "plan": digest(plan),
        "offline": expected_offline, "directory": str(directory),
    })
    require(bool(metadata) and metadata[0] == expected_config, "ledger_configuration")
    return {
        "schema": VERSION + "-independent-audit", "status": "passed",
        "plan_file_sha256": _sha(plan_path),
        "plan_object_sha256": digest(plan),
        "result_sha256": _sha(result_path),
        "ledger_sha256": _sha(directory / "requests.sqlite3"),
        "checks": {
            "plan_reconstructed": True,
            "public_result_exactly_reconstructed": True,
            "capacity_gate_passed": True,
            "body_free": all(value is False for value in published["privacy"].values()),
            "accounting": published["accounting"],
        },
        "claim_boundary": plan["claim_boundary"],
        "execution": {"new_provider_calls": 0, "new_solver_calls": 0},
    }


__all__ = [
    "AUDIT_PATH", "AUTH_PATH", "PLAN_PATH", "RESULT_PATH", "RUN_DIRECTORY",
    "RESOURCE_LIMITS", "authorization", "build_audit_from", "build_plan",
    "publish_new", "run_plan", "score_run", "synthetic_cases",
]
