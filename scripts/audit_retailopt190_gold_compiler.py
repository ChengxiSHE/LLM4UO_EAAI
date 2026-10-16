#!/usr/bin/env python3
"""Resume-safe validation of the shared RetailOpt short-decision compiler."""

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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.retailopt190_compiler import compile_model, solve_model
from llm4or.retailopt190_endpoint import reloop_code_correct, relative_objective_error
from llm4or.retailopt190_knowledge import gold_decision, library_sha256, questions, route


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        try: os.unlink(temporary)
        except FileNotFoundError: pass


def worker(source_root: Path, source_id: str) -> int:
    data = json.loads((source_root / "scenarios/data" / f"{source_id}.json").read_text())
    selected = route(data)
    decision = {"schema": "llm4or-retailopt190-short-decision-v1", "answers": gold_decision(selected)}
    result = solve_model(compile_model(data, decision, selected))
    result.update({"route_cards": len(selected), "questions": len(questions(selected))})
    print(json.dumps(result, sort_keys=True))
    return 0


def run_one(python: str, source_root: Path, source_id: str, timeout: float) -> dict:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [python, str(Path(__file__)), "--worker", "--source-root", str(source_root), "--source-id", source_id],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"terminal": "timeout", "elapsed_seconds": time.monotonic() - started}
    if completed.returncode:
        return {"terminal": "worker_error", "elapsed_seconds": time.monotonic() - started}
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{") and line.endswith("}")]
    if not lines:
        return {"terminal": "worker_protocol", "elapsed_seconds": time.monotonic() - started}
    try: value = json.loads(lines[-1])
    except ValueError: return {"terminal": "worker_protocol", "elapsed_seconds": time.monotonic() - started}
    return {"terminal": "complete", "elapsed_seconds": time.monotonic() - started, **value}


def controller(source_root: Path, ledger_path: Path, python: str, checkpoint_path: Path, output: Path, workers: int) -> int:
    ledger_raw = ledger_path.read_bytes(); ledger = json.loads(ledger_raw)
    records = ledger["records"]
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"schema": "llm4or-retailopt190-gold-compiler-checkpoint-v1", "records": {}}
    saved = checkpoint["records"]
    pending = [(row["opaque_id"], row["source_id"]) for row in records if row["opaque_id"] not in saved]
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_one, python, source_root, source_id, 90.0): opaque for opaque, source_id in pending}
        for future in as_completed(futures):
            saved[futures[future]] = future.result()
            atomic_write(checkpoint_path, render(checkpoint))
    terminal = Counter(); status = Counter(); routes = Counter(); qs = Counter(); correct = 0; errors = []
    maxima = {"variables": 0, "constraints": 0, "nonzeros": 0}
    by_opaque = {row["opaque_id"]: row for row in records}
    archetype = {}
    for opaque, expected in by_opaque.items():
        result = saved.get(opaque, {"terminal": "missing"}); terminal[result["terminal"]] += 1
        if result["terminal"] != "complete":
            archetype.setdefault(expected["archetype"], []).append(False); continue
        status[result["status"]] += 1; routes[result["route_cards"]] += 1; qs[result["questions"]] += 1
        for key in maxima: maxima[key] = max(maxima[key], int(result[key]))
        ok = reloop_code_correct(expected, result); correct += int(ok); archetype.setdefault(expected["archetype"], []).append(ok)
        errors.append(relative_objective_error(result["objective"], expected["reference_objective"]))
    fully_correct_archetypes = sum(len(values) == 5 and all(values) for values in archetype.values())
    audit = {
        "schema": "llm4or-retailopt190-gold-compiler-audit-v1",
        "status": "passed" if correct == 190 and fully_correct_archetypes == 38 else "failed_or_incomplete",
        "source": {"commit": ledger["source"]["commit"], "private_ledger_sha256": hashlib.sha256(ledger_raw).hexdigest()},
        "implementation": {
            "compiler_sha256": sha(ROOT / "llm4or/retailopt190_compiler.py"),
            "knowledge_sha256": sha(ROOT / "llm4or/retailopt190_knowledge.py"),
            "library_content_sha256": library_sha256(),
            "runner_sha256": sha(Path(__file__)),
        },
        "counts": {"records": len(records), "correct": correct, "archetypes": len(archetype), "fully_correct_archetypes": fully_correct_archetypes},
        "terminal_counts": dict(sorted(terminal.items())),
        "solver_status_counts": dict(sorted(status.items())),
        "route_card_count_distribution": {str(key): value for key, value in sorted(routes.items())},
        "question_count_distribution": {str(key): value for key, value in sorted(qs.items())},
        "maximum_model_size": maxima,
        "relative_objective_error": {"max": max(errors) if errors else None, "mean": sum(errors) / len(errors) if errors else None},
        "checkpoint": {"sha256": sha(checkpoint_path), "resumed_records": len(records) - len(pending), "new_records": len(pending)},
        "wall_seconds_this_invocation": time.monotonic() - started,
        "endpoint": "relative objective error < 0.01; execution and solver status separately reported",
        "privacy": {"contains_problem_bodies": False, "contains_source_ids": False, "contains_per_item_results": False, "contains_objectives": False},
        "execution": {"api_calls": 0, "model_calls": 0, "solver_calls": len(pending), "credentials_read": False},
        "claim_boundary": "This validates the shared compiler under the admitted decision. It does not evaluate either language-model arm and cannot establish an accuracy improvement.",
    }
    atomic_write(output, render(audit))
    print(json.dumps({"status": audit["status"], "correct": correct, "fully_correct_archetypes": fully_correct_archetypes, "new_solver_calls": len(pending)}, sort_keys=True))
    return 0 if audit["status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-id")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--python")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=5)
    arguments = parser.parse_args()
    if arguments.worker:
        if not arguments.source_id: parser.error("--source-id required")
        return worker(arguments.source_root, arguments.source_id)
    if None in (arguments.ledger, arguments.python, arguments.checkpoint, arguments.output): parser.error("controller arguments missing")
    return controller(arguments.source_root, arguments.ledger, arguments.python, arguments.checkpoint, arguments.output, arguments.workers)


if __name__ == "__main__":
    raise SystemExit(main())
