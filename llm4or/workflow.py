"""Bounded workflow programs. Data, prompts, solvers and grading are not editable.

No eval, imports, templates, arbitrary strings, loops or sample identifiers are
part of the language. Each node executes at most once, in list order.
"""
from copy import deepcopy
from .schema import Invalid, digest, keys

VERSION = 'workflow-v1'
FEATURES = {'always', 'optimal', 'nonoptimal', 'has_integer', 'has_witness',
            'teacher_unresolved', 'last_repair_accepted', 'remaining_three_calls',
            'remaining_two_calls', 'semantic_budget_available','semantic_consensus_budget_available'}
OPERATIONS = {'solver_repair', 'semantic_review', 'stop'}
SCOPES = {'solver_repair': {'whole_model'}, 'semantic_review': {'one_witness', 'all_witnesses'}, 'stop': {'none'}}
MAX_NODES = 5


def guard(value, depth=0):
    if depth > 3: raise Invalid('guard_depth')
    if isinstance(value, str):
        if value not in FEATURES: raise Invalid('guard_feature_not_allowed')
    elif isinstance(value, dict) and len(value) == 1 and next(iter(value)) in {'and', 'or'}:
        args = next(iter(value.values()))
        if not isinstance(args, list) or not 2 <= len(args) <= 3: raise Invalid('guard_arity')
        for arg in args: guard(arg, depth + 1)
    else: raise Invalid('guard_syntax')
    return value


def triggered(value, features):
    guard(value)
    if isinstance(value, str): return bool(features.get(value, False))
    name, args = next(iter(value.items()))
    return (all if name == 'and' else any)(triggered(a, features) for a in args)


def node(value):
    keys(value, {'op', 'guard', 'scope'})
    if not isinstance(value['op'], str) or value['op'] not in OPERATIONS: raise Invalid('operation_not_allowed')
    if not isinstance(value['scope'], str) or value['scope'] not in SCOPES[value['op']]: raise Invalid('scope_not_allowed')
    guard(value['guard'])
    return value


def compile_program(value):
    keys(value, {'schema', 'nodes'})
    if value['schema'] != VERSION or not isinstance(value['nodes'], list) or len(value['nodes']) > MAX_NODES:
        raise Invalid('program_bounds')
    stopped = False
    for n in value['nodes']:
        node(n)
        if stopped: raise Invalid('unreachable_node')
        stopped = n['op'] == 'stop' and n['guard'] == 'always'
    return deepcopy(value)


def apply_patch(program, patch):
    """Exactly one local edit; compile the complete resulting program."""
    old = compile_program(program); new = deepcopy(old)
    keys(patch, {'kind', 'index', 'value'})
    kind, index, value = patch['kind'], patch['index'], patch['value']
    if type(index) is not int or not 0 <= index <= len(old['nodes']): raise Invalid('patch_index')
    if kind == 'insert': new['nodes'].insert(index, node(value))
    else:
        if index == len(old['nodes']): raise Invalid('patch_index')
        if kind == 'delete':
            if value is not None: raise Invalid('delete_value')
            del new['nodes'][index]
        elif kind == 'guard': new['nodes'][index]['guard'] = guard(value)
        elif kind == 'scope': new['nodes'][index]['scope'] = value
        elif kind == 'move':
            if type(value) is not int or not 0 <= value < len(old['nodes']): raise Invalid('move_index')
            new['nodes'].insert(value, new['nodes'].pop(index))
        else: raise Invalid('patch_kind')
    compile_program(new)
    if digest(old) == digest(new): raise Invalid('unchanged_patch')
    return new


def seed_programs():
    repair = {'op': 'solver_repair', 'guard': 'always', 'scope': 'whole_model'}
    semantic = {'op': 'semantic_review', 'guard': 'remaining_three_calls', 'scope': 'all_witnesses'}
    make = lambda nodes: compile_program({'schema': VERSION, 'nodes': nodes})
    return {'Base': make([]), 'SolverRepair': make([repair, repair]), 'A': make([semantic]),
            'B': make([repair, repair]), 'SimpleAB': make([semantic, repair]), 'Full': make([semantic, repair])}


def seed_programs_v2():
    """Mechanism-v2 seeds: one useful repair and a budget-aware semantic branch."""
    repair = {'op':'solver_repair','guard':'always','scope':'whole_model'}
    semantic = {'op':'semantic_review','guard':{'and':['remaining_two_calls','semantic_budget_available']},
                'scope':'all_witnesses'}
    make=lambda nodes:compile_program({'schema':VERSION,'nodes':nodes})
    return {'Base':make([]),'SolverRepair':make([repair]),'A':make([semantic]),'B':make([repair]),
            'SimpleAB':make([semantic,repair]),'Full':make([semantic,repair])}


def seed_programs_v4():
    """Consensus semantic review needs three remaining calls after initial."""
    repair={'op':'solver_repair','guard':'always','scope':'whole_model'}
    semantic={'op':'semantic_review','guard':{'and':['remaining_three_calls','semantic_consensus_budget_available']},
              'scope':'all_witnesses'}
    make=lambda nodes:compile_program({'schema':VERSION,'nodes':nodes})
    return {'Base':make([]),'SolverRepair':make([repair]),'A':make([semantic]),'B':make([repair]),
            'SimpleAB':make([semantic,repair]),'Full':make([semantic,repair])}


def proposal_payload(program, diagnostics, method, generation):
    if method not in {'B', 'SimpleAB', 'Full'}: raise Invalid('not_an_evolving_method')
    # Diagnostics are produced by the controller, never include problem text,
    # IDs, reference values or source models. Only bounded aggregate evidence.
    return {'version': VERSION, 'instruction':
            'Propose at most two distinct SINGLE local patches to this bounded workflow. '
            'Return {"patches":[{"kind":"insert|delete|guard|scope|move","index":0,"value":...}]}. '
            'No explanations, problem-specific constants or new tools. Optimize held-out development terminal proxy matches; '
            'executable witnesses are differences, not truth. Keep successful branches and avoid regressions.',
            'program': compile_program(program), 'diagnostics': diagnostics,
            'method': method, 'generation': generation, 'max_nodes': MAX_NODES,
            'features': sorted(FEATURES), 'operations': {k: sorted(v) for k, v in SCOPES.items()},
            'patch_rules': 'insert node; delete with null value; replace guard; replace scope; move to integer index. At most one local edit per candidate.'}
