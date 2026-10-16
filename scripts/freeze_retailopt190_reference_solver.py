#!/usr/bin/env python3
"""Freeze an answer-free RetailOpt-190 reference-solver environment check."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    audit_path = ROOT / "experiments/retailopt190_source_custody_audit_20261017.json"
    audit = json.loads(audit_path.read_text())
    ledger_path = arguments.custody_root / "private/ledger.json"
    ledger_raw = ledger_path.read_bytes()
    if hashlib.sha256(ledger_raw).hexdigest() != audit["private_ledger_sha256"]:
        raise SystemExit("custody ledger drift")
    ledger = json.loads(ledger_raw)
    selection = []
    for record in ledger["records"]:
        data_path = arguments.source_root / "scenarios/data" / f"{record['source_id']}.json"
        selection.append({"opaque_id": record["opaque_id"], "data_sha256": sha(data_path)})
    version = subprocess.run(
        [str(arguments.python), "-c", "import gurobipy as g; print('.'.join(map(str,g.gurobi.version())))"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip().splitlines()[-1]
    plan = {
        "schema": "llm4or-retailopt190-reference-solver-plan-v1",
        "status": "frozen_ready_for_offline_execution",
        "source": {
            "commit": audit["source"]["commit"],
            "dataset_sha256": audit["source"]["dataset_sha256"],
            "reference_solver_sha256": audit["source"]["reference_solver_sha256"],
            "benchmark_csv_sha256": audit["source"]["benchmark_csv_sha256"],
        },
        "custody": {
            "public_audit": "experiments/retailopt190_source_custody_audit_20261017.json",
            "public_audit_sha256": sha(audit_path),
            "private_ledger_sha256": audit["private_ledger_sha256"],
        },
        "selection": sorted(selection, key=lambda value: value["opaque_id"]),
        "endpoint": {
            "kind": "upstream_universal_retail_solver",
            "gurobi_version": version,
            "threads": 1,
            "seed": 0,
            "upstream_time_limit_seconds": 60,
            "upstream_mip_gap": 0.01,
            "worker_wall_seconds": 90,
            "max_workers": 5,
            "status_compatibility": "OPTIMAL must remain OPTIMAL; OPTIMAL (TL) may strengthen to OPTIMAL",
            "objective_tolerance": {
                "default_relative": 0.0001,
                "default_absolute": 1e-6,
                "relaxed_relative": 0.01,
                "relaxed_archetypes": ["fixed_order_cost", "pack_size_integer"],
            },
        },
        "environment": {
            "python": str(arguments.python),
            "python_sha256": sha(arguments.python.resolve()),
        },
        "frozen_files": {
            "llm4or/retailopt190_custody.py": sha(ROOT / "llm4or/retailopt190_custody.py"),
            "scripts/audit_retailopt190_reference_solver.py": sha(ROOT / "scripts/audit_retailopt190_reference_solver.py"),
        },
        "output": {
            "private_checkpoint": "results/private/retailopt190_reference_solver_v1/checkpoint.json",
            "public_audit": "experiments/retailopt190_reference_solver_audit_20261017.json",
        },
        "execution": {"api_calls": 0, "model_calls": 0, "credentials_read": False},
        "claim_boundary": "Environment and upstream endpoint reproducibility check only; no method output or model accuracy is evaluated.",
    }
    arguments.output.write_bytes(render(plan))
    print(json.dumps({"status": "frozen", "records": len(selection), "sha256": sha(arguments.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
