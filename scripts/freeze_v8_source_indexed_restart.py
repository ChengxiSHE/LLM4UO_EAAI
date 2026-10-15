"""Freeze a clean V8 restart after the pre-model CLI argument incident."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.codex_cli_gateway import VERSION as GATEWAY_VERSION
from llm4or.schema import digest


SOURCE_PLAN = ROOT / "experiments/v8_source_indexed_development_plan.json"
SOURCE_AUTH = ROOT / "experiments/v8_source_indexed_development_authorization.json"
PLAN = ROOT / "experiments/v8_source_indexed_restart_plan.json"
AUTH = ROOT / "experiments/v8_source_indexed_restart_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source = json.loads(SOURCE_PLAN.read_text())
    incident = json.loads(SOURCE_AUTH.read_text())
    usage = incident.get("closed_usage", {})
    if usage.get("completed_physical_attempts") != 0 or usage.get("physical_attempts") != 20:
        raise ValueError("v8_incident_accounting_changed")
    if incident.get("status") not in {
        "completed_stage1_gate_failed", "invalidated_pre_model_cli_argument_error",
    }:
        raise ValueError("v8_incident_status_changed")

    plan = json.loads(json.dumps(source))
    plan.update({
        "schema": "v8-source-indexed-restart-plan-v1",
        "kind": "v8_source_indexed_restart",
        "run_directory": "results/private/v8_source_indexed_restart_20261003",
        "gateway_version": GATEWAY_VERSION,
        "restart_of_plan_sha256": digest(source),
        "restart_reason": "All prior CLI invocations exited locally with code 2 before model dispatch.",
        "prior_incident_accounted_attempts": usage["physical_attempts"],
        "prior_incident_accounted_tokens": usage["physical_reserved_or_reported_tokens"],
        "codex_cli_interface_preflight": True,
    })
    plan["limits"]["max_requests"] -= usage["physical_attempts"]
    plan["limits"]["max_total_reserved_or_reported_tokens"] -= usage[
        "physical_reserved_or_reported_tokens"
    ]
    plan["matrix"]["physical_attempt_ceiling_with_retries"] = plan["limits"]["max_requests"]
    plan["frozen_files"]["llm4or/codex_cli_gateway.py"] = sha(
        ROOT / "llm4or/codex_cli_gateway.py"
    )
    plan["frozen_files"]["scripts/run_v8_source_indexed_development.py"] = sha(
        ROOT / "scripts/run_v8_source_indexed_development.py"
    )
    version = subprocess.run(
        [plan["codex_cli"], "--version"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    if version != plan["codex_cli_version"]:
        raise ValueError("codex_cli_version_changed")

    PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"], "status": "pending",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": None, "historical_authorizations_reused": False,
        "api_key_used": False, "codex_login_credentials_copied": False,
        "authorization_basis": "User authorized autonomous subsequent execution on 2026-10-03.",
    }
    AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "plan": str(PLAN.relative_to(ROOT)), "plan_sha256": digest(plan),
        "authorization": str(AUTH.relative_to(ROOT)),
        "remaining_physical_attempt_ceiling": plan["limits"]["max_requests"],
        "remaining_token_ceiling": plan["limits"]["max_total_reserved_or_reported_tokens"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
