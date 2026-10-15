"""Validate v2 repair mechanics on controlled LP/MILP faults; no model calls."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_inputs import payload_sha256
from llm4or.milp_feedback import compile_record_v2,apply_teacher_edits,repair_gate,repair_gate_v2
from llm4or.milp_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.semantic_decision import build_catalog,compile_decision

CACHE={}


def solve(operation):
    key=digest(operation)
    if key not in CACHE:CACHE[key]=execute(operation)
    return CACHE[key]


def problem(index):
    return {'id':f'synthetic_v2_{index}','profile':'description_parameters_v1',
            'text':f'Choose a quantity for controlled test {index}. Follow the stated limit and preference.',
            'parameters':[],'instances':[]}


def model(n,*,domain='continuous',row=None,sense='max'):
    constraints=[] if row is None else [{'id':'cap','coefficients':{'x':row[0]},'sense':'le','rhs':row[1]}]
    return {'schema':'milp-v1','variables':[{'id':'x','meaning':'quantity','unit':'item','domain':domain,'lower':0,'upper':2*n}],
            'constraints':constraints,'objective':{'coefficients':{'x':1},'sense':sense,'unit':'items','offset':0}}


def suite(p,tests):return {'schema':'clause-tests-v1','input_sha256':payload_sha256(p),'tests':tests}


def raw(p,initial,teacher,kind,target):
    return {'schema':'teacher-milp-v1','status':'repair','input_sha256':payload_sha256(p),
            'model_hashes':{'initial':digest(initial),'teacher':digest(teacher)},
            'quote':{'field':'incorrect.field','text':p['text'],'start':99,'end':100},
            'interpretation':'Synthetic controlled interpretation.','edits':[{'kind':kind,'target':target}],
            'positive_examples':[{'x':0}]}


def scenarios(n,index):
    p=problem(index);free=model(n);tight=model(n,row=(1,n));loose=model(n,row=(1,2*n));scaled=model(n,row=(2,2*n))
    continuous=model(n,domain='continuous');integer=model(n,domain='integer')
    maximum=model(n,sense='max');minimum=model(n,sense='min')
    return [
        ('missing_row',p,free,tight,'row','cap',suite(p,[{'kind':'feasibility','point':{'x':n+1},'expected_feasible':False},{'kind':'feasibility','point':{'x':0},'expected_feasible':True}])),
        ('extra_row',p,tight,free,'row','cap',suite(p,[{'kind':'feasibility','point':{'x':n+1},'expected_feasible':True},{'kind':'feasibility','point':{'x':0},'expected_feasible':True}])),
        ('wrong_rhs',p,loose,tight,'row','cap',suite(p,[{'kind':'feasibility','point':{'x':n+1},'expected_feasible':False},{'kind':'feasibility','point':{'x':0},'expected_feasible':True}])),
        ('wrong_coefficient',p,loose,scaled,'row','cap',suite(p,[{'kind':'feasibility','point':{'x':n+1},'expected_feasible':False},{'kind':'feasibility','point':{'x':0},'expected_feasible':True}])),
        ('missing_integrality',p,continuous,integer,'domain','x',suite(p,[{'kind':'feasibility','point':{'x':n+.5},'expected_feasible':False},{'kind':'feasibility','point':{'x':n},'expected_feasible':True}])),
        ('excess_integrality',p,integer,continuous,'domain','x',suite(p,[{'kind':'feasibility','point':{'x':n+.5},'expected_feasible':True},{'kind':'feasibility','point':{'x':n},'expected_feasible':True}])),
        ('objective_reversal',p,maximum,minimum,'objective','objective',suite(p,[{'kind':'preference','better':{'x':0},'worse':{'x':1}}])),
    ]


def run_case(p,faulty,correct,kind,target,tests):
    evidence=solve({'op':'compare','left':faulty,'right':correct})
    packet=compile_record_v2(raw(p,faulty,correct,kind,target),p,faulty,correct,evidence)
    proposal=apply_teacher_edits(p,faulty,correct,packet)
    legacy=repair_gate(p,faulty,correct,proposal,packet,solver=solve)
    guarded=repair_gate_v2(p,faulty,correct,proposal,packet,tests,solver=solve)
    return proposal==correct,legacy['status'],guarded['status'],guarded.get('reason','none')


def run_decision(p,initial,teacher,kind,target,independent_tests):
    evidence=solve({'op':'compare','left':initial,'right':teacher});catalog=build_catalog(p,initial,teacher,evidence)
    candidate=next((item for item in catalog['candidates'] if item['edit']=={'kind':kind,'target':target}),None)
    if candidate is None:return False,False,None,None
    decision={'schema':'semantic-decision-v1','status':'reviewed','decisions':[{ 
        'candidate_id':candidate['id'],'verdict':'teacher','quote_text':p['text'],
        'interpretation':'Synthetic controlled interpretation.'}]}
    compiled=compile_decision(decision,p,initial,teacher,evidence,catalog)
    proposal=apply_teacher_edits(p,initial,teacher,compiled['packet'])
    self_gate=repair_gate_v2(p,initial,teacher,proposal,compiled['packet'],compiled['clause_tests'],solver=solve)
    independent_gate=repair_gate_v2(p,initial,teacher,proposal,compiled['packet'],independent_tests,solver=solve)
    return True,proposal==teacher,self_gate['status'],independent_gate['status']


def main():
    results=Counter();by_type={}
    index=0
    for n in range(2,7):
        for name,p,faulty,correct,kind,target,tests in scenarios(n,index):
            index+=1;local=by_type.setdefault(name,Counter())
            exact,legacy,status,reason=run_case(p,faulty,correct,kind,target,tests)
            results['correct_cases']+=1;local['correct_cases']+=1
            results['exact_restoration']+=exact;local['exact_restoration']+=exact
            results['legacy_accepts_correct']+=legacy=='accepted_relative_to_evidence';local['v2_accepts_correct']+=status=='accepted_relative_to_evidence'
            results['v2_accepts_correct']+=status=='accepted_relative_to_evidence'
            if name not in {'missing_row','extra_row'}:results['v3_supported_correct_cases']+=1
            found,restored,self_status,independent_status=run_decision(p,faulty,correct,kind,target,tests)
            results['v3_correct_candidate_present']+=found;results['v3_exact_restoration']+=restored
            results['v3_self_consistency_accepts_correct']+=self_status=='accepted_relative_to_evidence'
            results['v3_independent_accepts_correct']+=independent_status=='accepted_relative_to_evidence'
            # Reverse teacher direction while retaining tests bound to the known-correct model.
            _,legacy_bad,status_bad,reason_bad=run_case(p,correct,faulty,kind,target,tests)
            results['harmful_cases']+=1;local['harmful_cases']+=1
            results['legacy_accepts_harmful']+=legacy_bad=='accepted_relative_to_evidence';local['legacy_accepts_harmful']+=legacy_bad=='accepted_relative_to_evidence'
            results['v2_rejects_harmful']+=status_bad=='rejected';local['v2_rejects_harmful']+=status_bad=='rejected'
            results['v2_harmful_reason:'+reason_bad]+=1
            found_bad,_,self_bad,independent_bad=run_decision(p,correct,faulty,kind,target,tests)
            if name not in {'missing_row','extra_row'}:results['v3_supported_harmful_cases']+=1
            results['v3_harmful_candidate_present']+=found_bad
            results['v3_self_consistency_accepts_harmful']+=self_bad=='accepted_relative_to_evidence'
            results['v3_independent_rejects_harmful']+=independent_bad=='rejected'
    passed=(results['exact_restoration']==results['correct_cases']==results['v2_accepts_correct'] and
            results['v2_rejects_harmful']==results['harmful_cases'] and
            results['v3_correct_candidate_present']==results['v3_supported_correct_cases']==results['v3_exact_restoration'] and
            results['v3_independent_accepts_correct']==results['v3_supported_correct_cases'] and
            results['v3_independent_rejects_harmful']==results['v3_supported_harmful_cases'])
    report={'schema':'mechanism-v2-synthetic-validation-v1','status':'passed' if passed else 'failed',
            'scope':'controlled one-fault LP/MILP fixtures; no model or API calls',
            'aggregate':dict(results),'by_fault_type':{k:dict(v) for k,v in sorted(by_type.items())},
            'coverage_gaps':['unmatched_row_add_remove_pending_semantic_alignment','variable_add_remove','unit_correction','index_set_correction','nonlinear_or_conic_models'],
            'interpretation':('Candidate-derived tests enforce the selected direction but accept a wrong semantic selection. '
                              'Only independently authored truth tests rejected all reversed repairs in this controlled set.'),
            'claim_guard':'Passing synthetic fixtures establishes mechanism behavior only, not natural-language benchmark improvement.'}
    write_json(ROOT/'results/mechanism_v2_synthetic_validation.json',report)
    print(json.dumps({'status':report['status'],'correct_cases':results['correct_cases'],'harmful_cases':results['harmful_cases']}))
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
