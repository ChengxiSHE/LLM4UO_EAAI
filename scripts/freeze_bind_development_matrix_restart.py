#!/usr/bin/env python3
"""Freeze a hash-bound continuation after a local BIND item failure."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.schema import digest


SOURCE_PLAN_PATH = ROOT / "experiments/text2opt_bind_development_matrix_plan.json"
SOURCE_AUTH_PATH = ROOT / "experiments/text2opt_bind_development_matrix_authorization.json"
PLAN_PATH = ROOT / "experiments/text2opt_bind_development_matrix_restart_plan.json"
AUTH_PATH = ROOT / "experiments/text2opt_bind_development_matrix_restart_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if PLAN_PATH.exists() or AUTH_PATH.exists():
        raise ValueError("bind_development_matrix_restart_already_frozen")
    source_plan = json.loads(SOURCE_PLAN_PATH.read_text())
    source_auth = json.loads(SOURCE_AUTH_PATH.read_text())
    source_dir = ROOT / source_plan["run_directory"]
    controller = json.loads((source_dir / "controller.json").read_text())
    interrupted = json.loads((source_dir / "interrupted.json").read_text())
    if (
        source_auth["status"] != "approved"
        or source_auth["plan_sha256"] != digest(source_plan)
        or controller.get("state") != "resumable_interruption"
        or interrupted.get("reason") != "invalid_json_response"
        or interrupted.get("usage", {}).get("halt") is not None
    ):
        raise ValueError("bind_development_matrix_restart_source_invalid")

    source_db = source_dir / "requests.sqlite3"
    database = sqlite3.connect(source_db)
    database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        physical = database.execute("SELECT count(*) FROM physical").fetchone()[0]
    finally:
        database.close()
    if physical != 8 or len(rows) != 26:
        raise ValueError("bind_development_matrix_restart_ledger_changed")

    plan = dict(source_plan)
    plan["schema"] = "text2opt-bind-development-matrix-restart-plan-v1"
    plan["run_directory"] = "results/private/text2opt_bind_development_matrix_restart_20261003"
    plan["public_report"] = "results/text2opt_bind_development_matrix_evaluation.json"
    plan["restart_of_plan_sha256"] = digest(source_plan)
    plan["restart_reason"] = (
        "Preserve the local invalid-JSON item as a method failure and continue independent records. "
        "Completed responses are imported by exact fingerprint; the source ledger remains immutable."
    )
    plan["historical_usage"] = interrupted["usage"]
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db),
        "source_plan_sha256": digest(source_plan),
        "request_count": len(rows),
        "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }
    plan["resilience"] = dict(source_plan["resilience"], max_attempts_per_request=2)
    plan["limits"] = dict(source_plan["limits"], max_requests=262)
    plan["expected_new_physical_request_ceiling_with_retries"] = 144
    frozen = {name: sha(ROOT / name) for name in source_plan["frozen_files"]}
    frozen["scripts/run_bind_development_pilot.py"] = sha(ROOT / "scripts/run_bind_development_pilot.py")
    frozen["scripts/freeze_bind_development_matrix_restart.py"] = sha(
        ROOT / "scripts/freeze_bind_development_matrix_restart.py"
    )
    plan["frozen_files"] = frozen
    PLAN_PATH.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")

    authorization = {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": "User authorized autonomous subsequent execution on 2026-10-03.",
        "authorization_basis": "后续不需要我批准，你自行执行即可",
        "api_key_used": False, "codex_login_credentials_copied": False,
        "historical_authorizations_reused": False,
        "existing_academic_solver_license_only": True,
    }
    AUTH_PATH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")

    source_auth.update(
        status="superseded_after_resumable_interruption",
        closed_at=datetime.now(timezone.utc).isoformat(),
        closed_usage=interrupted["usage"], further_api_calls_authorized=False,
        continuation_plan_sha256=digest(plan),
    )
    SOURCE_AUTH_PATH.write_text(json.dumps(source_auth, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "plan_sha256": digest(plan), "imported_complete_requests": len(rows),
        "historical_physical_attempts": physical, "new_max_attempts_per_request": 2,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
