"""Record exact user authorization for the frozen V8 development plan."""
import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest


PLAN = ROOT / "experiments/v8_source_indexed_development_plan.json"
AUTH = ROOT / "experiments/v8_source_indexed_development_authorization.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    actual = digest(plan)
    if args.plan_sha256 != actual:
        raise ValueError("v8_plan_hash_mismatch")
    authorization = json.loads(AUTH.read_text())
    if authorization["status"] != "pending" or authorization["plan_sha256"] != actual:
        raise ValueError("v8_authorization_not_pending_or_changed")
    authorization.update({
        "status": "approved",
        "user_confirmation": "批准按照计划哈希 " + actual + " 启动 v8 Source-Indexed 两阶段开发实验",
    })
    write_json(AUTH, authorization)
    print(json.dumps({"status": "approved", "plan_sha256": actual}, sort_keys=True))


if __name__ == "__main__":
    main()
