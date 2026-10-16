#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.nlequiv_skill_route import CAPACITY_AUDIT_PATH, CAPACITY_PLAN_PATH, build_capacity_plan, capacity_audit  # noqa: E402
from llm4or.schema import canonical  # noqa: E402

parser = argparse.ArgumentParser(); parser.add_argument("--custody-root", required=True); args = parser.parse_args()
inference = Path(args.custody_root).resolve() / "inference"
plan = json.loads((ROOT / CAPACITY_PLAN_PATH).read_text()); _rebuilt, entries = build_capacity_plan(ROOT, inference)
observed = capacity_audit(ROOT, plan, entries, inference); expected = json.loads((ROOT / CAPACITY_AUDIT_PATH).read_text())
if canonical(observed) != canonical(expected): raise SystemExit("audit_drift")
print(observed["status"])
