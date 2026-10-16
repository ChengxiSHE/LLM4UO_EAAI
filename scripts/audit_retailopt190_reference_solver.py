#!/usr/bin/env python3
"""Resume-safe offline validation of the fixed RetailOpt-190 solver endpoint."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def worker(source_root: Path, source_id: str) -> int:
    import gurobipy as gp

    gp.setParam("Threads", 1)
    gp.setParam("Seed", 0)
    module_path = source_root / "solvers/universal_retail_solver.py"
    spec = importlib.util.spec_from_file_location("retailopt_fixed_solver", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("solver_import")
    module = importlib.util.module_from_spec(spec)
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        spec.loader.exec_module(module)
        model = module.solve_scenario(module.load_data(source_root / "scenarios/data" / f"{source_id}.json"), summarize=False)
    if model.Status == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif model.Status == gp.GRB.TIME_LIMIT and model.SolCount > 0:
        status = "OPTIMAL (TL)"
    elif model.Status == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    else:
        status = f"CODE_{model.Status}"
    value = float(model.ObjVal) if model.SolCount > 0 else None
    print(json.dumps({"status": status, "objective": value, "solver_status_code": int(model.Status)}, sort_keys=True))
    return 0


def run_one(python: str, script: Path, source_root: Path, source_id: str, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [python, str(script), "--worker", "--source-root", str(source_root), "--source-id", source_id],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"terminal": "timeout", "elapsed_seconds": time.monotonic() - started}
    if completed.returncode != 0:
        return {"terminal": "worker_error", "elapsed_seconds": time.monotonic() - started}
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{") and line.endswith("}")]
    if not lines:
        return {"terminal": "worker_protocol", "elapsed_seconds": time.monotonic() - started}
    try:
        payload = json.loads(lines[-1])
    except ValueError:
        return {"terminal": "worker_protocol", "elapsed_seconds": time.monotonic() - started}
    return {"terminal": "complete", "elapsed_seconds": time.monotonic() - started, **payload}


def controller(plan_path: Path, source_root: Path, custody_root: Path) -> int:
    plan = json.loads(plan_path.read_text())
    for relative, expected in plan["frozen_files"].items():
        if sha(ROOT / relative) != expected:
            raise RuntimeError("frozen_file_drift")
    if sha(source_root / "retailopt_190.jsonl") != plan["source"]["dataset_sha256"]:
        raise RuntimeError("dataset_drift")
    if sha(source_root / "solvers/universal_retail_solver.py") != plan["source"]["reference_solver_sha256"]:
        raise RuntimeError("solver_drift")
    ledger_path = custody_root / "private/ledger.json"
    ledger_raw = ledger_path.read_bytes()
    if hashlib.sha256(ledger_raw).hexdigest() != plan["custody"]["private_ledger_sha256"]:
        raise RuntimeError("ledger_drift")
    ledger = json.loads(ledger_raw)
    by_opaque = {row["opaque_id"]: row for row in ledger["records"]}
    checkpoint_path = ROOT / plan["output"]["private_checkpoint"]
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"schema": "llm4or-retailopt190-reference-solver-checkpoint-v1", "records": {}}
    records = checkpoint["records"]
    pending = []
    for descriptor in plan["selection"]:
        opaque = descriptor["opaque_id"]
        row = by_opaque.get(opaque)
        if row is None:
            raise RuntimeError("ledger_membership")
        data_path = source_root / "scenarios/data" / f"{row['source_id']}.json"
        if sha(data_path) != descriptor["data_sha256"]:
            raise RuntimeError("data_drift")
        if opaque not in records:
            pending.append((opaque, row["source_id"]))
    python = plan["environment"]["python"]
    timeout = float(plan["endpoint"]["worker_wall_seconds"])
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=int(plan["endpoint"]["max_workers"])) as pool:
        futures = {pool.submit(run_one, python, Path(__file__), source_root, source_id, timeout): opaque for opaque, source_id in pending}
        for future in as_completed(futures):
            opaque = futures[future]
            records[opaque] = future.result()
            atomic_write(checkpoint_path, render(checkpoint))
    complete = 0
    compatible = 0
    objective_matches = 0
    fully_matching = 0
    terminal_counts: dict[str, int] = {}
    status_pairs: dict[str, int] = {}
    relative_errors: list[float] = []
    for descriptor in plan["selection"]:
        opaque = descriptor["opaque_id"]
        result = records.get(opaque, {"terminal": "missing"})
        terminal = result["terminal"]
        terminal_counts[terminal] = terminal_counts.get(terminal, 0) + 1
        if terminal != "complete":
            continue
        complete += 1
        expected = by_opaque[opaque]
        observed_status = result["status"]
        expected_status = expected["reference_status"]
        status_pairs[f"{expected_status}->{observed_status}"] = status_pairs.get(f"{expected_status}->{observed_status}", 0) + 1
        status_ok = observed_status == expected_status or (expected_status == "OPTIMAL (TL)" and observed_status == "OPTIMAL")
        compatible += int(status_ok)
        observed = result.get("objective")
        expected_objective = float(expected["reference_objective"])
        if observed is None or not math.isfinite(observed):
            continue
        error = abs(observed - expected_objective) / max(abs(expected_objective), 1.0)
        relative_errors.append(error)
        archetype = expected["archetype"]
        tolerance = plan["endpoint"]["objective_tolerance"]["relaxed_relative"] if archetype in plan["endpoint"]["objective_tolerance"]["relaxed_archetypes"] else plan["endpoint"]["objective_tolerance"]["default_relative"]
        objective_ok = abs(observed - expected_objective) <= plan["endpoint"]["objective_tolerance"]["default_absolute"] + tolerance * abs(expected_objective)
        objective_matches += int(objective_ok)
        fully_matching += int(status_ok and objective_ok)
    audit = {
        "schema": "llm4or-retailopt190-reference-solver-audit-v1",
        "status": "passed" if fully_matching == len(plan["selection"]) else "failed_or_incomplete",
        "plan_sha256": sha(plan_path),
        "source_commit": plan["source"]["commit"],
        "environment": {"python_sha256": plan["environment"]["python_sha256"], "gurobi_version": plan["endpoint"]["gurobi_version"], "threads": 1, "seed": 0, "max_workers": plan["endpoint"]["max_workers"]},
        "counts": {"planned": len(plan["selection"]), "complete": complete, "status_compatible": compatible, "objective_within_official_tolerance": objective_matches, "fully_matching": fully_matching},
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "status_transition_counts": dict(sorted(status_pairs.items())),
        "relative_objective_error": {"max": max(relative_errors) if relative_errors else None, "mean": sum(relative_errors) / len(relative_errors) if relative_errors else None},
        "checkpoint": {"sha256": sha(checkpoint_path), "resumed_records": len(plan["selection"]) - len(pending), "new_records": len(pending)},
        "wall_seconds_this_invocation": time.monotonic() - started,
        "privacy": {"contains_problem_bodies": False, "contains_source_ids": False, "contains_per_item_objectives": False, "contains_reference_objectives": False},
        "execution": {"api_calls": 0, "model_calls": 0, "solver_calls": len(pending), "credentials_read": False},
        "claim_boundary": "This is an upstream endpoint and local environment reproducibility audit. It does not evaluate any language-model method or establish formulation accuracy.",
    }
    output = ROOT / plan["output"]["public_audit"]
    atomic_write(output, render(audit))
    print(json.dumps({"status": audit["status"], "planned": len(plan["selection"]), "complete": complete, "fully_matching": fully_matching, "new_solver_calls": len(pending)}, sort_keys=True))
    return 0 if audit["status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-id")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--custody-root", type=Path)
    arguments = parser.parse_args()
    if arguments.worker:
        if not arguments.source_id:
            parser.error("--source-id is required in worker mode")
        return worker(arguments.source_root, arguments.source_id)
    if arguments.plan is None or arguments.custody_root is None:
        parser.error("--plan and --custody-root are required in controller mode")
    return controller(arguments.plan, arguments.source_root, arguments.custody_root)


if __name__ == "__main__":
    raise SystemExit(main())
