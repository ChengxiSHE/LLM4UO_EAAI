#!/usr/bin/env python3
"""Publish aggregate, body-free diagnostics for the two RetailOpt studies."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from llm4or.retailopt190_knowledge import CARD_BY_ID,gold_decision


STUDIES={
    "prospective_primary":(
        "experiments/retailopt190_short_full_plan_v2_20261017.json",
        "results/private/retailopt190_short_full_v2_20261017",
    ),
    "posthoc_label_blind":(
        "experiments/retailopt190_label_blind_plan_20261017.json",
        "results/private/retailopt190_label_blind_20261017",
    ),
}


def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()


def main()->int:
    result={"schema":"llm4or-retailopt190-decision-diagnostics-v1","status":"complete","studies":{}}
    for label,(plan_name,run_name) in STUDIES.items():
        plan_path=ROOT/plan_name;run=ROOT/run_name;plan=json.loads(plan_path.read_text())
        questions={arm:defaultdict(lambda:[0,0]) for arm in ("base_short","knowledge_short")}
        cards={arm:defaultdict(lambda:[0,0]) for arm in questions}
        for cell_id,descriptor in plan["cells"].items():
            cell=json.loads((run/"cells"/f"{cell_id}.json").read_text());arm=descriptor["arm"]
            answers=cell["record"]["answers"];gold=gold_decision(descriptor["selected_skill_ids"])
            for key,expected in gold.items():
                questions[arm][key][1]+=1;questions[arm][key][0]+=int(answers[key]==expected)
            for skill_id in descriptor["selected_skill_ids"]:
                ids=[q.question_id for q in CARD_BY_ID[skill_id].questions]
                cards[arm][skill_id][1]+=1;cards[arm][skill_id][0]+=int(all(answers[key]==gold[key] for key in ids))
        result["studies"][label]={
            "plan_sha256":sha(plan_path),
            "question_correct_over_archetypes":{arm:{key:{"correct":value[0],"total":value[1]} for key,value in sorted(questions[arm].items())} for arm in questions},
            "card_fully_correct_over_routed_archetypes":{arm:{key:{"correct":value[0],"total":value[1]} for key,value in sorted(cards[arm].items())} for arm in cards},
        }
    result["privacy"]={"contains_problem_bodies":False,"contains_source_ids":False,"contains_per_item_results":False,"contains_responses":False,"contains_objectives":False}
    result["claim_boundary"]="Post-hoc aggregate decision diagnostics; counts localize errors but do not create an independent accuracy estimate or causal decomposition."
    output=ROOT/"experiments/retailopt190_decision_diagnostics_20261017.json"
    output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"studies":list(result["studies"])},sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
