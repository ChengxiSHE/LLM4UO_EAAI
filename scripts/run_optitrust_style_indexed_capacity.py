#!/usr/bin/env python3
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formal_gateway import FormalGateway  # noqa: E402
from llm4or.optitrust_style_indexed_capacity import (  # noqa: E402
    AUDIT_PATH, AUTH_PATH, PLAN_PATH, RESULT_PATH, build_audit_from,
    publish_new, run_plan, score_run,
)

plan = json.loads((ROOT / PLAN_PATH).read_text())
directory = ROOT / plan["run_directory"]
gateway = FormalGateway(ROOT, plan, authorization_path=AUTH_PATH)
first = run_plan(ROOT, plan, directory, gateway, workers=3)
second = run_plan(ROOT, plan, directory, gateway, workers=3)
result = score_run(plan, directory, restart_new_items=second["new_items"])
publish_new(ROOT / RESULT_PATH, result)
audit = build_audit_from(ROOT, plan, ROOT / PLAN_PATH, directory, ROOT / RESULT_PATH, expected_offline=False)
publish_new(ROOT / AUDIT_PATH, audit)
print(json.dumps({"first": first, "restart": second, "passed": result["capacity_gate"]["passed"]}, sort_keys=True))
