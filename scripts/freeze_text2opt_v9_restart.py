"""Freeze a hash-bound V9 continuation after the reservation-overrun stop."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.codex_cli_gateway import VERSION as GATEWAY_VERSION
from llm4or.pipeline import write_json
from llm4or.schema import digest

SOURCE_PLAN = ROOT / "experiments/text2opt_v9_confirmation_plan.json"
SOURCE_AUTH = ROOT / "experiments/text2opt_v9_confirmation_authorization.json"
SOURCE_DIR = ROOT / "results/private/text2opt_v9_confirmation_20261003"
SOURCE_DB = SOURCE_DIR / "requests.sqlite3"
PLAN = ROOT / "experiments/text2opt_v9_confirmation_restart_plan.json"
AUTH = ROOT / "experiments/text2opt_v9_confirmation_restart_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if PLAN.exists() or AUTH.exists():
        raise ValueError("v9_restart_already_frozen")
    source_plan = json.loads(SOURCE_PLAN.read_text()); source_auth = json.loads(SOURCE_AUTH.read_text())
    interrupted = json.loads((SOURCE_DIR / "interrupted.json").read_text())
    usage = interrupted["usage"]
    if interrupted["reason"] != "global_halt:codex_cli_token_reservation_overrun" or usage["physical_attempts"] != 397:
        raise ValueError("v9_restart_source_state_changed")
    checkpoints = {}
    for path in sorted((SOURCE_DIR / "inference").glob("*.json")):
        saved = json.loads(path.read_text()); problem_id = saved["record"]["problem_id"]
        if saved["record_sha256"] != digest(saved["record"]) or problem_id in checkpoints:
            raise ValueError("v9_restart_checkpoint_integrity")
        checkpoints[problem_id] = {"record_path": str(path.relative_to(ROOT)), "file_sha256": sha(path)}
    if len(checkpoints) != 397:
        raise ValueError("v9_restart_checkpoint_count_changed")
    database = sqlite3.connect("file:" + str(SOURCE_DB) + "?mode=ro", uri=True); database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
    finally:
        database.close()
    entries = [dict(row) for row in rows]; cache_tokens = sum(row["charged"] for row in rows)
    if len(entries) != 345 or cache_tokens != 8849068:
        raise ValueError("v9_restart_cache_accounting_changed")
    plan = json.loads(json.dumps(source_plan))
    plan.update({
        "schema": "text2opt-v9-confirmation-restart-plan-v1",
        "kind": "text2opt_v9_confirmation_restart",
        "run_directory": "results/private/text2opt_v9_confirmation_restart_20261003",
        "gateway_version": GATEWAY_VERSION,
        "restart_of_plan_sha256": digest(source_plan),
        "restart_reason": "Resume four uncheckpointed records after a single-turn hidden-context reservation overrun.",
        "prior_incident_accounted_attempts": usage["physical_attempts"],
        "prior_incident_accounted_tokens": usage["physical_reserved_or_reported_tokens"],
        "checkpoint_import": {"source_plan_sha256": digest(source_plan),
                              "record_count": len(checkpoints), "records": checkpoints},
        "cache_import": {"source_database": str(SOURCE_DB.relative_to(ROOT)),
                         "source_db_sha256": sha(SOURCE_DB), "source_plan_sha256": digest(source_plan),
                         "request_count": len(entries), "charged": cache_tokens, "entries": entries},
    })
    plan["limits"]["max_requests"] -= usage["physical_attempts"]
    plan["limits"]["max_total_reserved_or_reported_tokens"] -= usage["physical_reserved_or_reported_tokens"]
    plan["limits"]["token_overhead_reserve"] = 524288
    plan["matrix"]["physical_attempt_ceiling_with_retries"] = plan["limits"]["max_requests"]
    plan["frozen_files"][str(SOURCE_DB.relative_to(ROOT))] = sha(SOURCE_DB)
    plan["frozen_files"]["scripts/run_text2opt_v9_confirmation.py"] = sha(
        ROOT / "scripts/run_text2opt_v9_confirmation.py"
    )
    for item in checkpoints.values():
        plan["frozen_files"][item["record_path"]] = item["file_sha256"]
    PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    auth = {"schema": plan["authorization_schema"], "status": "pending",
            "plan_sha256": digest(plan), "model": plan["model"],
            "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
            "user_confirmation": None, "historical_authorizations_reused": False,
            "api_key_used": False, "codex_login_credentials_copied": False,
            "authorization_basis": "User authorized autonomous subsequent execution on 2026-10-03."}
    AUTH.write_text(json.dumps(auth, sort_keys=True, separators=(",", ":")) + "\n")
    source_auth.update(status="halted_token_reservation_overrun", closed_usage=usage,
                       further_api_calls_authorized=False,
                       continuation_plan_sha256=digest(plan))
    write_json(SOURCE_AUTH, source_auth)
    print(json.dumps({"plan": str(PLAN.relative_to(ROOT)), "plan_sha256": digest(plan),
                      "checkpoint_imports": len(checkpoints), "cache_imports": len(entries),
                      "remaining_records": 401-len(checkpoints),
                      "remaining_request_ceiling": plan["limits"]["max_requests"],
                      "remaining_token_ceiling": plan["limits"]["max_total_reserved_or_reported_tokens"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
