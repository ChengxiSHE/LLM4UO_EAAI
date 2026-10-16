#!/usr/bin/env python3
"""Run frozen static and evolved methods on the answer-free confirmation bundle."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from llm4or.or_debug_public_runner import execute_public_record
from llm4or.or_debug_static_public_runner import execute_static_public_record


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/or_debug_confirmation_plan_20261014.json"
BUNDLE = ROOT / "experiments/or_debug_confirmation_public_bundle_20261014.json"
OUTPUT = ROOT / "results/or_debug_confirmation_method_outputs_20261014.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite confirmation method output")
    plan = json.loads(PLAN.read_text())
    bundle = json.loads(BUNDLE.read_text())
    if bundle.get("plan_sha256") != sha(PLAN):
        raise SystemExit("confirmation bundle plan mismatch")
    for relative, expected in plan["method_code_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise SystemExit(f"confirmation method code pin mismatch: {relative}")
    records = bundle["records"]
    if len(records) != plan["denominator"]["records"]:
        raise SystemExit("confirmation bundle denominator mismatch")
    model_root = ROOT / "vendor/solver-in-the-loop/or_debug_bench"
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="or-debug-confirmation-method-") as directory:
        work = Path(directory)

        def run_one(index_row: tuple[int, dict[str, Any]]) -> dict[str, Any]:
            index, row = index_row
            result = {"problem_id": row["problem_id"]}
            for arm, function in (("static", execute_static_public_record), ("evolved", execute_public_record)):
                try:
                    result[arm] = function(row, model_root=model_root, workspace=work / f"{index:04d}_{arm}")
                except Exception as exc:
                    result[arm] = {"problem_id": row["problem_id"], "status": "method_exception", "reason": type(exc).__name__, "solver_calls": 0}
            return result

        with ThreadPoolExecutor(max_workers=plan["execution"]["concurrency"]) as executor:
            outputs = list(executor.map(run_one, enumerate(records)))
    outputs.sort(key=lambda row: row["problem_id"])
    calls = {arm: sum(int(row[arm].get("solver_calls", 0)) for row in outputs) for arm in ("static", "evolved")}
    if calls["static"] > plan["execution"]["maximum_static_solver_calls"] or calls["evolved"] > plan["execution"]["maximum_evolved_solver_calls"]:
        raise SystemExit("confirmation solver-call ceiling exceeded")
    result = {
        "schema": "or-debug-confirmation-method-outputs-v1",
        "plan_sha256": sha(PLAN),
        "public_bundle_sha256": sha(BUNDLE),
        "records": outputs,
        "execution": {"concurrency": plan["execution"]["concurrency"], "static_solver_calls": calls["static"], "evolved_solver_calls": calls["evolved"], "model_or_api_calls": 0, "elapsed_seconds": time.monotonic() - started},
        "custody": {"method_imported_evaluator_module": False, "method_received_hidden_answers": False, "operating_system_level_isolation_established": False}
    }
    temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "records": len(outputs), "calls": calls, "sha256": sha(OUTPUT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
