#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import publish_new  # noqa: E402
from llm4or.nlequiv_skill_route import PACED_PLAN_PATH, PACED_RESULT_PATH, evaluate_full  # noqa: E402

parser = argparse.ArgumentParser(); parser.add_argument("--custody-root", required=True); args = parser.parse_args()
plan = json.loads((ROOT / PACED_PLAN_PATH).read_text()); result = evaluate_full(plan, ROOT / plan["run_directory"], Path(args.custody_root).resolve())
publish_new(ROOT / PACED_RESULT_PATH, result)
print(json.dumps({"status": result["status"], "primary_gate_passed": result["primary_gate"]["passed"]}, sort_keys=True))
