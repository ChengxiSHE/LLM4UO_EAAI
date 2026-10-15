#!/usr/bin/env python3
"""Freeze BIND restart 4, reusing stable prefixes and regenerating changed repairs."""

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


OLD_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_restart3_plan.json"
OLD_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_restart3_authorization.json"
NEW_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_restart4_plan.json"
NEW_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_restart4_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if NEW_PLAN.exists() or NEW_AUTH.exists():
        raise ValueError("bind_restart4_already_frozen")
    old_plan = json.loads(OLD_PLAN.read_text())
    old_auth = json.loads(OLD_AUTH.read_text())
    if old_auth["status"] != "approved" or old_auth["plan_sha256"] != digest(old_plan):
        raise ValueError("bind_restart4_old_authorization_state")
    source_db = ROOT / old_plan["run_directory"] / "requests.sqlite3"
    database = sqlite3.connect(source_db)
    database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        physical = [tuple(row) for row in database.execute(
            "SELECT status,error,count(*) FROM physical GROUP BY status,error"
        ).fetchall()]
    finally:
        database.close()
    if len(rows) != 15 or physical != [("failed", "codex_cli_runtime_error", 1)]:
        raise ValueError("bind_restart4_evidence_changed")
    old_auth.update(
        status="closed_changed_repair_fingerprint", further_api_calls_authorized=False,
        closed_at=datetime.now(timezone.utc).isoformat(),
        closure_reason=(
            "The hardened adapter changed RCPSP round-1 feedback from translator rejection to solver limit; "
            "the old round-2 response therefore could not be reused under the same-slot integrity rule."
        ),
    )
    OLD_AUTH.write_text(json.dumps(old_auth, sort_keys=True, separators=(",", ":")) + "\n")

    plan = dict(old_plan)
    plan["schema"] = "text2opt-bind-development-pilot-restart4-plan-v1"
    plan["run_directory"] = "results/private/text2opt_bind_development_pilot_restart4_20261003"
    plan["runtime_version"] = VERSION
    plan["restart_of_plan_sha256"] = digest(old_plan)
    plan["restart_reason"] = (
        "Reuse all exact compatible v1-prompt responses; issue new calls only where the hardened adapter changes "
        "the official oracle-repair feedback trajectory."
    )
    plan["expected_new_logical_request_ceiling"] = 6
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db), "source_plan_sha256": digest(old_plan),
        "request_count": len(rows), "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }
    plan["frozen_files"] = {name: sha(ROOT / name) for name in old_plan["frozen_files"]}
    relative = "scripts/freeze_bind_development_pilot_restart4.py"
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
    }
    NEW_AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"plan_sha256": digest(plan), "cache_import_requests": len(rows),
                      "new_logical_request_ceiling": 6}, sort_keys=True))


if __name__ == "__main__":
    main()
