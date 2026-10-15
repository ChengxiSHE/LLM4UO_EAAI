#!/usr/bin/env python3
"""Offline safe replay of completed common-input CoE outputs.

This script makes no model requests.  It re-evaluates the already-recorded final
programs with the bounded AST interpreter and the fixed solver backend so that
adapter improvements can be separated from method failures.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.bind_runtime import bind_reference_projection
from llm4or.external_code_adapter import evaluate_coe_program
from llm4or.gurobi_cli_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest


PLAN_PATH = ROOT / "experiments/coe_common_development_pilot_plan.json"
PREPARED_PATH = ROOT / "data/prepared_benchmarks/coe_common_development_pilot_v1.json"
OUTPUT = ROOT / "results/coe_common_development_pilot_safe_replay.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text())
    prepared = json.loads(PREPARED_PATH.read_text())
    index = {row["problem_id"]: row for row in prepared["records"]}
    directory = ROOT / plan["run_directory"]
    complete = json.loads((directory / "inference_complete.json").read_text())
    database = sqlite3.connect(
        "file:" + str(directory / "requests.sqlite3") + "?mode=ro", uri=True
    )
    database.row_factory = sqlite3.Row
    by_snapshot = defaultdict(
        lambda: {
            "planned": 0,
            "evaluated": 0,
            "author_exact": 0,
            "tolerance": 0,
            "adapter_supported": 0,
            "post_hoc_objective_projection_correct": 0,
            "infrastructure_unavailable": 0,
            "method_failure": 0,
        }
    )
    reasons = Counter()
    records = []
    try:
        for cell in complete["cells"]:
            aggregate = by_snapshot[cell["snapshot"]]
            aggregate["planned"] += 1
            if cell["status"] != "complete":
                aggregate[cell["status"]] += 1
                reason = cell.get("reason", cell["status"])
                reasons[reason] += 1
                records.append({**cell, "replayed": False})
                continue

            problem_id = cell["problem_id"]
            source = index[problem_id]
            scope = f"coecdev:CoE:{plan['replicates'][0]}:{problem_id}"
            slot = database.execute(
                "SELECT key FROM slots WHERE scope=? AND slot=10", (scope,)
            ).fetchone()
            if slot is None:
                raise RuntimeError(f"missing final reducer slot: {problem_id}")
            request = database.execute(
                "SELECT response FROM requests WHERE key=? AND status='complete'",
                (slot["key"],),
            ).fetchone()
            if request is None:
                raise RuntimeError(f"missing final reducer response: {problem_id}")
            transport = json.loads(request["response"])
            final_answer = json.loads(transport["text"])["text"]
            reference = bind_reference_projection(
                json.loads((ROOT / source["source_file"]).read_text())
            )["optimum"]
            result = evaluate_coe_program(
                final_answer,
                function_name="solve_problem",
                arguments={},
                solver=execute,
            )
            returned = result.get("returned_value")
            exact = result["status"] == "evaluated" and returned == reference
            tolerant = (
                result["status"] == "evaluated"
                and type(returned) in (int, float)
                and type(reference) in (int, float)
                and math.isclose(
                    float(returned), float(reference), rel_tol=1e-7, abs_tol=1e-7
                )
            )
            projection_keys = ("objective_value", "total_cost", "makespan")
            projection_matches = []
            if isinstance(returned, dict):
                for key in projection_keys:
                    value = returned.get(key)
                    if type(value) in (int, float) and math.isclose(
                        float(value), float(reference), rel_tol=1e-7, abs_tol=1e-7
                    ):
                        projection_matches.append(key)
            projected_correct = tolerant or bool(projection_matches)
            aggregate["evaluated"] += 1
            aggregate["author_exact"] += int(exact)
            aggregate["tolerance"] += int(tolerant)
            aggregate["adapter_supported"] += int(result["status"] == "evaluated")
            aggregate["post_hoc_objective_projection_correct"] += int(projected_correct)
            if result["status"] != "evaluated":
                reasons[result.get("reason", result["status"])] += 1
            records.append(
                {
                    "problem_id": problem_id,
                    "source_problem_id": source["source_problem_id"],
                    "family": source["family"],
                    "snapshot": source["snapshot"],
                    "replayed": True,
                    "status": result["status"],
                    "reason": result.get("reason"),
                    "final_output_sha256": hashlib.sha256(
                        final_answer.encode()
                    ).hexdigest(),
                    "code_sha256": result.get("code_sha256"),
                    "model_sha256": result.get("model_sha256"),
                    "solver_status": result.get("solver_status"),
                    "returned_value_type": (
                        type(returned).__name__
                        if result["status"] == "evaluated"
                        else None
                    ),
                    "returned_value_sha256": (
                        digest(returned) if result["status"] == "evaluated" else None
                    ),
                    "author_exact_match": exact,
                    "tolerance_match": tolerant,
                    "post_hoc_objective_projection_match": projected_correct,
                    "post_hoc_projection_keys_matched": projection_matches,
                }
            )
    finally:
        database.close()

    for value in by_snapshot.values():
        value["author_exact_accuracy"] = (
            value["author_exact"] / value["evaluated"] if value["evaluated"] else None
        )
        value["tolerance_accuracy"] = (
            value["tolerance"] / value["evaluated"] if value["evaluated"] else None
        )

    report = {
        "schema": "coe-common-development-pilot-safe-replay-v1",
        "role": "development_only_offline_replay_no_new_api_requests",
        "source_plan_sha256": digest(plan),
        "source_usage": complete["usage"],
        "api_requests_in_replay": 0,
        "generated_python_executed": False,
        "safe_execution": (
            "bounded AST interpreter plus validated milp-v1 and fixed Gurobi CLI"
        ),
        "adapter_files_sha256": {
            "llm4or/restricted_gurobi.py": sha(ROOT / "llm4or/restricted_gurobi.py"),
            "llm4or/external_code_adapter.py": sha(
                ROOT / "llm4or/external_code_adapter.py"
            ),
        },
        "by_snapshot": dict(sorted(by_snapshot.items())),
        "failure_reasons": dict(sorted(reasons.items())),
        "records": records,
        "comparison_context": {
            "V9_on_same_records": "6/6",
            "BIND_round1_on_same_records": "6/6",
            "BIND_final_on_same_records": "6/6",
        },
        "post_hoc_diagnostic": {
            "name": "recognized objective field projection",
            "recognized_keys": ["objective_value", "total_cost", "makespan"],
            "status": "created after observing development outputs; invalid for confirmatory scoring",
            "purpose": (
                "separate objective/formulation correctness from failure to obey the frozen "
                "single-scalar return contract"
            ),
        },
        "claim_guard": (
            "six outcome-exposed development records per snapshot; adapter validation, "
            "not a superiority claim"
        ),
    }
    write_json(OUTPUT, report)
    print(
        json.dumps(
            {"by_snapshot": report["by_snapshot"], "output": str(OUTPUT)},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
