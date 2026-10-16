#!/usr/bin/env python3
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formal_gateway import FormalGateway  # noqa: E402
from llm4or.formulationbench_same_knowledge import (  # noqa: E402
    FULL_AUTH_PATH, FULL_EXECUTION_PATH, FULL_PLAN_PATH,
    full_execution_summary, publish_new, run_plan,
)

plan = json.loads((ROOT / FULL_PLAN_PATH).read_text())
directory = ROOT / plan["run_directory"]
gateway = FormalGateway(ROOT, plan, authorization_path=FULL_AUTH_PATH)
first = run_plan(ROOT, plan, directory, gateway, workers=5)
second = run_plan(ROOT, plan, directory, gateway, workers=5)
execution = full_execution_summary(plan, directory, restart_new_items=second["new_items"])
publish_new(ROOT / FULL_EXECUTION_PATH, execution)
print(json.dumps({"first": first, "restart": second, "status": execution["status"]}, sort_keys=True))
