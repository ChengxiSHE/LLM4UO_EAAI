#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import (  # noqa: E402
    FULL_AUDIT_PATH, FULL_PLAN_PATH, FULL_RESULT_PATH, build_full_material,
    evaluate_full, full_plan_audit,
)
from llm4or.schema import canonical  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--custody-root", required=True)
parser.add_argument("--mode", choices=("plan", "terminal"), default="plan")
args = parser.parse_args()
custody = Path(args.custody_root).resolve()
plan = json.loads((ROOT / FULL_PLAN_PATH).read_text())
capacity = json.loads((ROOT / "experiments/formulationbench_capacity_canary_result_20261016.json").read_text())
_rebuilt, entries = build_full_material(ROOT, custody / "inference", capacity)
audit = full_plan_audit(ROOT, plan, entries, custody / "inference", capacity)
if args.mode == "plan":
    expected = json.loads((ROOT / FULL_AUDIT_PATH).read_text())
    if canonical(audit) != canonical(expected):
        raise SystemExit("full_plan_audit_drift")
else:
    result = json.loads((ROOT / FULL_RESULT_PATH).read_text())
    rebuilt_result = evaluate_full(plan, ROOT / plan["run_directory"], custody)
    audit = {
        "schema": "formulationbench-same-knowledge-v1-terminal-audit",
        "status": "passed" if canonical(result) == canonical(rebuilt_result) else "failed",
        "plan_sha256": hashlib.sha256((ROOT / FULL_PLAN_PATH).read_bytes()).hexdigest(),
        "result_sha256": hashlib.sha256((ROOT / FULL_RESULT_PATH).read_bytes()).hexdigest(),
        "score_reconstruction": canonical(result) == canonical(rebuilt_result),
        "privacy": {"bodies_published": False, "per_pair_predictions_published": False, "per_pair_labels_published": False},
    }
    if audit["status"] != "passed":
        raise SystemExit("terminal_audit_failed")
    print(json.dumps(audit, sort_keys=True))
    raise SystemExit(0)
if audit["status"] != "passed":
    raise SystemExit("plan_audit_failed")
print(audit["status"])
