"""Durable formal-run ledger with bounded recovery and global safeguards."""
from contextlib import contextmanager
import datetime
import hashlib
import fcntl
import html
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import ssl
import tempfile
import time
import urllib.error
import urllib.request
import certifi
from .gateway import Stopped
from .schema import canonical, digest
from .live import NoRedirect, decode_response
from .formal_provider import BASE_URL, MODEL, load_credential
from .run_interruption import RunInterrupted

VERSION = 'formal-gateway-v1'
VERIFIED_CA_SHA256 = '9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f'
FRESH_EXTERNAL_KIND = 'fresh_common_external'
FRESH_COE_EXPERT_STAGES = {
    'terminology_interpreter', 'parameter_extractor', 'modeling_expert',
    'programming_example_provider', 'programming_expert',
    'modeling_knowledge_supplement_expert', 'code_reviewer',
}


def fresh_external_scope_spec(plan, scope, calls, tokens):
    """Validate one plan-bound fresh external trajectory without touching I/O."""
    if plan.get('kind') != FRESH_EXTERNAL_KIND:
        raise Stopped('fresh_external_plan_kind')
    method = plan.get('external_method')
    if not isinstance(method, dict):
        raise Stopped('fresh_external_method')
    parts = scope.split(':')
    if len(parts) != 4:
        raise Stopped('fresh_external_scope_not_authorized')
    stage, name, replicate_text, problem_id = parts
    try:
        replicate = int(replicate_text)
    except ValueError:
        raise Stopped('fresh_external_scope_not_authorized') from None
    public_inputs = plan.get('public_inputs')
    if (
        stage != method.get('scope_stage')
        or name != method.get('name')
        or replicate not in plan.get('replicates', [])
        or not isinstance(public_inputs, dict)
        or problem_id not in public_inputs
        or calls != method.get('max_calls')
        or tokens != plan.get('token_cap')
    ):
        raise Stopped('fresh_external_scope_not_authorized')
    return {
        'stage': stage, 'method': name, 'replicate': replicate,
        'problem_id': problem_id, 'calls': calls, 'tokens': tokens,
    }


def validate_fresh_external_payload(plan, scope, payload, replicate, slot):
    """Bind a Base/BIND/CoE request to the frozen public input and exact slot."""
    method = plan.get('external_method', {})
    spec = fresh_external_scope_spec(
        plan, scope, method.get('max_calls'), plan.get('token_cap'),
    )
    if replicate != spec['replicate']:
        raise Stopped('fresh_external_payload_changed')
    calls = spec['calls']
    if type(slot) is not int or not 0 <= slot < calls:
        raise Stopped('request_slot_limit')
    if not isinstance(payload, dict) or set(payload) != {
        'version', 'instruction', 'problem', 'context',
        'output_contract', 'response_schema',
    }:
        raise Stopped('fresh_external_payload_changed')
    from .benchmark_inputs import validate_public_input, payload_sha256
    public = validate_public_input(payload.get('problem'))
    if (
        public['id'] != spec['problem_id']
        or payload_sha256(public) != plan['public_inputs'][spec['problem_id']]
        or payload.get('version') != plan.get('runtime_version')
        or not isinstance(payload.get('instruction'), str)
        or not isinstance(payload.get('response_schema'), dict)
        or not isinstance(payload.get('context'), dict)
    ):
        raise Stopped('fresh_external_payload_changed')
    context = payload['context']
    if spec['method'] == 'BIND':
        expected = {
            'method': 'Text2Opt/BIND', 'upstream_mode': 'instance_data',
            'round': slot + 1,
            'transport_adapter': 'stateless_antchat_chat_completions',
        }
        if context != expected:
            raise Stopped('fresh_external_payload_changed')
    elif spec['method'] == 'Base':
        if calls != 1 or slot != 0 or context != {}:
            raise Stopped('fresh_external_payload_changed')
    elif spec['method'] == 'CoE':
        if set(context) != {'method', 'snapshot', 'stage', 'step'}:
            raise Stopped('fresh_external_payload_changed')
        collaboration_count = (calls - 1) // 2
        if slot == calls - 1:
            expected_stage, expected_step = 'reducer', collaboration_count
        elif slot % 2 == 0:
            expected_stage, expected_step = 'conductor', slot // 2
        else:
            expected_stage, expected_step = None, slot // 2
        stage = context.get('stage')
        if (
            context.get('method') != 'Chain-of-Experts'
            or context.get('snapshot') != method.get('snapshot')
            or context.get('step') != expected_step
            or (expected_stage is not None and stage != expected_stage)
            or (expected_stage is None and stage not in FRESH_COE_EXPERT_STAGES)
        ):
            raise Stopped('fresh_external_payload_changed')
    else:
        raise Stopped('fresh_external_method')
    return spec


def atomic_text(path, text):
    """Atomically replace one formal-run status artifact under concurrent writers."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name);stream.write(text);stream.flush();os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():temporary.unlink()


def pinned_tls_context():
    """Build the provider TLS context from reviewed CA bytes, not host defaults."""
    path = Path(certifi.where())
    raw = path.read_bytes()
    if not 0 < len(raw) <= 2 * 1024 * 1024:
        raise Stopped('provider_ca_bundle_size')
    if hashlib.sha256(raw).hexdigest() != VERIFIED_CA_SHA256:
        raise Stopped('provider_ca_bundle_changed')
    try:
        context = ssl.create_default_context(cadata=raw.decode('ascii'))
    except (UnicodeError, ssl.SSLError, ValueError):
        raise Stopped('provider_ca_bundle_invalid') from None
    if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
        raise Stopped('provider_tls_verification_disabled')
    return context


class RequestUnavailable(Stopped):
    """One request exhausted its retry allowance; other work may continue."""


def failure_class(reason):
    if not isinstance(reason, str): return 'fatal'
    if reason.startswith('transport_') or reason == 'request_timeout_outcome_unknown': return 'retryable'
    if reason in {'URLError','TimeoutError','ConnectionError','ConnectionResetError','ConnectionAbortedError',
                  'ConnectionRefusedError','BrokenPipeError','EOFError','OSError','gaierror','SSLError','SSLEOFError'}:
        return 'retryable'
    if reason in {'http_408','http_409','http_425','http_429','http_500','http_502','http_503','http_504'}:
        return 'retryable'
    if reason.startswith(('http_401','http_403','provider_usage_','provider_token_','provider_model_',
                          'provider_ca_','provider_tls_')):
        return 'fatal'
    return 'local'


def wire_body(payload, max_output):
    return {'model': MODEL, 'messages': [
        {'role': 'system', 'content': payload['instruction']},
        {'role': 'user', 'content': canonical({k: v for k, v in payload.items() if k != 'instruction'})}],
        'temperature': 0, 'max_tokens': max_output, 'stream': False,
        'response_format': {'type': 'json_object'}}


def live_worker(pipe, body, seconds, output_bytes):
    secret = None
    try:
        secret = load_credential()  # Only reached after durable authorization/reservation.
        request = urllib.request.Request(BASE_URL + '/chat/completions', data=canonical(body).encode(),
                headers={'Authorization': 'Bearer ' + secret, 'Content-Type': 'application/json'}, method='POST')
        # Environment proxy variables previously overrode the macOS
        # *.alipay.com bypass rule. Use the intended direct AntChat route.
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=pinned_tls_context()),
            NoRedirect(),
        )
        with opener.open(request, timeout=seconds - 2) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000: raise Stopped('provider_envelope_limit')
        result = decode_response(raw, output_bytes)
    except urllib.error.HTTPError as exc:
        result = {'error': 'http_' + str(exc.code)}  # Never log a server's error body.
    except Exception as exc:
        result = {'error': str(exc) if isinstance(exc, Stopped) else 'transport_' + type(exc).__name__}
    text = canonical(result)
    if secret: text = text.replace(secret, '[REDACTED]')
    pipe.send_bytes(text.encode()); pipe.close()


class FormalGateway:
    def __init__(self, root, plan, *, offline=False, directory=None, responder=None, authorization_path=None):
        self.root = Path(root).resolve(); self.plan = plan; self.offline = offline
        self.plan_hash = digest(plan); self.responder = responder
        self.directory = Path(directory or self.root / plan['run_directory']).resolve()
        if not offline and (directory is not None or responder is not None): raise Stopped('live_override_forbidden')
        self.auth_path = self.root / (authorization_path or 'experiments/full_run_authorization.json')
        self._pin_stats = {}
        if not offline: self._approved()
        elif self.directory == (self.root / plan['run_directory']).resolve(): raise Stopped('offline_must_use_separate_directory')
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = self.directory / 'requests.sqlite3'
        self.config = {'version': VERSION, 'plan': self.plan_hash, 'offline': offline,
                       'directory': str(self.directory)}
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, config TEXT, started REAL);
                CREATE TABLE IF NOT EXISTS scopes (id TEXT PRIMARY KEY, calls INTEGER, tokens INTEGER);
                CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, fingerprint TEXT, status TEXT,
                  reserved INTEGER, charged INTEGER, response TEXT, response_hash TEXT, error TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS retry_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT,
                  ordinal INTEGER, status TEXT, reserved INTEGER, charged INTEGER, response TEXT,
                  response_hash TEXT, error TEXT, created REAL, UNIQUE(key,ordinal));
                CREATE TABLE IF NOT EXISTS logical (scope TEXT, key TEXT, charged INTEGER, PRIMARY KEY(scope,key));
                CREATE TABLE IF NOT EXISTS slots (scope TEXT, slot INTEGER, key TEXT, PRIMARY KEY(scope,slot));
                CREATE TABLE IF NOT EXISTS halt (id INTEGER PRIMARY KEY, reason TEXT);
                CREATE TABLE IF NOT EXISTS work (scope TEXT PRIMARY KEY, stage TEXT, status TEXT, error TEXT, updated REAL);
                CREATE TABLE IF NOT EXISTS totals (id INTEGER PRIMARY KEY, physical_calls INTEGER, physical_tokens INTEGER,
                                                    logical_calls INTEGER, logical_tokens INTEGER);
                INSERT OR IGNORE INTO totals SELECT 1,(SELECT count(*) FROM attempts),(SELECT coalesce(sum(charged),0) FROM attempts),
                    (SELECT count(*) FROM logical),(SELECT coalesce(sum(charged),0) FROM logical);
                CREATE TRIGGER IF NOT EXISTS physical_insert AFTER INSERT ON attempts BEGIN
                    UPDATE totals SET physical_calls=physical_calls+1,physical_tokens=physical_tokens+NEW.charged WHERE id=1; END;
                CREATE TRIGGER IF NOT EXISTS physical_update AFTER UPDATE OF charged ON attempts BEGIN
                    UPDATE totals SET physical_tokens=physical_tokens+NEW.charged-OLD.charged WHERE id=1; END;
                CREATE TRIGGER IF NOT EXISTS logical_insert AFTER INSERT ON logical BEGIN
                    UPDATE totals SET logical_calls=logical_calls+1,logical_tokens=logical_tokens+NEW.charged WHERE id=1; END;
                CREATE TRIGGER IF NOT EXISTS logical_update AFTER UPDATE OF charged ON logical BEGIN
                    UPDATE totals SET logical_tokens=logical_tokens+NEW.charged-OLD.charged WHERE id=1; END;
                CREATE INDEX IF NOT EXISTS attempts_created ON attempts(created);
                CREATE INDEX IF NOT EXISTS retry_attempts_created ON retry_attempts(created);
            ''')
            prior = db.execute('SELECT config FROM metadata WHERE id=1').fetchone()
            if prior and prior[0] != canonical(self.config): raise Stopped('ledger_configuration_changed')
            db.execute('INSERT OR IGNORE INTO metadata VALUES (1,?,?)', (canonical(self.config), time.time()))
            # The previous controller treated the first transient error as a
            # permanent halt. The new policy resumes it in the same ledger.
            halt=db.execute('SELECT reason FROM halt WHERE id=1').fetchone()
            if halt and failure_class(halt[0])=='retryable':db.execute('DELETE FROM halt WHERE id=1')
        self.write_progress()

    def _approved(self):
        auth = json.loads(self.auth_path.read_text())
        expected = {'schema': self.plan.get('authorization_schema','formal-run-authorization-v1'),
                    'status': 'approved', 'plan_sha256': self.plan_hash,
                    'endpoint': BASE_URL, 'model': MODEL, 'run_directory': str(self.root / self.plan['run_directory']),
                    'limits': self.plan['limits']}
        if any(auth.get(k) != v for k, v in expected.items()) or not auth.get('user_confirmation'):
            raise Stopped('new_full_run_approval_required')
        for path, sha in self.plan['frozen_files'].items():
            import hashlib
            file=self.root/path;stat=file.stat();stamp=(stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
            if self._pin_stats.get(path)==stamp:continue
            if hashlib.sha256(file.read_bytes()).hexdigest() != sha:
                raise Stopped('frozen_file_changed:' + path)
            self._pin_stats[path]=stamp

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row; db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA busy_timeout=30000')
        try:
            with db: yield db
        finally: db.close()

    @contextmanager
    def lock(self, key):
        locks=self.directory/'request_locks';locks.mkdir(exist_ok=True)
        with (locks/(digest(key)+'.lock')).open('a') as f:
            fcntl.flock(f,fcntl.LOCK_EX)
            yield

    def register(self, scope, calls, tokens):
        maximum_calls = 11 if self.plan.get('kind') == FRESH_EXTERNAL_KIND else 6
        if type(calls) is not int or type(tokens) is not int or not 0 < calls <= maximum_calls or tokens not in self.plan['trajectory_token_caps']:
            raise Stopped('invalid_trajectory_limits')
        if not self.offline and self.plan.get('kind') == FRESH_EXTERNAL_KIND:
            fresh_external_scope_spec(self.plan, scope, calls, tokens)
        elif not self.offline and self.plan.get('kind')=='v7_source_ledger_pilot':
            parts=scope.split(':')
            selected={r['problem_id'] for r in self.plan['selection']['records']}
            if (len(parts)!=4 or parts[0]!='v7dev' or parts[1] not in self.plan['methods'] or
                int(parts[2]) not in self.plan['replicates'] or parts[3] not in selected or
                calls!=self.plan['methods'][parts[1]]['max_calls'] or tokens!=self.plan['token_cap']):
                raise Stopped('v7_pilot_scope_not_authorized')
        elif not self.offline and self.plan.get('kind')=='v4_development_pilot':
            parts=scope.split(':')
            selected={r['problem_id'] for r in self.plan['selection']['records']}
            if (len(parts)!=4 or parts[0]!='pilot' or parts[1] not in self.plan['methods'] or
                int(parts[2]) not in self.plan['replicates'] or parts[3] not in selected or
                calls!=self.plan['methods'][parts[1]]['max_calls'] or tokens!=self.plan['token_cap']):
                raise Stopped('pilot_scope_not_authorized')
        elif not self.offline and self.plan.get('kind') in {'text2opt_confirmation','text2opt_v6_confirmation'}:
            parts=scope.split(':')
            selected={r['problem_id'] for r in self.plan['selection']['records']}
            expected_stage='text2optv6' if self.plan.get('kind')=='text2opt_v6_confirmation' else 'text2opt'
            if (len(parts)!=4 or parts[0]!=expected_stage or parts[1] not in self.plan['methods'] or
                int(parts[2]) not in self.plan['replicates'] or parts[3] not in selected or
                calls!=self.plan['methods'][parts[1]]['max_calls'] or tokens!=self.plan['token_cap']):
                raise Stopped('text2opt_scope_not_authorized')
        elif not self.offline:
            parts=scope.split(':')
            if parts[0]=='proposal':
                if len(parts)!=4 or parts[1] not in self.plan['evolution']['methods'] or int(parts[2]) not in self.plan['replicates'] or not 1<=int(parts[3])<=self.plan['evolution']['generations']:
                    raise Stopped('proposal_scope_not_authorized')
                if calls!=1 or tokens!=self.plan['evolution']['token_cap']:raise Stopped('proposal_budget_changed')
            else:
                if len(parts)!=7:raise Stopped('trajectory_scope_not_authorized')
                stage,method,seed,generation,label,cap,pid=parts
                if method not in self.plan['methods'] or int(seed) not in self.plan['replicates'] or pid not in self.plan['public_inputs'] or int(cap)!=tokens or calls!=self.plan['methods'][method]['max_calls']:
                    raise Stopped('trajectory_scope_not_authorized')
                if stage=='test':
                    if generation!='0' or label!='frozen':raise Stopped('test_scope_changed')
                else:
                    if stage not in {'build','select','gate'} or method not in self.plan['evolution']['methods'] or not 1<=int(generation)<=self.plan['evolution']['generations'] or tokens!=self.plan['evolution']['token_cap']:
                        raise Stopped('development_scope_changed')
                    split=json.loads((self.root/'experiments/family_split_v1.json').read_text())
                    if stage=='gate':
                        allowed_families=set(split['schedules']['gate'][int(generation)-1])
                        allowed={f['representative'] for f in split['families'] if f['id'] in allowed_families}
                    else:allowed=set(split['schedules'][stage])
                    allowed_labels={'build':{'inc','contrast'},'select':{'inc','0','1'},'gate':{'inc','candidate'}}
                    if pid not in allowed or label not in allowed_labels[stage]:raise Stopped('development_record_or_candidate_changed')
        with self.connection() as db:
            old = db.execute('SELECT calls,tokens FROM scopes WHERE id=?', (scope,)).fetchone()
            if old and tuple(old) != (calls, tokens): raise Stopped('trajectory_changed')
            db.execute('INSERT OR IGNORE INTO scopes VALUES (?,?,?)', (scope, calls, tokens))

    def request(self, scope, payload, prefix, replicate, slot=0):
        if not self.offline: self._approved()
        import shutil
        if shutil.disk_usage(self.directory).free<self.plan['limits'].get('minimum_free_disk_bytes',0):raise Stopped('global_disk_guard')
        if not self.offline:
            parts=scope.split(':')
            if self.plan.get('kind') == FRESH_EXTERNAL_KIND:
                validate_fresh_external_payload(self.plan, scope, payload, replicate, slot)
            elif int(parts[2])!=replicate:raise Stopped('replicate_changed')
            if self.plan.get('kind') == FRESH_EXTERNAL_KIND:
                pass
            elif parts[0]=='proposal':
                if payload.get('method')!=parts[1] or payload.get('generation')!=int(parts[3]) or payload.get('version')!='workflow-v1':raise Stopped('proposal_payload_changed')
                if set(payload)!={'version','instruction','program','diagnostics','method','generation','max_nodes','features','operations','patch_rules'}:raise Stopped('proposal_payload_extra_fields')
            else:
                from .benchmark_inputs import validate_public_input,payload_sha256
                p=validate_public_input(payload.get('problem'))
                runtime_version=self.plan.get('runtime_version','formal-runtime-v1')
                if p['id']!=parts[-1] or payload_sha256(p)!=self.plan['public_inputs'].get(p['id']) or payload.get('version')!=runtime_version:raise Stopped('public_payload_not_authorized')
                if set(payload)!={'version','instruction','problem','context','output_contract','response_schema'}:raise Stopped('inference_payload_extra_fields')
                allowed_contexts=[set(),{'initial','solve'},{'interface','objective_unit'},
                                  {'initial','teacher','evidence','input_sha256','model_hashes','quote_spans'},
                                  {'initial','teacher','teacher_packet'},{'catalog'},
                                  {'view','input_sha256'}]
                if not isinstance(payload['context'],dict) or set(payload['context']) not in allowed_contexts:raise Stopped('inference_context_extra_fields')
        limits = self.plan['limits']
        body = wire_body(payload, limits['max_completion_tokens'])
        wire_bytes = len(canonical(body).encode())
        if wire_bytes > limits['max_input_bytes']: raise Stopped('wire_input_byte_limit')
        # Conservative token admission bound, NOT a guarantee about a proprietary
        # tokenizer or provider billing. A reported overrun globally halts the run.
        reserve = wire_bytes + limits['token_overhead_reserve'] + limits['max_completion_tokens']
        fingerprint = digest({'body': body, 'prefix': prefix, 'replicate': replicate})
        key = fingerprint
        with self.lock(key):
            with self.connection() as db:
                stop = db.execute('SELECT reason FROM halt WHERE id=1').fetchone()
                if stop: raise Stopped('global_halt:' + stop[0])
                limit = db.execute('SELECT calls,tokens FROM scopes WHERE id=?', (scope,)).fetchone()
                if not limit: raise Stopped('unregistered_trajectory')
                previous = db.execute('SELECT * FROM attempts WHERE key=?', (key,)).fetchone()
                old_logical = db.execute('SELECT 1 FROM logical WHERE scope=? AND key=?', (scope,key)).fetchone()
                usage = db.execute('SELECT count(*),coalesce(sum(charged),0) FROM logical WHERE scope=?', (scope,)).fetchone()
                charge = previous['charged'] if previous and previous['status'] == 'complete' else reserve
                # Identical admission rules with/without physical cache reuse.
                if not old_logical and (usage[0] >= limit[0] or usage[1] + reserve > limit[1]): raise Stopped('trajectory_budget_exhausted')
                if type(slot) is not int or not 0<=slot<limit[0]:raise Stopped('request_slot_limit')
                prior_slot=db.execute('SELECT key FROM slots WHERE scope=? AND slot=?',(scope,slot)).fetchone()
                if prior_slot and prior_slot[0]!=key:raise Stopped('resumed_request_content_drift')
                db.execute('INSERT OR IGNORE INTO slots VALUES (?,?,?)',(scope,slot,key))
                if previous and previous['status']=='complete':
                    response = json.loads(previous['response'])
                    if digest(response) != previous['response_hash']: raise Stopped('cache_integrity_failure')
                    db.execute('INSERT OR IGNORE INTO logical VALUES (?,?,?)', (scope,key,charge))
                    return response
                if previous and previous['status']=='exhausted':
                    if failure_class(previous['error'])=='retryable':
                        raise RequestUnavailable('request_unavailable:'+previous['error'])
                    raise Stopped(previous['error'])
                if previous and previous['status'] not in {'failed','reserved'}:
                    raise Stopped('prior_attempt_'+previous['status'])
                if previous and failure_class(previous['error'] or 'transport_process_interrupted')!='retryable':
                    raise RequestUnavailable('request_unavailable:'+(previous['error'] or previous['status']))
                used = db.execute('SELECT physical_calls,physical_tokens FROM totals WHERE id=1').fetchone()
                started = db.execute('SELECT started FROM metadata WHERE id=1').fetchone()[0]
                if not previous:
                    if used[0]>=limits['max_requests'] or used[1]+reserve>limits['max_total_reserved_or_reported_tokens']:
                        raise RunInterrupted('global_budget_exhausted')
                    if time.time()-started>limits['max_run_seconds']:raise RunInterrupted('run_time_limit')
                    db.execute("INSERT INTO attempts VALUES (?,?,'reserved',?,?,NULL,NULL,NULL,?)",(key,fingerprint,reserve,reserve,time.time()))
                    db.execute('INSERT INTO logical VALUES (?,?,?)',(scope,key,reserve))
                elif previous['status']=='reserved':
                    db.execute("UPDATE attempts SET status='failed',error='transport_process_interrupted' WHERE key=?",(key,))
                    db.execute('INSERT OR IGNORE INTO logical VALUES (?,?,?)',(scope,key,previous['charged']))
            # Every retry is a new physical attempt. All reservations remain
            # charged conservatively when the provider returns no usage.
            from .pipeline import write_json
            write_json(self.directory/'request_payloads'/(key+'.json'),{'scope_first_use':scope,'body':body,'prefix':prefix,'replicate':replicate,'fingerprint':fingerprint})
            policy=self.plan.get('resilience',{'max_attempts_per_request':3,'backoff_seconds':[0,0],
                'circuit_breaker_consecutive_failures':8})
            with self.connection() as db:
                retry_count=db.execute('SELECT count(*) FROM retry_attempts WHERE key=?',(key,)).fetchone()[0]
            attempt_number=(2+retry_count) if previous else 1
            while True:
                is_retry=attempt_number>1
                if is_retry:
                    with self.connection() as db:
                        db.execute('BEGIN IMMEDIATE')
                        used=db.execute('SELECT physical_calls,physical_tokens FROM totals WHERE id=1').fetchone()
                        if used[0]>=limits['max_requests'] or used[1]+reserve>limits['max_total_reserved_or_reported_tokens']:
                            raise RunInterrupted('global_budget_exhausted')
                        # Preserve the first physical outcome before the main
                        # row becomes the aggregate/cache row on recovery.
                        db.execute("INSERT OR IGNORE INTO retry_attempts(key,ordinal,status,reserved,charged,response,response_hash,error,created) SELECT key,1,status,reserved,charged,response,response_hash,error,created FROM attempts WHERE key=?",(key,))
                        db.execute("INSERT INTO retry_attempts(key,ordinal,status,reserved,charged,response,response_hash,error,created) VALUES (?,?,'reserved',?,?,NULL,NULL,NULL,?)",
                                   (key,attempt_number,reserve,reserve,time.time()))
                        retry_id=db.execute('SELECT last_insert_rowid()').fetchone()[0]
                        db.execute('UPDATE attempts SET charged=charged+? WHERE key=?',(reserve,key))
                        db.execute('UPDATE totals SET physical_calls=physical_calls+1 WHERE id=1')
                        aggregate_charge=db.execute('SELECT charged FROM attempts WHERE key=?',(key,)).fetchone()[0]
                        db.execute('UPDATE logical SET charged=? WHERE key=?',(aggregate_charge,key))
                response=None;error=None;charge=reserve
                try:
                    if self.offline:
                        if self.responder is None:raise Stopped('offline_response_missing')
                        response=self.responder(payload,body)
                    else:
                        ctx=multiprocessing.get_context('spawn');receive,send=ctx.Pipe(False)
                        proc=ctx.Process(target=live_worker,args=(send,body,limits['request_seconds'],limits['max_output_bytes']))
                        try:
                            proc.start();send.close()
                            if not receive.poll(limits['request_seconds']):raise Stopped('request_timeout_outcome_unknown')
                            response=json.loads(receive.recv_bytes(1_100_000))
                        finally:
                            if proc.pid is not None:
                                if proc.is_alive():proc.terminate()
                                proc.join(2)
                                if proc.is_alive():proc.kill();proc.join(2)
                            receive.close();send.close()
                    if response.get('error'):raise Stopped(response['error'])
                    for k in ('prompt_tokens','completion_tokens','total_tokens'):
                        if type(response.get(k)) is not int or response[k]<0:raise Stopped('provider_usage_missing')
                    if response['total_tokens']!=response['prompt_tokens']+response['completion_tokens']:raise Stopped('provider_usage_inconsistent')
                    if response['total_tokens']<=10**12:charge=response['total_tokens']
                    if response['total_tokens']>reserve or response['completion_tokens']>limits['max_completion_tokens']:raise Stopped('provider_token_reservation_overrun')
                    charge=response['total_tokens']
                    if response.get('finish_reason')!='stop':raise Stopped('incomplete_response')
                    if not isinstance(response.get('text'),str) or len(response['text'].encode())>limits['max_output_bytes']:raise Stopped('output_byte_limit')
                    from .milp_schema import loads as strict_loads
                    try:strict_loads(response['text'])
                    except ValueError:raise Stopped('invalid_json_response') from None
                    if not self.offline and response.get('reported_model')!=MODEL:raise Stopped('provider_model_changed')
                except Exception as exc:error=str(exc) if isinstance(exc,Stopped) else type(exc).__name__
                with self.connection() as db:
                    if is_retry:
                        db.execute('UPDATE retry_attempts SET status=?,charged=?,response=?,response_hash=?,error=? WHERE id=?',
                            ('failed' if error else 'complete',charge,canonical(response) if response else None,digest(response) if response else None,error,retry_id))
                        db.execute('UPDATE attempts SET charged=charged-?+? WHERE key=?',(reserve,charge,key))
                    else:
                        db.execute('UPDATE attempts SET status=?,charged=?,response=?,response_hash=?,error=? WHERE key=?',
                            ('failed' if error else 'complete',charge,canonical(response) if response else None,digest(response) if response else None,error,key))
                    aggregate_charge=db.execute('SELECT charged FROM attempts WHERE key=?',(key,)).fetchone()[0]
                    db.execute('UPDATE logical SET charged=? WHERE key=?',(aggregate_charge,key))
                    if not error:
                        db.execute("UPDATE attempts SET status='complete',response=?,response_hash=?,error=NULL WHERE key=?",(canonical(response),digest(response),key))
                    kind=failure_class(error) if error else None
                    if kind=='fatal':db.execute('INSERT OR REPLACE INTO halt VALUES (1,?)',(error,))
                    window=policy['circuit_breaker_consecutive_failures']
                    recent=list(db.execute("SELECT error FROM (SELECT error,created FROM retry_attempts UNION ALL SELECT a.error,a.created FROM attempts a WHERE NOT EXISTS (SELECT 1 FROM retry_attempts r WHERE r.key=a.key AND r.ordinal=1)) ORDER BY created DESC LIMIT ?",(window,)))
                    circuit=error and kind=='retryable' and len(recent)==window and all(r[0] and failure_class(r[0])=='retryable' for r in recent)
                    if circuit:db.execute('INSERT OR REPLACE INTO halt VALUES (1,?)',('circuit_breaker_transport_failures',))
                self.write_progress(scope)
                if not error:return response
                if kind=='fatal' or circuit:raise RunInterrupted('global_halt:'+(error if kind=='fatal' else 'circuit_breaker_transport_failures'))
                if kind=='local':
                    with self.connection() as db:db.execute("UPDATE attempts SET status='exhausted' WHERE key=?",(key,))
                    raise Stopped(error)
                if attempt_number>=policy['max_attempts_per_request']:
                    with self.connection() as db:db.execute("UPDATE attempts SET status='exhausted' WHERE key=?",(key,))
                    raise RequestUnavailable('request_unavailable:'+error)
                delays=policy.get('backoff_seconds',[]);delay=delays[min(attempt_number-1,len(delays)-1)] if delays else 0
                if delay and not self.offline:time.sleep(delay)
                attempt_number+=1

    def scope_usage(self, scope):
        with self.connection() as db:
            row = db.execute('SELECT count(*),coalesce(sum(charged),0) FROM logical WHERE scope=?',(scope,)).fetchone()
        return {'logical_requests': row[0], 'logical_tokens': row[1]}

    def prefix_usage(self, scope, through_slot):
        """Replay guards see only the prefix replayed so far, not future cache rows."""
        with self.connection() as db:
            row=db.execute('SELECT count(*),coalesce(sum(l.charged),0) FROM logical l JOIN slots s ON l.scope=s.scope AND l.key=s.key WHERE s.scope=? AND s.slot<=?',(scope,through_slot)).fetchone()
        return {'logical_requests':row[0],'logical_tokens':row[1]}

    def work_started(self, scope):
        stage=scope.split(':',1)[0]
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO work VALUES (?,?,?,?,?)',(scope,stage,'running',None,time.time()))
        self.write_progress(scope)

    def work_finished(self, scope, status, error=None):
        stage=scope.split(':',1)[0]
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO work VALUES (?,?,?,?,?)',(scope,stage,status,error,time.time()))
        self.write_progress(scope)

    def summary(self):
        with self.connection() as db:
            states=dict(db.execute('SELECT status,count(*) FROM attempts GROUP BY status'))
            total=db.execute('SELECT * FROM totals WHERE id=1').fetchone()
            halt = db.execute('SELECT reason FROM halt WHERE id=1').fetchone()
            retries=db.execute('SELECT count(*) FROM retry_attempts WHERE ordinal>1').fetchone()[0]
            failed_physical=db.execute("SELECT count(*) FROM retry_attempts WHERE status='failed'").fetchone()[0]
            failed_physical+=db.execute("SELECT count(*) FROM attempts a WHERE status IN ('failed','exhausted') AND NOT EXISTS (SELECT 1 FROM retry_attempts r WHERE r.key=a.key AND r.ordinal=1)").fetchone()[0]
            work={f'{r[0]}:{r[1]}':r[2] for r in db.execute('SELECT stage,status,count(*) FROM work GROUP BY stage,status')}
        return {'mode': 'offline' if self.offline else 'authorized_live', 'physical_attempts': total['physical_calls'],
                'actual_api_attempts': 0 if self.offline else total['physical_calls'],
                'reserved_or_reported_tokens': total['physical_tokens'],
                'logical_requests': total['logical_calls'], 'logical_tokens': total['logical_tokens'],
                'model':MODEL,'failed':failed_physical,'retry_attempts':retries,'work':work,
                'unknown': states.get('reserved',0),
                'halt': halt[0] if halt else None, 'currency_cost': None}

    def halt_reason(self):
        with self.connection() as db:row=db.execute('SELECT reason FROM halt WHERE id=1').fetchone()
        return row[0] if row else None

    def write_progress(self,current_scope=None):
        """Write a secret-free machine snapshot and auto-refreshing status page."""
        try:
            snapshot=self.summary();work=snapshot['work']
            stage=self.plan.get('progress_stage','test')
            accounted=work.get(stage+':complete',0)+work.get(stage+':unavailable',0)
            planned=self.plan.get('matrix',{}).get('inference_cells',0)
            snapshot.update(schema='formal-progress-v1',updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                current_scope=current_scope,test_cells_accounted=accounted,test_cells_planned=planned,
                test_percent=round(100*accounted/planned,3) if planned else None,
                max_concurrent_requests=self.plan.get('resilience',{}).get('max_concurrent_requests'))
            atomic_text(self.directory/'progress.json',canonical(snapshot)+'\n')
            state='已熔断' if snapshot['halt'] else '运行中或可恢复'
            color='#b91c1c' if snapshot['halt'] else '#166534'
            page=f'''<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="20"><title>LLM4UO 运行进度</title>
<style>body{{font:16px system-ui;max-width:900px;margin:40px auto;padding:0 20px;color:#172033}}progress{{width:100%;height:28px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.card{{padding:16px;border:1px solid #d7dce5;border-radius:12px}}small{{color:#657085}}code{{overflow-wrap:anywhere}}</style>
<h1>LLM4UO 正式实验</h1><p>模型：<b>{html.escape(MODEL)}</b>　状态：<b style="color:{color}">{state}</b></p>
<progress max="{planned or 1}" value="{accounted}"></progress><p>正式矩阵：{accounted:,} / {planned:,}（{snapshot['test_percent'] or 0}%）</p>
<div class="cards"><div class="card"><small>物理请求</small><br><b>{snapshot['physical_attempts']:,}</b></div><div class="card"><small>API并发</small><br><b>{snapshot['max_concurrent_requests']}</b></div><div class="card"><small>重试请求</small><br><b>{snapshot['retry_attempts']:,}</b></div></div>
<p>当前单元：<code>{html.escape(current_scope or '等待启动')}</code></p><p>账本 token：{snapshot['reserved_or_reported_tokens']:,}</p><p>熔断原因：<code>{html.escape(snapshot['halt'] or '无')}</code></p><small>页面每20秒刷新；数据更新时间 {snapshot['updated_at']}</small>'''
            atomic_text(self.directory/'progress.html',page)
        except (OSError,sqlite3.Error):pass
