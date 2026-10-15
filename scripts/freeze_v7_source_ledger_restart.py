"""Close the network-sandbox incident and freeze an outcome-clean v7 restart."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest

ORIGINAL_PLAN_SHA256 = "39232e2abe57b0ae0cf16fbd56167082cad31b9bc8d3a90ba5d3445cfa8880b7"
ORIGINAL_PLAN_PATH = ROOT / "experiments/v7_source_ledger_pilot_plan.json"
ORIGINAL_AUTH_PATH = ROOT / "experiments/v7_source_ledger_pilot_authorization.json"
PLAN_PATH = ROOT / "experiments/v7_source_ledger_restart_plan.json"
AUTH_PATH = ROOT / "experiments/v7_source_ledger_restart_authorization.json"
NEW_RUN_DIRECTORY = "results/private/v7_source_ledger_restart_20261003"
NEW_FILES = [
    "scripts/run_v7_source_ledger_restart.py",
    "scripts/approve_v7_source_ledger_restart.py",
    "scripts/freeze_v7_source_ledger_restart.py",
]


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def incident_state(plan):
    run = ROOT / plan["run_directory"]
    controller = json.loads((run / "controller.json").read_text())
    if controller.get("state") != "halted" or controller.get("reason") != "global_halt:circuit_breaker_transport_failures":
        raise ValueError("unexpected_incident_controller_state")
    with (run / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("incident_controller_still_running") from None
        db = sqlite3.connect(run / "requests.sqlite3")
        try:
            statuses = dict(db.execute("SELECT status,count(*) FROM attempts GROUP BY status"))
            errors = dict(db.execute("SELECT error,count(*) FROM attempts GROUP BY error"))
            retry_errors = dict(db.execute("SELECT error,count(*) FROM retry_attempts GROUP BY error"))
            successes = db.execute(
                "SELECT (SELECT count(*) FROM attempts WHERE status='complete'),"
                "(SELECT count(*) FROM retry_attempts WHERE status='complete')"
            ).fetchone()
            totals = db.execute(
                "SELECT physical_calls,physical_tokens,logical_calls,logical_tokens FROM totals WHERE id=1"
            ).fetchone()
            halt = db.execute("SELECT reason FROM halt WHERE id=1").fetchone()
        finally:
            db.close()
    probe_path = run / "antchat_connectivity_probe.json"
    probe = json.loads(probe_path.read_text())
    if (statuses != {"complete": 1, "exhausted": 3, "failed": 3}
            or errors != {None: 1, "EOFError": 1, "transport_URLError": 5}
            or retry_errors != {"transport_URLError": 14} or successes != (1, 0)
            or halt is not None or probe.get("provider_response_received") is not True
            or probe.get("reported_model_matches") is not True
            or probe.get("strict_ledger_valid") is not False):
        raise ValueError("incident_or_connectivity_probe_changed")
    return {
        "schema": "v7-environment-incident-v1",
        "original_plan_sha256": ORIGINAL_PLAN_SHA256,
        "original_run_directory": plan["run_directory"],
        "reason": "circuit_breaker_transport_failures",
        "cause": "local_network_egress_restriction_then_stdin_spawn_diagnostic_failure",
        "provider_responses_received": 1,
        "model_outputs_observed": 1,
        "physical_attempts": totals[0],
        "reserved_or_reported_tokens": totals[1],
        "logical_requests": totals[2],
        "logical_tokens": totals[3],
        "attempt_statuses": statuses,
        "failed_attempt_errors": {"transport_URLError": 14, "EOFError": 1},
        "connectivity_probe_strict_ledger_valid": False,
        "scientific_disposition": "invalid_environment_setup_run; excluded from method evaluation",
        "accounting_disposition": "retained and deducted from restart ceilings",
    }


def main():
    if PLAN_PATH.exists() or AUTH_PATH.exists():
        raise ValueError("v7_restart_already_frozen")
    original = json.loads(ORIGINAL_PLAN_PATH.read_text())
    if digest(original) != ORIGINAL_PLAN_SHA256:
        raise ValueError("original_plan_changed")
    original_auth = json.loads(ORIGINAL_AUTH_PATH.read_text())
    if (original_auth.get("status") != "approved"
            or original_auth.get("plan_sha256") != ORIGINAL_PLAN_SHA256):
        raise ValueError("original_authorization_not_active")
    incident = incident_state(original)
    if incident["physical_attempts"] >= original["limits"]["max_requests"]:
        raise ValueError("no_request_budget_remaining")
    if incident["reserved_or_reported_tokens"] >= original["limits"]["max_total_reserved_or_reported_tokens"]:
        raise ValueError("no_token_budget_remaining")

    closed_at = datetime.now(timezone.utc).isoformat()
    incident_path = ROOT / original["run_directory"] / "environment_incident.json"
    write_json(incident_path, {**incident, "closed_at": closed_at})
    original_auth.update(
        status="closed_invalid_environment_incident",
        closed_at=closed_at,
        closed_usage={
            "physical_attempts": incident["physical_attempts"],
            "reserved_or_reported_tokens": incident["reserved_or_reported_tokens"],
            "logical_requests": incident["logical_requests"],
            "logical_tokens": incident["logical_tokens"],
        },
        further_api_calls_authorized=False,
        incident_report=str(incident_path),
    )
    write_json(ORIGINAL_AUTH_PATH, original_auth)

    plan = json.loads(json.dumps(original))
    plan["status"] = "pending_user_authorization"
    plan["run_directory"] = NEW_RUN_DIRECTORY
    plan["limits"]["max_requests"] -= incident["physical_attempts"]
    plan["limits"]["max_total_reserved_or_reported_tokens"] -= incident["reserved_or_reported_tokens"]
    plan["matrix"]["physical_attempt_ceiling_with_retries"] = plan["limits"]["max_requests"]
    plan["incident_recovery"] = {
        "schema": incident["schema"],
        "original_plan_sha256": ORIGINAL_PLAN_SHA256,
        "authorization_path": str(ORIGINAL_AUTH_PATH.relative_to(ROOT)),
        "incident_report": str(incident_path.relative_to(ROOT)),
        "provider_responses_received": incident["provider_responses_received"],
        "model_outputs_observed": incident["model_outputs_observed"],
        "deducted_physical_attempts": incident["physical_attempts"],
        "deducted_reserved_or_reported_tokens": incident["reserved_or_reported_tokens"],
        "method_selection_evaluator_or_gates_changed": False,
    }
    plan["cost_note"] = (
        "This clean-room restart keeps the original method, records, and gates. Its ceilings deduct every "
        f"incident-ledger attempt from the originally approved cumulative ceilings: at most "
        f"{plan['limits']['max_requests']} additional physical attempts and "
        f"{plan['limits']['max_total_reserved_or_reported_tokens']} additional reserved-or-reported tokens."
    )
    frozen = dict(plan["frozen_files"])
    for obsolete in (
        "scripts/approve_v7_source_ledger_pilot.py",
        "scripts/freeze_v7_source_ledger_pilot.py",
    ):
        frozen.pop(obsolete, None)
    for path in NEW_FILES:
        frozen[path] = sha(path)
    plan["frozen_files"] = dict(sorted(frozen.items()))
    write_json(PLAN_PATH, plan)
    authorization = {
        "schema": plan["authorization_schema"],
        "status": "pending",
        "plan_sha256": digest(plan),
        "endpoint": plan["endpoint"],
        "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]),
        "limits": plan["limits"],
        "user_confirmation": None,
        "historical_authorizations_reused": False,
        "replaces_invalid_environment_plan": ORIGINAL_PLAN_SHA256,
    }
    write_json(AUTH_PATH, authorization)
    print(json.dumps({
        "status": "frozen_pending_user_authorization",
        "plan_sha256": digest(plan),
        "incident": incident,
        "remaining_limits": plan["limits"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
