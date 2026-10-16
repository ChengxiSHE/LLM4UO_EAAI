#!/usr/bin/env python3
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formal_gateway import FormalGateway  # noqa: E402
from llm4or.formulationbench_same_knowledge import publish_new  # noqa: E402
from llm4or.nlequiv_skill_route import (  # noqa: E402
    CAPACITY_AUTH_PATH, CAPACITY_PLAN_PATH, CAPACITY_RESULT_PATH,
    run_plan, score_capacity,
)

plan = json.loads((ROOT / CAPACITY_PLAN_PATH).read_text()); directory = ROOT / plan["run_directory"]
gateway = FormalGateway(ROOT, plan, authorization_path=CAPACITY_AUTH_PATH)
first = run_plan(ROOT, plan, directory, gateway, workers=5)
second = run_plan(ROOT, plan, directory, gateway, workers=5)
result = score_capacity(plan, directory, restart_new_items=second["new_items"])
publish_new(ROOT / CAPACITY_RESULT_PATH, result)
print(json.dumps({"first": first, "restart": second, "passed": result["capacity_gate"]["passed"]}, sort_keys=True))
