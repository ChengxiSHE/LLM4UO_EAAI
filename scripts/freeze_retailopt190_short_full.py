#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.formulationbench_same_knowledge import authorization,publish_new,publish_private_requests
from llm4or.retailopt190_experiment import *
parser=argparse.ArgumentParser();parser.add_argument('--source-root',required=True);parser.add_argument('--ledger',required=True);args=parser.parse_args()
capacity=json.loads((ROOT/CAPACITY_RESULT_PATH).read_text())
plan,entries=build_full_plan(ROOT,args.source_root,args.ledger,capacity);audit=material_audit(plan,entries,capacity=False)
for relative in (
    "llm4or/retailopt190_compiler.py",
    "llm4or/retailopt190_endpoint.py",
    "llm4or/retailopt190_evaluation.py",
    "scripts/evaluate_retailopt190_short_full.py",
):
    plan["frozen_files"][relative]=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
plan["output"]["public_evaluation"]="experiments/retailopt190_short_full_evaluation_v2_20261017.json"
audit=material_audit(plan,entries,capacity=False)
if audit["status"]!="passed":raise SystemExit('offline_gate_failed')
publish_private_requests(ROOT,entries,relative_root=FULL_REQUEST_ROOT)
publish_new(ROOT/FULL_PLAN_PATH,plan);publish_new(ROOT/FULL_AUTH_PATH,authorization(ROOT,plan));publish_new(ROOT/FULL_AUDIT_PATH,audit)
print(plan["schema"])
