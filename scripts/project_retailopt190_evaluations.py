#!/usr/bin/env python3
"""Create deterministic body-free projections from private evaluation checkpoints."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from llm4or.retailopt190_evaluation import aggregate_evaluation
from llm4or.schema import digest


STUDIES={
    "prospective_primary":{
        "plan":"experiments/retailopt190_short_full_plan_v2_20261017.json",
        "run":"results/private/retailopt190_short_full_v2_20261017",
        "output":"experiments/retailopt190_short_full_evaluation_projection_v1_20261017.json",
        "role":"prospective_independent_confirmation",
    },
    "posthoc_label_blind":{
        "plan":"experiments/retailopt190_label_blind_plan_20261017.json",
        "run":"results/private/retailopt190_label_blind_20261017",
        "output":"experiments/retailopt190_label_blind_evaluation_projection_v1_20261017.json",
        "role":"posthoc_same_benchmark_robustness",
    },
}


def render(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n"


def project(label,config):
    plan_path=ROOT/config["plan"];plan=json.loads(plan_path.read_text());run=ROOT/config["run"]
    checkpoint=json.loads((run/"evaluation_checkpoint.json").read_text())
    if checkpoint.get("plan_sha256")!=digest(plan) or len(checkpoint.get("records",{}))!=380:raise ValueError(label+":checkpoint")
    completed=Counter()
    for cell_id,descriptor in plan["cells"].items():
        cell=json.loads((run/"cells"/f"{cell_id}.json").read_text())
        if cell.get("plan_sha256")!=digest(plan):raise ValueError(label+":cell_plan")
        completed[descriptor["arm"]]+=int(cell.get("status")=="completed")
    aggregate=aggregate_evaluation(checkpoint["records"].values(),inference_completed=completed)
    value={
        "schema":"llm4or-retailopt190-public-evaluation-projection-v1",
        "study":label,"study_role":config["role"],
        "status":"confirmed_improvement" if aggregate["confirmation_gate"]["passed"] else "improvement_not_confirmed",
        "plan_sha256":digest(plan),"plan_file_sha256":hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "source":{"commit":plan["source"]["commit"],"records":190,"archetypes":38},
        **aggregate,
        "execution":{"api_calls_in_evaluation":0,"model_calls_in_evaluation":0,"solver_evaluations":380,"workers":5},
        "privacy":{"contains_problem_bodies":False,"contains_source_ids":False,"contains_per_item_results":False,"contains_objectives":False,"contains_responses":False},
        "claim_boundary":plan["claim_boundary"],
    }
    path=ROOT/config["output"];raw=render(value)
    if path.exists() and path.read_text()!=raw:raise ValueError(label+":projection_drift")
    path.write_text(raw);return path,hashlib.sha256(raw.encode()).hexdigest()


def main():
    output={label:project(label,config)[1] for label,config in STUDIES.items()}
    print(json.dumps(output,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
