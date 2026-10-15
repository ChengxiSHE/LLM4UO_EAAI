"""Frozen, resumable one-call Base evaluation on the fresh common-38 cohort."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
from typing import Any, Callable

from .benchmark_inputs import payload_sha256
from .formal_gateway import RequestUnavailable, VERSION as GATEWAY_VERSION
from .formal_provider import BASE_URL, MODEL
from .formal_runtime import parse_model
from .fresh_common38 import SOURCE_RELATIVE, build_private_bundle
from .gateway import Stopped
from .gurobi_cli_solver import DEFAULT_BINARY, VERSION as SOLVER_VERSION, execute as gurobi_execute
from .run_interruption import RunInterrupted
from .schema import canonical, digest
from .text2opt_v9_runtime import VERSION as BASE_RUNTIME_VERSION, initial_payload


VERSION = "fresh-common38-base-v1"
PACKET_READINESS = "experiments/fresh_common38_packet_readiness_20261015.json"
PLAN_PATH = "experiments/fresh_common38_base_plan_v1_20261015.json"
AUTH_PATH = "experiments/fresh_common38_base_authorization_v1_20261015.json"
RESULT_PATH = "experiments/fresh_common38_base_result_v1_20261015.json"
AUDIT_PATH = "experiments/fresh_common38_base_audit_v1_20261015.json"
RUN_DIRECTORY = "results/private/fresh_common38_base_v1"
CODE_PATHS = (
    "llm4or/fresh_common38_base.py",
    "llm4or/fresh_common38.py",
    "llm4or/text2opt_v9_runtime.py",
    "llm4or/text2opt_v6_runtime.py",
    "llm4or/formal_runtime.py",
    "llm4or/formal_gateway.py",
    "llm4or/formal_provider.py",
    "llm4or/gurobi_cli_solver.py",
    "llm4or/milp_schema.py",
    "llm4or/milp_solver.py",
    "scripts/freeze_fresh_common38_base.py",
    "scripts/run_fresh_common38_base.py",
    "scripts/score_fresh_common38_base.py",
)
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
    version = completed.stdout.splitlines()[0].strip()
    require(bool(version), "solver_version")
    return version


def build_plan(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    bundle = build_private_bundle(root)
    source_root = root / SOURCE_RELATIVE
    frozen_files = {path: _sha(root / path) for path in CODE_PATHS}
    frozen_files[PACKET_READINESS] = _sha(root / PACKET_READINESS)
    bindings = []
    for row in bundle["records"]:
        source_path = source_root / row["source_file"]
        require(_sha(source_path) == row["source_file_sha256"], "source_binding")
        public = row["public_payload"]
        require(payload_sha256(public) == row["public_payload_sha256"], "public_binding")
        payload = initial_payload(public)
        bindings.append({
            "id": row["id"], "family": row["family"],
            "public_input_sha256": row["public_payload_sha256"],
            "source_file": f"{SOURCE_RELATIVE}/{row['source_file']}",
            "source_file_sha256": row["source_file_sha256"],
            "initial_payload_sha256": digest(payload),
        })
        frozen_files[f"{SOURCE_RELATIVE}/{row['source_file']}"] = row["source_file_sha256"]
    binary = str(Path(DEFAULT_BINARY).resolve())
    maximum_reservation = 524_288 + 8_192 + 16_384
    token_cap = maximum_reservation + 1
    limits = {
        "max_requests": 38 * 3,
        "max_total_reserved_or_reported_tokens": 38 * 3 * maximum_reservation,
        "max_completion_tokens": 16_384,
        "max_input_bytes": 524_288,
        "max_output_bytes": 256_000,
        "token_overhead_reserve": 8_192,
        "request_seconds": 600,
        "max_run_seconds": 3 * 24 * 3600,
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
        "runtime_version": BASE_RUNTIME_VERSION,
        "gateway_version": GATEWAY_VERSION,
        "external_method": {
            "name": "Base", "scope_stage": "freshbase", "max_calls": 1,
            "answer_blind": True,
        },
        "replicates": [0],
        "public_inputs": {row["id"]: row["public_input_sha256"] for row in bindings},
        "bindings": bindings,
        "token_cap": token_cap, "trajectory_token_caps": [token_cap],
        "limits": limits,
        "resilience": {
            "max_attempts_per_request": 3, "backoff_seconds": [2, 5],
            "circuit_breaker_consecutive_failures": 8,
            "max_concurrent_requests": 5,
        },
        "matrix": {"inference_cells": 38},
        "progress_stage": "freshbase", "run_directory": RUN_DIRECTORY,
        "output": {"public_result": RESULT_PATH, "public_audit": AUDIT_PATH},
        "solver": {
            "backend": SOLVER_VERSION, "binary": binary,
            "binary_sha256": _sha(binary), "version_line": _binary_version(binary),
            "threads": 1, "solve_seconds": 20, "wall_seconds": 30,
        },
        "endpoint_metric": {
            "solver_status": 2, "relative_tolerance": 1e-5,
            "absolute_tolerance": 1e-6,
        },
        "runtime": {
            "python": platform.python_version(), "machine": platform.machine(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "psutil", "certifi")
            },
        },
        "frozen_files": dict(sorted(frozen_files.items())),
        "claim_boundary": {
            "answer_blind": True, "repair_calls": 0, "full_denominator": 38,
            "baseline_prompt_tuning": False, "broad_superiority_supported": False,
        },
    }


def authorization(root: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    return {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "endpoint": BASE_URL, "model": MODEL,
        "run_directory": str(root / plan["run_directory"]), "limits": plan["limits"],
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
    return f"freshbase:Base:0:{problem_id}"


def run_base(
    public: dict[str, Any], gateway: Any, scope: str, replicate: int,
    token_cap: int, *, solver: Callable[..., dict[str, Any]] = gurobi_execute,
    solver_config: dict[str, Any],
) -> dict[str, Any]:
    gateway.register(scope, 1, token_cap)
    payload = initial_payload(public)
    prefix = digest({
        "problem": public, "replicate": replicate,
        "version": BASE_RUNTIME_VERSION, "channel": "base",
    })
    parsed = parse_model(gateway.request(scope, payload, prefix, replicate, 0)["text"])
    if parsed.get("schema") != "milp-v1":
        return {
            "status": "unsupported", "reason": parsed.get("reason"),
            "model_sha256": None, "objective": None, "point": None,
        }
    solved = solver(
        {"op": "solve", "model": deepcopy(parsed)},
        time_limit=solver_config["solve_seconds"],
        threads=solver_config["threads"], wall_seconds=solver_config["wall_seconds"],
    )
    return {
        "status": solved.get("status"), "reason": solved.get("reason"),
        "model_sha256": digest(parsed), "objective": solved.get("objective"),
        "point": solved.get("point"),
    }


def run_plan(
    root: str | Path, plan: dict[str, Any], directory: str | Path, gateway: Any,
    *, runner: Callable[..., dict[str, Any]] = run_base,
    solver: Callable[..., dict[str, Any]] = gurobi_execute, workers: int = 5,
) -> dict[str, Any]:
    root = Path(root).resolve(); directory = Path(directory)
    require(canonical(plan) == canonical(build_plan(root)), "plan_reconstruction")
    require(workers == plan["resilience"]["max_concurrent_requests"] == 5, "worker_binding")
    plan_sha = digest(plan)
    rows = {row["id"]: row for row in build_private_bundle(root)["records"]}
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def one(binding: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        path = _cell_path(directory, binding["id"])
        if path.exists():
            return _load_cell(path, binding, plan_sha), False
        public = rows[binding["id"]]["public_payload"]
        require(payload_sha256(public) == binding["public_input_sha256"], "public_changed")
        require(digest(initial_payload(public)) == binding["initial_payload_sha256"], "payload_changed")
        scope = _scope(binding["id"]); gateway.work_started(scope)
        try:
            record = runner(
                public, gateway, scope, 0, plan["token_cap"],
                solver=solver, solver_config=plan["solver"],
            )
            cell = {
                "schema": VERSION + "-private-cell", "plan_sha256": plan_sha,
                "id": binding["id"], "family": binding["family"],
                "public_input_sha256": binding["public_input_sha256"],
                "status": "completed", "error": None, "record": record,
            }
            gateway.work_finished(scope, "complete")
        except RequestUnavailable as exc:
            cell = {
                "schema": VERSION + "-private-cell", "plan_sha256": plan_sha,
                "id": binding["id"], "family": binding["family"],
                "public_input_sha256": binding["public_input_sha256"],
                "status": "infrastructure_unavailable",
                "error": str(exc).split(":", 1)[-1][:160], "record": None,
            }
            gateway.work_finished(scope, "unavailable", cell["error"])
        except RunInterrupted:
            raise
        except Stopped as exc:
            halt = gateway.halt_reason() if hasattr(gateway, "halt_reason") else None
            if halt:
                raise RunInterrupted("global_halt:" + halt) from exc
            cell = {
                "schema": VERSION + "-private-cell", "plan_sha256": plan_sha,
                "id": binding["id"], "family": binding["family"],
                "public_input_sha256": binding["public_input_sha256"],
                "status": "method_failure", "error": str(exc)[:160], "record": None,
            }
            gateway.work_finished(scope, "complete", cell["error"])
        except Exception as exc:
            cell = {
                "schema": VERSION + "-private-cell", "plan_sha256": plan_sha,
                "id": binding["id"], "family": binding["family"],
                "public_input_sha256": binding["public_input_sha256"],
                "status": "method_failure", "error": type(exc).__name__, "record": None,
            }
            gateway.work_finished(scope, "complete", cell["error"])
        _write_new(path, cell)
        return cell, True

    cells = []; new_items = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, binding) for binding in plan["bindings"]]
        for future in as_completed(futures):
            cell, created = future.result(); cells.append(cell); new_items += int(created)
    return {
        "terminal": len(cells), "new_items": new_items,
        "status_counts": dict(sorted(Counter(cell["status"] for cell in cells).items())),
        "gateway": gateway.summary(),
    }


def load_cells(plan: dict[str, Any], directory: str | Path) -> list[dict[str, Any]]:
    plan_sha = digest(plan)
    return [_load_cell(_cell_path(directory, row["id"]), row, plan_sha) for row in plan["bindings"]]


def ledger_summary(directory: str | Path) -> dict[str, Any]:
    path = Path(directory) / "requests.sqlite3"
    require(path.is_file(), "ledger_missing")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        total = connection.execute(
            "SELECT physical_calls,physical_tokens,logical_calls,logical_tokens FROM totals WHERE id=1"
        ).fetchone()
        halt = connection.execute("SELECT reason FROM halt WHERE id=1").fetchone()
        retries = connection.execute("SELECT count(*) FROM retry_attempts WHERE ordinal>1").fetchone()[0]
        failed = connection.execute("SELECT count(*) FROM retry_attempts WHERE status='failed'").fetchone()[0]
    finally:
        connection.close()
    return {
        "physical_attempts": total[0], "reserved_or_reported_tokens": total[1],
        "logical_requests": total[2], "logical_tokens": total[3],
        "retry_attempts": retries, "failed_physical_attempts": failed,
        "halt": halt[0] if halt else None,
    }


def load_references(root: str | Path, plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    root = Path(root).resolve(); rows = {row["id"]: row for row in build_private_bundle(root)["records"]}
    references = {}
    for binding in plan["bindings"]:
        source = json.loads((root / binding["source_file"]).read_text())
        require(_sha(root / binding["source_file"]) == binding["source_file_sha256"], "source_changed")
        result = source.get("gurobi_result", {})
        optimum, status = result.get("theoretical_optimum"), result.get("solver_status")
        require(type(optimum) in (int, float) and math.isfinite(optimum) and type(status) is int,
                "reference_endpoint")
        references[binding["id"]] = {"optimum": optimum, "solver_status": status}
    return references


def score_cells(
    plan: dict[str, Any], cells: list[dict[str, Any]],
    references: dict[str, dict[str, Any]], accounting: dict[str, Any],
) -> dict[str, Any]:
    by_id = {cell["id"]: cell for cell in cells}
    require(len(by_id) == len(cells) == len(plan["bindings"]) == 38, "score_denominator")
    total = Counter(); families = {name: Counter() for name in ("rcpsp", "vrptw")}; rows = []
    endpoint = plan["endpoint_metric"]
    for binding in plan["bindings"]:
        cell = by_id[binding["id"]]; record = cell.get("record") or {}; reference = references[binding["id"]]
        correct = bool(
            cell["status"] == "completed" and record.get("status") == "optimal"
            and reference["solver_status"] == endpoint["solver_status"]
            and type(record.get("objective")) in (int, float)
            and math.isclose(record["objective"], reference["optimum"],
                             rel_tol=endpoint["relative_tolerance"],
                             abs_tol=endpoint["absolute_tolerance"])
        )
        if correct:
            disposition = "correct"
        elif cell["status"] in {"method_failure", "infrastructure_unavailable"}:
            disposition = cell["status"]
        elif record.get("status") == "optimal":
            disposition = "incorrect_objective"
        elif record.get("status") == "unsupported":
            disposition = "unsupported"
        else:
            disposition = "solver_unavailable"
        total[disposition] += 1; families[binding["family"]][disposition] += 1
        rows.append({
            "id": binding["id"], "family": binding["family"],
            "status": cell["status"], "solver_status": record.get("status"),
            "model_sha256": record.get("model_sha256"),
            "disposition": disposition, "correct": correct,
        })
    return {
        "schema": VERSION + "-public-result", "status": "complete",
        "plan_sha256": digest(plan),
        "aggregate": {"planned": 38, **dict(sorted(total.items())), "accuracy": total["correct"] / 38},
        "families": {
            name: {"planned": sum(families[name].values()), **dict(sorted(families[name].items()))}
            for name in sorted(families)
        },
        "rows": rows, "accounting": accounting,
        "privacy": {
            "contains_credentials": False, "contains_request_bodies": False,
            "contains_response_bodies": False, "contains_objectives": False,
            "contains_points": False, "contains_reference_values": False,
        },
        "information_regime": {
            "public_problem_and_structured_facts": True, "answer_blind": True,
            "repair_feedback": False, "calls_per_identity": 1,
        },
        "claim_boundary": plan["claim_boundary"],
    }


__all__ = [
    "AUDIT_PATH", "AUTH_PATH", "PLAN_PATH", "RESULT_PATH", "authorization",
    "build_plan", "ledger_summary", "load_cells", "load_references", "publish_new",
    "run_base", "run_plan", "score_cells",
]
