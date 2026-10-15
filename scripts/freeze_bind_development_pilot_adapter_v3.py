#!/usr/bin/env python3
"""Freeze a zero-inference replay for the final BIND adapter-v3 audit."""

import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.bind_runtime import VERSION
from llm4or.schema import digest


SOURCE_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_restart4_plan.json"
SOURCE_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_restart4_authorization.json"
PLAN = ROOT / "experiments/text2opt_bind_development_pilot_adapter_v3_plan.json"
AUTH = ROOT / "experiments/text2opt_bind_development_pilot_adapter_v3_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if PLAN.exists() or AUTH.exists():
        raise ValueError("bind_adapter_v3_replay_already_frozen")
    source_plan = json.loads(SOURCE_PLAN.read_text())
    source_auth = json.loads(SOURCE_AUTH.read_text())
    if source_auth["status"] != "completed_development_pilot" or source_auth["plan_sha256"] != digest(source_plan):
        raise ValueError("bind_adapter_v3_source_not_complete")
    source_db = ROOT / source_plan["run_directory"] / "requests.sqlite3"
    database = sqlite3.connect(source_db)
    database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        incomplete = database.execute("SELECT count(*) FROM requests WHERE status!='complete'").fetchone()[0]
    finally:
        database.close()
    if len(rows) != 19 or incomplete:
        raise ValueError("bind_adapter_v3_cache_set_changed")
    plan = dict(source_plan)
    plan["schema"] = "text2opt-bind-development-pilot-adapter-v3-plan-v1"
    plan["run_directory"] = "results/private/text2opt_bind_development_pilot_adapter_v3_20261003"
    plan["runtime_version"] = VERSION
    plan["replay_of_plan_sha256"] = digest(source_plan)
    plan["replay_reason"] = (
        "Accept and ignore the official Gurobi performance-only MIPFocus hint; no mathematical model, "
        "prompt, response, endpoint, or solver safety limit changes."
    )
    plan["expected_new_physical_requests"] = 0
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db), "source_plan_sha256": digest(source_plan),
        "request_count": len(rows), "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }
    plan["frozen_files"] = {name: sha(ROOT / name) for name in source_plan["frozen_files"]}
    relative = "scripts/freeze_bind_development_pilot_adapter_v3.py"
    plan["frozen_files"][relative] = sha(ROOT / relative)
    PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": "User authorized autonomous subsequent execution on 2026-10-03.",
        "authorization_basis": "后续不需要我批准，你自行执行即可",
        "api_key_used": False, "codex_login_credentials_copied": False,
        "historical_authorizations_reused": False, "cache_import_only_expected": True,
    }
    AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"plan_sha256": digest(plan), "cache_import_requests": len(rows),
                      "expected_new_physical_requests": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
