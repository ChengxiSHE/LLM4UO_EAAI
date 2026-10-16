"""Exercise all six methods with real numerical workers and fixed responses."""
from copy import deepcopy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_inputs import payload_sha256
from llm4or.formal_gateway import FormalGateway
from llm4or.formal_runtime import run_program
from llm4or.workflow import seed_programs
from llm4or.pipeline import write_json
from llm4or.schema import digest
from scripts.verify_milp_pipeline import fixture


def main():
    plan=json.loads((ROOT/'experiments/full_run_plan.json').read_text());programs=seed_programs()
    cases=[('integer_tightening',fixture('continuous'),fixture(),'domain','x',0,True),
           ('divisible_relaxation',fixture(),fixture('continuous'),'domain','x',.5,True),
           ('missing_row',fixture(),fixture(restricted=True),'row','cap',0,True),
           ('extra_row',fixture(restricted=True),fixture(),'row','cap',1,True),
           ('objective_direction',fixture(),fixture(sense='min'),'objective','objective',0,True),
           ('out_of_scope_rollback',fixture('continuous'),fixture(),'domain','x',0,False)]
    table={};results=[]
    for name,a,b,kind,target,positive,accepted in cases:
        p={'id':'synthetic_'+name,'profile':'description_parameters_v1','text':'Synthetic protocol fixture with a specified alternate interpretation.','parameters':[],'instances':[]}
        table[p['id']]=(p,a,b,kind,target,positive,accepted)
    def reply(payload,body):
        p,a,b,kind,target,positive,accepted=table[payload['problem']['id']];ctx=payload['context']
        if 'teacher_packet' in ctx:
            value=deepcopy(b)
            if not accepted:value['variables'][0]['upper']=3
        elif 'evidence' in ctx:
            value={'schema':'teacher-milp-v1','status':'repair','input_sha256':payload_sha256(p),
                   'model_hashes':{'initial':digest(ctx['initial']),'teacher':digest(b)},
                   'quote':{'field':'text','text':p['text'],'start':0,'end':len(p['text'])},
                   'interpretation':'Synthetic fixture, not a benchmark result.','edits':[{'kind':kind,'target':target}],
                   'positive_examples':[{'x':positive}]}
        elif 'interface' in ctx:value=b
        elif 'initial' in ctx:value=ctx['initial']
        else:value=a
        return {'text':json.dumps(value),'prompt_tokens':100,'completion_tokens':100,'total_tokens':200,
                'finish_reason':'stop','usage_source':'simulated'}
    directory=ROOT/'results'/('offline_formal_stack_'+digest(plan)[:12])
    gateway=FormalGateway(ROOT,plan,offline=True,directory=directory,responder=reply)
    for p,a,b,kind,target,positive,accepted in table.values():
        for method,program in programs.items():
            scope='verification:'+p['id']+':'+method
            out=run_program(p,program,gateway,scope,17,plan['methods'][method]['max_calls'],65536)
            expected=b if accepted and method in {'A','SimpleAB','Full'} else a
            passed=out['final_model']==expected and not out['errors']
            if method=='A':
                before=gateway.summary()['physical_attempts']
                again=run_program(p,program,gateway,scope,17,4,65536)
                passed=passed and again['final_model']==expected and gateway.summary()['physical_attempts']==before
            write_json(directory/(digest(scope)+'.json'),out)
            results.append({'problem':p['id'],'method':method,'passed':passed,'errors':out['errors'],
                            'logical_usage':out['usage'],'trace':str(directory/(digest(scope)+'.json'))})
    report={'status':'passed' if all(r['passed'] for r in results) else 'failed','plan_sha256':digest(plan),
            'total':len(results),'passed':sum(r['passed'] for r in results),'cases':results,'ledger':gateway.summary(),
            'scope':'synthetic fixed responses and real trusted numerical workers; not LLM or benchmark performance'}
    write_json(ROOT/'results/formal_stack_verification.json',report)
    print(json.dumps({k:report[k] for k in ['status','total','passed','ledger']}))
    if report['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
