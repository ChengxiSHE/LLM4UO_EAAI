"""Read-only final audit. Does not read keys, approve spending or call a model."""
from collections import Counter
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.schema import digest,canonical
from llm4or.pipeline import write_json
from llm4or.benchmark_registry import load_public_registry
from llm4or.milp_pipeline import make_payload
from llm4or.formal_gateway import wire_body
from scripts.run_formal import preflight


def main():
    plan=json.loads((ROOT/'experiments/full_run_plan.json').read_text());checks=[]
    def check(name,ok,details=None):
        checks.append({'name':name,'passed':bool(ok),'details':details})
        if not ok:raise ValueError(name)
    initial=preflight(plan);check('offline_preflight',initial['status']=='offline_preflight_passed')
    check('full_authorization_still_pending',initial['authorization']=='pending')
    public=load_public_registry(ROOT)
    check('complete_source_count',len(public)==1356)
    split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
    roles={m:f['role'] for f in split['families'] for m in f['all_version_members']}
    isolation=json.loads((ROOT/'data/manifests/formal_family_edges_v1.json').read_text())
    crossing=[e for e in isolation['edges'] if e['left'] in roles and e['right'] in roles and roles[e['left']]!=roles[e['right']]]
    check('no_known_cross_role_duplicate_or_template_edges',not crossing,{'edges_checked':len(isolation['edges']),**split['counts']})
    check('no_fabricated_iid_certificate',split['semantic_independence_certified'] is False)
    gate_ids=[x for batch in split['schedules']['gate'] for x in batch]
    check('two_fixed_disjoint_gate_batches',len(gate_ids)==48 and len(set(gate_ids))==48)
    cells={(pid,method,seed,cap) for pid in plan['public_inputs'] for method in plan['methods'] for seed in plan['replicates'] for cap in plan['trajectory_token_caps']}
    check('complete_matrix_enumeration',len(cells)==plan['matrix']['inference_cells'],len(cells))
    requests=len(public)*len(plan['replicates'])*len(plan['trajectory_token_caps'])*sum(v['max_calls'] for v in plan['methods'].values())
    check('request_ceiling_arithmetic',requests+plan['matrix']['development_trajectory_ceiling']*6+plan['matrix']['proposal_requests']==plan['limits']['max_requests'])
    check('canaries_already_in_full_matrix',all((p,'Base',plan['replicates'][0],65536) in cells for p in plan['canary_ids']))
    # Exact runtime payload capture is done without gateway/network calls.
    from llm4or.formal_runtime import run_program
    from llm4or.workflow import seed_programs
    class Capture:
        def register(self,*_):pass
        def request(self,scope,payload,prefix,replicate,slot):
            self.payload=payload
            return {'text':'{"schema":"unsupported-v1","reason":"schema_capacity"}'}
        def scope_usage(self,*_):return {'logical_requests':0,'logical_tokens':0}
    sizes=[]
    for row in public:
        capture=Capture();run_program(row['public'],seed_programs()['Base'],capture,'capture',17,1,65536)
        sizes.append(len(canonical(wire_body(capture.payload,8192)).encode())+2048+8192)
    check('all_initial_payloads_admissible_at_top_budget',max(sizes)<=65536,
          {'min_reserved_tokens':min(sizes),'max_reserved_tokens':max(sizes),
           'initial_reservation_exceeds_budget':{str(cap):sum(x>cap for x in sizes) for cap in plan['trajectory_token_caps']}})
    protected=json.loads((ROOT/'results/preparation_preservation_manifest.json').read_text())
    changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    check('historical_code_and_pilot_archive_unchanged',not changed,{'files':len(protected),'changed':changed})
    run=ROOT/plan['run_directory']
    check('no_live_ledger_created',not (run/'requests.sqlite3').exists())
    total_sources=0
    for manifest in ['data/manifests/source_manifest.json','data/manifests/benchmark_inventory_20260831_sources.json','data/manifests/complexor_sources.json']:
        path=ROOT/manifest
        if not path.exists():continue
        records=json.loads(path.read_text())['records']
        for r in records:
            if 'local_path' not in r or 'sha256' not in r:continue
            file=ROOT/r['local_path']
            if file.is_file():
                check('source_hash:'+r['local_path'],hashlib.sha256(file.read_bytes()).hexdigest()==r['sha256']);total_sources+=1
    check('source_snapshots_checked',total_sources>=142,total_sources)
    for name in ['formal_runtime.py','milp_pipeline.py','milp_feedback.py','workflow.py','evolution.py','formal_gateway.py']:
        tree=ast.parse((ROOT/'llm4or'/name).read_text())
        imports=[(n.module or '') for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        check('no_evaluator_import:'+name,not any('evaluat' in x or 'reference' in x for x in imports))
    stack=json.loads((ROOT/'results/formal_stack_verification.json').read_text())
    check('six_methods_real_solver_stack',stack['plan_sha256']==digest(plan) and stack['passed']==36 and stack['total']==36)
    log=(ROOT/'results/full_preparation_tests.txt').read_text()
    binding=json.loads((ROOT/'results/test_run_binding.json').read_text())
    check('tests_bound_to_current_plan',binding['plan_sha256']==digest(plan) and binding['exit_code']==0 and
          binding['test_log_sha256']==hashlib.sha256((ROOT/'results/full_preparation_tests.txt').read_bytes()).hexdigest())
    import re
    count=re.search(r'Ran (\d+) tests',log)
    check('complete_test_suite',bool(count) and int(count[1])>=239 and log.strip().endswith('OK'),int(count[1]) if count else None)
    report={'status':'passed','plan_sha256':digest(plan),'new_model_api_calls':0,'checks':checks,
            'tests':int(count[1]),'synthetic_stack_cases':36,'source_files_checked':total_sources,
            'disk_free_gib':round(shutil.disk_usage(ROOT).free/2**30,1),'scientific_limits':plan['scientific_limits'],
            'authorization':'pending','remaining_user_decision':'approve or decline this exact full-run scope; not certification of unresolved scientific assumptions'}
    write_json(ROOT/'results/full_preparation_verification.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in {'checks','scientific_limits'}}))


if __name__=='__main__':main()
