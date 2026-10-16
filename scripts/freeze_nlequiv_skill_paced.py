#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import authorization, publish_new, publish_private_requests  # noqa: E402
from llm4or.nlequiv_skill_route import (  # noqa: E402
    PACED_AUDIT_PATH, PACED_AUTH_PATH, PACED_PLAN_PATH, PACED_REQUEST_ROOT,
    build_paced_restart_plan, paced_plan_audit,
)

parser = argparse.ArgumentParser(); parser.add_argument("--custody-root", required=True); args = parser.parse_args()
custody = Path(args.custody_root).resolve(); inference = custody / "inference"
capacity = json.loads((ROOT / "experiments/nlequiv_skill_capacity_result_20261016.json").read_text())
predecessor = json.loads((ROOT / "experiments/nlequiv_skill_full_plan_20261016.json").read_text())
halt = json.loads((ROOT / "experiments/nlequiv_skill_full_infrastructure_halt_20261017.json").read_text())
plan, entries = build_paced_restart_plan(ROOT, inference, capacity, predecessor["source"], predecessor, halt)
audit = paced_plan_audit(ROOT, plan, entries, inference, capacity, predecessor, halt)
if audit["status"] != "passed": raise SystemExit("paced_plan_gate_failed")
publish_private_requests(ROOT, entries, relative_root=PACED_REQUEST_ROOT)
publish_new(ROOT / PACED_PLAN_PATH, plan); publish_new(ROOT / PACED_AUTH_PATH, authorization(ROOT, plan)); publish_new(ROOT / PACED_AUDIT_PATH, audit)
print(plan["schema"])
