"""Bounded semantic choice over controller-generated executable differences.

The model chooses among numbered differences and quotes public input. Hashes,
offsets, edit scopes, and clause tests are generated and checked locally.
"""
from copy import deepcopy

from .benchmark_inputs import payload_sha256, validate_public_input
from .contracts import obj, validate
from .milp_feedback import _domain_ok, _row_ok, bind_quote, stable
from .milp_schema import business_interface, model
from .schema import Invalid, digest, keys, string

MAX_CANDIDATES = 4
MAX_DECISIONS = 4


def _difference_points(evidence):
    points=[]
    for direction in ('left_to_right','right_to_left'):
        result=evidence.get(direction,{})
        if result.get('status')=='witness':points.append(deepcopy(result['point']))
    return points


def build_catalog(problem, initial, teacher, evidence):
    """Enumerate only edit targets separated by replayable solver evidence."""
    p=validate_public_input(problem);a=model(initial);b=model(teacher)
    if business_interface(a)!=business_interface(b) or a['objective']['unit']!=b['objective']['unit']:
        raise Invalid('unaligned_teacher_interface')
    points=_difference_points(evidence);candidates=[]
    ar={r['id']:r for r in a['constraints']};br={r['id']:r for r in b['constraints']}
    # Row names are model-generated, not stable semantic identifiers. Until a
    # separate row-alignment certificate exists, never interpret an unmatched
    # name as evidence that the public problem requires adding/deleting a row.
    for target in sorted(ar.keys()&br.keys()):
        left,right=ar.get(target),br.get(target)
        tests=[]
        for point in points:
            before,after=_row_ok(left,point),_row_ok(right,point)
            if before!=after:
                variables=set((left or {'coefficients':{}})['coefficients'])|set((right or {'coefficients':{}})['coefficients'])
                tests.append({'kind':'row','target':target,'point':{k:point[k] for k in sorted(variables)},
                              'expected_satisfied':after})
        if left!=right and tests:
            candidates.append({'id':'candidate_'+str(len(candidates)),'edit':{'kind':'row','target':target},
                'initial_fragment':deepcopy(left),'teacher_fragment':deepcopy(right),'tests':tests[:4]})
    av={v['id']:v for v in a['variables']};bv={v['id']:v for v in b['variables']}
    for target in sorted(av):
        left,right=av[target],bv[target]
        tests=[]
        if left['domain']!=right['domain'] and all(left[k]==right[k] for k in ('lower','upper')):
            for point in points:
                before,after=_domain_ok(left,point[target]),_domain_ok(right,point[target])
                if before!=after:
                    tests.append({'kind':'domain','target':target,'value':point[target],'expected_satisfied':after})
        if tests:
            candidates.append({'id':'candidate_'+str(len(candidates)),'edit':{'kind':'domain','target':target},
                'initial_fragment':{'domain':left['domain']},'teacher_fragment':{'domain':right['domain']},'tests':tests[:4]})
    pref=evidence.get('preference',{})
    if a['objective']!=b['objective'] and pref.get('status')=='strict_reversal':
        candidates.append({'id':'candidate_'+str(len(candidates)),'edit':{'kind':'objective','target':'objective'},
            'initial_fragment':deepcopy(a['objective']),'teacher_fragment':deepcopy(b['objective']),
            'tests':[{'kind':'objective','better':{k:pref['y'][k] for k in sorted(b['objective']['coefficients'])},
                      'worse':{k:pref['x'][k] for k in sorted(b['objective']['coefficients'])}}]})
    eligible_candidates=len(candidates);candidates=candidates[:MAX_CANDIDATES]
    catalog={'schema':'semantic-catalog-v1','input_sha256':payload_sha256(p),'initial_sha256':digest(a),
             'teacher_sha256':digest(b),'evidence_sha256':digest(stable(evidence)),'candidates':candidates}
    catalog['unmatched_rows_omitted']=len(ar.keys()^br.keys())
    catalog['eligible_candidate_count']=eligible_candidates
    catalog['candidates_truncated']=max(0,eligible_candidates-len(candidates))
    catalog['catalog_sha256']=digest(catalog)
    return catalog


def decision_schema(catalog):
    identifiers=[item['id'] for item in catalog['candidates']]
    choice={'type':'string','enum':identifiers or ['no_candidate']}
    text={'type':'string','minLength':1,'maxLength':2000}
    schema=obj({'schema':{'const':'semantic-decision-v1'},'status':{'enum':['reviewed','unresolved']},
        'decisions':{'type':'array','maxItems':MAX_DECISIONS,'items':obj({
            'candidate_id':choice,'verdict':{'enum':['teacher','initial','unclear']},
            'quote_text':{'type':'string','minLength':1,'maxLength':20000},'interpretation':text})}})
    schema['$schema']='https://json-schema.org/draft/2020-12/schema'
    return schema


def validate_decision(raw,catalog):
    return validate(raw,decision_schema(catalog))


def compile_decision(raw,problem,initial,teacher,evidence,catalog):
    """Compile selected teacher-side clauses into a hashed edit packet and tests."""
    p=validate_public_input(problem);a=model(initial);b=model(teacher)
    expected=build_catalog(p,a,b,evidence)
    if catalog!=expected:
        raise Invalid('stale_semantic_catalog')
    raw=validate_decision(raw,expected)
    if raw['status']=='unresolved':
        if raw['decisions']:raise Invalid('unresolved_with_decisions')
        return {'packet':{'status':'unresolved','reason':'semantic_abstention'},'clause_tests':None}
    if not raw['decisions']:raise Invalid('repair_without_decisions')
    by_id={item['id']:item for item in expected['candidates']};selected=[];seen=set();quotes=[]
    for decision in raw['decisions']:
        cid=decision['candidate_id']
        if cid in seen:raise Invalid('duplicate_semantic_decision')
        seen.add(cid);string(decision['interpretation'],2000)
        bound=bind_quote(p,{'field':'','text':decision['quote_text'],'start':0,'end':1})
        quotes.append({'candidate_id':cid,'verdict':decision['verdict'],'quote':bound})
        if decision['verdict']=='teacher':selected.append(by_id[cid])
    if seen!=set(by_id):raise Invalid('incomplete_semantic_review')
    if not selected:
        return {'packet':{'status':'unresolved','reason':'no_teacher_side_clause_selected','semantic_quotes':quotes},
                'clause_tests':None}
    packet={'status':'repair','protocol':'semantic-decision-v1','input_sha256':payload_sha256(p),
            'initial_sha256':digest(a),'teacher_sha256':digest(b),'evidence_sha256':digest(stable(evidence)),
            'catalog_sha256':expected['catalog_sha256'],'edits':[deepcopy(x['edit']) for x in selected],
            'positive_examples':[],'semantic_quotes':quotes,
            'warning':'Quoted semantic choices remain model judgments; executable tests only enforce the chosen direction.'}
    packet['packet_sha256']=digest(packet)
    suite={'schema':'clause-tests-v1','input_sha256':payload_sha256(p),
           'tests':[deepcopy(test) for item in selected for test in item['tests']]}
    return {'packet':packet,'clause_tests':suite}


def compile_consensus(first,second,problem,initial,teacher,evidence,catalog):
    """Accept an edit only when two separately prompted reviews choose teacher."""
    first=validate_decision(first,catalog);second=validate_decision(second,catalog)
    if first['status']=='unresolved' or second['status']=='unresolved':
        return {'packet':{'status':'unresolved','reason':'semantic_review_abstention'},'clause_tests':None}
    by_first={d['candidate_id']:d for d in first['decisions']};by_second={d['candidate_id']:d for d in second['decisions']}
    if set(by_first)!=set(by_second) or set(by_first)!={x['id'] for x in catalog['candidates']}:
        raise Invalid('incomplete_semantic_review')
    agreed=[]
    for cid in sorted(by_first):
        a,b=by_first[cid],by_second[cid]
        if a['verdict']=='teacher' and b['verdict']=='teacher':
            agreed.append({'candidate_id':cid,'verdict':'teacher','quote_text':a['quote_text'],
                           'interpretation':a['interpretation']})
    if not agreed:return {'packet':{'status':'unresolved','reason':'no_unanimous_teacher_clause'},'clause_tests':None}
    # Fill nonaccepted candidates so the same complete-review invariant applies.
    included={d['candidate_id'] for d in agreed}
    for cid in sorted(by_first):
        if cid not in included:
            agreed.append({'candidate_id':cid,'verdict':'unclear','quote_text':by_first[cid]['quote_text'],
                           'interpretation':by_first[cid]['interpretation']})
    compiled=compile_decision({'schema':'semantic-decision-v1','status':'reviewed','decisions':agreed},
                              problem,initial,teacher,evidence,catalog)
    packet=compiled['packet'];packet['consensus_reviews']=2
    packet['second_review_quotes']=[{'candidate_id':d['candidate_id'],'verdict':d['verdict'],
        'quote':bind_quote(validate_public_input(problem),{'field':'','text':d['quote_text'],'start':0,'end':1})} for d in second['decisions']]
    packet['packet_sha256']=digest({k:v for k,v in packet.items() if k!='packet_sha256'})
    return {'packet':packet,'clause_tests':compiled['clause_tests']}
