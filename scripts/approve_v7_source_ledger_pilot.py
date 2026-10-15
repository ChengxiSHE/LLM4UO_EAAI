"""Record explicit approval of the exact frozen v7 development pilot."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest
from scripts.run_v7_source_ledger_pilot import preflight


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--user-confirmation", required=True)
    args = parser.parse_args()
    plan = json.loads((ROOT / "experiments/v7_source_ledger_pilot_plan.json").read_text())
    if digest(plan) != args.plan_sha256 or not args.user_confirmation.strip():
        raise ValueError("exact_scope_confirmation_required")
    preflight(plan, require_approval=False)
    path = ROOT / "experiments/v7_source_ledger_pilot_authorization.json"
    auth = json.loads(path.read_text())
    if auth["status"] != "pending" or auth["plan_sha256"] != digest(plan):
        raise ValueError("authorization_not_pending")
    auth.update(status="approved", user_confirmation=args.user_confirmation,
                approved_at=datetime.now(timezone.utc).isoformat())
    write_json(path, auth)
    print(json.dumps({"status": "approved", "plan_sha256": digest(plan)}))


if __name__ == "__main__":
    main()
