"""Evaluator-only strict native label parsing and input-bound evaluation.

Parsing a source label is not independent certification. This module must not
be imported by an inference runner, teacher, or workflow proposer.
"""
import math
import re
from .benchmark_inputs import payload_sha256, validate_public_input
from .milp_evaluator import evaluate
from .milp_solver import execute
from .schema import Invalid, digest

DECIMAL = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?')
OBJECTIVE_KEY = re.compile(r'^(?:the )?(?:(?:maximum|minimum|optimal|total|net)\b|objective\b)',re.I)


def parse_native(value, *, singleton_list=False, objective_field=None):
    if singleton_list:
        if not isinstance(value,list) or len(value)!=1:return dict(parse_status='unresolved',reason='non_singleton_output')
        value=value[0]
    if isinstance(value,dict):
        if objective_field is not None:
            if objective_field not in value:return dict(parse_status='unresolved',reason='missing_reviewed_objective_field')
            selected=objective_field
        elif len(value)==1:selected=next(iter(value))
        else:
            possible=[k for k in value if OBJECTIVE_KEY.match(k)]
            if len(possible)!=1:return dict(parse_status='unresolved',reason='objective_field_ambiguous',candidate_field_count=len(possible))
            selected=possible[0]
        result=parse_native(value[selected]); result['selected_field']=selected
        result['field_selection_reviewed']=objective_field is not None
        return result
    if isinstance(value,str):
        text=value.strip()
        if text.casefold() in {'infeasible','unbounded'}:
            return dict(parse_status='parsed',status=text.casefold(),objective=None)
        if not DECIMAL.fullmatch(text):return dict(parse_status='unresolved',reason='not_strict_numeric_or_status')
        value=float(text)
    if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>1e12:
        return dict(parse_status='unresolved',reason='invalid_numeric_label')
    return dict(parse_status='parsed',status='optimal',objective=value)


def evaluate_bound(candidate, public_input, reference, *, solver=execute):
    """Grade only an audited artifact tied to this exact public input revision."""
    p=validate_public_input(public_input)
    base=dict(problem_id=p['id'],benchmark_success=None,denominator_included=True,
              scope='audited_reference_proxy_not_expert_natural_language_truth')
    if reference.get('problem_id')!=p['id'] or reference.get('input_sha256')!=payload_sha256(p):
        return {**base,'grade_reason':'stale_or_wrong_input_reference'}
    if reference.get('audit_status')!='numeric_transcription_and_native_label_agree':
        return {**base,'grade_reason':'reference_not_ready'}
    m=reference.get('model')
    if reference.get('model_sha256')!=digest(m):
        return {**base,'grade_reason':'reference_model_hash_mismatch'}
    if reference.get('certificate_binding')!=digest({'model':m,'solve':reference.get('solve'),'certificate':reference.get('independent_certificate')}):
        return {**base,'grade_reason':'reference_certificate_hash_mismatch'}
    if reference.get('independent_certificate',{}).get('verified') is not True:
        return {**base,'grade_reason':'reference_certificate_missing'}
    return {**base,**evaluate(candidate,m,solver=solver),'reference_scope':'assistant_transcription_numeric_certificate_plus_native_agreement_not_expert_gold'}
