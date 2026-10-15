#!/usr/bin/env python3
"""Offline safe replay of the completed CoE native development responses."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.external_code_adapter import evaluate_coe_program
from llm4or.gurobi_cli_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest


PLAN_PATH = ROOT / "experiments/coe_native_development_pilot_plan.json"
PREPARED_PATH = ROOT / "data/prepared_benchmarks/coe_native_development_pilot_v1.json"
OUTPUT = ROOT / "results/coe_native_development_pilot_safe_replay.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads(PLAN_PATH.read_text())
    prepared = json.loads(PREPARED_PATH.read_text())
    index = {row["problem_id"]: row for row in prepared["records"]}
    directory = ROOT / plan["run_directory"]
    complete = json.loads((directory / "inference_complete.json").read_text())
    database = sqlite3.connect("file:" + str(directory / "requests.sqlite3") + "?mode=ro", uri=True)
    database.row_factory = sqlite3.Row
    rows = []
    by_snapshot = defaultdict(lambda: {"records": 0, "author_exact": 0, "tolerance": 0,
                                       "adapter_supported": 0})
    try:
        for cell in complete["cells"]:
            problem_id = cell["problem_id"]
            source = index[problem_id]
            scope = f"coedev:CoE:{plan['replicates'][0]}:{problem_id}"
            slot = database.execute("SELECT key FROM slots WHERE scope=? AND slot=10", (scope,)).fetchone()
            request = database.execute("SELECT response FROM requests WHERE key=? AND status='complete'",
                                       (slot["key"],)).fetchone()
            response = json.loads(request["response"])
            final_answer = json.loads(response["text"])["text"]
            samples = json.loads((ROOT / source["sample_file"]).read_text())
            sample_rows = []
            for sample_index, sample in enumerate(samples):
                result = evaluate_coe_program(
                    final_answer, function_name=source["native_problem_id"],
                    arguments=sample["input"], solver=execute,
                )
                returned = result.get("returned_value")
                expected = sample["output"][0] if len(sample["output"]) == 1 else tuple(sample["output"])
                exact = result["status"] == "evaluated" and returned == expected
                tolerant = type(returned) in (int, float) and type(expected) in (int, float) \
                    and math.isclose(float(returned), float(expected), rel_tol=1e-7, abs_tol=1e-7)
                sample_rows.append({
                    "sample_index": sample_index,
                    "status": result["status"],
                    "reason": result.get("reason"),
                    "code_sha256": result.get("code_sha256"),
                    "model_sha256": result.get("model_sha256"),
                    "solver_status": result.get("solver_status"),
                    "returned_value_type": type(returned).__name__ if result["status"] == "evaluated" else None,
                    "returned_value_sha256": digest(returned) if result["status"] == "evaluated" else None,
                    "author_exact_match": exact,
                    "tolerance_match": tolerant,
                })
            author_accept = all(row["author_exact_match"] for row in sample_rows)
            tolerance_accept = all(row["tolerance_match"] for row in sample_rows)
            adapter_supported = all(row["status"] == "evaluated" for row in sample_rows)
            aggregate = by_snapshot[source["snapshot"]]
            aggregate["records"] += 1
            aggregate["author_exact"] += int(author_accept)
            aggregate["tolerance"] += int(tolerance_accept)
            aggregate["adapter_supported"] += int(adapter_supported)
            rows.append({
                "problem_id": problem_id,
                "native_problem_id": source["native_problem_id"],
                "snapshot": source["snapshot"],
                "final_output_sha256": hashlib.sha256(final_answer.encode()).hexdigest(),
                "author_accept": author_accept,
                "tolerance_accept": tolerance_accept,
                "adapter_supported": adapter_supported,
                "samples": sample_rows,
            })
    finally:
        database.close()
    for value in by_snapshot.values():
        value["author_exact_accuracy"] = value["author_exact"] / value["records"]
        value["tolerance_accuracy"] = value["tolerance"] / value["records"]
    report = {
        "schema": "coe-native-development-pilot-safe-replay-v1",
        "role": "development_only_offline_replay_no_new_api_requests",
        "source_plan_sha256": digest(plan),
        "source_usage": complete["usage"],
        "api_requests_in_replay": 0,
        "generated_python_executed": False,
        "safe_execution": "bounded AST interpreter plus validated milp-v1 and fixed Gurobi CLI",
        "adapter_files_sha256": {
            "llm4or/restricted_gurobi.py": sha(ROOT / "llm4or/restricted_gurobi.py"),
            "llm4or/external_code_adapter.py": sha(ROOT / "llm4or/external_code_adapter.py"),
        },
        "by_snapshot": dict(sorted(by_snapshot.items())),
        "records": rows,
        "interpretation": (
            "Five programs reproduce the released scalar endpoint. The paper-snapshot netasgn program "
            "solves the correct objective but returns a dictionary, so it fails the authors' exact evaluator contract."
        ),
        "claim_guard": "three outcome-exposed records per snapshot; adapter validation, not a superiority claim",
    }
    write_json(OUTPUT, report)
    print(json.dumps({"by_snapshot": report["by_snapshot"], "output": str(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
