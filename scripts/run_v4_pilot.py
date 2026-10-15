"""Run the explicitly authorized, checkpointed v4 development diagnostic."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_gateway import FormalGateway
from llm4or.formal_provider import BASE_URL,MODEL,PROFILE,check_profile_metadata
from llm4or.formal_runtime import run_program,VERSION_V4
from llm4or.gateway import Stopped
from llm4or.pipeline import write_json
from llm4or.run_interruption import RunInterrupted,require_scoreable_record
from llm4or.schema import digest
from llm4or.workflow import seed_programs_v4

PLAN_PATH=ROOT/'experiments/v4_development_pilot_plan.json'
AUTH_PATH=ROOT/'experiments/v4_development_pilot_authorization.json'


def preflight(plan,require_approval=True):
    import shutil
    actual={'python':platform.python_version(),'machine':platform.machine(),
            'packages':{n:importlib.metadata.version(n) for n in plan['runtime']['packages']}}
    if actual!=plan['runtime']:raise Stopped('runtime_version_changed')
    if plan['runtime_version']!=VERSION_V4 or plan['resilience']['max_concurrent_requests']!=5:raise Stopped('pilot_runtime_changed')
    if shutil.disk_usage(ROOT).free<plan['limits']['minimum_free_disk_bytes']:raise Stopped('free_disk_below_guard')
    for path,sha in plan['frozen_files'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise Stopped('frozen_file_changed:'+path)
    registry={r['id']:r for r in load_public_registry(ROOT)}
    if any(pid not in registry or registry[pid]['input_sha256']!=sha for pid,sha in plan['public_inputs'].items()):raise Stopped('public_input_changed')
    if (plan['endpoint'],plan['model'],plan['credential_profile'])!=(BASE_URL,MODEL,str(PROFILE)):raise Stopped('formal_provider_changed')
    check_profile_metadata()
    auth=json.loads(AUTH_PATH.read_text())
    if auth['plan_sha256']!=digest(plan) or (require_approval and auth['status']!='approved'):raise Stopped('v4_pilot_approval_required')
    return {'status':'passed','plan_sha256':digest(plan),'authorization':auth['status'],'api_requests':0}


class Driver:
    def __init__(self,plan,gateway):
        self.plan=plan;self.gateway=gateway;self.directory=gateway.directory
        self.public={r['id']:r for r in load_public_registry(ROOT)}
        seeds=seed_programs_v4();self.programs={'Base':seeds['Base'],'A-v4':seeds['A']}

    def one(self,method,pid):
        replicate=self.plan['replicates'][0];scope=f'pilot:{method}:{replicate}:{pid}'
        path=self.directory/'inference'/(digest(scope)+'.json');path.parent.mkdir(parents=True,exist_ok=True)
        program=self.programs[method];binding={'scope':scope,'input_sha256':self.public[pid]['input_sha256'],
                                              'program_hash':digest(program),'runtime_version':VERSION_V4}
        self.gateway.work_started(scope)
        if path.exists():
            saved=json.loads(path.read_text())
            if saved['binding']!=binding or saved['record_sha256']!=digest(saved['record']):raise Stopped('pilot_checkpoint_changed')
            record=saved['record']
        else:
            if self.public[pid]['input_status']!='ready':
                record={'version':VERSION_V4,'problem_id':pid,'input_sha256':binding['input_sha256'],'final_model':None,
                        'status':'input_ambiguity','usage':{'logical_requests':0,'logical_tokens':0},'trace':[],'errors':[]}
            else:
                record=run_program(self.public[pid]['public'],program,self.gateway,scope,replicate,
                                   self.plan['methods'][method]['max_calls'],self.plan['token_cap'],protocol=VERSION_V4)
            if record.get('status')!='infrastructure_unavailable':require_scoreable_record(record)
            write_json(path,{'binding':binding,'record_sha256':digest(record),'record':record})
        self.gateway.work_finished(scope,'unavailable' if record.get('status')=='infrastructure_unavailable' else 'complete',
                                   record.get('errors',[{}])[-1].get('reason') if record.get('errors') else None)
        return {'method':method,'problem_id':pid,'record_path':str(path),'record_sha256':digest(record)}

    def execute(self):
        ids=[r['problem_id'] for r in self.plan['selection']['records']];cells=[]
        with ThreadPoolExecutor(max_workers=5,thread_name_prefix='v4-pilot') as pool:
            for method in ('Base','A-v4'):
                cells.extend(pool.map(lambda pid:self.one(method,pid),ids))
        write_json(self.directory/'inference_complete.json',{'plan_sha256':digest(self.plan),'cells':cells,
                   'usage':self.gateway.summary(),'completed_at':datetime.now(timezone.utc).isoformat()})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute-approved',action='store_true');args=parser.parse_args()
    plan=json.loads(PLAN_PATH.read_text());print(json.dumps(preflight(plan,require_approval=args.execute_approved)))
    if not args.execute_approved:return
    gateway=FormalGateway(ROOT,plan,authorization_path='experiments/v4_development_pilot_authorization.json')
    with (gateway.directory/'controller.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Stopped('controller_already_running') from None
        write_json(gateway.directory/'controller.json',{'pid':os.getpid(),'state':'running','plan_sha256':digest(plan)})
        try:
            Driver(plan,gateway).execute()
        except BaseException as exc:
            write_json(gateway.directory/'interrupted.json',{'reason':str(exc) if isinstance(exc,Stopped) else type(exc).__name__,
                'usage':gateway.summary(),'automatic_resume':not gateway.halt_reason()})
            write_json(gateway.directory/'controller.json',{'pid':os.getpid(),'state':'resumable_interruption' if not gateway.halt_reason() else 'halted',
                                                             'reason':str(exc),'plan_sha256':digest(plan)})
            raise
        auth=json.loads(AUTH_PATH.read_text());auth.update(status='completed',closed_usage=gateway.summary(),
            closed_at=datetime.now(timezone.utc).isoformat(),further_api_calls_authorized=False);write_json(AUTH_PATH,auth)
        try:subprocess.run([sys.executable,str(ROOT/'scripts/evaluate_v4_pilot.py')],check=True)
        except BaseException as exc:
            write_json(gateway.directory/'controller.json',{'pid':os.getpid(),'state':'inference_completed_evaluation_failed',
                                                             'reason':type(exc).__name__,'plan_sha256':digest(plan)})
            raise
        (gateway.directory/'interrupted.json').unlink(missing_ok=True)
        write_json(gateway.directory/'completed.json',{'plan_sha256':digest(plan),'usage':gateway.summary()})
        write_json(gateway.directory/'controller.json',{'pid':os.getpid(),'state':'completed','plan_sha256':digest(plan)})


if __name__=='__main__':main()
