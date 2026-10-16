#!/usr/bin/env python3
"""Freeze a zero-inference Gurobi-CLI replay of the BIND development pilot."""

import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.bind_runtime import VERSION
from llm4or.gurobi_cli_solver import DEFAULT_BINARY, VERSION as SOLVER_VERSION
from llm4or.schema import digest


SOURCE_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_adapter_v3_plan.json"
SOURCE_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_adapter_v3_authorization.json"
PLAN = ROOT / "experiments/text2opt_bind_development_pilot_gurobi_plan.json"
AUTH = ROOT / "experiments/text2opt_bind_development_pilot_gurobi_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if PLAN.exists() or AUTH.exists():
        raise ValueError("bind_gurobi_replay_already_frozen")
    source_plan = json.loads(SOURCE_PLAN.read_text())
    source_auth = json.loads(SOURCE_AUTH.read_text())
    if source_auth["status"] != "completed_development_pilot" or source_auth["plan_sha256"] != digest(source_plan):
        raise ValueError("bind_gurobi_source_not_complete")
    source_db = ROOT / source_plan["run_directory"] / "requests.sqlite3"
    database = sqlite3.connect(source_db)
    database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        physical = database.execute("SELECT count(*) FROM physical").fetchone()[0]
    finally:
        database.close()
    if len(rows) != 19 or physical != 0:
        raise ValueError("bind_gurobi_cache_set_changed")
    solver_version = subprocess.run(
        [DEFAULT_BINARY, "--version"], capture_output=True, text=True, timeout=15, check=True,
    ).stdout.splitlines()[0].strip()
    plan = dict(source_plan)
    plan["schema"] = "text2opt-bind-development-pilot-gurobi-plan-v1"
    plan["run_directory"] = "results/private/text2opt_bind_development_pilot_gurobi_20261003"
    plan["runtime_version"] = VERSION
    plan["replay_of_plan_sha256"] = digest(source_plan)
    plan["replay_reason"] = (
        "Use the installed Gurobi optimizer through a controller-generated LP file, matching the upstream "
        "100-second solver family while retaining the no-generated-code-execution boundary."
    )
    plan["solver_backend"] = {
        "name": "gurobi_cli", "binary": DEFAULT_BINARY, "version": solver_version,
        "adapter_version": SOLVER_VERSION, "time_limit_seconds": 100,
        "threads": 1, "mip_gap": 0, "independent_primal_recheck": True,
    }
    plan["expected_new_physical_requests"] = 0
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db), "source_plan_sha256": digest(source_plan),
        "request_count": len(rows), "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }
    frozen = {name: sha(ROOT / name) for name in source_plan["frozen_files"]}
    for name in ("llm4or/gurobi_cli_solver.py", "scripts/run_bind_development_pilot.py",
                 "scripts/freeze_bind_development_pilot_gurobi.py"):
        frozen[name] = sha(ROOT / name)
    plan["frozen_files"] = frozen
    PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": "User authorized autonomous subsequent execution on 2026-10-03.",
        "authorization_basis": "后续不需要我批准，你自行执行即可",
        "api_key_used": False, "codex_login_credentials_copied": False,
        "historical_authorizations_reused": False, "cache_import_only_expected": True,
        "existing_academic_solver_license_only": True,
    }
    AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"plan_sha256": digest(plan), "cache_import_requests": len(rows),
                      "expected_new_physical_requests": 0, "solver": solver_version}, sort_keys=True))


if __name__ == "__main__":
    main()
