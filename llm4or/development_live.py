"""A separately authorized four-problem probe; cannot reopen the closed S1 run."""
from dataclasses import asdict
import hashlib
from pathlib import Path

from .gateway import Gateway, Limits, Stopped
from .live import BASE_URL, MODEL, LiveGateway, LiveRequest, build_request
from .schema import digest, loads, validate_public
from .verified_pipeline import VERSION

ROOT=Path(__file__).resolve().parents[1]
RUN_DIR=ROOT/'results/private/probe_s2_20260831'
AUTH_PATH=ROOT/'experiments/probe_s2_authorization.json'
PUBLIC_PATH=ROOT/'data/next_development/public/problems.jsonl'
PROBLEMS=('opti_dev_058','opti_dev_150','opti_dev_226','opti_dev_583')
PHASES=('initial','baseline_repair','teacher_model','teacher_feedback','semantic_repair')
PROBE_LIMITS=Limits(requests=20,per_problem=5,completion_tokens=2048,request_seconds=90,run_seconds=1800)


class DevelopmentGateway(LiveGateway):
    mode='approved_live_antchat_four_problem_probe_v3'

    def __init__(self,directory=None,limits=PROBE_LIMITS,manifest=None):
        directory=Path(directory or RUN_DIR)
        auth=loads(AUTH_PATH.read_text())
        if (auth.get('status')!='approved' or auth.get('endpoint')!=BASE_URL
                or auth.get('model')!=MODEL or auth.get('protocol')!=VERSION
                or auth.get('problem_ids')!=list(PROBLEMS)
                or auth.get('run_directory')!=str(RUN_DIR)
                or directory.resolve()!=RUN_DIR.resolve()
                or auth.get('limits')!=asdict(PROBE_LIMITS) or limits!=PROBE_LIMITS
                or auth.get('retry_policy')!='none'
                or auth.get('cross_task_evolution') is not False
                or not manifest or digest(manifest)!=auth.get('manifest_hash')):
            raise Stopped('probe_authorization_scope_mismatch')
        self.auth_hash=digest(auth)
        self.manifest=manifest
        self.public={p['id']:p for p in map(lambda s:validate_public(loads(s)),PUBLIC_PATH.read_text().splitlines())}
        if set(self.public)!=set(PROBLEMS): raise Stopped('probe_public_scope_mismatch')
        self.check_frozen_inputs()
        Gateway.__init__(self,directory,limits,{'authorization_hash':self.auth_hash,'manifest':manifest})

    def check_frozen_inputs(self):
        for relative,expected in self.manifest['source_hashes'].items():
            if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
                raise Stopped('probe_source_changed')
        if hashlib.sha256(PUBLIC_PATH.read_bytes()).hexdigest()!=self.manifest['public_sha256']:
            raise Stopped('probe_public_changed')

    def preflight(self,payload,reply):
        if digest(loads(AUTH_PATH.read_text()))!=self.auth_hash:
            raise Stopped('probe_authorization_changed_or_revoked')
        self.check_frozen_inputs()
        p=validate_public(payload.get('problem'))
        if p!=self.public.get(p['id']) or payload.get('version')!=VERSION:
            raise Stopped('probe_problem_or_protocol_mismatch')
        build_request(payload,self.limits)  # Includes context and complete wire envelope.
        with self._connect() as con:
            recent=list(con.execute('SELECT error FROM attempts ORDER BY created DESC LIMIT 3'))
        if any(r['error'] and r['error'].startswith(('http_401','http_402','http_403','http_429','provider_usage','completion_token_limit')) for r in recent):
            raise Stopped('probe_provider_guard_stopped')
        if len(recent)==3 and all(r['error'] for r in recent):
            raise Stopped('probe_three_transport_failures')

    def request(self,key,problem,phase,payload,reply):
        if problem not in PROBLEMS or phase not in PHASES or key!=problem+':'+phase:
            raise Stopped('probe_request_scope_or_retry_forbidden')
        if payload.get('problem',{}).get('id')!=problem:
            raise Stopped('probe_request_problem_mismatch')
        return Gateway.request(self,key,problem,phase,payload,reply)
