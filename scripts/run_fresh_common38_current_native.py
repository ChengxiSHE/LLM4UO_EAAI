"""Run or resume the frozen current-method native plan."""

import json
from pathlib import Path

from llm4or.fresh_common38_native import run_plan


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/fresh_common38_current_native_plan_20261015.json"


def main():
    plan = json.loads(PLAN.read_text())
    directory = ROOT / plan["output"]["private_run_directory"]
    print(json.dumps(run_plan(ROOT, plan, directory), sort_keys=True))


if __name__ == "__main__":
    main()
