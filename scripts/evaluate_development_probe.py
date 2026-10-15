"""Frozen post-inference scoring; explicit mappings, no model calls or artifact repair."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from llm4or.alignment import align_units
from llm4or.development_live import RUN_DIR, AUTH_PATH, PROBLEMS
from llm4or.evaluator import evaluate
from llm4or.pipeline import write_json
from llm4or.schema import digest,loads

BRANCHES=('initial','baseline_final','teacher_model','semantic_final')
MATCH='same_within_tolerance_exact_objective'


def main():
    if not (RUN_DIR/'inference_complete.json').exists() or loads(AUTH_PATH.read_text())['status']!='completed':
        raise SystemExit('Complete inference and close API authorization before scoring')
    manifest=loads((RUN_DIR/'manifest.json').read_text())
    for path,sha in manifest['reference_hashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise ValueError('frozen_reference_changed')
    reviews=loads((RUN_DIR/'mapping_review.json').read_text())
    records=[]
    for pid in PROBLEMS:
        inference=loads((RUN_DIR/f'{pid}.inference.json').read_text())
        reference=loads((ROOT/f'data/next_development/evaluator/{pid}.json').read_text())['reference']
        scores={};cache={}
        for branch in BRANCHES:
            candidate=inference.get(branch)
            if candidate is None:
                scores[branch]={'formulation_check':'no_valid_model','objective_match_proxy':None};continue
            key=pid+':'+digest(candidate)
            review=reviews.get(key)
            if review is None or review.get('status')!='semantic_mapping_reviewed':
                scores[branch]={'formulation_check':'mapping_unresolved','objective_match_proxy':None};continue
            mapped=align_units(candidate,reference,review)
            if key not in cache:cache[key]=evaluate(mapped,reference)
            scores[branch]={**deepcopy(cache[key]),'raw_candidate_hash':digest(candidate),'mapping_review_hash':digest(review)}
        transitions={}
        for branch in ('baseline_final','semantic_final'):
            old,new=scores['initial']['formulation_check'],scores[branch]['formulation_check']
            if old==MATCH and new==MATCH:transition='correct_to_correct'
            elif old=='different' and new==MATCH:transition='wrong_to_correct'
            elif old==MATCH and new=='different':transition='correct_to_wrong'
            elif old==new=='different':transition='wrong_to_wrong'
            else:transition='unresolved_transition'
            transitions[branch]=transition
        record={'problem':pid,'scores':scores,'transitions':transitions,'errors':inference['errors'],
                'repair_gate':inference.get('repair_gate',{}),'teacher_fact_gate':inference.get('teacher_packet',{}).get('fact_gate_status'),
                'initial_changed':{b:inference.get(b)!=inference.get('initial') for b in ('baseline_final','semantic_final')}}
        write_json(RUN_DIR/f'{pid}.evaluation.json',record);records.append(record)
    totals={}
    for branch in BRANCHES:
        scores=[r['scores'][branch] for r in records]
        totals[branch]={'denominator':len(PROBLEMS),'objective_match':sum(s['objective_match_proxy'] is True for s in scores),
                        'formulation_match':sum(s['formulation_check']==MATCH for s in scores),
                        'formulation_different':sum(s['formulation_check']=='different' for s in scores),
                        'formulation_unresolved':sum(s['formulation_check'] not in {MATCH,'different'} for s in scores)}
    with sqlite3.connect(f'file:{RUN_DIR / "requests.sqlite3"}?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        attempts=list(con.execute('SELECT * FROM attempts ORDER BY created'))
    assert len(attempts)<=20
    assert all(sum(a['problem']==pid for a in attempts)<=5 for pid in PROBLEMS)
    usage=[]
    for a in attempts:
        request=loads(a['request']);assert set(request['problem'])=={'id','text'}
        if a['response']:
            response=loads(a['response']);assert digest(response)==a['response_hash']
            if response.get('usage_source')=='provider_reported':
                assert response['completion_tokens']<=2048 and response['request_utf8_bytes']<=24000
                usage.append((a,response))
    phases={phase:{'requests':sum(a['phase']==phase for a in attempts),
                   'tokens':sum(r['total_tokens'] for a,r in usage if a['phase']==phase)}
            for phase in sorted({a['phase'] for a in attempts})}
    groups={'base':('initial',),'ordinary_repair':('initial','baseline_repair'),
            'semantic_repair':('initial','teacher_model','teacher_feedback','semantic_repair')}
    report={'kind':'four_question_development_ceiling_probe_not_superiority_test','totals':totals,'records':records,
            'actual_requests':len(attempts),'attempts_with_usage':len(usage),
            'prompt_tokens':sum(r['prompt_tokens'] for _,r in usage),
            'completion_tokens':sum(r['completion_tokens'] for _,r in usage),
            'total_tokens':sum(r['total_tokens'] for _,r in usage),'phases':phases,
            'standalone_branch_tokens_including_shared_initial':{b:sum(r['total_tokens'] for a,r in usage if a['phase'] in included) for b,included in groups.items()},
            'inference_closed_before_scoring':True,'frozen_references_verified':True,
            'equal_token_comparison':False,'cross_task_evolution':False,'monetary_cost':None,
            'reference_status':'assistant_text_transcription_not_independent_expert_gold',
            'api_errors':[{'key':a['key'],'error':a['error']} for a in attempts if a['status']!='complete']}
    write_json(RUN_DIR/'evaluation_summary.json',report)
    write_json(ROOT/'results/probe_s2_summary.json',{k:v for k,v in report.items() if k!='records'})
    print(json.dumps({k:report[k] for k in ('totals','actual_requests','total_tokens','phases','api_errors')},ensure_ascii=False))


if __name__=='__main__':main()
