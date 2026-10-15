"""Input-quoted, executable-evidence MILP repair. No reference imports/access."""
from copy import deepcopy
import math
from .benchmark_inputs import payload_sha256, validate_public_input
from .milp_schema import model, business_interface, effective_bounds
from .milp_solver import execute, check_point, FEAS_TOL, INTEGER_TOL
from .schema import Invalid, digest, keys, string


def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in {'wall_seconds','peak_rss_bytes_sampled'}}
    if isinstance(value,list):return [stable(v) for v in value]
    return value


def _row_ok(row, point):
    if row is None:return True
    value=math.fsum(a*point[k] for k,a in row['coefficients'].items())-row['rhs']
    scale=max([1,abs(row['rhs'])]+[abs(a) for a in row['coefficients'].values()])
    if row['sense']=='ge':value=-value
    if row['sense']=='eq':value=abs(value)
    return value/scale<=FEAS_TOL


def _domain_ok(v,x):
    lo,hi=effective_bounds(v)
    return ((lo is None or x>=lo-FEAS_TOL*max(1,abs(lo))) and (hi is None or x<=hi+FEAS_TOL*max(1,abs(hi)))
            and (v['domain']=='continuous' or abs(x-round(x))<=INTEGER_TOL))


def _quote(problem,q):
    keys(q,{'field','text','start','end'})
    source=problem['text'] if q['field']=='text' else None
    for p in problem['parameters']:
        if q['field']=='parameters.'+p['symbol']+'.definition':source=p['definition']
    if source is None or type(q['start']) is not int or type(q['end']) is not int or not 0<=q['start']<q['end']<=len(source) or source[q['start']:q['end']]!=q['text']:
        raise Invalid('quote_provenance_mismatch')


def bind_quote(problem, q):
    """Bind quoted text to one unique public-input field and compute offsets."""
    p = validate_public_input(problem); keys(q, {'field','text','start','end'})
    if not isinstance(q['text'], str) or not q['text']:
        raise Invalid('quote_provenance_mismatch')
    sources = {'text': p['text']}
    sources.update({'parameters.'+item['symbol']+'.definition': item['definition'] for item in p['parameters']})
    matches = []
    for field, source in sources.items():
        start = 0
        while True:
            index = source.find(q['text'], start)
            if index < 0: break
            matches.append((field,index)); start=index+1
    if len(matches) != 1:
        raise Invalid('quote_not_uniquely_bindable')
    field,start = matches[0]
    bound = {'field':field,'text':q['text'],'start':start,'end':start+len(q['text'])}
    _quote(p,bound)
    return bound


def compile_record_v2(raw,problem,initial,teacher,evidence):
    """Compile v2 feedback after deterministic provenance binding."""
    revised=deepcopy(raw);revised['quote']=bind_quote(problem,revised['quote'])
    return compile_record(revised,problem,initial,teacher,evidence)


def _proposal_from_edits(initial,teacher,edits):
    expected=deepcopy(initial);teacher_rows={r['id']:r for r in teacher['constraints']};current={r['id']:r for r in expected['constraints']}
    teacher_vars={v['id']:v for v in teacher['variables']};target_rows=[];target_domains=[];needs_reverse=False
    for edit in edits:
        kind,target=edit['kind'],edit['target']
        if kind=='row':
            if target in teacher_rows:current[target]=deepcopy(teacher_rows[target]);target_rows.append(teacher_rows[target])
            else:current.pop(target,None);needs_reverse=True
        elif kind=='domain':
            for v in expected['variables']:
                if v['id']==target:
                    needs_reverse |= v['domain']!='continuous' and teacher_vars[target]['domain']=='continuous'
                    v['domain']=teacher_vars[target]['domain'];target_domains.append(target)
        else:expected['objective']=deepcopy(teacher['objective'])
    expected['constraints']=list(current.values())
    return expected,teacher_rows,teacher_vars,target_rows,target_domains,needs_reverse


def apply_teacher_edits(problem,initial,teacher,packet):
    """Apply an already compiled packet without another fallible LLM copy step."""
    initial=model(initial);teacher=model(teacher)
    if packet.get('status')!='repair' or packet.get('packet_sha256')!=digest({k:v for k,v in packet.items() if k!='packet_sha256'}):
        raise Invalid('packet_modified')
    if (packet['initial_sha256'],packet['teacher_sha256'],packet['input_sha256'])!=(digest(initial),digest(teacher),payload_sha256(validate_public_input(problem))):
        raise Invalid('stale_evidence')
    return model(_proposal_from_edits(initial,teacher,packet['edits'])[0])


def _clause_tests(model_value,suite):
    m=model(model_value);keys(suite,{'schema','input_sha256','tests'})
    if suite['schema']!='clause-tests-v1' or not isinstance(suite['tests'],list) or not 1<=len(suite['tests'])<=32:
        raise Invalid('clause_test_schema')
    outcomes=[]
    rows={r['id']:r for r in m['constraints']};variables={v['id']:v for v in m['variables']}
    for test in suite['tests']:
        if not isinstance(test,dict) or test.get('kind') not in {'feasibility','preference','row','domain','objective'}:raise Invalid('clause_test_kind')
        if test['kind']=='feasibility':
            keys(test,{'kind','point','expected_feasible'})
            if type(test['expected_feasible']) is not bool:raise Invalid('clause_test_expected')
            passed=check_point(m,test['point'])['feasible']==test['expected_feasible']
        elif test['kind']=='row':
            keys(test,{'kind','target','point','expected_satisfied'})
            if type(test['expected_satisfied']) is not bool:raise Invalid('clause_test_expected')
            passed=_row_ok(rows.get(test['target']),test['point'])==test['expected_satisfied']
        elif test['kind']=='domain':
            keys(test,{'kind','target','value','expected_satisfied'})
            if type(test['expected_satisfied']) is not bool or test['target'] not in variables:raise Invalid('clause_test_expected')
            passed=_domain_ok(variables[test['target']],test['value'])==test['expected_satisfied']
        elif test['kind']=='objective':
            keys(test,{'kind','better','worse'});objective=m['objective'];keys(test['better'],objective['coefficients']);keys(test['worse'],objective['coefficients'])
            sign=1 if objective['sense']=='max' else -1
            better=math.fsum(v*test['better'][k] for k,v in objective['coefficients'].items())
            worse=math.fsum(v*test['worse'][k] for k,v in objective['coefficients'].items())
            scale=max(1,abs(better),abs(worse));passed=sign*(better-worse)>FEAS_TOL*scale
        else:
            keys(test,{'kind','better','worse'})
            for point in (test['better'],test['worse']):
                if not check_point(m,point)['feasible']:raise Invalid('clause_preference_point_infeasible')
            objective=m['objective'];sign=1 if objective['sense']=='max' else -1
            better=objective['offset']+math.fsum(v*test['better'][k] for k,v in objective['coefficients'].items())
            worse=objective['offset']+math.fsum(v*test['worse'][k] for k,v in objective['coefficients'].items())
            scale=max(1,abs(better),abs(worse));passed=sign*(better-worse)>FEAS_TOL*scale
        outcomes.append(passed)
    return outcomes


def repair_gate_v2(problem,initial,teacher,proposal,packet,clause_tests,solver=execute):
    """Require a repair to improve bound clause tests as well as numerical evidence."""
    p=validate_public_input(problem)
    if clause_tests.get('input_sha256')!=payload_sha256(p):
        return {'status':'rejected','reason':'stale_clause_tests','retained_model':model(initial)}
    result=repair_gate(p,initial,teacher,proposal,packet,solver=solver)
    if result['status']!='accepted_relative_to_evidence':return result
    try:
        before=_clause_tests(initial,clause_tests);after=_clause_tests(proposal,clause_tests)
    except (ValueError,RuntimeError,KeyError,TypeError) as exc:
        return {'status':'rejected','reason':str(exc) if isinstance(exc,Invalid) else type(exc).__name__,
                'retained_model':model(initial)}
    if not all(after):
        return {'status':'rejected','reason':'clause_test_failed','retained_model':model(initial),
                'clause_tests_passed':sum(after),'clause_tests_total':len(after)}
    if all(before):
        return {'status':'rejected','reason':'no_demonstrated_clause_improvement','retained_model':model(initial),
                'clause_tests_passed':len(after),'clause_tests_total':len(after)}
    return {**result,'clause_tests_passed':len(after),'clause_tests_total':len(after),
            'clause_test_warning':'Validity depends on clause-test fidelity to the public input.'}


def compile_record(raw,problem,initial,teacher,evidence):
    p=validate_public_input(problem); initial=model(initial); teacher=model(teacher)
    keys(raw,{'schema','status','input_sha256','model_hashes','quote','interpretation','edits','positive_examples'})
    if raw['schema']!='teacher-milp-v1' or raw['status'] not in ('repair','no_witness','unresolved'):raise Invalid('teacher_schema_status')
    if raw['input_sha256']!=payload_sha256(p) or raw['model_hashes']!={'initial':digest(initial),'teacher':digest(teacher)}:
        raise Invalid('stale_teacher_input_or_models')
    _quote(p,raw['quote']);string(raw['interpretation'],2000)
    if business_interface(initial)!=business_interface(teacher) or initial['objective']['unit']!=teacher['objective']['unit']:
        raise Invalid('unaligned_teacher_interface')
    if not isinstance(raw['edits'],list) or len(raw['edits'])>4 or not isinstance(raw['positive_examples'],list) or len(raw['positive_examples'])>8:
        raise Invalid('teacher_scope_size')
    if raw['status']!='repair' and (raw['edits'] or raw['positive_examples']):raise Invalid('nonrepair_edits')
    points=[]
    for direction,source,target in [('left_to_right',initial,teacher),('right_to_left',teacher,initial)]:
        w=evidence.get(direction,{})
        if w.get('status')=='witness':
            point=w.get('point')
            if not check_point(source,point)['feasible'] or check_point(target,point)['feasible']:raise Invalid('nonreplayable_witness')
            points.append(point)
    pref=evidence.get('preference',{})
    reversal=False
    if pref.get('status')=='strict_reversal':
        x,y=pref['x'],pref['y']
        if not all(check_point(m,z)['feasible'] for m in (initial,teacher) for z in (x,y)):raise Invalid('preference_points_invalid')
        gains=[]
        for m,a,b in ((initial,x,y),(teacher,y,x)):
            obj=m['objective'];sign=1 if obj['sense']=='max' else -1
            scale=max([1]+[abs(v) for v in obj['coefficients'].values()])
            gains.append(sign*math.fsum(v*(a[k]-b[k]) for k,v in obj['coefficients'].items())/scale)
        reversal=min(gains)>FEAS_TOL
        if not reversal:raise Invalid('nonreplayable_preference')
    if raw['status']!='repair':
        return dict(status='unresolved',reason='no_repair_requested',warning='agreement_is_not_truth')
    if not raw['edits'] or not raw['positive_examples']:raise Invalid('repair_requires_scope_and_protected_points')
    edits=[]; seen=set(); av={v['id']:v for v in initial['variables']}; bv={v['id']:v for v in teacher['variables']}
    ar={r['id']:r for r in initial['constraints']}; br={r['id']:r for r in teacher['constraints']}
    for edit in raw['edits']:
        keys(edit,{'kind','target'})
        kind,target=edit['kind'],edit['target']
        if not isinstance(kind,str) or not isinstance(target,str) or (kind,target) in seen:raise Invalid('duplicate_or_invalid_edit')
        seen.add((kind,target)); supported=False
        if kind=='row' and target in ar.keys()|br.keys():
            if ar.get(target)!=br.get(target):supported=any(_row_ok(ar.get(target),w)!=_row_ok(br.get(target),w) for w in points)
        elif kind=='domain' and target in av:
            if av[target]['domain']!=bv[target]['domain'] and all(av[target][k]==bv[target][k] for k in ('lower','upper')):
                supported=any(_domain_ok(av[target],w[target])!=_domain_ok(bv[target],w[target]) for w in points)
        elif kind=='objective' and target=='objective':supported=reversal
        if not supported:raise Invalid('edit_lacks_replayed_target_evidence')
        edits.append(deepcopy(edit))
    for point in raw['positive_examples']:
        if not check_point(teacher,point)['feasible']:raise Invalid('positive_example_not_teacher_feasible')
    packet=dict(status='repair',protocol='teacher-milp-v1',input_sha256=payload_sha256(p),
                initial_sha256=digest(initial),teacher_sha256=digest(teacher),evidence_sha256=digest(stable(evidence)),
                quote=deepcopy(raw['quote']),edits=edits,positive_examples=deepcopy(raw['positive_examples']),
                verified_difference_points=points,interpretation_used_as_verified_fact=False,
                warning='Exact quote and formal difference do not certify the teacher interpretation.')
    packet['packet_sha256']=digest(packet)
    return packet


def repair_gate(problem,initial,teacher,proposal,packet,solver=execute):
    initial=model(initial);teacher=model(teacher)
    def reject(reason,**details):return dict(status='rejected',reason=reason,retained_model=initial,**details)
    if packet.get('status')!='repair':return reject('teacher_unresolved')
    if packet.get('packet_sha256')!=digest({k:v for k,v in packet.items() if k!='packet_sha256'}):return reject('packet_modified')
    if (packet['initial_sha256'],packet['teacher_sha256'],packet['input_sha256'])!=(digest(initial),digest(teacher),payload_sha256(validate_public_input(problem))):return reject('stale_evidence')
    try:proposal=model(proposal)
    except Invalid:return reject('invalid_proposal')
    if digest(proposal)==digest(initial):return reject('no_change')
    expected,teacher_rows,teacher_vars,target_rows,target_domains,needs_reverse=_proposal_from_edits(initial,teacher,packet['edits'])
    def normalized(m):
        m=deepcopy(m);m['variables']=sorted(m['variables'],key=lambda v:v['id']);m['constraints']=sorted(m['constraints'],key=lambda r:r['id']);return m
    if normalized(expected)!=normalized(proposal):return reject('write_scope_or_teacher_fragment_violation')
    for point in packet['positive_examples']:
        if not check_point(proposal,point)['feasible']:return reject('protected_example_regression')
    state=solver({'op':'solve','model':proposal})
    if state['status']!='optimal':return reject('proposal_not_certified_optimal',solve=state)
    # Re-search all selected teacher clauses/domains under the complete proposal,
    # without forcing unrelated teacher rows into the accepted formulation.
    target=deepcopy(proposal);target['constraints']=target_rows
    for v in target['variables']:
        v['lower']=None;v['upper']=None
        v['domain']=teacher_vars[v['id']]['domain'] if v['id'] in target_domains else 'continuous'
    check=solver({'op':'compare','left':proposal,'right':target})
    if check.get('left_to_right',{}).get('status')!='contained_within_tolerance':return reject('target_recheck_not_certified',check=check)
    if needs_reverse:
        reverse=solver({'op':'compare','left':teacher,'right':proposal})
        if reverse.get('left_to_right',{}).get('status')!='contained_within_tolerance':return reject('relaxation_recheck_not_certified',check=reverse)
    return dict(status='accepted_relative_to_evidence',retained_model=proposal,edits=packet['edits'],target_check=check,
                solve=state,warning='Scoped numerical checks do not establish natural-language truth.')
