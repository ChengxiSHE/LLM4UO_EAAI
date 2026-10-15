"""Replay completed v1 responses through deterministic v2 compilation; no API calls."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_inputs import payload_sha256
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.milp_contracts import validate_output
from llm4or.milp_feedback import (compile_record,compile_record_v2,apply_teacher_edits,
                                  repair_gate,repair_gate_v2)
from llm4or.milp_schema import loads
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.semantic_decision import build_catalog,compile_decision

SOLVER_CACHE={}


def solve(operation):
    key=digest(operation)
    if key not in SOLVER_CACHE:
        from llm4or.milp_solver import execute
        SOLVER_CACHE[key]=execute(operation)
    return SOLVER_CACHE[key]


def sha256(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def reason(exc):
    value=str(exc)
    safe={'quote_provenance_mismatch','quote_not_uniquely_bindable','edit_lacks_replayed_target_evidence',
          'repair_requires_scope_and_protected_points','positive_example_not_teacher_feasible',
          'stale_teacher_input_or_models','nonrepair_edits','unaligned_teacher_interface'}
    return value if value in safe or value.startswith('output_contract_violation:') else type(exc).__name__


def ordered(counter):return dict(sorted(counter.items(),key=lambda item:(-item[1],item[0])))


def proxy(problem,model,reference):
    record={'input_sha256':payload_sha256(problem),'final_model':model,'status':'completed','errors':[],'trace':[]}
    return grade(record,problem,reference,independent=False).get('published_proxy_match')


def direction(tests):
    values={test.get('expected_satisfied') for test in tests if test['kind'] in {'row','domain'}}
    if not values:return 'objective'
    if values=={False}:return 'restrictive'
    if values=={True}:return 'relaxing'
    return 'mixed'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-directory',required=True)
    parser.add_argument('--output',default=str(ROOT/'results/mechanism_v2_offline_replay.json'));args=parser.parse_args()
    directory=Path(args.run_directory).resolve();ledger=directory/'requests.sqlite3'
    registry={x['id']:x for x in load_public_registry(ROOT)};public={k:v['public'] for k,v in registry.items()}
    references={x['problem_id']:x for x in json.loads((ROOT/'data/evaluation/bound_reference_audit_v1.json').read_text())['records']}
    split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
    roles={member:family['role'] for family in split['families'] for member in family['members']}
    with sqlite3.connect(ledger) as database:
        database.row_factory=sqlite3.Row
        weights=dict(database.execute('SELECT key,count(*) FROM logical GROUP BY key'))
        attempts=list(database.execute("SELECT key,response FROM attempts WHERE status='complete'"))
    physical=Counter();logical=Counter();gates=Counter();development=Counter();processed=0
    v3=Counter();v3_gates=Counter();v3_development=Counter();v3_cases=[]
    for attempt in attempts:
        path=directory/'request_payloads'/(attempt['key']+'.json')
        if not path.exists():continue
        saved=json.loads(path.read_text());payload=json.loads(saved['body']['messages'][1]['content']);context=payload.get('context',{})
        if set(context)!={'initial','teacher','evidence','input_sha256','model_hashes','quote_spans'}:continue
        processed+=1;weight=weights.get(attempt['key'],0)
        try:raw=validate_output(loads(json.loads(attempt['response'])['text']),teacher=True)
        except (ValueError,RuntimeError,KeyError,TypeError) as exc:
            label='schema:'+reason(exc);physical[label]+=1;logical[label]+=weight;continue
        try:
            catalog=build_catalog(payload['problem'],context['initial'],context['teacher'],context['evidence'])
            v3['catalog_built']+=1;v3['catalog_candidates']+=len(catalog['candidates'])
            if raw['status']=='repair':
                by_edit={(item['edit']['kind'],item['edit']['target']):item['id'] for item in catalog['candidates']}
                chosen=[]
                for edit in raw['edits']:
                    candidate=by_edit.get((edit['kind'],edit['target']))
                    if candidate and candidate not in chosen:chosen.append(candidate)
                if not chosen:
                    v3['repair_without_catalog_match']+=1
                else:
                    decision={'schema':'semantic-decision-v1','status':'reviewed','decisions':[
                        {'candidate_id':item['id'],'verdict':'teacher' if item['id'] in chosen[:4] else 'unclear',
                         'quote_text':raw['quote']['text'],'interpretation':raw['interpretation']}
                        for item in catalog['candidates']]}
                    compiled=compile_decision(decision,payload['problem'],context['initial'],context['teacher'],context['evidence'],catalog)
                    packet3,tests3=compiled['packet'],compiled['clause_tests'];v3['compiled_repair']+=1
                    proposal3=apply_teacher_edits(payload['problem'],context['initial'],context['teacher'],packet3)
                    result3=repair_gate_v2(payload['problem'],context['initial'],context['teacher'],proposal3,packet3,tests3,solver=solve)
                    v3_gates[result3['status']+':'+str(result3.get('reason','none'))]+=1
                    pid=payload['problem']['id']
                    if result3['status']=='accepted_relative_to_evidence' and roles.get(pid) in {'development_propose','development_select'}:
                        old=proxy(public[pid],context['initial'],references[pid]);new=proxy(public[pid],proposal3,references[pid])
                        if old in {True,False} and new in {True,False}:
                            v3_development['known']+=1
                            transition='correction' if new and not old else 'regression' if old and not new else 'both_match' if old else 'neither_match'
                            v3_development[transition]+=1
                            selected={item['id']:item for item in catalog['candidates']}
                            used=[selected[d['candidate_id']] for d in decision['decisions'] if d['verdict']=='teacher']
                            v3_cases.append({'problem_id':pid,'role':roles[pid],'benchmark':registry[pid]['benchmark'],
                                'transition':transition,'edit_kinds':sorted({item['edit']['kind'] for item in used}),
                                'edit_count':len(used),'direction':direction(tests3['tests']),
                                'quote_characters':len(raw['quote']['text']),'catalog_candidates':len(catalog['candidates'])})
            else:v3['compiled_unresolved']+=1
        except (ValueError,RuntimeError,KeyError,TypeError) as exc:
            v3['error:'+reason(exc)]+=1
        try:
            strict=compile_record(raw,payload['problem'],context['initial'],context['teacher'],context['evidence'])
            label='v1_compiled:'+strict['status']
        except (ValueError,RuntimeError,KeyError,TypeError) as exc:label='v1_error:'+reason(exc)
        physical[label]+=1;logical[label]+=weight
        try:
            packet=compile_record_v2(raw,payload['problem'],context['initial'],context['teacher'],context['evidence'])
            label='v2_compiled:'+packet['status'];physical[label]+=1;logical[label]+=weight
        except (ValueError,RuntimeError,KeyError,TypeError) as exc:
            label='v2_error:'+reason(exc);physical[label]+=1;logical[label]+=weight;continue
        if packet['status']!='repair':continue
        proposal=apply_teacher_edits(payload['problem'],context['initial'],context['teacher'],packet)
        result=repair_gate(payload['problem'],context['initial'],context['teacher'],proposal,packet,solver=solve)
        gate_label=result['status']+':'+str(result.get('reason','none'));gates[gate_label]+=1
        pid=payload['problem']['id']
        if result['status']=='accepted_relative_to_evidence' and roles.get(pid) in {'development_propose','development_select'}:
            old=proxy(public[pid],context['initial'],references[pid]);new=proxy(public[pid],proposal,references[pid])
            if old in {True,False} and new in {True,False}:
                development['known']+=1
                development['correction' if new and not old else 'regression' if old and not new
                            else 'both_match' if old else 'neither_match']+=1
    report={'schema':'mechanism-v2-offline-replay-v1','source_ledger_sha256':sha256(ledger),
            'source_evaluation_sha256':sha256(directory/'evaluation_v2.json'),
            'scope':'completed responses replayed locally; no API; proxy outcomes restricted to development roles',
            'teacher_feedback_unique_responses':processed,'physical_results':ordered(physical),'logical_results':ordered(logical),
            'deterministic_repair_gates':ordered(gates),'development_proxy_transitions':ordered(development),
            'v3_candidate_replay':ordered(v3),'v3_repair_gates':ordered(v3_gates),
            'v3_development_proxy_transitions':ordered(v3_development),
            'v3_development_cases':sorted(v3_cases,key=lambda x:(x['role'],x['problem_id'],x['transition'])),
            'claim_guard':'Mechanical recovery and development proxy transitions do not establish held-out formulation improvement.'}
    output=Path(args.output);write_json(output,report);print(json.dumps({'output':str(output),'responses':processed,'gates':sum(gates.values())}))


if __name__=='__main__':main()
