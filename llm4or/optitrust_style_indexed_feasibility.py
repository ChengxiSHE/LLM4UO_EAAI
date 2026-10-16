"""Two-family end-to-end feasibility gate for the indexed review pipeline."""

from __future__ import annotations

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
from .gurobi_cli_solver import DEFAULT_BINARY, VERSION as SOLVER_VERSION, execute as gurobi_execute
from .optitrust_style_indexed_capacity import (
    PREPARATION_PYTHON, RESOURCE_LIMITS, _preparation_runtime,
    publish_new, selected_cases as capacity_cases,
)
from .optitrust_style_indexed_runtime import (
    LANGUAGES, STAGES, VERSION as RUNTIME_VERSION, run_optitrust_style_indexed,
)
from .run_interruption import RunInterrupted
from .schema import canonical, digest


VERSION = "optitrust-style-indexed-feasibility-v2"
PLAN_PATH = "experiments/optitrust_style_indexed_feasibility_plan_v2_20261016.json"
AUTH_PATH = "experiments/optitrust_style_indexed_feasibility_authorization_v2_20261016.json"
RESULT_PATH = "experiments/optitrust_style_indexed_feasibility_result_v2_20261016.json"
AUDIT_PATH = "experiments/optitrust_style_indexed_feasibility_audit_v2_20261016.json"
RUN_DIRECTORY = "results/private/optitrust_style_indexed_feasibility_v2_20261016"
CODE_PATHS = (
    "llm4or/optitrust_style_indexed_feasibility.py",
    "llm4or/optitrust_style_indexed_capacity.py",
    "llm4or/optitrust_style_indexed_runtime.py",
    "llm4or/indexed_milp_ir.py",
    "llm4or/formal_gateway.py", "llm4or/formal_provider.py",
    "llm4or/openai_httpx_worker.py", "llm4or/gurobi_cli_solver.py",
    "llm4or/milp_schema.py", "llm4or/schema.py",
    "scripts/openai_httpx_transport_worker.py",
    "scripts/freeze_optitrust_style_indexed_feasibility.py",
    "scripts/run_optitrust_style_indexed_feasibility.py",
    "scripts/audit_optitrust_style_indexed_feasibility.py",
)
TERMINAL = frozenset({"completed", "method_failure", "infrastructure_unavailable"})


def require(ok: bool, code: str) -> None:
    if not ok: raise ValueError(code)


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected_cases(root: str | Path) -> list[dict[str, Any]]:
    rows = [row for row in capacity_cases(root) if "max_public_bytes" in row["selection_reasons"]]
    require(len(rows) == 2 and len({row["family"] for row in rows}) == 2, "feasibility_selection")
    return sorted(rows, key=lambda row: row["id"])


def _stage_slots():
    return [
        {"stage": stage, "modeling_language": LANGUAGES[index - 5] if index >= 5 else None}
        for index, stage in enumerate(STAGES)
    ]


def _binary_version(binary: str) -> str:
    completed = subprocess.run([binary, "--version"], capture_output=True, text=True, check=True, timeout=10)
    value = completed.stdout.splitlines()[0].strip(); require(bool(value), "solver_version"); return value


def build_plan(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve(); cases = selected_cases(root)
    frozen_files = {path: _sha(root / path) for path in CODE_PATHS}
    bundle = build_private_bundle(root); bundle_rows = {row["id"]: row for row in bundle["records"]}
    for case in cases:
        source = bundle_rows[case["id"]]; path = f"{SOURCE_RELATIVE}/{source['source_file']}"
        require(_sha(root / path) == source["source_file_sha256"], "source_binding")
        frozen_files[path] = source["source_file_sha256"]
    maximum_reservation = 262_144 + 8_192 + 3_072
    max_requests = len(cases) * 10 * 3
    limits = {
        "max_requests": max_requests,
        "max_total_reserved_or_reported_tokens": max_requests * maximum_reservation,
        "max_completion_tokens": 3_072, "max_input_bytes": 262_144,
        "max_output_bytes": 32_768, "token_overhead_reserve": 8_192,
        "request_seconds": 150, "max_run_seconds": 8 * 3600,
        "minimum_free_disk_bytes": 5_000_000_000,
    }
    token_cap = 10 * maximum_reservation + 1
    binary = str(Path(DEFAULT_BINARY).resolve())
    return {
        "schema": VERSION + "-plan", "status": "frozen_ready_for_authorized_antchat_feasibility_gate",
        "authorization": "standing_user_approval_no_reconfirmation_20261016",
        "authorization_schema": VERSION + "-authorization", "authorization_path": AUTH_PATH,
        "kind": "fresh_common_external", "endpoint": BASE_URL, "model": MODEL,
        "runtime_version": RUNTIME_VERSION, "gateway_version": GATEWAY_VERSION,
        "external_method": {
            "name": "OptiTrustStyleIndexed", "paper_label": "OptiTrust-style-indexed-sidecar",
            "scope_stage": "optitrustindexedfeasibility", "max_calls": 10,
            "stage_slots": _stage_slots(),
        },
        "replicates": [0],
        "public_inputs": {row["id"]: row["public_input_sha256"] for row in cases},
        "selection": [{key: row[key] for key in (
            "id", "family", "public_input_sha256", "public_bytes",
        )} for row in cases],
        "selection_rule": "per_family_argmax_public_bytes_tie_id",
        "resource_limits": dict(RESOURCE_LIMITS), "token_cap": token_cap,
        "trajectory_token_caps": [token_cap], "limits": limits,
        "resilience": {
            "max_attempts_per_request": 3, "backoff_seconds": [2, 5],
            "circuit_breaker_consecutive_failures": 8,
            "retryable_local_errors": ["invalid_json_response"],
            "max_concurrent_requests": 2,
        },
        "matrix": {"feasibility_cells": 2, "logical_requests": 20, "candidate_solves_at_most": 10},
        "progress_stage": "optitrustindexedfeasibility", "run_directory": RUN_DIRECTORY,
        "output": {"public_result": RESULT_PATH, "public_audit": AUDIT_PATH},
        "solver": {
            "backend": SOLVER_VERSION, "binary": binary, "binary_sha256": _sha(binary),
            "version_line": _binary_version(binary), "threads": 1,
            "solve_seconds": 20, "wall_seconds": 30,
        },
        "transport": {
            "kind": "openai_httpx_single_attempt_v1", "python": str(PREPARATION_PYTHON),
            "python_sha256": _sha(PREPARATION_PYTHON),
            "worker": "scripts/openai_httpx_transport_worker.py",
        },
        "runtime": {
            "controller_python": platform.python_version(), "controller_machine": platform.machine(),
            "controller_packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "psutil", "certifi")},
            "transport_runtime": _preparation_runtime(),
        },
        "frozen_files": dict(sorted(frozen_files.items())),
        "feasibility_gate": {
            "terminal_cells": 2, "infrastructure_unavailable": 0, "logical_slots": 20,
            "views_per_cell": 5, "minimum_optimal_views_per_cell": 3,
            "selected_consensus_cells": 2, "review_abstentions": 0,
            "max_attempt_ordinal": 3, "restart_new_items": 0,
        },
        "information_regime": {
            "public_problem_and_structured_facts": True, "answer_blind_inference": True,
            "reference_loaded": False, "generated_code_executed": False,
            "strict_compilation_before_solver": True,
        },
        "claim_boundary": {
            "feasibility_gate_only": True, "benchmark_accuracy_estimated": False,
            "official_optitrust_reproduction": False, "native_five_language_execution": False,
            "common38_dispatch_authorized_by_this_gate_only_if_passed": True,
            "v1_failed_on_generic_ir_surface_mismatch": True,
        },
    }


def authorization(root: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    return {"schema": plan["authorization_schema"], "status": "approved", "plan_sha256": digest(plan),
            "endpoint": BASE_URL, "model": MODEL, "run_directory": str(root / plan["run_directory"]),
            "limits": plan["limits"], "user_confirmation": "Standing autonomous approval reaffirmed 2026-10-16."}


def _cell_path(directory, problem_id):
    return Path(directory) / "cells" / (hashlib.sha256(problem_id.encode()).hexdigest() + ".json")


def _load_cell(path, problem_id, plan_sha):
    value = json.loads(Path(path).read_text())
    require(value.get("schema") == VERSION + "-private-cell" and value.get("plan_sha256") == plan_sha
            and value.get("id") == problem_id and value.get("status") in TERMINAL, "checkpoint_binding")
    return value


def _scope(problem_id):
    return f"optitrustindexedfeasibility:OptiTrustStyleIndexed:0:{problem_id}"


def run_plan(root, plan, directory, gateway, *, runner=run_optitrust_style_indexed,
             solver=gurobi_execute, workers=2):
    root = Path(root).resolve(); directory = Path(directory)
    require(canonical(plan) == canonical(build_plan(root)), "plan_reconstruction")
    require(workers == plan["resilience"]["max_concurrent_requests"] == 2, "worker_binding")
    cases = {row["id"]: row for row in selected_cases(root)}; plan_sha = digest(plan)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    def one(problem_id):
        path = _cell_path(directory, problem_id)
        if path.exists(): return _load_cell(path, problem_id, plan_sha), False
        public = cases[problem_id]["public"]; require(payload_sha256(public) == plan["public_inputs"][problem_id], "public_changed")
        scope = _scope(problem_id); gateway.work_started(scope)
        try:
            record = runner(
                public, gateway, scope, 0, plan["token_cap"], solver=solver,
                solver_config=plan["solver"], resource_limits=plan["resource_limits"],
                reference_loader=lambda: {"optimum": None, "solver_status": None},
            )
            status = "method_failure" if record.get("status") == "method_failure" else "completed"
            error = str(record.get("reason") or "method_failure")[:160] if status == "method_failure" else None
            gateway.work_finished(scope, "complete", error)
        except RequestUnavailable as exc:
            record, status, error = None, "infrastructure_unavailable", str(exc).split(":", 1)[-1][:160]
            gateway.work_finished(scope, "unavailable", error)
        except RunInterrupted: raise
        except Stopped as exc:
            halt = gateway.halt_reason() if hasattr(gateway, "halt_reason") else None
            if halt: raise RunInterrupted("global_halt:" + halt) from exc
            record, status, error = None, "method_failure", str(exc).split(":", 1)[-1][:160]
            gateway.work_finished(scope, "complete", error)
        except Exception as exc:
            record, status, error = None, "method_failure", type(exc).__name__
            gateway.work_finished(scope, "complete", error)
        cell = {"schema": VERSION + "-private-cell", "plan_sha256": plan_sha, "id": problem_id,
                "family": cases[problem_id]["family"], "status": status, "error": error, "record": record}
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700); publish_new(path, cell); return cell, True
    cells, new_items = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, problem_id) for problem_id in sorted(cases)]
        for future in as_completed(futures):
            cell, created = future.result(); cells.append(cell); new_items += int(created)
    return {"terminal": len(cells), "new_items": new_items,
            "status_counts": dict(sorted(Counter(x["status"] for x in cells).items())), "gateway": gateway.summary()}


def _ledger(directory):
    con = sqlite3.connect(f"file:{Path(directory) / 'requests.sqlite3'}?mode=ro", uri=True); con.row_factory = sqlite3.Row
    try:
        totals = con.execute("select * from totals where id=1").fetchone()
        per = con.execute("select scope,count(*) n,min(slot) lo,max(slot) hi from slots group by scope").fetchall()
        retry = con.execute("select coalesce(max(ordinal),1) from retry_attempts").fetchone()[0]
        halt = con.execute("select reason from halt where id=1").fetchone()
        attempts = dict(con.execute("select status,count(*) from attempts group by status"))
        config = json.loads(con.execute("select config from metadata where id=1").fetchone()[0])
    finally: con.close()
    return {"physical_attempts": totals["physical_calls"], "logical_slots": sum(row["n"] for row in per),
            "all_scope_slots_contiguous": len(per) == 2 and all(row["n"] == 10 and row["lo"] == 0 and row["hi"] == 9 for row in per),
            "max_attempt_ordinal": retry, "attempt_status_counts": dict(sorted(attempts.items())),
            "halt": halt[0] if halt else None, "offline": config["offline"]}


def _cells(plan, directory):
    return [_load_cell(_cell_path(directory, pid), pid, digest(plan)) for pid in sorted(plan["public_inputs"])]


def score_run(plan, directory, *, restart_new_items):
    cells = _cells(plan, Path(directory)); ledger = _ledger(directory); statuses = Counter(x["status"] for x in cells)
    rows = []; min_optimal = 5; selected = 0; abstentions = 0
    for cell in cells:
        record = cell.get("record") or {}; views = record.get("views") if isinstance(record.get("views"), list) else []
        optimal = sum(isinstance(view, dict) and view.get("status") == "optimal" for view in views)
        abstain = sum(isinstance(view, dict) and view.get("status") == "abstained" for view in views)
        consensus_selected = (record.get("consensus") or {}).get("status") == "selected"
        min_optimal = min(min_optimal, optimal); selected += int(consensus_selected); abstentions += abstain
        rows.append({"id": cell["id"], "family": cell["family"], "status": cell["status"],
                     "views": len(views), "optimal_views": optimal, "review_abstentions": abstain,
                     "consensus_selected": consensus_selected, "canonical_admitted": record.get("canonical_admitted")})
    observed = {"terminal_cells": len(cells), "infrastructure_unavailable": statuses["infrastructure_unavailable"],
                "logical_slots": ledger["logical_slots"], "views_per_cell": min((row["views"] for row in rows), default=0),
                "minimum_optimal_views_per_cell": min_optimal if rows else 0,
                "selected_consensus_cells": selected, "review_abstentions": abstentions,
                "max_attempt_ordinal": ledger["max_attempt_ordinal"], "restart_new_items": restart_new_items}
    required = plan["feasibility_gate"]
    checks = {"terminal": observed["terminal_cells"] == 2, "no_infrastructure_unavailable": observed["infrastructure_unavailable"] == 0,
              "logical_slots": observed["logical_slots"] == 20 and ledger["all_scope_slots_contiguous"],
              "views": observed["views_per_cell"] == 5, "optimal_views": observed["minimum_optimal_views_per_cell"] >= 3,
              "selected_consensus": observed["selected_consensus_cells"] == 2,
              "no_review_abstention": observed["review_abstentions"] == 0,
              "attempt_cap": observed["max_attempt_ordinal"] <= 3, "restart": restart_new_items == 0,
              "no_global_halt": ledger["halt"] is None}
    return {"schema": VERSION + "-public-result", "status": "complete", "method": "OptiTrust-style-indexed-sidecar-feasibility",
            "plan_sha256": digest(plan), "feasibility_gate": {**observed, "passed": all(checks.values()), "checks": checks},
            "rows": rows, "ledger": ledger, "claim_boundary": plan["claim_boundary"]}


def build_audit_from(root, plan, plan_path, directory, result_path, *, expected_offline):
    root = Path(root).resolve(); result = json.loads(Path(result_path).read_text()); loaded = json.loads(Path(plan_path).read_text())
    ledger = _ledger(directory); cells = _cells(plan, directory)
    checks = {"plan_reconstruction": canonical(plan) == canonical(build_plan(root)) == canonical(loaded),
              "frozen_files": all(_sha(root / path) == sha for path, sha in plan["frozen_files"].items()),
              "two_terminal_cells": len(cells) == 2 and all(x["status"] in TERMINAL for x in cells),
              "result_binding": result.get("plan_sha256") == digest(plan),
              "feasibility_gate_passed": result.get("feasibility_gate", {}).get("passed") is True,
              "offline_mode": ledger["offline"] is expected_offline,
              "reference_absent": plan["information_regime"]["reference_loaded"] is False}
    return {"schema": VERSION + "-audit", "status": "passed" if all(checks.values()) else "failed",
            "plan_sha256": digest(plan), "result_sha256": _sha(result_path), "checks": checks, "ledger": ledger,
            "execution": {"new_provider_calls": 0, "new_solver_calls": 0}}
