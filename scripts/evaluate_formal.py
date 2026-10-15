"""Evaluate once all frozen inference cells exist; never feed test scores back."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from pathlib import Path
import sys
import threading
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.schema import digest
from llm4or.pipeline import write_json
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import VERSION as EVALUATION_VERSION,grade,aggregate,evaluation_cache_binding


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-directory',required=True)
    ap.add_argument('--output',default='evaluation.json');ap.add_argument('--workers',type=int,default=1)
    args=ap.parse_args();directory=Path(args.run_directory)
    if Path(args.output).name!=args.output:raise ValueError('output_must_be_a_filename')
    if not 1<=args.workers<=8:raise ValueError('workers_must_be_between_1_and_8')
    plan=json.loads((ROOT/'experiments/full_run_plan.json').read_text());complete=json.loads((directory/'inference_complete.json').read_text())
    if complete['plan_sha256']!=digest(plan):raise ValueError('plan_changed')
    expected={(pid,m,s,t) for pid in plan['public_inputs'] for m in plan['methods'] for s in plan['replicates'] for t in plan['trajectory_token_caps']}
    actual=[(c['id'],c['method'],c['replicate'],c['token_cap']) for c in complete['cells']]
    if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError('matrix_incomplete_or_duplicated')
    public={r['id']:r['public'] for r in load_public_registry(ROOT)}
    refs={r['problem_id']:r for r in json.loads((ROOT/'data/evaluation/bound_reference_audit_v1.json').read_text())['records']}
    split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
    roles={x:(f['role'],f['id']) for f in split['families'] for x in f['members']}
    cache_locks={};cache_locks_guard=threading.Lock()
    def evaluate_cell(cell):
        record=json.loads(Path(cell['record_path']).read_text())
        if digest(record)!=cell['record_sha256']:raise ValueError('inference_record_changed')
        # Evaluation cache is separated from inference and keys include label
        # and input bindings; repeated budgets do not trigger redundant solves.
        key=digest(evaluation_cache_binding(record,refs[cell['id']]))
        path=directory/'evaluation_cache'/(key+'.json')
        with cache_locks_guard:lock=cache_locks.setdefault(key,threading.Lock())
        with lock:
            if path.exists():
                saved=json.loads(path.read_text())
                if saved['result_sha256']!=digest(saved['result']):raise ValueError('evaluation_cache_changed')
                result=saved['result']
            else:
                result=grade(record,public[cell['id']],refs[cell['id']]);write_json(path,{'result':result,'result_sha256':digest(result)})
        role,family=roles[cell['id']]
        return {**cell,'role':role,'family':family,'evaluation':result,'logical_usage':record.get('usage',{}),
                'tool_operations':record.get('tool_operations',0)}
    with ThreadPoolExecutor(max_workers=args.workers,thread_name_prefix='evaluation') as pool:
        rows=list(pool.map(evaluate_cell,complete['cells']))
    summaries=defaultdict(list)
    for row in rows:
        for cohort in ['full_source_cohort',row['role']]:
            group=(cohort,row['benchmark'],row['method'],row['replicate'],row['token_cap'])
            summaries[group].append(row['evaluation'])
    indexed={(r['id'],r['method'],r['replicate'],r['token_cap']):r for r in rows}
    contrasts=[]
    for old,new in [('Base','SolverRepair'),('Base','A'),('Base','B'),('A','SimpleAB'),('B','SimpleAB'),('SimpleAB','Full')]:
        for cap in plan['trajectory_token_caps']:
            for seed in plan['replicates']:
                for cohort in ['full_source_cohort','locked_test']:
                    pairs=[(indexed[(pid,old,seed,cap)],indexed[(pid,new,seed,cap)]) for pid in plan['public_inputs'] if cohort=='full_source_cohort' or roles[pid][0]=='locked_test']
                    eligible=[(a,b) for a,b in pairs if a['evaluation'].get('evaluation_eligible') is not False and b['evaluation'].get('evaluation_eligible') is not False]
                    plus=sum(a['evaluation']['published_proxy_match'] is not True and b['evaluation']['published_proxy_match'] is True for a,b in eligible)
                    minus=sum(a['evaluation']['published_proxy_match'] is True and b['evaluation']['published_proxy_match'] is not True for a,b in eligible)
                    contrasts.append({'old':old,'new':new,'token_cap':cap,'replicate':seed,'cohort':cohort,'n':len(pairs),'eligible_pairs':len(eligible),
                                      'new_only_match':plus,'old_only_match':minus,'net_match_difference':(plus-minus)/len(eligible) if eligible else None,
                                      'old_logical_tokens':sum(a['logical_usage'].get('logical_tokens',0) for a,b in pairs),
                                      'new_logical_tokens':sum(b['logical_usage'].get('logical_tokens',0) for a,b in pairs),
                                      'interpretation':'descriptive paired proxy counts; unresolved counts as no match; no iid confidence claim'})
    report={'evaluation_version':EVALUATION_VERSION,'plan_sha256':digest(plan),'cells':rows,'paired_comparisons':contrasts,'summary':[{'cohort':k[0],'benchmark':k[1],'method':k[2],'replicate':k[3],'token_cap':k[4],**aggregate(v)} for k,v in summaries.items()],
            'scientific_limits':plan['scientific_limits'],'test_feedback_used_for_evolution':False,
            'claim_guard':'No formulation-accuracy or statistically independent generalization claim may be inferred from published scalar matches.'}
    write_json(directory/args.output,report)
    print(json.dumps({'evaluated_cells':len(rows),'performance_claim':'published proxy only; full and held-out cohorts separate'}))


if __name__=='__main__':main()
