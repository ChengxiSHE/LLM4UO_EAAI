"""Bind the user's standing authorization to the exact frozen V9 plan."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest

PLAN = ROOT / "experiments/text2opt_v9_confirmation_plan.json"
AUTH = ROOT / "experiments/text2opt_v9_confirmation_authorization.json"


def main():
    plan = json.loads(PLAN.read_text()); auth = json.loads(AUTH.read_text())
    if auth["status"] != "pending" or auth["plan_sha256"] != digest(plan):
        raise ValueError("v9_authorization_state_changed")
    auth.update(status="approved", user_confirmation="后续不需要我批准，你自行执行即可",
                approved_under_standing_instruction=True,
                authorization_scope="This exact frozen confirmation plan only.")
    write_json(AUTH, auth)
    print(json.dumps({"status": "approved", "plan_sha256": digest(plan)}, sort_keys=True))


if __name__ == "__main__":
    main()
