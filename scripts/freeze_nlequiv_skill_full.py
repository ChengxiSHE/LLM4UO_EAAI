#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import authorization, publish_new, publish_private_requests  # noqa: E402
from llm4or.nlequiv_skill_route import (  # noqa: E402
    FULL_AUDIT_PATH, FULL_AUTH_PATH, FULL_PLAN_PATH, FULL_REQUEST_ROOT,
    build_full_plan, full_plan_audit,
)

parser = argparse.ArgumentParser(); parser.add_argument("--custody-root", required=True); args = parser.parse_args()
custody = Path(args.custody_root).resolve(); inference = custody / "inference"
capacity = json.loads((ROOT / "experiments/nlequiv_skill_capacity_result_20261016.json").read_text())
source = json.loads((ROOT / "experiments/nlequiv150_custody_audit_20261016.json").read_text())["source"]
plan, entries = build_full_plan(ROOT, inference, capacity, source)
audit = full_plan_audit(ROOT, plan, entries, inference, capacity)
if audit["status"] != "passed": raise SystemExit("full_plan_gate_failed")
publish_private_requests(ROOT, entries, relative_root=FULL_REQUEST_ROOT)
publish_new(ROOT / FULL_PLAN_PATH, plan); publish_new(ROOT / FULL_AUTH_PATH, authorization(ROOT, plan)); publish_new(ROOT / FULL_AUDIT_PATH, audit)
print(plan["schema"])
