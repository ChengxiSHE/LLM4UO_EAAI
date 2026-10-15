"""Frozen, resumable OptiTrust-style compact-sidecar common-38 evaluation.

This is a paper-structure sensitivity, not an official OptiTrust reproduction.
One validated ``milp-v1`` candidate receives five bounded, hash-bound typed
reviews; no generated Python or third-party modeling-language runtime runs.
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from .fresh_common38 import SOURCE_RELATIVE, build_private_bundle
from .gateway import Stopped
from .gurobi_cli_solver import (
    DEFAULT_BINARY, VERSION as SOLVER_VERSION, execute as gurobi_execute,
)
from .optitrust_style_compact_runtime import (
    LANGUAGES, STAGES, VERSION as RUNTIME_VERSION, run_optitrust_style_compact,
)
from .run_interruption import RunInterrupted
from .schema import canonical, digest


VERSION = "fresh-common38-optitrust-style-compact-sidecar-v2"
PACKET_READINESS = "experiments/fresh_common38_packet_readiness_20261015.json"
PLAN_PATH = "experiments/fresh_common38_optitrust_style_compact_plan_v2_20261016.json"
AUTH_PATH = "experiments/fresh_common38_optitrust_style_compact_authorization_v2_20261016.json"
RESULT_PATH = "experiments/fresh_common38_optitrust_style_compact_result_v2_20261016.json"
AUDIT_PATH = "experiments/fresh_common38_optitrust_style_compact_audit_v2_20261016.json"
RUN_DIRECTORY = "results/private/fresh_common38_optitrust_style_compact_v2"
CODE_PATHS = (
    "llm4or/fresh_common38_optitrust_style_compact.py",
    "llm4or/fresh_common38_optitrust_style_compact_audit.py",
    "llm4or/optitrust_style_compact_runtime.py",
    "llm4or/fresh_common38.py",
    "llm4or/formal_gateway.py",
    "llm4or/formal_provider.py",
    "llm4or/gurobi_cli_solver.py",
    "llm4or/milp_contracts.py",
    "llm4or/milp_schema.py",
    "llm4or/milp_solver.py",
    "scripts/freeze_fresh_common38_optitrust_style_compact.py",
    "scripts/run_fresh_common38_optitrust_style_compact.py",
    "scripts/score_fresh_common38_optitrust_style_compact.py",
    "scripts/audit_fresh_common38_optitrust_style_compact.py",
)
TERMINAL = frozenset({"completed", "method_failure", "infrastructure_unavailable"})
RESOURCE_LIMITS = {
    "variables": 2_000, "constraints": 10_000, "nonzeros": 100_000,
    "serialized_bytes": 196_608,
}


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


def _stage_slots() -> list[dict[str, str | None]]:
    return [
        {
            "stage": stage,
            "modeling_language": LANGUAGES[index - 5] if index >= 5 else None,
        }
        for index, stage in enumerate(STAGES)
    ]


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
        bindings.append({
            "id": row["id"], "family": row["family"],
            "public_input_sha256": row["public_payload_sha256"],
            "source_file": f"{SOURCE_RELATIVE}/{row['source_file']}",
            "source_file_sha256": row["source_file_sha256"],
        })
        frozen_files[f"{SOURCE_RELATIVE}/{row['source_file']}"] = row["source_file_sha256"]
    binary = str(Path(DEFAULT_BINARY).resolve())
    maximum_reservation = 524_288 + 8_192 + 32_768
    token_cap = 10 * maximum_reservation + 1
    max_requests = 38 * 10 * 3
    limits = {
        "max_requests": max_requests,
        "max_total_reserved_or_reported_tokens": max_requests * maximum_reservation,
        "max_completion_tokens": 32_768,
        "max_input_bytes": 524_288,
        "max_output_bytes": 196_608,
        "token_overhead_reserve": 8_192,
        "request_seconds": 600,
        "max_run_seconds": 7 * 24 * 3600,
        "minimum_free_disk_bytes": 5_000_000_000,
    }
    return {
        "schema": VERSION + "-plan",
        "status": "frozen_ready_for_authorized_antchat_run",
        "authorization": "standing_user_approval_no_reconfirmation_20261016",
        "authorization_schema": VERSION + "-authorization",
        "authorization_path": AUTH_PATH,
        "kind": "fresh_common_external",
        "source_revision": bundle["source_revision"],
        "packet_readiness_sha256": frozen_files[PACKET_READINESS],
        "endpoint": BASE_URL, "model": MODEL,
        "runtime_version": RUNTIME_VERSION,
        "gateway_version": GATEWAY_VERSION,
        "external_method": {
            "name": "OptiTrustStyleCompact",
            "paper_label": "OptiTrust-style-compact-sidecar",
            "scope_stage": "freshoptitrustcompact",
            "max_calls": 10,
            "stage_slots": _stage_slots(),
            "strict_majority": {
                "required_votes": 3, "views": 5,
                "relative_tolerance": 1e-5, "absolute_tolerance": 1e-6,
            },
        },
        "replicates": [0],
        "public_inputs": {
            row["id"]: row["public_input_sha256"] for row in bindings
        },
        "bindings": bindings,
        "resource_limits": RESOURCE_LIMITS,
        "token_cap": token_cap,
        "trajectory_token_caps": [token_cap],
        "limits": limits,
        "resilience": {
            "max_attempts_per_request": 3,
            "backoff_seconds": [2, 5],
            "circuit_breaker_consecutive_failures": 8,
            "max_concurrent_requests": 5,
        },
        "matrix": {
            "inference_cells": 38,
            "logical_requests": 38 * 10,
            "candidate_solves_at_most": 38 * 5,
        },
        "progress_stage": "freshoptitrustcompact",
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
            "public_problem_and_structured_facts": True,
            "answer_blind_inference": True,
            "reference_loaded_after_all_inference_and_candidate_solves": True,
            "generated_python_executed": False,
            "single_canonical_strict_sidecar": True,
            "language_conditioned_bounded_typed_reviews": True,
        },
        "claim_boundary": {
            "official_optitrust_reproduction": False,
            "paper_structure_sensitivity_only": True,
            "fine_tuned_granite_checkpoint_used": False,
            "native_five_language_execution": False,
            "compact_typed_review_adapter": True,
            "full_denominator": 38,
            "baseline_prompt_tuning": False,
            "equal_budget_leaderboard": False,
            "broad_superiority_supported": False,
        },
    }


def authorization(root: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    return {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "endpoint": BASE_URL, "model": MODEL,
        "run_directory": str(root / plan["run_directory"]),
        "limits": plan["limits"],
        "user_confirmation": (
            "Standing autonomous approval reaffirmed 2026-10-16; AntChat runs "
            "need no repeated confirmation."
        ),
    }


def _write_new(path: str | Path, value: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
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
    return Path(directory) / "cells" / (
        hashlib.sha256(problem_id.encode()).hexdigest() + ".json"
    )


def _load_cell(
    path: str | Path, binding: dict[str, Any], plan_sha: str,
) -> dict[str, Any]:
    cell = json.loads(Path(path).read_text())
    require(
        cell.get("schema") == VERSION + "-private-cell"
        and cell.get("plan_sha256") == plan_sha
        and cell.get("id") == binding["id"]
        and cell.get("family") == binding["family"]
        and cell.get("public_input_sha256") == binding["public_input_sha256"]
        and cell.get("status") in TERMINAL,
        "checkpoint_binding",
    )
    return cell


def _scope(problem_id: str) -> str:
    return f"freshoptitrustcompact:OptiTrustStyleCompact:0:{problem_id}"


def _terminal_cell(
    plan_sha: str, binding: dict[str, Any], status: str,
    record: dict[str, Any] | None, error: str | None,
) -> dict[str, Any]:
    return {
        "schema": VERSION + "-private-cell", "plan_sha256": plan_sha,
        "id": binding["id"], "family": binding["family"],
        "public_input_sha256": binding["public_input_sha256"],
        "status": status, "error": error, "record": record,
    }


def _load_reference(path: Path, expected_sha: str) -> dict[str, Any]:
    require(_sha(path) == expected_sha, "source_changed")
    source = json.loads(path.read_text())
    result = source.get("gurobi_result", {})
    optimum, status = result.get("theoretical_optimum"), result.get("solver_status")
    require(
        type(optimum) in (int, float) and math.isfinite(float(optimum))
        and type(status) is int,
        "reference_endpoint",
    )
    return {"optimum": optimum, "solver_status": status}


def run_plan(
    root: str | Path, plan: dict[str, Any], directory: str | Path, gateway: Any,
    *, runner: Callable[..., dict[str, Any]] = run_optitrust_style_compact,
    solver: Callable[..., dict[str, Any]] = gurobi_execute,
    workers: int = 5,
) -> dict[str, Any]:
    root = Path(root).resolve()
    directory = Path(directory)
    require(canonical(plan) == canonical(build_plan(root)), "plan_reconstruction")
    require(
        workers == plan["resilience"]["max_concurrent_requests"] == 5,
        "worker_binding",
    )
    plan_sha = digest(plan)
    rows = {row["id"]: row for row in build_private_bundle(root)["records"]}
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def one(binding: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        path = _cell_path(directory, binding["id"])
        if path.exists():
            return _load_cell(path, binding, plan_sha), False
        public = rows[binding["id"]]["public_payload"]
        require(
            payload_sha256(public) == binding["public_input_sha256"],
            "public_changed",
        )
        scope = _scope(binding["id"])
        gateway.work_started(scope)

        def reference_loader() -> dict[str, Any]:
            return _load_reference(
                root / binding["source_file"], binding["source_file_sha256"],
            )

        try:
            record = runner(
                public, gateway, scope, 0, plan["token_cap"],
                solver=solver, solver_config=plan["solver"],
                resource_limits=plan["resource_limits"],
                reference_loader=reference_loader,
            )
            if record.get("status") == "method_failure":
                cell = _terminal_cell(
                    plan_sha, binding, "method_failure", record,
                    str(record.get("reason") or "method_failure")[:160],
                )
            else:
                cell = _terminal_cell(plan_sha, binding, "completed", record, None)
            gateway.work_finished(scope, "complete", cell["error"])
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
            cell = _terminal_cell(
                plan_sha, binding, "method_failure", None,
                str(exc).split(":", 1)[-1][:160],
            )
            gateway.work_finished(scope, "complete", cell["error"])
        except Exception as exc:
            cell = _terminal_cell(
                plan_sha, binding, "method_failure", None, type(exc).__name__,
            )
            gateway.work_finished(scope, "complete", cell["error"])
        _write_new(path, cell)
        return cell, True

    cells = []
    new_items = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, binding) for binding in plan["bindings"]]
        for future in as_completed(futures):
            cell, created = future.result()
            cells.append(cell)
            new_items += int(created)
    counts = Counter(cell["status"] for cell in cells)
    return {
        "terminal": len(cells), "new_items": new_items,
        "status_counts": dict(sorted(counts.items())),
        "gateway": gateway.summary(),
    }


def load_cells(plan: dict[str, Any], directory: str | Path) -> list[dict[str, Any]]:
    plan_sha = digest(plan)
    return [
        _load_cell(_cell_path(directory, row["id"]), row, plan_sha)
        for row in plan["bindings"]
    ]


def ledger_summary(directory: str | Path) -> dict[str, Any]:
    path = Path(directory) / "requests.sqlite3"
    require(path.is_file(), "ledger_missing")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        total = connection.execute(
            "SELECT physical_calls,physical_tokens,logical_calls,logical_tokens "
            "FROM totals WHERE id=1"
        ).fetchone()
        require(total is not None, "ledger_totals")
        halt = connection.execute("SELECT reason FROM halt WHERE id=1").fetchone()
        retries = connection.execute(
            "SELECT count(*) FROM retry_attempts WHERE ordinal>1"
        ).fetchone()[0]
        failed = connection.execute(
            "SELECT count(*) FROM retry_attempts WHERE status='failed'"
        ).fetchone()[0]
        failed += connection.execute(
            "SELECT count(*) FROM attempts a WHERE status IN ('failed','exhausted') "
            "AND NOT EXISTS (SELECT 1 FROM retry_attempts r "
            "WHERE r.key=a.key AND r.ordinal=1)"
        ).fetchone()[0]
    finally:
        connection.close()
    return {
        "physical_attempts": total[0],
        "reserved_or_reported_tokens": total[1],
        "logical_requests": total[2], "logical_tokens": total[3],
        "retry_attempts": retries, "failed_physical_attempts": failed,
        "halt": halt[0] if halt else None,
    }


def score_cells(
    plan: dict[str, Any], cells: list[dict[str, Any]], accounting: dict[str, Any],
) -> dict[str, Any]:
    by_id = {cell["id"]: cell for cell in cells}
    require(
        len(by_id) == len(cells) == len(plan["bindings"]) == 38,
        "score_denominator",
    )
    total = Counter()
    families = {name: Counter() for name in ("rcpsp", "vrptw")}
    rows = []
    for binding in plan["bindings"]:
        cell = by_id[binding["id"]]
        record = cell.get("record") if cell["status"] == "completed" else None
        correct = bool(record and record.get("author_accept"))
        if cell["status"] in {"method_failure", "infrastructure_unavailable"}:
            disposition = cell["status"]
        else:
            disposition = "correct" if correct else "incorrect"
        total[disposition] += 1
        families[binding["family"]][disposition] += 1
        consensus = record.get("consensus") if record else None
        views = record.get("views", []) if record else []
        rows.append({
            "id": binding["id"], "family": binding["family"],
            "status": cell["status"], "disposition": disposition,
            "correct": correct,
            "consensus_status": consensus.get("status") if consensus else None,
            "consensus_votes": consensus.get("votes") if consensus else 0,
            "valid_view_count": sum(
                view.get("status") == "optimal" for view in views
            ),
        })
    for counter in (total, *families.values()):
        for key in (
            "correct", "incorrect", "method_failure", "infrastructure_unavailable",
        ):
            counter[key] += 0
    return {
        "schema": VERSION + "-public-result", "status": "complete",
        "method": "OptiTrust-style-compact-sidecar",
        "plan_sha256": digest(plan),
        "aggregate": {
            "planned": 38, **dict(sorted(total.items())),
            "accuracy": total["correct"] / 38,
        },
        "families": {
            name: {"planned": sum(value.values()), **dict(sorted(value.items()))}
            for name, value in sorted(families.items())
        },
        "rows": rows,
        "accounting": {
            key: accounting.get(key) for key in (
                "physical_attempts", "retry_attempts", "failed_physical_attempts",
                "reserved_or_reported_tokens", "logical_requests", "logical_tokens",
                "halt",
            )
        },
        "privacy": {
            "contains_request_bodies": False,
            "contains_response_bodies": False,
            "contains_generated_code": False,
            "contains_objectives": False,
            "contains_points": False,
            "contains_reference_values": False,
            "contains_credentials": False,
        },
        "information_regime": plan["information_regime"],
        "claim_boundary": plan["claim_boundary"],
    }


__all__ = [
    "AUDIT_PATH", "AUTH_PATH", "PLAN_PATH", "RESULT_PATH", "RUN_DIRECTORY",
    "RESOURCE_LIMITS", "authorization", "build_plan", "ledger_summary", "load_cells", "publish_new",
    "run_plan", "score_cells",
]
