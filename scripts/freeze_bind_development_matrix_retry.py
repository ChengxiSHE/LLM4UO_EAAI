#!/usr/bin/env python3
"""Freeze the final bounded retry for one local-format BIND failure."""

import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.schema import digest


SOURCE_PLAN_PATH = ROOT / "experiments/text2opt_bind_development_matrix_restart_plan.json"
SOURCE_AUTH_PATH = ROOT / "experiments/text2opt_bind_development_matrix_restart_authorization.json"
PLAN_PATH = ROOT / "experiments/text2opt_bind_development_matrix_retry_plan.json"
AUTH_PATH = ROOT / "experiments/text2opt_bind_development_matrix_retry_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if PLAN_PATH.exists() or AUTH_PATH.exists():
        raise ValueError("bind_development_matrix_retry_already_frozen")
    source_plan = json.loads(SOURCE_PLAN_PATH.read_text())
    source_auth = json.loads(SOURCE_AUTH_PATH.read_text())
    source_dir = ROOT / source_plan["run_directory"]
    completed = json.loads((source_dir / "completed.json").read_text())
    if (
        source_auth["status"] != "completed_development_pilot"
        or source_auth["plan_sha256"] != digest(source_plan)
        or completed["plan_sha256"] != digest(source_plan)
        or completed["evaluation"]["failure_reasons"] != {"invalid_json_response": 1}
    ):
        raise ValueError("bind_development_matrix_retry_source_invalid")

    source_db = source_dir / "requests.sqlite3"
    database = sqlite3.connect(source_db)
    database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        request_status = dict(database.execute("SELECT status,count(*) FROM requests GROUP BY status"))
        physical_status = dict(database.execute("SELECT status,count(*) FROM physical GROUP BY status"))
        work_status = dict(database.execute("SELECT status,count(*) FROM work GROUP BY status"))
    finally:
        database.close()
    if (
        len(rows) != 48 or request_status != {"complete": 48, "exhausted": 1}
        or physical_status != {"complete": 22, "failed": 1}
        or work_status != {"complete": 29, "method_failure": 1}
    ):
        raise ValueError("bind_development_matrix_retry_ledger_changed")

    plan = dict(source_plan)
    plan["schema"] = "text2opt-bind-development-matrix-retry-plan-v1"
    plan["run_directory"] = "results/private/text2opt_bind_development_matrix_retry_20261003"
    plan["public_report"] = "results/text2opt_bind_development_matrix_evaluation.json"
    plan["restart_of_plan_sha256"] = digest(source_plan)
    plan["restart_reason"] = (
        "Give the sole invalid-JSON fingerprint its two remaining predeclared physical attempts. "
        "All 48 completed responses are imported by exact fingerprint."
    )
    plan["historical_usage"] = completed["usage"]
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db),
        "source_plan_sha256": digest(source_plan),
        "request_count": len(rows),
        "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }
    plan["resilience"] = dict(
        source_plan["resilience"], max_attempts_per_request=2,
        retryable_local_errors=["invalid_json_response"],
    )
    plan["limits"] = dict(source_plan["limits"], max_requests=2)
    plan["expected_new_logical_request_ceiling"] = 1
    plan["expected_new_physical_request_ceiling_with_retries"] = 2
    frozen = {name: sha(ROOT / name) for name in source_plan["frozen_files"]}
    frozen["llm4or/codex_cli_gateway.py"] = sha(ROOT / "llm4or/codex_cli_gateway.py")
    frozen["scripts/run_bind_development_pilot.py"] = sha(ROOT / "scripts/run_bind_development_pilot.py")
    frozen["scripts/freeze_bind_development_matrix_retry.py"] = sha(
        ROOT / "scripts/freeze_bind_development_matrix_retry.py"
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
    print(json.dumps({
        "plan_sha256": digest(plan), "imported_complete_requests": len(rows),
        "remaining_fingerprint_attempts": 2,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
