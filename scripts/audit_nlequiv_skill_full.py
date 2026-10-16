#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.nlequiv_skill_route import FULL_AUDIT_PATH, FULL_PLAN_PATH, FULL_RESULT_PATH, build_full_plan, evaluate_full, full_plan_audit  # noqa: E402
from llm4or.schema import canonical  # noqa: E402

parser = argparse.ArgumentParser(); parser.add_argument("--custody-root", required=True); parser.add_argument("--mode", choices=("plan", "terminal"), default="plan"); args = parser.parse_args()
custody = Path(args.custody_root).resolve(); inference = custody / "inference"
plan = json.loads((ROOT / FULL_PLAN_PATH).read_text()); capacity = json.loads((ROOT / "experiments/nlequiv_skill_capacity_result_20261016.json").read_text())
if args.mode == "plan":
    _rebuilt, entries = build_full_plan(ROOT, inference, capacity, plan["source"]); observed = full_plan_audit(ROOT, plan, entries, inference, capacity); expected = json.loads((ROOT / FULL_AUDIT_PATH).read_text())
    if canonical(observed) != canonical(expected): raise SystemExit("plan_audit_drift")
else:
    expected = json.loads((ROOT / FULL_RESULT_PATH).read_text()); observed = evaluate_full(plan, ROOT / plan["run_directory"], custody)
    if canonical(observed) != canonical(expected): raise SystemExit("terminal_score_drift")
print("passed")
