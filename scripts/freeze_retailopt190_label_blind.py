#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.formulationbench_same_knowledge import authorization,publish_new,publish_private_requests
from llm4or.retailopt190_blind_replication import *
parser=argparse.ArgumentParser();parser.add_argument('--source-root',required=True);parser.add_argument('--ledger',required=True);args=parser.parse_args()
capacity=json.loads((ROOT/'experiments/retailopt190_short_capacity_result_v2_20261017.json').read_text())
plan,entries=build_plan(ROOT,args.source_root,args.ledger,capacity); report=audit(plan,entries)
if report['status']!='passed':raise SystemExit('offline_gate_failed')
publish_private_requests(ROOT,entries,relative_root=REQUEST_ROOT);publish_new(ROOT/PLAN_PATH,plan);publish_new(ROOT/AUTH_PATH,authorization(ROOT,plan));publish_new(ROOT/AUDIT_PATH,report)
print(plan['schema'])
