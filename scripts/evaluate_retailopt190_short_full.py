#!/usr/bin/env python3
"""Resume-safe independent evaluation for the frozen RetailOpt comparison."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from llm4or.retailopt190_compiler import compile_model, solve_model
from llm4or.retailopt190_endpoint import reloop_code_correct
from llm4or.retailopt190_evaluation import ARMS, aggregate_evaluation
from llm4or.schema import canonical, digest

RESULT = "experiments/retailopt190_short_full_evaluation_v2_20261017.json"


def _render(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_render(value)); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        try: os.unlink(temporary)
        except FileNotFoundError: pass


def worker(source_root: Path, plan_path: Path, run_directory: Path, cell_id: str, source_id: str) -> int:
    plan = json.loads(plan_path.read_text()); descriptor = plan["cells"][cell_id]
    cell = json.loads((run_directory / "cells" / f"{cell_id}.json").read_text())
    if cell.get("plan_sha256") != digest(plan) or cell.get("status") != "completed": return 2
    decision = {"schema": "llm4or-retailopt190-short-decision-v1", "answers": cell["record"]["answers"]}
    data = json.loads((source_root / "scenarios/data" / f"{source_id}.json").read_text())
    result = solve_model(compile_model(data, decision, descriptor["selected_skill_ids"]))
    print(json.dumps(result, sort_keys=True)); return 0


def _run_worker(python: str, source_root: Path, plan_path: Path, run_directory: Path, cell_id: str, source_id: str) -> dict:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [python, str(Path(__file__)), "--worker", "--source-root", str(source_root), "--plan", str(plan_path),
             "--run-directory", str(run_directory), "--cell-id", cell_id, "--source-id", source_id],
            capture_output=True, text=True, check=False, timeout=90,
        )
    except subprocess.TimeoutExpired:
        return {"terminal": "solver_timeout", "solver_status": None, "objective": None, "elapsed_seconds": time.monotonic() - started}
    if completed.returncode:
        return {"terminal": "worker_error", "solver_status": None, "objective": None, "elapsed_seconds": time.monotonic() - started}
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{") and line.endswith("}")]
    try: result = json.loads(lines[-1])
    except (IndexError, ValueError):
        return {"terminal": "worker_protocol", "solver_status": None, "objective": None, "elapsed_seconds": time.monotonic() - started}
    return {"terminal": "complete", "solver_status": result["status"], "objective": result["objective"], "elapsed_seconds": time.monotonic() - started}


def controller(args) -> int:
    plan_raw = args.plan.read_bytes(); plan = json.loads(plan_raw)
    run_directory = args.run_directory
    private_ledger_path = ROOT / plan["private_request_root"] / "private/archetype_ledger.json"
    private_raw = private_ledger_path.read_bytes(); private_ledger = json.loads(private_raw)
    if hashlib.sha256(private_raw).hexdigest() != plan["private_archetype_ledger_sha256"]: raise SystemExit("archetype_ledger_drift")
    source_raw = args.source_ledger.read_bytes(); source_ledger = json.loads(source_raw)
    if hashlib.sha256(source_raw).hexdigest() != private_ledger["source_custody_ledger_sha256"]: raise SystemExit("source_ledger_drift")
    source_records = {row["source_id"]: row for row in source_ledger["records"]}
    by_descriptor = {(row["opaque_archetype_id"], arm): cell_id for cell_id, row in plan["cells"].items() for arm in [row["arm"]]}
    checkpoint = json.loads(args.checkpoint.read_text()) if args.checkpoint.exists() else {"schema": "llm4or-retailopt190-short-evaluation-checkpoint-v1", "plan_sha256": digest(plan), "records": {}}
    if checkpoint.get("plan_sha256") != digest(plan): raise SystemExit("checkpoint_plan_drift")
    saved = checkpoint["records"]; jobs = []
    inference_completed = Counter()
    for cell_id, descriptor in plan["cells"].items():
        cell = json.loads((run_directory / "cells" / f"{cell_id}.json").read_text())
        if cell.get("status") == "completed": inference_completed[descriptor["arm"]] += 1
    for group in private_ledger["archetypes"]:
        opaque = group["opaque_archetype_id"]
        for arm in ARMS:
            cell_id = by_descriptor[opaque, arm]
            cell = json.loads((run_directory / "cells" / f"{cell_id}.json").read_text())
            for source in group["source_records"]:
                key = hashlib.sha256((cell_id + "\0" + source["opaque_id"]).encode()).hexdigest()
                if key in saved: continue
                if cell.get("status") != "completed":
                    saved[key] = {"arm": arm, "opaque_archetype_id": opaque, "opaque_instance_id": source["opaque_id"], "terminal": "inference_not_completed", "solver_status": None, "correct": False}
                else:
                    jobs.append((key, arm, opaque, source["opaque_id"], cell_id, source["source_id"]))
    _atomic(args.checkpoint, checkpoint)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_worker, args.python, args.source_root, args.plan, run_directory, cell_id, source_id): (key, arm, opaque, instance, source_id) for key, arm, opaque, instance, cell_id, source_id in jobs}
        for future in as_completed(futures):
            key, arm, opaque, instance, source_id = futures[future]; result = future.result()
            expected = source_records[source_id]
            correct = result["terminal"] == "complete" and result["objective"] is not None and reloop_code_correct(expected, result)
            saved[key] = {"arm": arm, "opaque_archetype_id": opaque, "opaque_instance_id": instance, "terminal": result["terminal"], "solver_status": result["solver_status"], "correct": bool(correct)}
            _atomic(args.checkpoint, checkpoint)
    aggregate = aggregate_evaluation(saved.values(), inference_completed=inference_completed)
    result = {
        "schema": "llm4or-retailopt190-short-full-evaluation-v2",
        "status": "confirmed_improvement" if aggregate["confirmation_gate"]["passed"] else "improvement_not_confirmed",
        "plan_sha256": digest(plan),
        "source": {"commit": plan["source"]["commit"], "records": 190, "archetypes": 38},
        **aggregate,
        "execution": {"api_calls": 0, "model_calls": 0, "solver_calls_this_invocation": len(jobs), "workers": args.workers, "wall_seconds_this_invocation": time.monotonic() - started},
        "privacy": {"contains_problem_bodies": False, "contains_source_ids": False, "contains_per_item_results": False, "contains_objectives": False, "contains_responses": False},
        "claim_boundary": "A passed gate confirms a prospective accuracy improvement on RetailOpt-190 under the frozen ReLoop endpoint, model, authored benchmark-specific library, shared compiler, and one-decision-per-archetype protocol; it does not establish universal OR superiority or automatic skill acquisition.",
    }
    _atomic(args.output, result)
    print(json.dumps({"status": result["status"], "instances": result["instances"], "archetypes": result["archetypes"], "paired_archetypes": result["paired_archetypes"], "new_solver_calls": len(jobs)}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--worker", action="store_true")
    parser.add_argument("--source-root", type=Path, required=True); parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run-directory", type=Path, required=True); parser.add_argument("--cell-id"); parser.add_argument("--source-id")
    parser.add_argument("--source-ledger", type=Path); parser.add_argument("--python"); parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / RESULT); parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    if args.worker:
        if not args.cell_id or not args.source_id: parser.error("worker identifiers required")
        return worker(args.source_root, args.plan, args.run_directory, args.cell_id, args.source_id)
    if None in (args.source_ledger, args.python, args.checkpoint): parser.error("controller arguments missing")
    if args.workers != 5: parser.error("workers must equal frozen concurrency 5")
    return controller(args)


if __name__ == "__main__": raise SystemExit(main())
