#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import authorization, publish_new, publish_private_requests  # noqa: E402
from llm4or.nlequiv_skill_route import (  # noqa: E402
    CAPACITY_AUDIT_PATH, CAPACITY_AUTH_PATH, CAPACITY_PLAN_PATH,
    CAPACITY_REQUEST_ROOT, build_capacity_plan, capacity_audit, skill_manifest,
)

parser = argparse.ArgumentParser(); parser.add_argument("--custody-root", required=True); args = parser.parse_args()
inference = Path(args.custody_root).resolve() / "inference"
plan, entries = build_capacity_plan(ROOT, inference)
audit = capacity_audit(ROOT, plan, entries, inference)
if audit["status"] != "passed": raise SystemExit("offline_gate_failed")
publish_private_requests(ROOT, entries, relative_root=CAPACITY_REQUEST_ROOT)
publish_new(ROOT / CAPACITY_PLAN_PATH, plan)
publish_new(ROOT / CAPACITY_AUTH_PATH, authorization(ROOT, plan))
publish_new(ROOT / CAPACITY_AUDIT_PATH, audit)
publish_new(ROOT / "experiments/nlequiv_skill_library_20261016.json", skill_manifest())
print(plan["schema"])
