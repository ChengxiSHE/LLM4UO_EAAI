#!/usr/bin/env python3
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.formal_gateway import FormalGateway
from llm4or.formulationbench_same_knowledge import publish_new
from llm4or.retailopt190_blind_replication import *
from llm4or.retailopt190_experiment import full_execution,run_plan
plan=json.loads((ROOT/PLAN_PATH).read_text());directory=ROOT/plan['run_directory'];gateway=FormalGateway(ROOT,plan,authorization_path=AUTH_PATH)
first=run_plan(ROOT,plan,directory,gateway,workers=5);second=run_plan(ROOT,plan,directory,gateway,workers=5)
execution=full_execution(plan,directory,restart_new_items=second['new_items']);publish_new(ROOT/EXECUTION_PATH,execution)
print(json.dumps({'first':first,'restart':second,'execution':execution},sort_keys=True))
