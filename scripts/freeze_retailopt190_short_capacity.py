#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.formulationbench_same_knowledge import authorization,publish_new,publish_private_requests
from llm4or.retailopt190_experiment import *

maximum_task_bytes=7607
plan,entries=build_capacity_plan(ROOT,maximum_task_bytes)
audit=material_audit(plan,entries,capacity=True)
if audit["status"]!="passed":raise SystemExit("offline_gate_failed")
publish_private_requests(ROOT,entries,relative_root=CAPACITY_REQUEST_ROOT)
publish_new(ROOT/CAPACITY_PLAN_PATH,plan);publish_new(ROOT/CAPACITY_AUTH_PATH,authorization(ROOT,plan));publish_new(ROOT/CAPACITY_AUDIT_PATH,audit)
publish_new(ROOT/"experiments/retailopt190_skill_library_20261017.json",library_payload())
print(plan["schema"])
