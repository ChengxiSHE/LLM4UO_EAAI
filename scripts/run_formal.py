"""A frozen full-matrix entry point. Defaults to read-only preflight, never live."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.schema import digest
from llm4or.pipeline import write_json
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_gateway import FormalGateway
from llm4or.formal_runtime import run_program
from llm4or.workflow import seed_programs
from llm4or.evolution import Evolution
from llm4or.gateway import Stopped
from llm4or.run_interruption import RunInterrupted, require_scoreable_record


def preflight(plan):
    import shutil
    import importlib.metadata
    import platform
    actual_runtime={'python':platform.python_version(),'machine':platform.machine(),
                    'packages':{n:importlib.metadata.version(n) for n in plan['runtime']['packages']}}
    if plan.get('resilience',{}).get('max_concurrent_requests')!=5:raise Stopped('unsupported_concurrency_setting')
    if actual_runtime!=plan['runtime']:raise Stopped('runtime_version_changed')
    if shutil.disk_usage(ROOT).free<plan['limits']['minimum_free_disk_bytes']:raise Stopped('free_disk_below_guard')
    problems=load_public_registry(ROOT)
    for path,sha in plan['frozen_files'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise Stopped('frozen_file_changed:'+path)
    if {r['id']:r['input_sha256'] for r in problems}!=plan['public_inputs']:raise Stopped('public_inventory_changed')
    for name in ['pilot_authorization.json','probe_s2_authorization.json']:
        if json.loads((ROOT/'experiments'/name).read_text())['status']!='completed':raise Stopped('historical_authorization_not_closed')
    split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
    members=[x for f in split['families'] for x in f['members']]
    if len(members)!=len(set(members)) or set(members)!=set(plan['public_inputs']):raise Stopped('split_membership_changed')
    # No credential parsing or network traffic is needed to verify permissions.
    from llm4or.formal_provider import BASE_URL,MODEL,PROFILE,check_profile_metadata
    if (plan['endpoint'],plan['model'],plan['credential_profile'])!=(BASE_URL,MODEL,str(PROFILE)):
        raise Stopped('formal_provider_changed')
    check_profile_metadata()
    return {'status':'offline_preflight_passed','plan_sha256':digest(plan),'new_api_requests':0,
            'authorization':json.loads((ROOT/'experiments/full_run_authorization.json').read_text())['status'],
            'records':len(problems),'limits':plan['limits'],'limitations':plan['scientific_limits']}


class Driver:
    def __init__(self,plan,gateway):
        self.plan=plan;self.gateway=gateway;self.directory=gateway.directory
        self.public={r['id']:r for r in load_public_registry(ROOT)}
        self.split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
        self.programs=seed_programs()
        self.pool=None

    def parallel_map(self,function,items):
        if self.pool is None:return [function(x) for x in items]
        return list(self.pool.map(function,items))

    def run_one(self,stage,stream,gen,label,pid,program,cap):
        if self.gateway.halt_reason():raise RunInterrupted('global_guard_stopped_controller')
        method,replicate=stream.split(':');replicate=int(replicate)
        scope=f'{stage}:{stream}:{gen}:{label}:{cap}:{pid}'
        path=self.directory/'inference'/(digest(scope)+'.json')
        binding={'scope':scope,'input_sha256':self.public[pid]['input_sha256'],'program_hash':digest(program)}
        self.gateway.work_started(scope)
        if path.exists():
            saved=json.loads(path.read_text())
            if saved['binding']!=binding or saved['record_sha256']!=digest(saved['record']):raise Stopped('inference_cache_changed')
            if saved['record'].get('status')!='infrastructure_unavailable':require_scoreable_record(saved['record'])
            plain=path.with_suffix('.record.json')
            if not plain.exists():write_json(plain,saved['record'])
            self.gateway.work_finished(scope,'unavailable' if saved['record'].get('status')=='infrastructure_unavailable' else 'complete')
            return saved['record'],path
        if self.public[pid]['input_status']!='ready':
            record={'problem_id':pid,'input_sha256':binding['input_sha256'],'final_model':None,'status':'input_ambiguity',
                    'usage':{'logical_requests':0,'logical_tokens':0},'trace':[],'errors':[]}
        else:
            record=run_program(self.public[pid]['public'],program,self.gateway,scope,replicate,self.plan['methods'][method]['max_calls'],cap)
        if record.get('status')!='infrastructure_unavailable':require_scoreable_record(record)
        if self.gateway.halt_reason():raise RunInterrupted('global_guard_stopped_controller')
        write_json(path,{'binding':binding,'record_sha256':digest(record),'record':record})
        # Evaluator receives an inference-only file; no state is writable back.
        plain=path.with_suffix('.record.json');write_json(plain,record)
        self.gateway.work_finished(scope,'unavailable' if record.get('status')=='infrastructure_unavailable' else 'complete',
                                   record.get('errors',[{}])[-1].get('reason') if record.get('errors') else None)
        return record,path

    def scored(self,stage,stream,gen,label,pid,program):
        run,path=self.run_one(stage,stream,gen,label,pid,program,self.plan['evolution']['token_cap'])
        if run.get('status')=='infrastructure_unavailable':return {'run':run,'score':False,'available':False}
        score_path=path.with_suffix('.score.json')
        if score_path.exists():
            saved=json.loads(score_path.read_text())
            if saved['record_sha256']!=digest(run) or type(saved['score']) is not bool:raise Stopped('score_binding_changed')
            return {'run':run,'score':saved['score'],'available':True}
        result=subprocess.run([sys.executable,str(ROOT/'scripts/score_formal_record.py'),'--record',str(path.with_suffix('.record.json')),'--development'],
                              capture_output=True,text=True,timeout=90,check=True)
        score=json.loads(result.stdout)['score']
        if type(score) is not bool:raise Stopped('invalid_external_score')
        write_json(score_path,{'record_sha256':digest(run),'score':score})
        return {'run':run,'score':score,'available':True}

    def propose(self,stream,generation,payload):
        scope=f'proposal:{stream}:{generation}'
        self.gateway.register(scope,1,self.plan['evolution']['token_cap'])
        return self.gateway.request(scope,payload,digest({'stream':stream,'generation':generation}),int(stream.split(':')[1]),0)['text']

    def execute(self):
        # Three first-prefix requests are inside the total budget. No labels are
        # inspected and no method is selected on canary accuracy.
        for pid in self.plan['canary_ids']:
            run,_=self.run_one('test','Base:'+str(self.plan['replicates'][0]),0,'frozen',pid,self.programs['Base'],max(self.plan['trajectory_token_caps']))
        streams=[m+':'+str(s) for m in self.plan['evolution']['methods'] for s in self.plan['replicates']]
        initial={s:self.programs[s.split(':')[0]] for s in streams}
        workers=self.plan['resilience']['max_concurrent_requests']
        with ThreadPoolExecutor(max_workers=workers,thread_name_prefix='formal') as pool:
            self.pool=pool
            evolution=Evolution(self.directory/'evolution',self.split,self.plan['evolution']['generations'],streams,
                                execute_scored=self.scored,propose=self.propose,parallel_map=self.parallel_map)
            evolved=evolution.run(initial)
            # Final programs are immutable before ANY test evaluation. No test
            # score is produced until every frozen inference cell is accounted for.
            grid=[]
            for cap in sorted(self.plan['trajectory_token_caps'],reverse=True):
                for seed in self.plan['replicates']:
                    for method in self.plan['methods']:
                        stream=method+':'+str(seed);program=evolved.get(stream,self.programs[method])
                        pids=list(self.plan['public_inputs'])
                        values=self.parallel_map(lambda pid:self.run_one('test',stream,0,'frozen',pid,program,cap),pids)
                        for pid,(run,path) in zip(pids,values):
                            grid.append({'id':pid,'benchmark':self.public[pid]['benchmark'],'method':method,'replicate':seed,
                                         'token_cap':cap,'record_path':str(path.with_suffix('.record.json')),'record_sha256':digest(run),
                                         'program_sha256':digest(program)})
            self.pool=None
        write_json(self.directory/'inference_complete.json',{'plan_sha256':digest(self.plan),'cells':grid,'usage':self.gateway.summary()})
        subprocess.run([sys.executable,str(ROOT/'scripts/evaluate_formal.py'),'--run-directory',str(self.directory)],check=True)
        write_json(self.directory/'completed.json',{'plan_sha256':digest(self.plan),'usage':self.gateway.summary()})
        if not self.gateway.offline:
            auth_path=ROOT/'experiments/full_run_authorization.json';auth=json.loads(auth_path.read_text())
            auth.update(status='completed',closed_usage=self.gateway.summary())
            write_json(auth_path,auth)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute-approved',action='store_true');args=parser.parse_args()
    plan=json.loads((ROOT/'experiments/full_run_plan.json').read_text())
    result=preflight(plan)
    if not args.execute_approved:print(json.dumps(result,ensure_ascii=False));return
    gateway=FormalGateway(ROOT,plan)
    # A single controller owns orchestration; its five workers use per-request
    # locks and the durable SQLite ledger.
    import fcntl
    with (gateway.directory/'controller.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Stopped('controller_already_running') from None
        write_json(gateway.directory/'controller.json',{'pid':os.getpid(),'state':'running','plan_sha256':digest(plan)})
        gateway.write_progress()
        try:
            Driver(plan,gateway).execute()
            (gateway.directory/'interrupted.json').unlink(missing_ok=True)
            write_json(gateway.directory/'controller.json',{'pid':os.getpid(),'state':'completed','plan_sha256':digest(plan)})
        except BaseException as exc:
            resumable=not gateway.halt_reason()
            write_json(gateway.directory/'interrupted.json',{'reason':str(exc) if isinstance(exc,Stopped) else type(exc).__name__,'usage':gateway.summary(),
                'automatic_resume':resumable,
                'resume':'Restart the same approved command and directory. Completed checkpoints are reused. '
                         'A request interrupted without a response keeps its reservation and consumes the next bounded retry. '
                         'A persistent circuit/invariant halt requires investigation before restart.'})
            write_json(gateway.directory/'controller.json',{'pid':os.getpid(),'state':'resumable_interruption' if resumable else 'halted',
                                                             'reason':str(exc),'plan_sha256':digest(plan)})
            gateway.write_progress()
            raise
    print(json.dumps(gateway.summary()))


if __name__=='__main__':main()
