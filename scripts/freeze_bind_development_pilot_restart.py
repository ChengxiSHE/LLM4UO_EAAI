#!/usr/bin/env python3
"""Close the sandbox-blocked BIND pilot and freeze an identical clean restart."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.schema import digest


OLD_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_plan.json"
OLD_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_authorization.json"
NEW_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_restart_plan.json"
NEW_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_restart_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if NEW_PLAN.exists() or NEW_AUTH.exists():
        raise ValueError("bind_restart_already_frozen")
    old_plan = json.loads(OLD_PLAN.read_text())
    old_auth = json.loads(OLD_AUTH.read_text())
    if old_auth["status"] != "approved" or old_auth["plan_sha256"] != digest(old_plan):
        raise ValueError("bind_old_authorization_state")
    database = sqlite3.connect(ROOT / old_plan["run_directory"] / "requests.sqlite3")
    try:
        failures = database.execute(
            "SELECT status,error,count(*) FROM physical GROUP BY status,error"
        ).fetchall()
        requests = database.execute("SELECT count(*) FROM requests").fetchone()[0]
    finally:
        database.close()
    if failures != [("failed", "codex_cli_runtime_error", 1)] or requests != 1:
        raise ValueError("bind_restart_failure_evidence_changed")
    old_auth.update(
        status="closed_local_execution_environment_failure", further_api_calls_authorized=False,
        closed_at=datetime.now(timezone.utc).isoformat(),
        closure_reason="first Codex CLI process was launched inside a network-restricted command sandbox",
        closed_usage={"physical_attempts": 1, "completed_physical_attempts": 0},
    )
    OLD_AUTH.write_text(json.dumps(old_auth, sort_keys=True, separators=(",", ":")) + "\n")

    plan = dict(old_plan)
    plan["schema"] = "text2opt-bind-development-pilot-restart-plan-v1"
    plan["run_directory"] = "results/private/text2opt_bind_development_pilot_restart_20261003"
    plan["restart_of_plan_sha256"] = digest(old_plan)
    plan["restart_reason"] = (
        "Clean ledger after a pre-response Codex CLI failure in the restricted command sandbox; "
        "scientific selection, prompts, model, budgets, endpoint, and method are unchanged."
    )
    plan["execution_environment"] = "controller_command_requires_network-enabled_host_execution"
    plan["frozen_files"] = dict(plan["frozen_files"])
    relative = "scripts/freeze_bind_development_pilot_restart.py"
    plan["frozen_files"][relative] = sha(ROOT / relative)
    NEW_PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": "User authorized autonomous subsequent execution on 2026-10-03.",
        "authorization_basis": "后续不需要我批准，你自行执行即可",
        "api_key_used": False, "codex_login_credentials_copied": False,
        "historical_authorizations_reused": False,
        "clean_restart": True,
    }
    NEW_AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"plan_sha256": digest(plan), "old_plan_sha256": digest(old_plan),
                      "old_physical_failures": 1, "new_run_directory": plan["run_directory"]}, sort_keys=True))


if __name__ == "__main__":
    main()
