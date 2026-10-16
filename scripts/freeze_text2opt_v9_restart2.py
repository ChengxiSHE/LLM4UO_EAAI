"""Freeze V9 continuation 2 after a pre-dispatch scope-budget mismatch."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.pipeline import write_json
from llm4or.schema import digest

PRIOR_PLAN = ROOT / "experiments/text2opt_v9_confirmation_restart_plan.json"
PRIOR_AUTH = ROOT / "experiments/text2opt_v9_confirmation_restart_authorization.json"
PRIOR_DIR = ROOT / "results/private/text2opt_v9_confirmation_restart_20261003"
PLAN = ROOT / "experiments/text2opt_v9_confirmation_restart2_plan.json"
AUTH = ROOT / "experiments/text2opt_v9_confirmation_restart2_authorization.json"


def main():
    if PLAN.exists() or AUTH.exists():
        raise ValueError("v9_restart2_already_frozen")
    prior = json.loads(PRIOR_PLAN.read_text()); prior_auth = json.loads(PRIOR_AUTH.read_text())
    interrupted = json.loads((PRIOR_DIR / "interrupted.json").read_text())
    if interrupted["reason"] != "codex_cli_trajectory_budget_exhausted" or interrupted["usage"]["physical_attempts"] != 0:
        raise ValueError("v9_restart2_source_state_changed")
    plan = json.loads(json.dumps(prior))
    plan.update({"schema": "text2opt-v9-confirmation-restart2-plan-v1",
                 "kind": "text2opt_v9_confirmation_restart2",
                 "run_directory": "results/private/text2opt_v9_confirmation_restart2_20261003",
                 "restart_of_plan_sha256": digest(prior),
                 "restart_reason": "No-send restart: synchronize the per-scope logical allowance with the enlarged reservation."})
    plan["token_cap"] = 1_200_000
    PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    auth = {"schema": plan["authorization_schema"], "status": "pending",
            "plan_sha256": digest(plan), "model": plan["model"],
            "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
            "user_confirmation": None, "historical_authorizations_reused": False,
            "api_key_used": False, "codex_login_credentials_copied": False,
            "authorization_basis": "User authorized autonomous subsequent execution on 2026-10-03."}
    AUTH.write_text(json.dumps(auth, sort_keys=True, separators=(",", ":")) + "\n")
    prior_auth.update(status="invalidated_pre_dispatch_trajectory_budget", closed_usage=interrupted["usage"],
                      further_api_calls_authorized=False, continuation_plan_sha256=digest(plan))
    write_json(PRIOR_AUTH, prior_auth)
    print(json.dumps({"plan": str(PLAN.relative_to(ROOT)), "plan_sha256": digest(plan),
                      "token_cap": plan["token_cap"], "new_physical_attempts": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
