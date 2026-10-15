"""Six synthetic fixed-response end-to-end traces, no model API transport."""
from copy import deepcopy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_inputs import payload_sha256
from llm4or.gateway import Gateway,Limits,MockReply
from llm4or.milp_pipeline import run_milp_problem
from llm4or.schema import digest
from llm4or.pipeline import write_json


def fixture(domain='integer',sense='max',restricted=False):
    return dict(schema='milp-v1',variables=[dict(id='x',meaning='synthetic decision',unit='items',domain=domain,lower=0,upper=2)],
                constraints=[dict(id='cap',coefficients={'x':1},sense='le',rhs=0)] if restricted else [],
                objective=dict(coefficients={'x':1},sense=sense,unit='items',offset=0))


def main():
    cases=[('integer_tightening',fixture('continuous'),fixture(),'domain','x',0,True),
           ('divisible_relaxation',fixture(),fixture('continuous'),'domain','x',.5,True),
           ('missing_row',fixture(),fixture(restricted=True),'row','cap',0,True),
           ('extra_row',fixture(restricted=True),fixture(),'row','cap',1,True),
           ('objective_direction',fixture(),fixture(sense='min'),'objective','objective',0,True),
           ('out_of_scope_rollback',fixture('continuous'),fixture(),'domain','x',0,False)]
    records=[]
    for name,a,b,kind,target,positive,accept in cases:
        p=dict(id='synthetic_'+name,profile='description_parameters_v1',text='Synthetic protocol check with a deliberately specified alternate formulation.',parameters=[],instances=[])
        raw=dict(schema='teacher-milp-v1',status='repair',input_sha256=payload_sha256(p),model_hashes=dict(initial=digest(a),teacher=digest(b)),
                 quote=dict(field='text',text=p['text'],start=0,end=len(p['text'])),interpretation='Synthetic declared interpretation; not a benchmark finding.',
                 edits=[dict(kind=kind,target=target)],positive_examples=[{'x':positive}])
        proposal=deepcopy(b)
        if not accept:proposal['variables'][0]['upper']=3
        replies={phase:MockReply(text=json.dumps(value)) for phase,value in {'initial':a,'baseline_repair':a,'teacher_model':b,'teacher_feedback':raw,'semantic_repair':proposal}.items()}
        directory=ROOT/'results/offline_milp_pipeline_v1_machine_contracts'/name
        gateway=Gateway(directory,Limits(requests=5,per_problem=5,input_bytes=200000,output_bytes=200000),manifest={'kind':'synthetic_fixed_response','version':'v1'})
        result=run_milp_problem(p,gateway,replies)
        expected=b if accept else a
        passed=result.get('semantic_final')==expected and not result['errors'] and (result.get('repair_gate',{}).get('status')=='accepted_relative_to_evidence')==accept
        records.append(dict(id=p['id'],passed=passed,expected_accept=accept,actual_gate=result.get('repair_gate',{}).get('status'),trace=str(directory.relative_to(ROOT)/(p['id']+'.inference.json'))))
    report=dict(status='passed' if all(r['passed'] for r in records) else 'failed',cases=records,passed=sum(r['passed'] for r in records),total=len(records),
                scope='synthetic_fixed_responses_not_LLM_or_benchmark_performance',actual_model_api_calls=0,cross_problem_evolution=False)
    write_json(ROOT/'results/milp_pipeline_verification.json',report)
    print(json.dumps({k:report[k] for k in ('status','passed','total','actual_model_api_calls')}))
    if report['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
