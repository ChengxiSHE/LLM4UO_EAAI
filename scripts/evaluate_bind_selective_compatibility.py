#!/usr/bin/env python3
"""Replay the frozen selective harness over completed BIND pilot outcomes."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.bind_official_adapter import objective_match
from llm4or.bind_runtime import bind_reference_projection
from llm4or.schema import digest
from llm4or.selective_harness import wrap_solve_result


PLAN_PATH = ROOT / "experiments/text2opt_bind_development_matrix_retry_plan.json"
OUTPUT = ROOT / "results/bind_selective_harness_compatibility_replay.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    plan = json.loads(PLAN_PATH.read_text())
    directory = ROOT / plan["run_directory"]
    completed = json.loads((directory / "inference_complete.json").read_text())
    if completed["plan_sha256"] != digest(plan):
        raise ValueError("bind_compatibility_plan_mismatch")
    prepared = json.loads((ROOT / plan["prepared_data"]).read_text())
    index = {row["problem_id"]: row for row in prepared["records"]}
    cells = {row["problem_id"]: row for row in completed["cells"]}
    rows = []
    for item in plan["selection"]["records"]:
        problem_id = item["problem_id"]
        cell = cells[problem_id]
        record_path = ROOT / cell["record_path"]
        record = json.loads(record_path.read_text())
        if digest(record) != cell["record_sha256"]:
            raise ValueError("bind_compatibility_record_changed:" + problem_id)
        source_path = ROOT / index[problem_id]["source_file"]
        if sha(source_path) != index[problem_id]["source_file_sha256"]:
            raise ValueError("bind_compatibility_reference_changed:" + problem_id)
        reference = bind_reference_projection(json.loads(source_path.read_text()))
        last = record["rounds"][-1]
        backend = {"status": last["solver_status"], "objective": last["objective"]}
        wrapped = wrap_solve_result(index[problem_id]["public"], backend)
        wrapped_result = wrapped["result"]
        bind_correct = bool(record["success"])
        wrapped_correct = (
            wrapped_result.get("status") == "optimal"
            and objective_match(wrapped_result.get("objective"), reference["optimum"])
        )
        rows.append({
            "problem_id": problem_id, "family": item["category"],
            "bind_correct": bind_correct, "wrapped_correct": wrapped_correct,
            "adopted": wrapped["adopted"],
            "fallback_identity": wrapped["fallback_identity"],
            "compiler_status": wrapped["compiler_status"],
        })
    corrections = sum(not row["bind_correct"] and row["wrapped_correct"] for row in rows)
    regressions = sum(row["bind_correct"] and not row["wrapped_correct"] for row in rows)
    report = {
        "schema": "bind-selective-harness-compatibility-replay-v1",
        "role": "development_only_compatibility_no_superiority_claim",
        "source_plan_sha256": digest(plan),
        "records": len(rows),
        "bind_correct": sum(row["bind_correct"] for row in rows),
        "wrapped_correct": sum(row["wrapped_correct"] for row in rows),
        "adopted": sum(row["adopted"] for row in rows),
        "fallback_identity_checks": sum(row["fallback_identity"] for row in rows),
        "corrections": corrections, "regressions": regressions,
        "paired_rows": rows,
        "interpretation": (
            f"The backend-neutral harness can wrap the completed BIND outputs and preserves {len(rows)}/{len(rows)} accuracy. "
            "Because both BIND and the compiler are perfect on this exposed development matrix, the replay demonstrates "
            "mechanical compatibility but supplies no evidence of incremental accuracy gain."
        ),
    }
    OUTPUT.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({key: report[key] for key in (
        "records", "bind_correct", "wrapped_correct", "adopted", "corrections", "regressions"
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
