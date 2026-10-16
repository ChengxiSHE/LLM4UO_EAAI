#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.nlequiv_skill_route import PACED_AUDIT_PATH, PACED_PLAN_PATH, PACED_RESULT_PATH, build_paced_restart_plan, evaluate_full, paced_plan_audit  # noqa: E402
from llm4or.schema import canonical  # noqa: E402

parser = argparse.ArgumentParser(); parser.add_argument("--custody-root", required=True); parser.add_argument("--mode", choices=("plan", "terminal"), default="plan"); args = parser.parse_args()
custody = Path(args.custody_root).resolve(); inference = custody / "inference"
plan = json.loads((ROOT / PACED_PLAN_PATH).read_text()); capacity = json.loads((ROOT / "experiments/nlequiv_skill_capacity_result_20261016.json").read_text()); predecessor = json.loads((ROOT / "experiments/nlequiv_skill_full_plan_20261016.json").read_text()); halt = json.loads((ROOT / "experiments/nlequiv_skill_full_infrastructure_halt_20261017.json").read_text())
if args.mode == "plan":
    _rebuilt, entries = build_paced_restart_plan(ROOT, inference, capacity, plan["source"], predecessor, halt); observed = paced_plan_audit(ROOT, plan, entries, inference, capacity, predecessor, halt); expected = json.loads((ROOT / PACED_AUDIT_PATH).read_text())
else:
    expected = json.loads((ROOT / PACED_RESULT_PATH).read_text()); observed = evaluate_full(plan, ROOT / plan["run_directory"], custody)
if canonical(observed) != canonical(expected): raise SystemExit("paced_audit_drift")
print("passed")
