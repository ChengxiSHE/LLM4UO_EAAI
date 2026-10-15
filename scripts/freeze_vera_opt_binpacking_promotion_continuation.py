#!/usr/bin/env python3
"""Freeze a checkpoint-preserving continuation after reservation overrun."""

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
PLAN_V1 = ROOT / "experiments/vera_opt_binpacking_promotion_plan_halted_v1.json"
AUTH_V1 = ROOT / "experiments/vera_opt_binpacking_promotion_authorization_halted_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if PLAN_V1.exists() or AUTH_V1.exists():
        raise ValueError("continuation_already_frozen")
    source_plan = json.loads(PLAN_PATH.read_text()); source_auth = json.loads(AUTH_PATH.read_text())
    source_dir = ROOT / source_plan["run_directory"]; source_db = source_dir / "requests.sqlite3"
    with sqlite3.connect(source_db) as database:
        database.row_factory = sqlite3.Row
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        request_status = dict(database.execute("SELECT status,count(*) FROM requests GROUP BY status"))
        physical_status = dict(database.execute("SELECT status,count(*) FROM physical GROUP BY status"))
        halt = database.execute("SELECT reason FROM halt WHERE id=1").fetchone()
    if len(rows) != 1 or request_status != {"complete": 1} \
            or physical_status != {"complete": 1} \
            or not halt or halt[0] != "codex_cli_token_reservation_overrun":
        raise ValueError("source_ledger_changed")
    source_auth.update(status="halted_token_reservation_overrun",
                       closed_at=datetime.now(timezone.utc).isoformat(),
                       further_api_calls_authorized=False)
    PLAN_V1.write_text(json.dumps(source_plan, sort_keys=True, separators=(",", ":")) + "\n")
    AUTH_V1.write_text(json.dumps(source_auth, sort_keys=True, separators=(",", ":")) + "\n")

    plan = dict(source_plan)
    plan["schema"] = "vera-opt-binpacking-promotion-continuation-plan-v1"
    plan["run_directory"] = "results/private/vera_opt_binpacking_promotion_continuation_20261004"
    plan["restart_of_plan_sha256"] = digest(source_plan)
    plan["restart_reason"] = (
        "The serial canary reported more tokens than the frozen reservation. Import its exact completed "
        "response and enlarge only the reservation overhead; preserve model, prompt, candidate, cohort, "
        "endpoint, retries, concurrency, and statistical gate."
    )
    plan["historical_usage"] = {"physical_attempts": 1, "charged_tokens": rows[0]["charged"]}
    plan["cache_import"] = {
        "source_database": str(source_db.relative_to(ROOT)), "source_db_sha256": sha(source_db),
        "source_plan_sha256": digest(source_plan), "request_count": 1,
        "charged": rows[0]["charged"], "entries": [dict(row) for row in rows],
    }
    plan["limits"] = dict(source_plan["limits"], max_requests=299,
                          token_overhead_reserve=400_000)
    plan["expected_new_logical_request_ceiling"] = 99
    plan["expected_new_physical_request_ceiling_with_retries"] = 297
    frozen = {name: sha(ROOT / name) for name in source_plan["frozen_files"]}
    frozen["scripts/freeze_vera_opt_binpacking_promotion_continuation.py"] = sha(Path(__file__))
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
    print(json.dumps({"plan_sha256": digest(plan), "imported_requests": 1,
                      "expected_new_requests": 99, "token_overhead_reserve": 400000}, sort_keys=True))


if __name__ == "__main__":
    main()
