"""Prepare harder text/table LP development candidates, not a locked test split."""
import itertools
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from llm4or.families import public_inventory,group_candidates
from llm4or.pipeline import write_json
from llm4or.schema import model,digest
from llm4or.solver import execute,matrices

OPTIBENCH='data/raw/yangzhch6__ReSocratic/data/OptiBench.json'
SPECS=[
    {'index':58,'family':'wilson_crop','variables':['corn','soybeans','wheat'],'unit':'acre',
     'objective':[300,320,240],'sense':'max','objective_unit':'USD',
     'rows':[([1,1,1],'le',200),([200,150,125],'le',35000),([35,40,30],'le',8000)],
     'bounds':[None]*3,'challenge':'Table-to-vector extraction; bushel profit must be multiplied by yield per acre.',
     'assumption':'Water per acre/week and labor per acre use their separately stated availability horizons.'},
    {'index':150,'family':'southfork_feed','variables':['oats','corn','soybeans','vitamin'],'unit':'pound',
     'objective':[0.5,1.2,0.6,2],'sense':'min','objective_unit':'USD',
     'rows':[([1,1,1,1],'ge',500),([-0.3,-0.3,0.7,-0.3],'ge',0),([-0.2,-0.2,-0.2,0.8],'ge',0),([-2,1,0,0],'le',0),([1,0,-1,0],'le',0)],
     'bounds':[300,400,200,100],'challenge':'Four ingredient quantities; percentages of endogenous total, availability bounds, and ratio constraints.',
     'assumption':'All weights are continuously divisible; composition percentages refer to total mix weight.'},
    {'index':226,'family':'western_pulp','variables':['grade1','grade2','grade3','grade4'],'unit':'ton',
     'objective':[150,110,90,50],'sense':'min','objective_unit':'USD',
     'rows':[([1,1,1,1],'eq',500),([8,6,5,3],'ge',3500),([9,7,5,4],'ge',2500),([8,5,6,5],'ge',3000)],
     'bounds':[None]*4,'challenge':'Quality requirements are weighted averages, not per-ingredient thresholds.',
     'assumption':'Order quantity is exactly 500 tons; quality is the problem-stated linear weighted average.'},
    {'index':583,'family':'birdie_fertilizer','variables':['fert1','fert2','fert3','fert4','fert5'],'unit':'fraction',
     'objective':[21.75,23.75,22,19.5,18.5],'sense':'min','objective_unit':'USD_per_100_pounds',
     'rows':[([1]*5,'eq',1),([.10,.08,.12,.10,.15],'ge',.10),([.10,.08,.12,.10,.15],'le',.105),
             ([.08,.11,.07,.10,.10],'ge',.08),([.08,.11,.07,.10,.10],'le',.085),
             ([.12,.15,.12,.10,.06],'ge',.12),([.12,.15,.12,.10,.06],'le',.125)],
     'bounds':[1]*5,'challenge':'Five fractions; three two-sided composition intervals; percent versus percentage-point conversion.',
     'assumption':'The text explicitly translates the 0.5% margin into percentage-point intervals; prices refer to 100 lb of mix.'},
]
REJECTIONS={
    4:'Binary facility opening and a duplicated City 5 row label; not a continuous LP despite linear-table tag.',
    43:'Integer staff counts; do not silently relax.',
    52:'Fixed line setup costs and integer workers require discrete activation decisions.',
    75:'Fixed machinery rentals require discrete activation despite the request saying LP.',
    140:'Decreasing incremental purchase prices need ordered tiers/nonconvex cost treatment; independent cheap tier variables would be wrong.',
    251:'One-pound box counts and minimum box counts need an explicit integrality/relaxation decision.',
    508:'Prose demand maxima (6000/7000) conflict with the table column labeled demand (5000/6000, matching plant capacities); reference review required.',
    565:'Only nutritional lower bounds give an unbounded feasible set; nutrient/food requirement wording also needs clarification.',
}


def reference(spec):
    ids=spec['variables']
    return model({'schema':'lp-v1','variables':[{'id':v,'meaning':v,'unit':spec['unit'],'domain':'continuous','lower':0,'upper':b} for v,b in zip(ids,spec['bounds'])],
                  'constraints':[{'id':f'r{i+1}','coefficients':dict(zip(ids,a)),'sense':s,'rhs':b} for i,(a,s,b) in enumerate(spec['rows'])],
                  'objective':{'coefficients':dict(zip(ids,spec['objective'])),'sense':spec['sense'],'unit':spec['objective_unit'],'offset':0}})


def vertex_optimum(m):
    # Independent active-set enumeration, not SciPy/HiGHS optimization. Shares
    # declared coefficients/row conversion, so it cannot audit text transcription.
    import numpy as np
    order,rows,rhs,_=matrices(m)
    a,b=np.array(rows),np.array(rhs);n=len(order)
    c=np.array([m['objective']['coefficients'][v] for v in order])
    values=[]
    for inds in itertools.combinations(range(len(rows)),n):
        aa=a[list(inds)]
        if np.linalg.matrix_rank(aa)<n: continue
        x=np.linalg.solve(aa,b[list(inds)])
        if np.all(a@x<=b+1e-7): values.append(float(c@x))
    if not values: raise ValueError('no feasible vertex')
    return min(values) if m['objective']['sense']=='min' else max(values)


def main():
    manifest=json.loads((ROOT/'data/manifests/source_manifest.json').read_text())
    records=public_inventory(ROOT,manifest)
    groups,membership,edges=group_candidates(records)
    selected={s['index']:s for s in SPECS}
    by_index={r['source_row_zero_based']:r for r in records if r['source_path']==OPTIBENCH}
    known_dev={r['id'] for r in records if r['source_path'].endswith('nl4opt__nl4opt-competition/generation_data/dev.jsonl')}
    # Candidate review itself is development exposure. Quarantine all identified
    # variants; never mark the rest as automatically safe for a future test.
    reviewed={by_index[i]['id'] for i in set(selected)|set(REJECTIONS)}
    quarantine_groups={membership[i] for i in known_dev|reviewed}
    public=[];entries=[]
    for index,spec in selected.items():
        source=by_index[index];pid=f'opti_dev_{index:03}'
        m=reference(spec);solved=execute({'op':'solve','model':m});v=vertex_optimum(m)
        assert solved['status']=='optimal' and abs(solved['objective']-v)<=1e-6*max(1,abs(v)),pid
        contained=execute({'op':'compare','left':m,'right':m})
        assert contained.get('left_to_right',{}).get('status')=='contained_within_tolerance',pid
        p={'id':pid,'text':source['text']};public.append(p)
        audit={'status':'assistant_transcribed_reference_not_expert_certified','source':{k:v for k,v in source.items() if k!='text'},
               'reference':m,'reference_hash':digest(m),'highs':solved,'vertex_enumeration_objective':v,
               'assumptions':[spec['assumption']],'upstream_answer_used':False,'source_model_code_executed':False}
        write_json(ROOT/'data/next_development/evaluator'/f'{pid}.json',audit)
        entries.append({'id':pid,'source_public_id':source['id'],'source_row_zero_based':index,
                        'public_hash':digest(p),'named_problem_group':spec['family'],
                        'candidate_component':membership[source['id']],'variables':len(m['variables']),
                        'challenge':spec['challenge'],'model_difficulty_measured':False,
                        'reference_numerically_cross_checked':True,'approved_for_api':False,'exclude_from_future_test':True})
    out=ROOT/'data/next_development';(out/'public').mkdir(parents=True,exist_ok=True)
    (out/'public/problems.jsonl').write_text(''.join(json.dumps(p,ensure_ascii=False)+'\n' for p in public))
    lightweight=[{**{k:v for k,v in r.items() if k!='text'},'candidate_component':membership[r['id']],
                  'split_status':'quarantine_development' if membership[r['id']] in quarantine_groups else 'unsplit_requires_semantic_family_review'} for r in records]
    quarantine_count=sum(r['split_status']=='quarantine_development' for r in lightweight)
    report={'status':'candidate_family_audit_not_locked_split','public_records':len(records),'source_files':len({r['source_path'] for r in records}),
            'components':groups,'edges':edges,'records':lightweight,'lexical_threshold':.86,
            'quarantined_records':quarantine_count,'quarantined_components':len(quarantine_groups),
            'formal_test_split_created':False,'labels_used_for_grouping':False,
            'limitations':['Lexical and named-entity edges can overmerge; non-edges cannot prove family independence.',
                           'All corpus grouping uses public problem text, never correctness labels or model scores.',
                           'No inferential gate may use these provisional components as certified iid families.']}
    write_json(out/'family_audit.json',report)
    write_json(out/'manifest.json',{'status':'offline_prepared_not_authorized_for_api','entries':entries,
                                  'screened_out':[{'source_row_zero_based':i,'reason':reason,'component':membership[by_index[i]['id']]} for i,reason in REJECTIONS.items()],
                                  'family_audit':'data/next_development/family_audit.json',
                                  'not_four_proven_independent_families':True,'actual_api_requests':0})
    print(json.dumps({'public_records':len(records),'candidate_components':len(groups),'edges':len(edges),
                      'quarantined_records':quarantine_count,'prepared_candidates':len(public),'screened_out':len(REJECTIONS),
                      'actual_api_requests':0}))


if __name__=='__main__':main()
