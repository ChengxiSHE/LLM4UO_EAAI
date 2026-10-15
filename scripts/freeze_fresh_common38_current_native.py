"""Freeze the body-free current-method native plan."""

import json
from pathlib import Path

from llm4or.fresh_common38_native import build_plan, publish_plan
from llm4or.schema import digest


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/fresh_common38_current_native_plan_20261015.json"


def main():
    plan = build_plan(ROOT)
    publish_plan(OUTPUT, plan)
    print(json.dumps({"state": "frozen", "plan_sha256": digest(plan),
                      "identities": len(plan["bindings"]), "api_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
