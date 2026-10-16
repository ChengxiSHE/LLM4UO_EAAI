"""Evaluator process only. Published-label agreement is not certified accuracy."""
import math
from .schema import digest
from .milp_solver import execute
from .reference_audit import evaluate_bound
from .run_interruption import interrupted_record

VERSION = 'formal-evaluation-v2'


def evaluation_cache_binding(record, reference):
    """Bind every record field that can change grade eligibility or outcome."""
    return {'version':VERSION,'input_sha256':record.get('input_sha256'),
            'status':record.get('status'),'errors':record.get('errors',[]),
            'trace_errors':[x.get('error') for x in record.get('trace',[]) if x.get('error')],
            'final_model':record.get('final_model'),'reference_sha256':digest(reference)}


def grade(record, public, reference, *, solver=execute, independent=True):
    result = {'problem_id': public['id'], 'denominator_included': True, 'published_proxy_match': None,
              'reference_audit_status': reference.get('audit_status'), 'reference_sha256': digest(reference),
              'metric': 'published_objective_status_agreement_not_semantic_accuracy',
              'semantic_correctness': None}
    if interrupted_record(record):
        return {**result,'reason':'infrastructure_interruption','evaluation_eligible':False}
    if reference.get('input_sha256') != record.get('input_sha256') or reference.get('problem_id') != public['id']:
        return {**result,'reason':'input_reference_binding_mismatch'}
    if reference['audit_status'] in {'input_ambiguity','reference_conflict','reference_comparison_unresolved'}:
        return {**result,'reason':reference['audit_status']}
    native = reference.get('native',{})
    if native.get('parse_status')!='parsed': return {**result,'reason':'native_label_unresolved'}
    if native.get('status') in {'infeasible','unbounded'} and reference['audit_status']!='numeric_transcription_and_native_label_agree':
        return {**result,'reason':'native_status_not_independently_audited'}
    candidate = record.get('final_model')
    if candidate is None:
        return {**result,'published_proxy_match':False,'reason':'no_supported_final_model'}
    # Recompute in this evaluator. Never trust a model's claimed objective or
    # the inference process's stored solver status as the grading oracle.
    state = solver({'op':'solve','model':candidate})
    result['candidate_status'] = state['status']
    if state['status'] not in {'optimal','infeasible','unbounded'}:
        return {**result,'reason':'candidate_solve_unresolved'}
    match = state['status']==native['status']
    if match and state['status']=='optimal':
        match = math.isclose(state['objective'],native['objective'],rel_tol=1e-6,abs_tol=1e-6)
    result.update(published_proxy_match=match,reason='published_label_match' if match else 'published_label_mismatch',
                  tolerance={'relative':1e-6,'absolute':1e-6},
                  limitations=['native objective direction/unit may be unspecified','source label may be erroneous','equal objective does not imply equal formulation'])
    if independent and reference['audit_status']=='numeric_transcription_and_native_label_agree':
        result['independent_model_audit'] = evaluate_bound(candidate,public,reference,solver=solver)
    return result


def aggregate(rows):
    if any(r.get('denominator_included') is not True for r in rows): raise ValueError('denominator_changed')
    good = sum(r['published_proxy_match'] is True for r in rows)
    bad = sum(r['published_proxy_match'] is False for r in rows)
    unavailable=sum(r.get('evaluation_eligible') is False for r in rows)
    return {'planned':len(rows),'matched':good,'not_matched':bad,'unresolved':len(rows)-good-bad,
            'infrastructure_unavailable':unavailable,
            'matched_over_full_denominator':good/len(rows) if rows else None,
            'interpretation':'published-label proxy; not independently established semantic modeling accuracy'}
