#!/usr/bin/env python3
"""Audit the safe CoE function adapter against released ComplexOR fixtures."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.gurobi_cli_solver import execute
from llm4or.pipeline import write_json
from llm4or.restricted_gurobi import RestrictedCodeError, compile_gurobi_function_source
from llm4or.schema import digest


UPSTREAM = ROOT / "data/raw/xzymustbexzy__Chain-of-Experts_20261003"
DATASET = UPSTREAM / "dataset/ComplexOR"
OUTPUT = ROOT / "results/coe_native_safe_adapter_audit.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    records = []
    for directory in sorted(path for path in DATASET.iterdir() if path.is_dir()):
        program = directory / f"{directory.name}.py"
        sample_path = directory / "sample.json"
        sample = json.loads(sample_path.read_text())[0]
        record = {
            "problem_id": directory.name,
            "program_sha256": sha(program),
            "sample_sha256": sha(sample_path),
            "translation": None,
            "solver_status": None,
            "objective_matches_released_sample": False,
            "reason": None,
        }
        try:
            model = compile_gurobi_function_source(
                program.read_text(), directory.name, sample["input"],
            )
            record["translation"] = "compiled"
            record["model_sha256"] = digest(model)
            record["variables"] = len(model["variables"])
            record["constraints"] = len(model["constraints"])
            solved = execute({"op": "solve", "model": model})
            record["solver_status"] = solved.get("status")
            record["objective"] = solved.get("objective")
            expected = sample["output"][0] if len(sample["output"]) == 1 else None
            record["objective_matches_released_sample"] = bool(
                expected is not None and solved.get("objective") is not None
                and math.isclose(float(solved["objective"]), float(expected), rel_tol=1e-7, abs_tol=1e-7)
            )
        except RestrictedCodeError as exc:
            record["translation"] = "rejected"
            record["reason"] = str(exc)
        except (ArithmeticError, IndexError, KeyError, TypeError, ValueError) as exc:
            record["translation"] = "fixture_runtime_error"
            record["reason"] = type(exc).__name__
        records.append(record)

    compiled = sum(row["translation"] == "compiled" for row in records)
    matched = sum(row["objective_matches_released_sample"] for row in records)
    report = {
        "schema": "coe-native-safe-adapter-audit-v1",
        "role": "adapter_and_upstream_fixture_audit_not_method_accuracy",
        "upstream_commit": "afb89bf602690ea621f13a23c42722f20f653a43",
        "programs": len(records),
        "compiled": compiled,
        "compile_coverage": compiled / len(records),
        "released_sample_objective_matches": matched,
        "released_sample_match_rate_all": matched / len(records),
        "generated_python_executed": False,
        "execution_boundary": "restricted AST to milp-v1 then fixed Gurobi CLI",
        "interpretation": (
            "Compilation coverage measures the adapter only. Objective mismatches also expose conflicts or bugs "
            "between released implementations, sample inputs, and sample outputs and must not be counted as CoE failures."
        ),
        "records": records,
    }
    write_json(OUTPUT, report)
    print(json.dumps({"programs": len(records), "compiled": compiled, "matched": matched,
                      "output": str(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
