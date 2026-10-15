#!/usr/bin/env python3
"""Independently rebuild, resolve and score frozen OR-Debug confirmation outputs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from llm4or.or_debug_comparison import compare_development_records
from llm4or.or_debug_confirmation_inference import summarize_group_confirmation
from llm4or.or_debug_hidden_score import score_hidden_record
from llm4or.or_debug_split import assign_shape_group, shape_group


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/or_debug_confirmation_plan_20261014.json"
EVAL_PLAN = ROOT / "experiments/or_debug_confirmation_evaluation_plan_20261014.json"
METHOD_OUTPUT = ROOT / "results/or_debug_confirmation_method_outputs_20261014.json"
OUTPUT = ROOT / "results/or_debug_confirmation_evaluation_20261014.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite confirmation evaluation")
    plan = json.loads(PLAN.read_text())
    evaluation_plan = json.loads(EVAL_PLAN.read_text())
    method = json.loads(METHOD_OUTPUT.read_text())
    if evaluation_plan["confirmation_plan_sha256"] != sha(PLAN) or evaluation_plan[
        "method_output_sha256"
    ] != sha(METHOD_OUTPUT):
        raise SystemExit("confirmation evaluation input pin mismatch")
    for relative, expected in evaluation_plan["evaluator_code_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise SystemExit(f"confirmation evaluator code pin mismatch: {relative}")

    dataset_path = ROOT / plan["source"]["dataset_path"]
    split_path = ROOT / plan["source"]["split_manifest_path"]
    dataset = json.loads(dataset_path.read_text())["problems"]
    split = json.loads(split_path.read_text())
    source = {row["problem_id"]: row for row in dataset}
    outputs = method["records"]
    if len(outputs) != plan["denominator"]["records"]:
        raise SystemExit("confirmation evaluation denominator mismatch")
    for item in outputs:
        row = source[item["problem_id"]]
        if assign_shape_group(
            shape_group(row), split["source"]["commit"], split["split_salt"]
        ) != "confirmation":
            raise SystemExit("non-confirmation identity in method output")

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="or-debug-confirmation-evaluator-") as directory:
        work = Path(directory)

        def score(index_item: tuple[int, dict[str, Any]]) -> dict[str, Any]:
            index, item = index_item
            row = source[item["problem_id"]]
            result = {"problem_id": row["problem_id"], "shape_group": shape_group(row)}
            for arm in ("static", "evolved"):
                try:
                    result[arm] = score_hidden_record(
                        row,
                        item[arm],
                        model_root=dataset_path.parent,
                        workspace=work / f"{index:04d}_{arm}",
                    )
                except Exception as exc:
                    result[arm] = {
                        "problem_id": row["problem_id"],
                        "error_type": row["error_type"],
                        "problem_type": row["problem_type"],
                        "status": "evaluator_exception",
                        "reason": type(exc).__name__,
                        "released_primary_correct": False,
                        "corrected_primary_correct": False,
                        "executable_optimal": False,
                        "objective_match": False,
                        "evaluator_solver_calls": 0,
                    }
            return result

        with ThreadPoolExecutor(max_workers=evaluation_plan["concurrency"]) as executor:
            scored = list(executor.map(score, enumerate(outputs)))

    scored.sort(key=lambda row: row["problem_id"])
    comparison = compare_development_records(
        [row["static"] for row in scored], [row["evolved"] for row in scored]
    )
    inference = summarize_group_confirmation(
        [
            {
                "shape_group": row["shape_group"],
                "static_correct": row["static"].get("corrected_primary_correct") is True,
                "evolved_correct": row["evolved"].get("corrected_primary_correct") is True,
            }
            for row in scored
        ],
        alpha=plan["inference"]["report_zero_regression_group_upper_bound_alpha"],
    )
    evaluator_calls = sum(
        int(row[arm].get("evaluator_solver_calls", 0))
        for row in scored
        for arm in ("static", "evolved")
    )
    if evaluator_calls > evaluation_plan["maximum_evaluator_solver_calls"]:
        raise SystemExit("confirmation evaluator-call ceiling exceeded")

    result = {
        "schema": "or-debug-confirmation-evaluation-v1",
        "confirmation_plan_sha256": sha(PLAN),
        "evaluation_plan_sha256": sha(EVAL_PLAN),
        "method_output_sha256": sha(METHOD_OUTPUT),
        "comparison": comparison,
        "confirmation_inference": inference,
        "execution": {
            "evaluator_solver_calls": evaluator_calls,
            "model_or_api_calls": 0,
            "elapsed_seconds": time.monotonic() - started,
        },
        "records": scored,
        "custody": {
            "method_outputs_were_terminal_before_hidden_scoring": True,
            "post_promotion_method_adaptations": 0,
            "operating_system_level_isolation_established": False,
        },
        "claim_guard": (
            "One-shot same-source confirmation over held-out shape groups; not automatic skill "
            "synthesis, independent-source generalization, or unrestricted RSI."
        ),
    }
    temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(OUTPUT)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "comparison": comparison["corrected_primary"],
                "inference": {key: value for key, value in inference.items() if key != "group_effects"},
                "sha256": sha(OUTPUT),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
