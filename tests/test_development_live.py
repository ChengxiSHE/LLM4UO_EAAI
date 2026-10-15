from contextlib import ExitStack
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from llm4or import development_live as dev
from llm4or.gateway import Stopped
from llm4or.live import LiveRequest
from llm4or.schema import digest
from llm4or.verified_pipeline import make_verified_payload


class DevelopmentScopeTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        root=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.run,self.auth_path,self.public_path=root/'run',root/'auth.json',root/'public.jsonl'
        self.public=[{'id':pid,'text':'Continuous bounded linear production problem.'} for pid in dev.PROBLEMS]
        self.public_path.write_text(''.join(json.dumps(p)+'\n' for p in self.public))
        self.manifest={'source_hashes':{},'public_sha256':hashlib.sha256(self.public_path.read_bytes()).hexdigest()}
        self.auth={'status':'approved','endpoint':dev.BASE_URL,'model':dev.MODEL,'protocol':dev.VERSION,
                   'problem_ids':list(dev.PROBLEMS),'run_directory':str(self.run),
                   'limits':asdict(dev.PROBE_LIMITS),'retry_policy':'none','cross_task_evolution':False,
                   'manifest_hash':digest(self.manifest)}
        self.auth_path.write_text(json.dumps(self.auth))
        for name,value in [('RUN_DIR',self.run),('AUTH_PATH',self.auth_path),('PUBLIC_PATH',self.public_path)]:
            self.stack.enter_context(patch.object(dev,name,value))
        self.stack.enter_context(patch('llm4or.live.load_credential',side_effect=AssertionError('No credential reads in tests')))
        self.payload=make_verified_payload(self.public[0],'initial')

    def gateway(self,**kwargs):return dev.DevelopmentGateway(manifest=self.manifest,**kwargs)

    def test_closed_scope_refused(self):
        self.auth['status']='completed';self.auth_path.write_text(json.dumps(self.auth))
        with self.assertRaisesRegex(Stopped,'scope'):self.gateway()
        self.assertFalse(self.run.exists())

    def test_limit_expansion_and_alternate_ledger_refused(self):
        with self.assertRaisesRegex(Stopped,'scope'):self.gateway(limits=replace(dev.PROBE_LIMITS,requests=21))
        with self.assertRaisesRegex(Stopped,'scope'):self.gateway(directory=self.run.parent/'other')

    def test_retries_refused_before_reservation(self):
        g=self.gateway();pid=dev.PROBLEMS[0]
        with self.assertRaisesRegex(Stopped,'retry_forbidden'):
            g.request(pid+':initial:retry1',pid,'initial',self.payload,LiveRequest())
        self.assertEqual(g.summary()['reserved_attempts_including_failures'],0)

    def test_public_text_change_detected(self):
        g=self.gateway();self.public_path.write_text(self.public_path.read_text()+'\n')
        with self.assertRaisesRegex(Stopped,'public_changed'):g.preflight(self.payload,LiveRequest())

    def test_unapproved_payload_and_auth_change_detected(self):
        g=self.gateway();bad=json.loads(json.dumps(self.payload));bad['problem']['text']='Altered question'
        with self.assertRaisesRegex(Stopped,'problem_or_protocol'):g.preflight(bad,LiveRequest())
        self.auth['status']='completed';self.auth_path.write_text(json.dumps(self.auth))
        with self.assertRaisesRegex(Stopped,'revoked'):g.preflight(self.payload,LiveRequest())

    def test_every_phase_wire_checked(self):
        g=self.gateway();self.payload['context']={'oversize':'x'*25000}
        with self.assertRaisesRegex(Stopped,'wire_input_byte_limit'):g.preflight(self.payload,LiveRequest())

    def test_auth_error_stops_next_dispatch(self):
        g=self.gateway()
        with g._connect() as con:
            con.execute("INSERT INTO attempts(key,problem,phase,fingerprint,request,status,error,created) VALUES('old','old','initial','h','{}','failed','http_401',0)")
        with self.assertRaisesRegex(Stopped,'provider_guard'):g.preflight(self.payload,LiveRequest())


if __name__=='__main__':unittest.main()
