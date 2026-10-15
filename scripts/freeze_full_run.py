"""Freeze a reviewable execution plan. Never approve or call a model."""
from collections import Counter
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.formal_provider import BASE_URL,MODEL,PROFILE


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--supersede-interrupted',action='store_true');args=ap.parse_args()
    auth_path=ROOT/'experiments/full_run_authorization.json'
    if auth_path.exists() and json.loads(auth_path.read_text()).get('status')!='pending':
        old=json.loads(auth_path.read_text());old_run=Path(old['run_directory'])
        if not args.supersede_interrupted or not (old_run/'interrupted.json').exists():raise ValueError('cannot_replace_an_existing_authorization')
        archive=old_run/'superseded_authorization.json'
        if archive.exists() and json.loads(archive.read_text())!=old:raise ValueError('authorization_archive_changed')
        write_json(archive,old)
    public=load_public_registry(ROOT);split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
    methods={'Base':{'max_calls':1,'kind':'direct'},'SolverRepair':{'max_calls':3,'kind':'two_solver_repairs'},
             'A':{'max_calls':4,'kind':'fixed_semantic_harness'},'B':{'max_calls':6,'kind':'terminal_feedback_workflow_search'},
             'SimpleAB':{'max_calls':6,'kind':'same_evidence_generic_workflow_search'},'Full':{'max_calls':6,'kind':'paired_action_outcome_workflow_search'}}
    caps=[16384,32768,65536];seeds=[17,31,47];evolved=['B','SimpleAB','Full'];R=2;M=2;build=12;select=12;gate=24
    trajectories=len(public)*len(methods)*len(seeds)*len(caps)
    test_requests=len(public)*len(seeds)*len(caps)*sum(v['max_calls'] for v in methods.values())
    dev_trajectories=len(evolved)*len(seeds)*R*(2*build+(M+1)*select+2*gate)
    proposals=len(evolved)*len(seeds)*R
    max_requests=test_requests+dev_trajectories*6+proposals
    max_tokens=len(public)*len(methods)*len(seeds)*sum(caps)+(dev_trajectories+proposals)*max(caps)
    paths=set(ROOT.glob('llm4or/*.py'))|set(ROOT.glob('scripts/*.py'))|set(ROOT.glob('tests/test_*.py'))
    paths|=set(ROOT.glob('data/prepared_benchmarks/*.json'))
    paths|={ROOT/p for p in ['experiments/family_split_v1.json','experiments/benchmark_plan.json','experiments/milp_protocol.json',
         'data/manifests/benchmark_input_audit.json','data/manifests/complexor_sources.json','data/manifests/source_manifest.json',
         'data/manifests/benchmark_inventory_20260831_sources.json','results/preparation_preservation_manifest.json',
         'docs/FULL_RUN_REVIEW.md','ark/FORMAL_RUN_BOUNDARY.md',
         'data/manifests/formal_family_edges_v1.json','data/revisions/complexor_parameters_v1.json',
         'data/evaluation/bound_reference_audit_v1.json','data/evaluation/reference_models_v1.json','data/evaluation/reference_transcriptions_v1.json']}
    frozen={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    plan={'schema':'full-run-plan-v2','status':'prepared_pending_user_approval','date':'2026-09-12',
          'runtime':{'python':platform.python_version(),'machine':platform.machine(),
                     'packages':{n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','PyYAML']}},
          'endpoint':BASE_URL,'model':MODEL,'credential_profile':str(PROFILE),'temperature':0,'provider_seed_control':False,
          'replicates':seeds,'replicate_note':'These are independent request/cache namespaces; not a claim the service honors random seeds.',
          'trajectory_token_caps':caps,'methods':methods,'source_records':len(public),
          'source_counts':dict(Counter(r['benchmark'] for r in public)),
          'public_inputs':{r['id']:r['input_sha256'] for r in public},
          'canary_ids':[r['id'] for r in sorted([r for r in public if r['input_status']=='ready'],key=lambda r:(len(json.dumps(r['public'])),r['id']))[:3]],
          'evolution':{'methods':evolved,'generations':R,'candidates_per_generation':M,'build_representatives':build,
                       'select_representatives':select,'gate_families_per_generation':gate,'token_cap':max(caps),
                       'all_stream_candidates_frozen_before_any_gate':True,'nominal_total_alpha':.05,
                       'alpha_split_across_streams_and_generations':True,'independence_claim':'conditional only; operational blocks are not certified iid'},
          'matrix':{'inference_cells':trajectories,'inference_request_ceiling':test_requests,
                    'development_trajectory_ceiling':dev_trajectories,'proposal_requests':proposals,
                    'canary_requests':'3 initial prefixes already contained in Base/replicate17/budget65536 cells; no extra quota',
                    'cost_basis':'Conservative no-cache request upper bound; actual identical prefixes shared physically and charged to every logical trajectory.'},
          'resilience':{'max_attempts_per_request':3,'backoff_seconds':[5,30],
                        'circuit_breaker_consecutive_failures':8,'max_concurrent_requests':5,
                        'transport_route':'direct_no_environment_proxy',
                        'isolated_failure_policy':'retain in denominator; exclude from paired comparisons; continue independent work'},
          'limits':{'max_requests':max_requests,'max_total_reserved_or_reported_tokens':max_tokens,
                    'max_completion_tokens':8192,'max_input_bytes':196608,'max_output_bytes':196608,
                    'token_overhead_reserve':2048,'request_seconds':90,'max_run_seconds':14*86400,'minimum_free_disk_bytes':8*2**30},
          'fee_limit_note':'No fiat price or hard currency cap is known for this private provider. Every retry is separately reserved and counts against the unchanged global request/token ceilings.',
          'run_directory':'results/private/formal_v3_20260912','frozen_files':frozen,
          'authorization':'New explicit confirmation only. Neither S1 nor S2 quota is available.',
          'evaluation_protocol':'published_proxy_v1 plus separate input-bound independent transcriptions; unresolved retained in full denominator',
          'split_counts':split['counts'],
          'scientific_limits':[
            'Published objective/status matching is a proxy, not expert-certified semantic accuracy. 12 references additionally have numeric transcription/native agreement; other native labels remain uncertified.',
            'The 4 ambiguous ComplexOR inputs and steel4 reference conflict stay unresolved without numerical repairs; remaining strict-parse failures remain in the denominator.',
            'Sparse LP/IP/MILP execution only. Nonlinear/conic or oversized formulations must explicitly abstain; no silent relaxation and no filtering of source records.',
            'Family blocks combine 23 conservative semantic templates with transitive public-text similarity at 0.70, not exhaustive semantic certification. Held-out operational blocks are not proof of iid or lack of pretraining contamination.',
            f"Full-source results include development/quarantine records. Report the {split['counts']['records_by_role']['locked_test']} operational held-out records separately and do not present 1356 as unseen tests.",
            'ARK research agents are not enabled and are outside this API authorization. No result or novelty claim is made before measurements.']}
    write_json(ROOT/'experiments/full_run_plan.json',plan)
    write_json(auth_path,{'schema':'formal-run-authorization-v1','status':'pending','plan_sha256':digest(plan),
                         'endpoint':BASE_URL,'model':MODEL,'run_directory':str(ROOT/plan['run_directory']),
                         'limits':plan['limits'],'user_confirmation':None,'historical_authorizations_reused':False})
    print(json.dumps({'plan_sha256':digest(plan),'matrix':plan['matrix'],'limits':plan['limits'],'authorization':'pending'}))


if __name__=='__main__':main()
