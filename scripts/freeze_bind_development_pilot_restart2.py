#!/usr/bin/env python3
"""Freeze a cache-preserving BIND pilot restart after adapter hardening."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.bind_runtime import VERSION
from llm4or.schema import digest


OLD_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_restart_plan.json"
OLD_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_restart_authorization.json"
NEW_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_restart2_plan.json"
NEW_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_restart2_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if NEW_PLAN.exists() or NEW_AUTH.exists():
        raise ValueError("bind_restart2_already_frozen")
    old_plan = json.loads(OLD_PLAN.read_text())
    old_auth = json.loads(OLD_AUTH.read_text())
    if old_auth["status"] != "approved" or old_auth["plan_sha256"] != digest(old_plan):
        raise ValueError("bind_restart2_old_authorization_state")
    source_db = ROOT / old_plan["run_directory"] / "requests.sqlite3"
    database = sqlite3.connect(source_db)
    database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        failed = database.execute(
            "SELECT count(*) FROM requests WHERE status!='complete'"
        ).fetchone()[0]
    finally:
        database.close()
    if len(rows) != 15 or failed:
        raise ValueError("bind_restart2_cache_set_changed")
    interrupted = json.loads((ROOT / old_plan["run_directory"] / "interrupted.json").read_text())
    if interrupted.get("reason") != "KeyError":
        raise ValueError("bind_restart2_interruption_changed")
    old_auth.update(
        status="closed_adapter_exception", further_api_calls_authorized=False,
        closed_at=datetime.now(timezone.utc).isoformat(),
        closure_reason="restricted interpreter KeyError escaped instead of becoming a per-output rejection",
    )
    OLD_AUTH.write_text(json.dumps(old_auth, sort_keys=True, separators=(",", ":")) + "\n")

    plan = dict(old_plan)
    plan["schema"] = "text2opt-bind-development-pilot-restart2-plan-v1"
    plan["run_directory"] = "results/private/text2opt_bind_development_pilot_restart2_20261003"
    plan["runtime_version"] = VERSION
    plan["restart_of_plan_sha256"] = digest(old_plan)
    plan["restart_reason"] = (
        "Adapter-only hardening: contain interpreter runtime exceptions; support bounded official-output idioms "
        "(tuplelist indices, mapped bounds, slicing, enumerate, string labels, numeric geometry, dict access)."
    )
    plan["adapter_revision_policy"] = (
        "No prompt, model, response, selection, endpoint, or repair-budget change. "
        "All 15 existing model responses are hash-imported; generated Python remains unexecuted."
    )
    plan["trusted_solver_budget"] = {
        "backend": "HiGHS via scipy.milp", "solve_seconds": 20,
        "total_seconds": 25, "node_limit": 100000,
        "upstream_gurobi_time_limit_seconds": 100,
    }
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db),
        "source_plan_sha256": digest(old_plan),
        "request_count": len(rows), "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }
    plan["frozen_files"] = {
        name: sha(ROOT / name) for name in old_plan["frozen_files"]
    }
    relative = "scripts/freeze_bind_development_pilot_restart2.py"
    plan["frozen_files"][relative] = sha(ROOT / relative)
    NEW_PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": "User authorized autonomous subsequent execution on 2026-10-03.",
        "authorization_basis": "后续不需要我批准，你自行执行即可",
        "api_key_used": False, "codex_login_credentials_copied": False,
        "historical_authorizations_reused": False, "cache_import_only_expected": True,
    }
    NEW_AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "plan_sha256": digest(plan), "cache_import_requests": len(rows),
        "cache_import_charged_tokens": plan["cache_import"]["charged"],
        "new_physical_requests_expected": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
