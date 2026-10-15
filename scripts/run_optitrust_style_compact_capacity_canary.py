#!/usr/bin/env python3
"""Run, restart-check and score the compact-sidecar capacity gate."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formal_gateway import FormalGateway
from llm4or.formal_provider import check_profile_metadata
from llm4or.optitrust_style_compact_canary import PLAN_PATH, publish_new, run_plan, score_run
from llm4or.schema import canonical


def main() -> None:
    plan = json.loads((ROOT / PLAN_PATH).read_text())
    check_profile_metadata()
    gateway = FormalGateway(ROOT, plan, authorization_path=plan["authorization_path"])
    directory = ROOT / plan["run_directory"]
    first = run_plan(ROOT, plan, directory, gateway, workers=4)
    before = gateway.summary()["physical_attempts"]
    restart = run_plan(ROOT, plan, directory, gateway, workers=4)
    after = gateway.summary()["physical_attempts"]
    if restart["new_items"] != 0 or after != before:
        raise ValueError("restart_created_new_physical_attempt")
    result = score_run(plan, directory, restart_new_items=restart["new_items"])
    output = ROOT / plan["output"]["public_result"]
    if output.exists():
        if canonical(json.loads(output.read_text())) != canonical(result):
            raise ValueError("result_byte_identity")
    else:
        publish_new(output, result)
    print(json.dumps({
        "state": "complete", "capacity_gate_passed": result["capacity_gate"]["passed"],
        "terminal": first["terminal"], "new_items": first["new_items"],
        "physical_attempts": after, "restart_new_items": restart["new_items"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
