"""Freeze the development-only v4 diagnostic; creates no API authorization."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.formal_provider import BASE_URL,MODEL,PROFILE
from llm4or.pipeline import write_json
from llm4or.schema import digest


FILES=['experiments/family_split_v1.json','experiments/v4_development_pilot_selection.json',
       'data/evaluation/bound_reference_audit_v1.json','llm4or/benchmark_inputs.py','llm4or/benchmark_registry.py',
       'llm4or/formal_evaluation.py','llm4or/formal_gateway.py','llm4or/formal_provider.py','llm4or/formal_runtime.py',
       'llm4or/milp_contracts.py','llm4or/milp_feedback.py','llm4or/milp_pipeline.py','llm4or/milp_schema.py',
       'llm4or/milp_solver.py','llm4or/run_interruption.py','llm4or/schema.py','llm4or/semantic_decision.py',
       'llm4or/workflow.py','scripts/approve_v4_pilot.py','scripts/evaluate_v4_pilot.py','scripts/run_v4_pilot.py']


def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def main():
    auth_path=ROOT/'experiments/v4_development_pilot_authorization.json'
    if auth_path.exists() and json.loads(auth_path.read_text()).get('status') not in {'pending'}:
        raise ValueError('refuse_to_replace_nonpending_authorization')
    selection=json.loads((ROOT/'experiments/v4_development_pilot_selection.json').read_text())
    if selection['locked_test_records'] or selection['problem_count']!=selection['family_count']:raise ValueError('selection_not_development_family_unique')
    plan={'schema':'v4-development-pilot-plan-v1','kind':'v4_development_pilot','status':'pending_user_authorization',
          'authorization_schema':'v4-development-pilot-authorization-v1','runtime_version':'formal-runtime-v4',
          'run_directory':'results/private/v4_development_pilot_20260913','endpoint':BASE_URL,'model':MODEL,
          'credential_profile':str(PROFILE),'selection':selection,'public_inputs':{r['problem_id']:r['input_sha256'] for r in selection['records']},
          'methods':{'Base':{'max_calls':1},'A-v4':{'max_calls':4}},'replicates':[17],'token_cap':65536,
          'trajectory_token_caps':[65536],'progress_stage':'pilot',
          'limits':{'max_requests':144,'max_total_reserved_or_reported_tokens':9500000,'max_completion_tokens':8192,
                    'max_input_bytes':196608,'max_output_bytes':196608,'token_overhead_reserve':2048,
                    'request_seconds':90,'max_run_seconds':172800,'minimum_free_disk_bytes':4294967296},
          'resilience':{'max_attempts_per_request':3,'backoff_seconds':[5,20],
                        'circuit_breaker_consecutive_failures':8,'max_concurrent_requests':5},
          'matrix':{'inference_cells':selection['problem_count']*2,'logical_request_ceiling':selection['problem_count']*5,
                    'unique_request_ceiling_without_retries':selection['problem_count']*4,
                    'physical_attempt_ceiling_with_retries':selection['problem_count']*12},
          'evaluation':{'development_only':True,'primary':'process funnel and paired development proxy transitions',
                        'confirmatory_claim_allowed':False,'locked_test_access_during_inference':False},
          'runtime':{'python':platform.python_version(),'machine':platform.machine(),
                     'packages':{n:importlib.metadata.version(n) for n in ['numpy','scipy','jsonschema','psutil']}},
          'frozen_files':{path:sha(path) for path in FILES},
          'cost_note':'Private-provider fiat pricing is unknown; ceilings cover requests and reserved/reported tokens only.'}
    write_json(ROOT/'experiments/v4_development_pilot_plan.json',plan)
    auth={'schema':plan['authorization_schema'],'status':'pending','plan_sha256':digest(plan),'endpoint':BASE_URL,'model':MODEL,
          'run_directory':str(ROOT/plan['run_directory']),'limits':plan['limits'],'user_confirmation':None,
          'historical_authorizations_reused':False}
    write_json(auth_path,auth)
    print(json.dumps({'status':'frozen_pending_user_authorization','plan_sha256':digest(plan),'matrix':plan['matrix']}))


if __name__=='__main__':main()
