#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import (  # noqa: E402
    FULL_AUDIT_PATH, FULL_AUTH_PATH, FULL_PLAN_PATH, FULL_PRIVATE_REQUEST_ROOT, authorization,
    build_full_material, full_plan_audit, publish_new, publish_private_requests,
)

parser = argparse.ArgumentParser()
parser.add_argument("--custody-root", required=True)
args = parser.parse_args()
custody = Path(args.custody_root).resolve()
capacity = json.loads((ROOT / "experiments/formulationbench_capacity_canary_result_20261016.json").read_text())
plan, entries = build_full_material(ROOT, custody / "inference", capacity)
audit = full_plan_audit(ROOT, plan, entries, custody / "inference", capacity)
if audit["status"] != "passed":
    raise SystemExit("full_plan_audit_failed")
publish_private_requests(ROOT, entries, relative_root=FULL_PRIVATE_REQUEST_ROOT)
publish_new(ROOT / FULL_PLAN_PATH, plan)
publish_new(ROOT / FULL_AUTH_PATH, authorization(ROOT, plan))
publish_new(ROOT / FULL_AUDIT_PATH, audit)
print(plan["schema"])
