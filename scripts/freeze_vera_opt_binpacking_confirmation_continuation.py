#!/usr/bin/env python3
"""Freeze a checkpoint-preserving BinPacking confirmation continuation."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.schema import digest

PLAN_PATH = ROOT / "experiments/vera_opt_binpacking_confirmation_plan.json"
AUTH_PATH = ROOT / "experiments/vera_opt_binpacking_confirmation_authorization.json"
PLAN_V1 = ROOT / "experiments/vera_opt_binpacking_confirmation_plan_interrupted_v1.json"
AUTH_V1 = ROOT / "experiments/vera_opt_binpacking_confirmation_authorization_interrupted_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if PLAN_V1.exists() or AUTH_V1.exists():
        raise ValueError("confirmation_continuation_already_frozen")
    source_plan = json.loads(PLAN_PATH.read_text())
    source_auth = json.loads(AUTH_PATH.read_text())
    source_dir = ROOT / source_plan["run_directory"]
    source_db = source_dir / "requests.sqlite3"
    with sqlite3.connect(source_db) as database:
        database.row_factory = sqlite3.Row
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        exhausted = dict(database.execute(
            "SELECT error,count(*) FROM requests WHERE status='exhausted' GROUP BY error"
        ))
        physical_attempts, physical_charged = database.execute(
            "SELECT count(*),coalesce(sum(charged),0) FROM physical"
        ).fetchone()
        halt_count = database.execute("SELECT count(*) FROM halt").fetchone()[0]
    checkpoints = sorted((source_dir / "inference").glob("*.json"))
    controller = json.loads((source_dir / "controller.json").read_text())
    if (
        len(rows) != 71
        or exhausted != {"codex_cli_runtime_error": 1, "invalid_json_response": 1}
        or physical_attempts != 94
        or len(checkpoints) != 72
        or halt_count != 0
        or controller.get("state") != "resumable_interruption"
        or controller.get("reason") != "codex_cli_runtime_error"
    ):
        raise ValueError("source_confirmation_ledger_changed")
    scopes = set()
    for path in checkpoints:
        value = json.loads(path.read_text())
        if set(value) != {"binding", "record", "record_sha256"} \
                or value["record_sha256"] != digest(value["record"]):
            raise ValueError("source_confirmation_checkpoint_integrity")
        scope = value["binding"].get("scope")
        if not isinstance(scope, str) or scope in scopes:
            raise ValueError("source_confirmation_checkpoint_scope_changed")
        scopes.add(scope)

    source_auth.update(
        status="halted_host_cli_runtime_error",
        closed_at=datetime.now(timezone.utc).isoformat(),
        further_api_calls_authorized=False,
    )
    PLAN_V1.write_text(json.dumps(source_plan, sort_keys=True, separators=(",", ":")) + "\n")
    AUTH_V1.write_text(json.dumps(source_auth, sort_keys=True, separators=(",", ":")) + "\n")

    new_run_directory = "results/private/vera_opt_binpacking_confirmation_continuation_20261004"
    destination = ROOT / new_run_directory
    if destination.exists():
        raise ValueError("confirmation_continuation_directory_exists")
    (destination / "inference").mkdir(parents=True, mode=0o700)
    for path in checkpoints:
        shutil.copy2(path, destination / "inference" / path.name)

    plan = dict(source_plan)
    plan["schema"] = "vera-opt-binpacking-confirmation-continuation-plan-v1"
    plan["run_directory"] = new_run_directory
    plan["restart_of_plan_sha256"] = digest(source_plan)
    plan["restart_reason"] = (
        "The frozen confirmation produced 72 integrity-checked inference checkpoints before a "
        "host Codex model-directory refresh subprocess timed out. Import all 71 successful request "
        "fingerprints, preserve the one completed method-level invalid-JSON exhaustion, and rerun "
        "only the 78 records without checkpoints. Model, prompt, candidate, cohort, endpoint, "
        "limits, retries, concurrency, and confirmation gate remain unchanged."
    )
    plan["historical_usage"] = {
        "physical_attempts": physical_attempts,
        "charged_tokens": physical_charged,
    }
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db),
        "source_plan_sha256": digest(source_plan),
        "request_count": len(rows),
        "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }
    plan["expected_new_logical_request_ceiling"] = 78
    plan["expected_new_physical_request_ceiling_with_retries"] = 234
    plan["checkpoint_import"] = {
        "source_directory": str((source_dir / "inference").relative_to(ROOT)),
        "record_count": len(checkpoints),
        "manifest_sha256": digest({path.name: sha(path) for path in checkpoints}),
    }
    frozen = {name: sha(ROOT / name) for name in source_plan["frozen_files"]}
    frozen["scripts/freeze_vera_opt_binpacking_confirmation_continuation.py"] = sha(Path(__file__))
    plan["frozen_files"] = dict(sorted(frozen.items()))
    PLAN_PATH.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": "User authorized autonomous subsequent execution and Codex quota use.",
        "authorization_basis": "后续不需要我批准，你自行执行即可；请你使用codex自己的额度进行api实验即可",
        "standing_authorization_recorded": True, "api_key_used": False,
        "codex_login_credentials_copied": False, "historical_authorizations_reused": False,
        "further_api_calls_authorized": True,
    }
    AUTH_PATH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "plan_sha256": digest(plan), "checkpoint_records": len(checkpoints),
        "imported_requests": len(rows), "expected_new_requests": 78,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
