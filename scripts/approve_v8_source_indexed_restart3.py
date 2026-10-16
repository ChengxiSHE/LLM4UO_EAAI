"""Bind standing autonomous authorization to V8 restart 3."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest


PLAN = ROOT / "experiments/v8_source_indexed_restart3_plan.json"
AUTH = ROOT / "experiments/v8_source_indexed_restart3_authorization.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    actual = digest(plan)
    if args.plan_sha256 != actual:
        raise ValueError("v8_restart3_plan_hash_mismatch")
    authorization = json.loads(AUTH.read_text())
    if authorization["status"] != "pending" or authorization["plan_sha256"] != actual:
        raise ValueError("v8_restart3_authorization_not_pending_or_changed")
    authorization.update({
        "status": "approved", "approved_at": datetime.now(timezone.utc).isoformat(),
        "user_confirmation": "后续不需要我批准，你自行执行即可",
        "authorization_scope": "This frozen restart and subsequent preregistered stages.",
    })
    write_json(AUTH, authorization)
    print(json.dumps({"status": "approved", "plan_sha256": actual}, sort_keys=True))


if __name__ == "__main__":
    main()
