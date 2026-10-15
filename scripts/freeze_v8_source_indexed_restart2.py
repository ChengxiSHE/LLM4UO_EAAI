"""Freeze V8 restart 2 with a serial canary and schema-wrapper transport."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.codex_cli_gateway import VERSION as GATEWAY_VERSION
from llm4or.schema import digest


METHOD_PLAN = ROOT / "experiments/v8_source_indexed_development_plan.json"
PRIOR_PLAN = ROOT / "experiments/v8_source_indexed_restart_plan.json"
AUTHORIZATIONS = [
    ROOT / "experiments/v8_source_indexed_development_authorization.json",
    ROOT / "experiments/v8_source_indexed_restart_authorization.json",
]
PLAN = ROOT / "experiments/v8_source_indexed_restart2_plan.json"
AUTH = ROOT / "experiments/v8_source_indexed_restart2_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    method = json.loads(METHOD_PLAN.read_text())
    prior = json.loads(PRIOR_PLAN.read_text())
    incidents = [json.loads(path.read_text()) for path in AUTHORIZATIONS]
    usages = [item.get("closed_usage", {}) for item in incidents]
    if any(usage.get("completed_physical_attempts") != 0 for usage in usages):
        raise ValueError("v8_prior_completed_call_detected")
    attempts = sum(usage.get("physical_attempts", 0) for usage in usages)
    tokens = sum(usage.get("physical_reserved_or_reported_tokens", 0) for usage in usages)
    if attempts != 40 or tokens != 2235730:
        raise ValueError("v8_cumulative_incident_accounting_changed")

    plan = json.loads(json.dumps(method))
    plan.update({
        "schema": "v8-source-indexed-restart2-plan-v1",
        "kind": "v8_source_indexed_restart2",
        "run_directory": "results/private/v8_source_indexed_restart2_20261003",
        "gateway_version": GATEWAY_VERSION,
        "method_plan_sha256": digest(method),
        "restart_of_plan_sha256": digest(prior),
        "restart_reason": (
            "Prior invocations completed no model response. Restart 2 uses a backend-compatible string wrapper, "
            "local full-schema validation, run-level CLI-error propagation, and a serial Stage 1 canary."
        ),
        "prior_incident_accounted_attempts": attempts,
        "prior_incident_accounted_tokens": tokens,
        "codex_cli_interface_preflight": True,
        "stage1_serial_canary_records": 1,
    })
    plan["limits"]["max_requests"] -= attempts
    plan["limits"]["max_total_reserved_or_reported_tokens"] -= tokens
    plan["matrix"]["physical_attempt_ceiling_with_retries"] = plan["limits"]["max_requests"]
    plan["frozen_files"]["llm4or/codex_cli_gateway.py"] = sha(
        ROOT / "llm4or/codex_cli_gateway.py"
    )
    plan["frozen_files"]["llm4or/run_interruption.py"] = sha(
        ROOT / "llm4or/run_interruption.py"
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
