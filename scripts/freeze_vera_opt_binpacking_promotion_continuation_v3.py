#!/usr/bin/env python3
"""Freeze a third continuation after a host-sandbox CLI initialization failure."""

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

PLAN_PATH = ROOT / "experiments/vera_opt_binpacking_promotion_plan.json"
AUTH_PATH = ROOT / "experiments/vera_opt_binpacking_promotion_authorization.json"
PLAN_V3 = ROOT / "experiments/vera_opt_binpacking_promotion_plan_halted_v3.json"
AUTH_V3 = ROOT / "experiments/vera_opt_binpacking_promotion_authorization_halted_v3.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if PLAN_V3.exists() or AUTH_V3.exists():
        raise ValueError("continuation_v3_already_frozen")
    source_plan = json.loads(PLAN_PATH.read_text())
    source_auth = json.loads(AUTH_PATH.read_text())
    source_dir = ROOT / source_plan["run_directory"]
    source_db = source_dir / "requests.sqlite3"
    with sqlite3.connect(source_db) as database:
        database.row_factory = sqlite3.Row
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        request_status = dict(database.execute("SELECT status,count(*) FROM requests GROUP BY status"))
        errors = dict(database.execute(
            "SELECT error,count(*) FROM requests WHERE status='exhausted' GROUP BY error"
        ))
        physical_attempts, physical_charged = database.execute(
            "SELECT count(*),coalesce(sum(charged),0) FROM physical"
        ).fetchone()
        halt_count = database.execute("SELECT count(*) FROM halt").fetchone()[0]
    checkpoints = sorted((source_dir / "inference").glob("*.json"))
    if (
        request_status != {"complete": 84, "exhausted": 7}
        or errors != {"codex_cli_runtime_error": 7}
        or len(rows) != 84
        or len(checkpoints) != 89
        or physical_attempts != 7
        or halt_count != 0
    ):
        raise ValueError("source_ledger_changed")
    controller = json.loads((source_dir / "controller.json").read_text())
    if controller.get("state") != "resumable_interruption" \
            or controller.get("reason") != "codex_cli_runtime_error":
        raise ValueError("source_controller_changed")

    scopes = set()
    for path in checkpoints:
        value = json.loads(path.read_text())
        if set(value) != {"binding", "record", "record_sha256"} \
                or value["record_sha256"] != digest(value["record"]):
            raise ValueError("source_checkpoint_integrity")
        scope = value["binding"].get("scope")
        if not isinstance(scope, str) or scope in scopes:
            raise ValueError("source_checkpoint_scope_changed")
        scopes.add(scope)

    source_auth.update(
        status="halted_host_sandbox_cli_initialization",
        closed_at=datetime.now(timezone.utc).isoformat(),
        further_api_calls_authorized=False,
    )
    PLAN_V3.write_text(json.dumps(source_plan, sort_keys=True, separators=(",", ":")) + "\n")
    AUTH_V3.write_text(json.dumps(source_auth, sort_keys=True, separators=(",", ":")) + "\n")

    new_run_directory = "results/private/vera_opt_binpacking_promotion_continuation3_20261004"
    destination = ROOT / new_run_directory
    if destination.exists():
        raise ValueError("continuation_v3_directory_exists")
    (destination / "inference").mkdir(parents=True, mode=0o700)
    for path in checkpoints:
        shutil.copy2(path, destination / "inference" / path.name)

    prior_historical = source_plan.get("historical_usage", {})
    plan = dict(source_plan)
    plan["schema"] = "vera-opt-binpacking-promotion-continuation-plan-v3"
    plan["run_directory"] = new_run_directory
    plan["restart_of_plan_sha256"] = digest(source_plan)
    plan["restart_reason"] = (
        "The second continuation inherited 89 checkpoints but all seven attempted new CLI processes "
        "failed before inference because the host sandbox made the existing Codex state database "
        "read-only. Preserve those failures in historical accounting, import the unchanged 84 "
        "completed fingerprints and 89 checkpoints, and rerun only the eleven unfinished records "
        "with host access restored. No model, prompt, candidate, data, output limit, retry policy, "
        "concurrency, endpoint, or statistical rule changes."
    )
    plan["historical_usage"] = {
        "physical_attempts": prior_historical.get("physical_attempts", 0) + physical_attempts,
        "charged_tokens": prior_historical.get("charged_tokens", 0) + physical_charged,
    }
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db),
        "source_plan_sha256": digest(source_plan),
        "request_count": len(rows),
        "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }
    plan["expected_new_logical_request_ceiling"] = 11
    plan["expected_new_physical_request_ceiling_with_retries"] = 33
    plan["checkpoint_import"] = {
        "source_directory": str((source_dir / "inference").relative_to(ROOT)),
        "record_count": len(checkpoints),
        "manifest_sha256": digest({path.name: sha(path) for path in checkpoints}),
    }
    frozen = {name: sha(ROOT / name) for name in source_plan["frozen_files"]}
    frozen["scripts/freeze_vera_opt_binpacking_promotion_continuation_v3.py"] = sha(Path(__file__))
    plan["frozen_files"] = dict(sorted(frozen.items()))
    PLAN_PATH.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"],
        "status": "approved",
        "plan_sha256": digest(plan),
        "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]),
        "limits": plan["limits"],
        "user_confirmation": "User authorized autonomous subsequent execution and Codex quota use.",
        "authorization_basis": "后续不需要我批准，你自行执行即可；请你使用codex自己的额度进行api实验即可",
        "standing_authorization_recorded": True,
        "api_key_used": False,
        "codex_login_credentials_copied": False,
        "historical_authorizations_reused": False,
        "further_api_calls_authorized": True,
    }
    AUTH_PATH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "plan_sha256": digest(plan),
        "checkpoint_records": len(checkpoints),
        "imported_requests": len(rows),
        "host_failures_accounted": 7,
        "expected_new_requests": 11,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
