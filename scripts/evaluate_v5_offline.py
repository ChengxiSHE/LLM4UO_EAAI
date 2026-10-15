"""Freeze, then evaluate Base+semantic-contracts without new model calls.

The locked-test aggregate is emitted once after the method and evaluator hashes
are frozen.  No per-record locked-test score is written.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime,timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_inputs import payload_sha256
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.milp_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.semantic_contracts import apply_contracts_transactionally,derive_contracts

PLAN_PATH=ROOT/'experiments/v5_offline_evaluation_plan.json'
RESULT_PATH=ROOT/'results/v5_offline_frozen_evaluation.json'
SOURCE_RUN=ROOT/'results/private/formal_v3_20260912'
FILES=[
    'experiments/family_split_v1.json','experiments/full_run_plan.json',
    'data/evaluation/bound_reference_audit_v1.json',
    'llm4or/benchmark_inputs.py','llm4or/benchmark_registry.py','llm4or/formal_evaluation.py',
    'llm4or/milp_schema.py','llm4or/milp_solver.py','llm4or/semantic_contracts.py',
    'scripts/evaluate_v5_offline.py','results/private/formal_v3_20260912/inference_complete.json',
]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    if PLAN_PATH.exists() or RESULT_PATH.exists():raise ValueError('v5_offline_evaluation_already_frozen')
    plan={
        'schema':'v5-offline-evaluation-plan-v1','method':'Base+SemanticContracts-v1',
        'source_run':str(SOURCE_RUN.relative_to(ROOT)),'source_method':'Base','replicate':17,'token_cap':65536,
        'roles':{'development':['development_propose','development_select'],'locked_test':['locked_test']},
        'locked_test_scoring':'aggregate_only_after_freeze_no_per_record_output',
        'new_api_requests':0,
        'success_rule':'promising iff locked changed records contain at least one correction and zero regressions',
        'claim_guard':('Deterministic post-processing of an existing run; published-label matches are proxies and '
                       'operational families are not expert-certified independent units.'),
        'frozen_files':{name:sha(ROOT/name) for name in FILES},
        'frozen_at':datetime.now(timezone.utc).isoformat(),
    }
    write_json(PLAN_PATH,plan);print(json.dumps({'status':'frozen','plan_sha256':digest(plan),'api_requests':0}))


def preflight(plan):
    for name,expected in plan['frozen_files'].items():
        if sha(ROOT/name)!=expected:raise ValueError('frozen_file_changed:'+name)
    full=json.loads((ROOT/'experiments/full_run_plan.json').read_text())
    public={r['id']:r for r in load_public_registry(ROOT)}
    if any(pid not in public or public[pid]['input_sha256']!=value for pid,value in full['public_inputs'].items()):
        raise ValueError('public_input_changed')
    return full,public


def classify(before,after):
    if before not in {True,False} or after not in {True,False}:return 'unknown'
    if after and not before:return 'correction'
    if before and not after:return 'regression'
    return 'both_match' if before else 'neither_match'


def evaluate():
    if RESULT_PATH.exists():raise ValueError('locked_evaluation_already_exists')
    plan=json.loads(PLAN_PATH.read_text());full,registry=preflight(plan)
    split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
    family_by_problem={pid:f['id'] for f in split['families'] for pid in f['members']}
    role_by_problem={pid:f['role'] for f in split['families'] for pid in f['members']}
    references={r['problem_id']:r for r in json.loads((ROOT/'data/evaluation/bound_reference_audit_v1.json').read_text())['records']}
    complete=json.loads((SOURCE_RUN/'inference_complete.json').read_text())
    cells={c['id']:c for c in complete['cells'] if c['method']==plan['source_method']
           and c['replicate']==plan['replicate'] and c['token_cap']==plan['token_cap']}
    groups={'development':set(plan['roles']['development']),'locked_test':set(plan['roles']['locked_test'])}
    summaries={};family_effects={}
    for group,roles in groups.items():
        counts=Counter();effects=defaultdict(Counter)
        for pid,role in role_by_problem.items():
            if role not in roles:continue
            counts['records']+=1;cell=cells[pid];path=Path(cell['record_path']);record=json.loads(path.read_text())
            if digest(record)!=cell['record_sha256']:raise ValueError('source_record_changed')
            if record.get('input_sha256')!=payload_sha256(registry[pid]['public']):raise ValueError('record_input_changed')
            initial=record.get('final_model')
            if initial is None:counts['no_model']+=1;continue
            contracts=derive_contracts(registry[pid]['public'],initial)
            if not contracts['contracts']:continue
            counts['contract_triggered']+=1
            for contract in contracts['contracts']:counts['contract:'+contract['source']]+=1
            repaired,report=apply_contracts_transactionally(registry[pid]['public'],initial,execute,contracts)
            counts['status:'+report['status']]+=1
            if digest(repaired)==digest(initial):continue
            counts['actual_model_change']+=1
            base=grade(record,registry[pid]['public'],references[pid],independent=False).get('published_proxy_match')
            replay={**deepcopy(record),'final_model':repaired,
                    'final_solve':execute({'op':'solve','model':repaired}),'status':'completed'}
            updated=grade(replay,registry[pid]['public'],references[pid],independent=False).get('published_proxy_match')
            transition=classify(base,updated);counts['transition:'+transition]+=1
            effects[family_by_problem[pid]][transition]+=1
        summaries[group]=dict(counts)
        family_effects[group]={
            'changed_operational_families':len(effects),
            'families_with_correction':sum(v['correction']>0 for v in effects.values()),
            'families_with_regression':sum(v['regression']>0 for v in effects.values()),
            'warning':'Operational families are not expert-certified independent statistical units.',
        }
    locked=summaries['locked_test']
    promising=locked.get('transition:correction',0)>=1 and locked.get('transition:regression',0)==0
    report={'schema':'v5-offline-frozen-evaluation-v1','plan_sha256':digest(plan),'method':plan['method'],
            'new_api_requests':0,'summaries':summaries,'family_effects':family_effects,'promising':promising,
            'success_rule':plan['success_rule'],'claim_guard':plan['claim_guard'],
            'completed_at':datetime.now(timezone.utc).isoformat()}
    write_json(RESULT_PATH,report)
    print(json.dumps(report,sort_keys=True))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');parser.add_argument('--evaluate',action='store_true');args=parser.parse_args()
    if args.freeze==args.evaluate:raise ValueError('choose_exactly_one_mode')
    freeze() if args.freeze else evaluate()


if __name__=='__main__':main()
