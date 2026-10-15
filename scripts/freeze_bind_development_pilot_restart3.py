#!/usr/bin/env python3
"""Freeze BIND restart 3 with stable prompt fingerprints for cache reuse."""

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


OLD_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_restart2_plan.json"
OLD_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_restart2_authorization.json"
NEW_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_restart3_plan.json"
NEW_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_restart3_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if NEW_PLAN.exists() or NEW_AUTH.exists():
        raise ValueError("bind_restart3_already_frozen")
    old_plan = json.loads(OLD_PLAN.read_text())
    old_auth = json.loads(OLD_AUTH.read_text())
    if old_auth["status"] != "approved" or old_auth["plan_sha256"] != digest(old_plan):
        raise ValueError("bind_restart3_old_authorization_state")
    directory = ROOT / old_plan["run_directory"]
    database = sqlite3.connect(directory / "requests.sqlite3")
    try:
        physical = database.execute(
            "SELECT status,error,count(*) FROM physical GROUP BY status,error"
        ).fetchall()
        imported = database.execute("SELECT sum(request_count) FROM imports").fetchone()[0]
    finally:
        database.close()
    if physical != [("failed", "codex_cli_runtime_error", 1)] or imported != 15:
        raise ValueError("bind_restart3_failure_evidence_changed")
    old_auth.update(
        status="closed_cache_fingerprint_drift", further_api_calls_authorized=False,
        closed_at=datetime.now(timezone.utc).isoformat(),
        closure_reason="adapter runtime version was accidentally included in the transport fingerprint",
    )
    OLD_AUTH.write_text(json.dumps(old_auth, sort_keys=True, separators=(",", ":")) + "\n")

    plan = dict(old_plan)
    plan["schema"] = "text2opt-bind-development-pilot-restart3-plan-v1"
    plan["run_directory"] = "results/private/text2opt_bind_development_pilot_restart3_20261003"
    plan["runtime_version"] = VERSION
    plan["restart_of_plan_sha256"] = digest(old_plan)
    plan["restart_reason"] = (
        "Separate adapter runtime version from the frozen v1 prompt/transport fingerprint so the exact 15 "
        "previously generated responses can be reused without another model call."
    )
    plan["expected_new_physical_requests"] = 0
    plan["frozen_files"] = {name: sha(ROOT / name) for name in old_plan["frozen_files"]}
    relative = "scripts/freeze_bind_development_pilot_restart3.py"
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
    print(json.dumps({"plan_sha256": digest(plan), "expected_new_physical_requests": 0,
                      "cache_import_requests": plan["cache_import"]["request_count"]}, sort_keys=True))


if __name__ == "__main__":
    main()
