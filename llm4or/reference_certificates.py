"""Evaluator-only arithmetic certificates, separate from the primal solver."""
import itertools
import math
from .milp_solver import execute


def inequalities(m):
    result=[]
    for r in m['constraints']:
        if r['sense'] in {'le','eq'}: result.append((r['coefficients'],r['rhs']))
        if r['sense'] in {'ge','eq'}: result.append(({k:-a for k,a in r['coefficients'].items()},-r['rhs']))
    for v in m['variables']:
        lo,hi=v['lower'],v['upper']
        if v['domain']=='binary': lo=max(0,lo) if lo is not None else 0; hi=min(1,hi) if hi is not None else 1
        if lo is not None: result.append(({v['id']:-1},-lo))
        if hi is not None: result.append(({v['id']:1},hi))
    return result


def certify_lp(m, primal, solver=execute):
    """Construct dual/Farkas multipliers, then independently recheck algebra.

    The certificate search uses the same solver; verification does not trust
    its reported objective. All conclusions remain floating-point numerical.
    """
    if any(v['domain']!='continuous' for v in m['variables']): return {'verified':False,'reason':'not_continuous'}
    if primal['status'] not in {'optimal','infeasible'}: return {'verified':False,'reason':'primal_not_certified'}
    ab=inequalities(m); sign=1 if m['objective']['sense']=='max' else -1
    infeasible=primal['status']=='infeasible'
    co={k:sign*a for k,a in m['objective']['coefficients'].items()}
    ids=['dual_'+str(j) for j in range(len(ab))]
    rows=[dict(id='column_'+str(i),coefficients={v:ab[j][0].get(x['id'],0) for j,v in enumerate(ids)},sense='eq',rhs=0 if infeasible else co.get(x['id'],0)) for i,x in enumerate(m['variables'])]
    if infeasible: rows.append(dict(id='contradiction',coefficients={v:ab[j][1] for j,v in enumerate(ids)},sense='le',rhs=-1))
    dm=dict(schema='milp-v1',variables=[dict(id=v,meaning=v,unit='dual',domain='continuous',lower=0,upper=None) for v in ids],constraints=rows,
            objective=dict(coefficients={} if infeasible else {v:ab[j][1] for j,v in enumerate(ids)},sense='min',offset=0,unit='dual'))
    result=solver({'op':'solve','model':dm}); point=result.get('point')
    if point is None: return {'verified':False,'reason':'no_dual_certificate','search_status':result['status']}
    y=[point[v] for v in ids]
    nonnegative=min(y,default=0)>=-1e-8
    residual=max(abs(math.fsum(a.get(v['id'],0)*yy for (a,b),yy in zip(ab,y))-(0 if infeasible else co.get(v['id'],0))) for v in m['variables'])
    dual=math.fsum(b*yy for (a,b),yy in zip(ab,y))
    if infeasible:
        valid=nonnegative and residual<=1e-7 and dual<=-1+1e-7
        return dict(verified=valid,kind='numerically_rechecked_Farkas',column_residual=residual,contradiction=dual,multipliers=y)
    x=primal.get('point',{})
    if set(x)!={v['id'] for v in m['variables']}: return dict(verified=False,reason='missing_primal')
    primal_violation=max([0]+[math.fsum(a.get(k,0)*v for k,v in x.items())-b for a,b in ab])
    value=math.fsum(co.get(k,0)*v for k,v in x.items())
    gap=dual-value
    valid=nonnegative and residual<=1e-7 and primal_violation<=1e-6 and abs(gap)<=1e-6*max(1,abs(value),abs(dual))
    return dict(verified=valid,kind='numerically_rechecked_primal_dual',column_residual=residual,primal_violation=primal_violation,gap=gap,multipliers=y)


def certify_discrete(m, primal, max_states=2_000_000):
    if not all(v['domain']=='binary' for v in m['variables']): return dict(verified=False,reason='enumeration_domain_not_supported')
    if 2**len(m['variables'])>max_states:return dict(verified=False,reason='enumeration_budget')
    ids=[v['id'] for v in m['variables']]; ab=inequalities(m); best=None; feasible=0
    for values in itertools.product((0,1),repeat=len(ids)):
        p=dict(zip(ids,values))
        if any(sum(a.get(k,0)*v for k,v in p.items())>b+1e-9 for a,b in ab):continue
        feasible+=1
        value=sum(m['objective']['coefficients'].get(k,0)*v for k,v in p.items())+m['objective']['offset']
        if best is None or (value<best if m['objective']['sense']=='min' else value>best):best=value
    valid=(primal['status']=='infeasible' if best is None else primal['status']=='optimal' and math.isclose(primal['objective'],best,abs_tol=1e-7,rel_tol=1e-7))
    return dict(verified=valid,kind='independent_full_binary_enumeration',states=2**len(ids),feasible_states=feasible,objective=best)
