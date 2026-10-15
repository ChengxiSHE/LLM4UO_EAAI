from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from llm4or.schema import Invalid,digest
from llm4or.gateway import Stopped
from llm4or.formal_gateway import (
    FormalGateway, VERIFIED_CA_SHA256, live_worker, pinned_tls_context, wire_body,
)
from llm4or.formal_runtime import run_program,VERSION_V2,VERSION_V3,VERSION_V4,VERSION_V5,VERSION_V6
from llm4or.workflow import compile_program,apply_patch,seed_programs,seed_programs_v2,seed_programs_v4
from llm4or.evolution import Evolution,diagnostic_bundle
from llm4or.formal_evaluation import grade,aggregate,evaluation_cache_binding
from llm4or.benchmark_inputs import payload_sha256
from llm4or.semantic_families import merge_semantic_templates
from llm4or.run_interruption import RunInterrupted, require_scoreable_record


def problem():
    return {'id':'synthetic_formal','profile':'description_parameters_v1','text':'Choose at most two whole items.', 'parameters':[],'instances':[]}


def model(domain='integer'):
    return {'schema':'milp-v1','variables':[{'id':'x','meaning':'number of items','unit':'item','domain':domain,'lower':0,'upper':2}],
            'constraints':[],'objective':{'coefficients':{'x':1},'sense':'max','unit':'items','offset':0}}


def plan():
    return {'run_directory':'paid','frozen_files':{},'trajectory_token_caps':[16384,32768,65536],
            'limits':{'max_requests':30,'max_total_reserved_or_reported_tokens':1_000_000,'max_completion_tokens':8192,
                      'max_input_bytes':196608,'max_output_bytes':196608,'token_overhead_reserve':2048,'request_seconds':90,'max_run_seconds':3600},
            'resilience':{'max_attempts_per_request':3,'backoff_seconds':[0,0],
                          'circuit_breaker_consecutive_failures':8,'max_concurrent_requests':1}}


def response(value):
    return {'text':json.dumps(value),'prompt_tokens':100,'completion_tokens':100,'total_tokens':200,'finish_reason':'stop'}


class WorkflowTests(unittest.TestCase):
    def test_business_renaming_stays_in_same_semantic_template_group(self):
        records=[{'id':'a','text':'A farm produces crops to maximize profit on limited acres of land.'},
                 {'id':'b','text':'A factory manufactures two products using labor hours. Maximize profit.'},
                 {'id':'c','text':'Find a shortest path between two nodes.'}]
        components=[{'members':[r['id']]} for r in records]
        _,membership,_,reviews=merge_semantic_templates(records,components,[])
        self.assertEqual(membership['a'],membership['b']);self.assertNotEqual(membership['a'],membership['c'])
        self.assertFalse(any(r['unrecognized_semantics_certified'] for r in reviews))
    def test_no_sample_constants_or_code(self):
        for bad in ['problem_id','eval','IndustryOR',{'not':'optimal'},{'and':['always','secret_answer']}]:
            with self.assertRaises(Invalid):compile_program({'schema':'workflow-v1','nodes':[{'op':'solver_repair','guard':bad,'scope':'whole_model'}]})

    def test_bounded_program_and_immutable_kernel(self):
        node={'op':'solver_repair','guard':'always','scope':'whole_model'}
        with self.assertRaises(Invalid):compile_program({'schema':'workflow-v1','nodes':[node]*6})
        with self.assertRaises(Invalid):compile_program({'schema':'workflow-v1','nodes':[{'op':'change_evaluator','guard':'always','scope':'none'}]})
        with self.assertRaises(Invalid):compile_program({'schema':'workflow-v1','nodes':[node],'threshold':0})

    def test_one_local_patch_and_scope_check(self):
        p=seed_programs()['A'];q=apply_patch(p,{'kind':'scope','index':0,'value':'one_witness'})
        self.assertNotEqual(digest(p),digest(q))
        with self.assertRaises(Invalid):apply_patch(p,{'kind':'scope','index':0,'value':'whole_model'})
        with self.assertRaises(Invalid):apply_patch(p,{'kind':'guard','index':0,'value':'remaining_three_calls'})

    def test_unreachable_tail_rejected(self):
        with self.assertRaises(Invalid):compile_program({'schema':'workflow-v1','nodes':[
            {'op':'stop','guard':'always','scope':'none'},{'op':'solver_repair','guard':'always','scope':'whole_model'}]})


class LedgerTests(unittest.TestCase):
    def test_provider_tls_uses_hash_pinned_ca_bundle(self):
        import certifi
        import hashlib
        self.assertEqual(
            hashlib.sha256(Path(certifi.where()).read_bytes()).hexdigest(),
            VERIFIED_CA_SHA256,
        )
        context = pinned_tls_context()
        self.assertTrue(context.check_hostname)

    def test_transport_envelope_and_secret_redaction_without_network(self):
        from llm4or.formal_provider import MODEL,BASE_URL
        fake_secret='synthetic-test-key-not-a-credential'
        raw={'id':'synthetic','model':MODEL,'choices':[{'finish_reason':'stop','message':{'content':fake_secret}}],
             'usage':{'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}}
        class Pipe:
            def send_bytes(self,value):self.value=value
            def close(self):pass
        pipe=Pipe()
        from unittest.mock import MagicMock
        reply=MagicMock();reply.read.return_value=json.dumps(raw).encode()
        opener=MagicMock();opener.open.return_value.__enter__.return_value=reply
        with patch('llm4or.formal_gateway.load_credential',return_value=fake_secret),patch('llm4or.formal_gateway.urllib.request.build_opener',return_value=opener):
            live_worker(pipe,wire_body(self.payload(),8192),90,196608)
        self.assertNotIn(fake_secret,pipe.value.decode());self.assertIn('[REDACTED]',pipe.value.decode())
        request=opener.open.call_args.args[0]
        self.assertEqual(request.full_url,BASE_URL+'/chat/completions')
        self.assertEqual(json.loads(request.data)['max_tokens'],8192)
        self.assertEqual(json.loads(pipe.value)['total_tokens'],3)

    def gateway(self,d,reply=None,p=None):return FormalGateway(d,p or plan(),offline=True,directory=Path(d)/'offline',responder=reply or (lambda *_:response(model())))
    def payload(self):return {'instruction':'Return a model.','problem':problem()}

    def test_no_live_without_new_approval_or_secret_read(self):
        with tempfile.TemporaryDirectory() as d,patch('llm4or.formal_gateway.load_credential',side_effect=AssertionError('credential touched')):
            with self.assertRaises((Stopped,FileNotFoundError)):FormalGateway(d,plan())

    def test_reservation_precedes_transport(self):
        with tempfile.TemporaryDirectory() as d:
            def respond(*_):
                with sqlite3.connect(Path(d)/'offline/requests.sqlite3') as db:
                    self.assertEqual(db.execute('SELECT status FROM attempts').fetchone()[0],'reserved')
                return response(model())
            g=self.gateway(d,respond);g.register('a',1,16384);g.request('a',self.payload(),'prefix',17)
            self.assertEqual(g.summary()['physical_attempts'],1)

    def test_shared_prefix_logical_cost_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d)
            for s in ['a','b']:g.register(s,1,16384);g.request(s,self.payload(),'prefix',17)
            self.assertEqual(g.summary()['physical_attempts'],1);self.assertEqual(g.summary()['logical_requests'],2)
            self.assertEqual(g.scope_usage('a'),g.scope_usage('b'))
            g=self.gateway(d,lambda *_:(_ for _ in ()).throw(AssertionError('repeat network')))
            g.request('a',self.payload(),'prefix',17)
            self.assertEqual(g.summary()['physical_attempts'],1)

    def test_replicates_never_share_random_draw(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d)
            for seed in [17,31]:g.register(str(seed),1,16384);g.request(str(seed),self.payload(),'prefix',seed)
            self.assertEqual(g.summary()['physical_attempts'],2)

    def test_five_workers_overlap_distinct_requests(self):
        with tempfile.TemporaryDirectory() as d:
            state={'active':0,'peak':0};guard=threading.Lock();ready=threading.Barrier(5)
            def respond(*_):
                with guard:state['active']+=1;state['peak']=max(state['peak'],state['active'])
                ready.wait(timeout=5)
                with guard:state['active']-=1
                return response(model())
            g=self.gateway(d,respond)
            for i in range(5):g.register(str(i),1,65536)
            with ThreadPoolExecutor(max_workers=5) as pool:
                values=list(pool.map(lambda i:g.request(str(i),self.payload(),str(i),17),range(5)))
            self.assertEqual(len(values),5);self.assertEqual(state['peak'],5);self.assertEqual(g.summary()['physical_attempts'],5)

    def test_concurrent_shared_prefix_sends_once(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def respond(*_):calls.append(1);time.sleep(.03);return response(model())
            g=self.gateway(d,respond)
            for scope in ['a','b','c','d','e']:g.register(scope,1,65536)
            with ThreadPoolExecutor(max_workers=5) as pool:
                values=list(pool.map(lambda scope:g.request(scope,self.payload(),'shared',17),['a','b','c','d','e']))
            self.assertEqual(len(values),5);self.assertEqual(len(calls),1);self.assertEqual(g.summary()['physical_attempts'],1)

    def test_oversized_request_stops_before_transport(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d,lambda *_:(_ for _ in ()).throw(AssertionError('network')));g.register('a',1,16384)
            with self.assertRaises(Stopped):g.request('a',{'instruction':'x'*200000},'p',17)
            self.assertEqual(g.summary()['physical_attempts'],0)

    def test_cache_does_not_relax_admission_bound(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d);p={'instruction':'x'*10000}
            g.register('large',1,65536);g.request('large',p,'p',17)
            g.register('small',1,16384)
            with self.assertRaisesRegex(Stopped,'trajectory_budget'):g.request('small',p,'p',17)

    def test_global_request_budget_includes_failed_calls(self):
        with tempfile.TemporaryDirectory() as d:
            p=plan();p['limits']['max_requests']=1
            g=self.gateway(d,lambda *_:{'error':'synthetic_timeout'},p);g.register('a',2,32768)
            with self.assertRaises(Stopped):g.request('a',self.payload(),'p',17)
            with self.assertRaisesRegex(Stopped,'global_budget'):g.request('a',self.payload(),'new',17,1)
            self.assertEqual(g.summary()['physical_attempts'],1)

    def test_token_accounting_violation_halts_every_role(self):
        with tempfile.TemporaryDirectory() as d:
            bad=response(model());bad['total_tokens']=999999
            g=self.gateway(d,lambda *_:bad);g.register('a',2,65536)
            with self.assertRaises(Stopped):g.request('a',self.payload(),'p',17)
            with self.assertRaisesRegex(Stopped,'global_halt'):g.request('a',self.payload(),'new',17,1)
            self.assertEqual(g.summary()['physical_attempts'],1)

    def test_format_failures_remain_local(self):
        with tempfile.TemporaryDirectory() as d:
            bad=response(model());bad['text']='{'
            g=self.gateway(d,lambda *_:bad);g.register('a',4,65536)
            for slot in range(3):
                with self.assertRaisesRegex(Stopped,'invalid_json_response'):g.request('a',self.payload(),str(slot),17,slot)
            with self.assertRaisesRegex(Stopped,'invalid_json_response'):g.request('a',self.payload(),'fourth',17,3)
            self.assertIsNone(g.halt_reason());self.assertEqual(g.summary()['physical_attempts'],4)

    def test_reserved_outcome_resumes_as_a_new_accounted_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d);g.register('a',2,32768);g.request('a',self.payload(),'p',17)
            with sqlite3.connect(g.db) as db:db.execute("UPDATE attempts SET status='reserved'")
            g=self.gateway(d);result=g.request('a',self.payload(),'p',17)
            self.assertEqual(result['finish_reason'],'stop');self.assertEqual(g.summary()['physical_attempts'],2)

    def test_same_slot_cannot_change_request_after_crash(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d);g.register('a',2,32768);g.request('a',self.payload(),'p',17)
            with self.assertRaisesRegex(Stopped,'content_drift'):g.request('a',{'instruction':'different'},'p',17)

    def test_corrupt_cache_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d);g.register('a',1,16384);g.request('a',self.payload(),'p',17)
            with sqlite3.connect(g.db) as db:db.execute("UPDATE attempts SET response_hash='wrong'")
            with self.assertRaisesRegex(Stopped,'integrity'):g.request('a',self.payload(),'p',17)


class RuntimeTests(unittest.TestCase):
    def test_v2_budget_guard_skips_semantic_branch_at_16k(self):
        with tempfile.TemporaryDirectory() as d:
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=lambda *_:response(model('continuous')))
            out=run_program(problem(),seed_programs_v2()['A'],g,'a',17,3,16384,protocol=VERSION_V2)
            self.assertEqual(out['usage']['logical_requests'],1)
            self.assertFalse(out['trace'][0]['triggered']);self.assertEqual(out['errors'],[])

    def test_v2_rejects_solver_noop_before_another_solve(self):
        with tempfile.TemporaryDirectory() as d:
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=lambda *_:response(model()))
            out=run_program(problem(),seed_programs_v2()['SolverRepair'],g,'a',17,2,65536,protocol=VERSION_V2)
            self.assertEqual(out['trace'][0]['gate']['reason'],'no_change')
            self.assertEqual(out['tool_operations'],1);self.assertEqual(out['usage']['logical_requests'],2)

    def test_v2_semantic_repair_is_deterministic_and_uses_three_calls(self):
        with tempfile.TemporaryDirectory() as d:
            initial=model('continuous');teacher=model('integer')
            def responder(payload,_):
                context=payload.get('context',{})
                if not context:return response(initial)
                if set(context)=={'interface','objective_unit'}:return response(teacher)
                if 'quote_spans' in context:
                    raw={'schema':'teacher-milp-v1','status':'repair','input_sha256':payload_sha256(problem()),
                         'model_hashes':{'initial':digest(initial),'teacher':digest(teacher)},
                         'quote':{'field':'wrong','text':problem()['text'],'start':50,'end':51},
                         'interpretation':'Whole items require an integer domain.',
                         'edits':[{'kind':'domain','target':'x'}],'positive_examples':[{'x':1}]}
                    return response(raw)
                raise AssertionError('unexpected semantic-repair API call')
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=responder)
            out=run_program(problem(),seed_programs_v2()['A'],g,'a',17,3,65536,protocol=VERSION_V2)
            self.assertEqual(out['usage']['logical_requests'],3);self.assertEqual(out['final_model'],teacher)
            self.assertEqual(out['trace'][0]['gate']['status'],'accepted_relative_to_evidence')

    def test_v3_semantic_choice_has_controller_owned_edits_and_tests(self):
        with tempfile.TemporaryDirectory() as d:
            initial=model('continuous');teacher=model('integer')
            def responder(payload,_):
                context=payload.get('context',{})
                if not context:return response(initial)
                if set(context)=={'interface','objective_unit'}:return response(teacher)
                if set(context)=={'catalog'}:
                    properties=payload['response_schema']['properties']
                    self.assertEqual(set(properties),{'schema','status','decisions'})
                    decision_fields=properties['decisions']['items']['properties']
                    self.assertTrue({'start','end','edits','positive_examples','model_hashes'}.isdisjoint(decision_fields))
                    return response({'schema':'semantic-decision-v1','status':'reviewed','decisions':[
                        {'candidate_id':'candidate_0','verdict':'teacher','quote_text':'whole items',
                         'interpretation':'Whole items require an integer domain.'}]})
                raise AssertionError('unexpected API phase')
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=responder)
            out=run_program(problem(),seed_programs_v2()['A'],g,'a',17,3,65536,protocol=VERSION_V3)
            self.assertEqual(out['usage']['logical_requests'],3);self.assertEqual(out['final_model'],teacher)
            self.assertEqual(out['trace'][0]['gate']['status'],'accepted_relative_to_evidence')
            self.assertEqual(out['trace'][0]['gate']['clause_tests_passed'],1)

    def test_v3_skips_judgment_when_solver_finds_no_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def responder(payload,_):calls.append(set(payload.get('context',{})));return response(model())
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=responder)
            out=run_program(problem(),seed_programs_v2()['A'],g,'a',17,3,65536,protocol=VERSION_V3)
            self.assertEqual(out['usage']['logical_requests'],2);self.assertEqual(len(calls),2)
            self.assertEqual(out['trace'][0]['teacher_packet']['reason'],'no_executable_candidate')

    def test_v4_requires_two_separately_prompted_semantic_votes(self):
        with tempfile.TemporaryDirectory() as d:
            initial=model('continuous');teacher=model('integer');reviews=[]
            def responder(payload,_):
                context=payload.get('context',{})
                if not context:return response(initial)
                if set(context)=={'interface','objective_unit'}:return response(teacher)
                if set(context)=={'catalog'}:
                    reviews.append(payload['instruction'])
                    return response({'schema':'semantic-decision-v1','status':'reviewed','decisions':[{
                        'candidate_id':'candidate_0','verdict':'teacher','quote_text':'whole items',
                        'interpretation':'Whole items require an integer domain.'}]})
                raise AssertionError('unexpected phase')
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=responder)
            out=run_program(problem(),seed_programs_v4()['A'],g,'a',17,4,65536,protocol=VERSION_V4)
            self.assertEqual(out['usage']['logical_requests'],4);self.assertEqual(out['final_model'],teacher)
            self.assertEqual(len(reviews),2);self.assertNotEqual(reviews[0],reviews[1])
            self.assertEqual(out['trace'][0]['teacher_packet']['consensus_reviews'],2)

    def test_v4_rolls_back_when_skeptic_disagrees(self):
        with tempfile.TemporaryDirectory() as d:
            initial=model('continuous');teacher=model('integer')
            def responder(payload,_):
                context=payload.get('context',{})
                if not context:return response(initial)
                if set(context)=={'interface','objective_unit'}:return response(teacher)
                verdict='initial' if 'Try to falsify' in payload['instruction'] else 'teacher'
                return response({'schema':'semantic-decision-v1','status':'reviewed','decisions':[{
                    'candidate_id':'candidate_0','verdict':verdict,'quote_text':'whole items',
                    'interpretation':'Independent synthetic review.'}]})
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=responder)
            out=run_program(problem(),seed_programs_v4()['A'],g,'a',17,4,65536,protocol=VERSION_V4)
            self.assertEqual(out['final_model'],initial)
            self.assertEqual(out['trace'][0]['teacher_packet']['reason'],'no_unanimous_teacher_clause')

    def test_v5_controller_contract_repairs_count_domain_before_workflow(self):
        with tempfile.TemporaryDirectory() as d:
            p={**problem(),'text':'Two pills are available. How many pills should the patient take?'}
            initial=model('continuous');initial['variables'][0]['meaning']='Number of pills'
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=lambda *_:response(initial))
            out=run_program(p,seed_programs_v4()['Base'],g,'a',17,1,65536,protocol=VERSION_V5)
            self.assertEqual(out['final_model']['variables'][0]['domain'],'integer')
            self.assertEqual(out['trace'][0]['op'],'semantic_contract')
            self.assertEqual(out['trace'][0]['contract_report']['status'],'accepted')

    def test_v6_extends_packaged_counts_without_changing_v5(self):
        with tempfile.TemporaryDirectory() as d:
            p={**problem(),'text':'How many reams of paper should the mill produce?'}
            initial=model('continuous');initial['variables'][0]['meaning']='Number of reams of paper'
            g5=FormalGateway(d,plan(),offline=True,directory=Path(d)/'v5',responder=lambda *_:response(initial))
            old=run_program(p,seed_programs_v4()['Base'],g5,'v5',17,1,65536,protocol=VERSION_V5)
            g6=FormalGateway(d,plan(),offline=True,directory=Path(d)/'v6',responder=lambda *_:response(initial))
            new=run_program(p,seed_programs_v4()['Base'],g6,'v6',17,1,65536,protocol=VERSION_V6)
            self.assertEqual(old['final_model']['variables'][0]['domain'],'continuous')
            self.assertEqual(new['final_model']['variables'][0]['domain'],'integer')
            self.assertEqual(new['trace'][0]['contract_report']['status'],'accepted')

    def test_v5_contract_vetoes_consensus_ratio_regression(self):
        with tempfile.TemporaryDirectory() as d:
            p={**problem(),'text':('A woman invests in a younger and an elder company. She wants to invest a '
                                   'minimum of 40% of her investment into the younger company, and maximize profit.')}
            variables=[{'id':'younger','meaning':'Investment into the younger company','unit':'dollars',
                        'domain':'continuous','lower':0,'upper':None},
                       {'id':'elder','meaning':'Investment into the elder company','unit':'dollars',
                        'domain':'continuous','lower':0,'upper':None}]
            initial={'schema':'milp-v1','variables':variables,'constraints':[
                {'id':'min_pct','coefficients':{'younger':.6,'elder':-.4},'sense':'ge','rhs':0},
                {'id':'budget','coefficients':{'younger':1,'elder':1},'sense':'le','rhs':100}],
                'objective':{'coefficients':{'younger':1,'elder':2},'sense':'max','unit':'dollars','offset':0}}
            teacher=deepcopy(initial);teacher['constraints'][0]['coefficients']['younger']=1
            def responder(payload,_):
                context=payload.get('context',{})
                if not context:return response(initial)
                if set(context)=={'interface','objective_unit'}:return response(teacher)
                return response({'schema':'semantic-decision-v1','status':'reviewed','decisions':[{
                    'candidate_id':'candidate_0','verdict':'teacher',
                    'quote_text':'minimum of 40% of her investment into the younger company',
                    'interpretation':'Select the teacher row.'}]})
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=responder)
            out=run_program(p,seed_programs_v4()['A'],g,'a',17,4,65536,protocol=VERSION_V5)
            self.assertEqual(out['final_model'],initial)
            semantic=next(x for x in out['trace'] if x['op']=='semantic_review')
            self.assertEqual(semantic['gate']['reason'],'semantic_contract_violation')

    def test_shared_local_format_failure_stays_a_model_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            bad=response(model());bad['text']='{'
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=lambda *_:bad)
            first=run_program(problem(),seed_programs()['Base'],g,'first',17,1,65536)
            second=run_program(problem(),seed_programs()['Base'],g,'second',17,1,65536)
            self.assertEqual(first['status'],'unresolved');self.assertEqual(second['status'],'unresolved')
            self.assertEqual(g.summary()['physical_attempts'],1)

    def test_concurrent_identical_solver_work_is_computed_once(self):
        with tempfile.TemporaryDirectory() as d,ThreadPoolExecutor(max_workers=5) as pool:
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=lambda *_:response(model()))
            calls=[];guard=threading.Lock()
            def solve(_):
                with guard:calls.append(1)
                time.sleep(.05)
                return {'status':'optimal','objective':2}
            values=list(pool.map(lambda i:run_program(problem(),seed_programs()['Base'],g,f'scope-{i}',17,1,65536,solver=solve),range(5)))
            self.assertTrue(all(v['status']=='completed' for v in values))
            self.assertEqual(len(calls),1)
            self.assertEqual(g.summary()['physical_attempts'],1)

    def test_solver_repair_runs_twice_and_restarts_without_extra_calls(self):
        with tempfile.TemporaryDirectory() as d:
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=lambda *_:response(model()))
            out=run_program(problem(),seed_programs()['SolverRepair'],g,'repair',17,3,65536)
            self.assertEqual(out['status'],'completed');self.assertEqual(out['usage']['logical_requests'],3)
            run_program(problem(),seed_programs()['SolverRepair'],g,'repair',17,3,65536)
            self.assertEqual(g.summary()['physical_attempts'],3)

    def test_unsupported_never_becomes_linear_or_silent_success(self):
        with tempfile.TemporaryDirectory() as d:
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=lambda *_:response({'schema':'unsupported-v1','reason':'nonlinear'}))
            out=run_program(problem(),seed_programs()['A'],g,'unsupported',17,4,65536)
            self.assertIsNone(out['final_model']);self.assertEqual(out['unsupported_reason'],'nonlinear')
            self.assertEqual(out['usage']['logical_requests'],1)

    def test_runtime_rejects_injected_gold_field(self):
        with tempfile.TemporaryDirectory() as d:
            g=FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=lambda *_:response(model()))
            p=problem();p['reference_answer']=2
            with self.assertRaises(Invalid):run_program(p,seed_programs()['Base'],g,'a',17,1,65536)
            self.assertEqual(g.summary()['physical_attempts'],0)


class EvaluationTests(unittest.TestCase):
    def reference(self):
        return {'problem_id':problem()['id'],'input_sha256':payload_sha256(problem()),'audit_status':'native_parsed_not_independently_certified',
                'native':{'parse_status':'parsed','status':'optimal','objective':2}}
    def record(self):return {'input_sha256':payload_sha256(problem()),'final_model':model()}

    def test_proxy_does_not_certify_semantics(self):
        r=grade(self.record(),problem(),self.reference())
        self.assertTrue(r['published_proxy_match']);self.assertIsNone(r['semantic_correctness'])
        self.assertEqual(r['reference_audit_status'],'native_parsed_not_independently_certified')

    def test_reference_conflict_and_missing_stay_in_denominator(self):
        ref=self.reference();ref['audit_status']='reference_conflict'
        r=grade(self.record(),problem(),ref)
        self.assertIsNone(r['published_proxy_match']);self.assertEqual(aggregate([r])['planned'],1)

    def test_inference_claimed_status_is_not_trusted(self):
        record=self.record();record['final_solve']={'status':'optimal','objective':999}
        r=grade(record,problem(),self.reference())
        self.assertTrue(r['published_proxy_match'])

    def test_status_reference_requires_independent_audit(self):
        ref=self.reference();ref['native']={'parse_status':'parsed','status':'infeasible','objective':None}
        r=grade(self.record(),problem(),ref);self.assertIsNone(r['published_proxy_match'])

    def test_solve_limit_cannot_score_as_optimum(self):
        r=grade(self.record(),problem(),self.reference(),solver=lambda *_:{'status':'limit','objective':2})
        self.assertIsNone(r['published_proxy_match'])

    def test_wrong_input_binding_rejected(self):
        ref=self.reference();ref['input_sha256']='wrong'
        r=grade(self.record(),problem(),ref);self.assertEqual(r['reason'],'input_reference_binding_mismatch')

    def test_cache_binding_and_eligibility_include_interruption_state(self):
        normal={**self.record(),'status':'completed','errors':[],'trace':[]}
        local={**self.record(),'status':'infrastructure_unavailable',
               'errors':[{'reason':'request_unavailable:invalid_json_response'}],'trace':[],'final_model':None}
        transport={**local,'errors':[{'reason':'request_unavailable:transport_TimeoutError'}]}
        self.assertNotEqual(evaluation_cache_binding(normal,self.reference()),evaluation_cache_binding(transport,self.reference()))
        self.assertEqual(grade(local,problem(),self.reference())['reason'],'no_supported_final_model')
        self.assertFalse(grade(local,problem(),self.reference())['published_proxy_match'])
        self.assertFalse(grade(transport,problem(),self.reference())['evaluation_eligible'])


def synthetic_split():
    families=[]
    for role,n in [('development_propose',2),('development_select',2),('update_gate',48)]:
        for i in range(n):families.append({'id':f'{role}_{i}','members':[f'{role}_{i}'],'representative':f'{role}_{i}','role':role})
    return {'families':families,'schedules':{'build':[f'development_propose_{i}' for i in range(2)],
            'select':[f'development_select_{i}' for i in range(2)],'gate':[[f'update_gate_{i}' for i in range(g*24,(g+1)*24)] for g in range(2)]}}


class EvolutionTests(unittest.TestCase):
    def test_proposal_selection_acceptance_rejection_and_inheritance(self):
        with tempfile.TemporaryDirectory() as d:
            streams=['B:17','SimpleAB:17','Full:17'];observed=[]
            def execute(stage,stream,gen,label,pid,program):
                if stage=='gate':self.assertTrue((Path(d)/f'g{gen}_all_candidates_committed.json').exists())
                count=len(program['nodes']);score=count>=gen if stage!='gate' else count==1
                return {'score':score,'run':{'usage':{'logical_tokens':200},'errors':[],'features':{'optimal':True},
                                           'trace':[{'features':{'optimal':True}}]}}
            def propose(stream,gen,payload):
                observed.append((stream,gen,len(payload['program']['nodes'])))
                return json.dumps({'patches':[{'kind':'insert','index':0,'value':{'op':'solver_repair','guard':'always','scope':'whole_model'}}]})
            engine=Evolution(d,synthetic_split(),2,streams,execute_scored=execute,propose=propose)
            empty={'schema':'workflow-v1','nodes':[]};result=engine.run({s:empty for s in streams})
            self.assertTrue(all(len(v['nodes'])==1 for v in result.values()))
            self.assertTrue(all(n==1 for _,g,n in observed if g==2))
            self.assertTrue(json.loads((Path(d)/'g1_Full_17_gate.json').read_text())['accept'])
            self.assertFalse(json.loads((Path(d)/'g2_Full_17_gate.json').read_text())['accept'])
            self.assertEqual(engine.run({s:empty for s in streams}),result)

    def test_fresh_gate_reuse_and_test_proposal_access_rejected(self):
        s=synthetic_split();s['schedules']['gate'][1]=s['schedules']['gate'][0]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(Invalid,'reuse'):Evolution(d,s,2,['Full:17'],execute_scored=None,propose=None)
            s=synthetic_split();s['schedules']['build']=['update_gate_1']
            with self.assertRaisesRegex(Invalid,'role_overlap'):Evolution(d,s,2,['Full:17'],execute_scored=None,propose=None)

    def test_contrastive_feedback_is_only_visible_to_full(self):
        pairs=[({'score':False,'run':{'errors':[],'features':{'optimal':True},'trace':[{'features':{'optimal':True}}]}},
                {'score':True,'run':{'errors':[],'features':{'has_witness':True}}})]
        self.assertIn('paired_action_outcomes',diagnostic_bundle('Full',pairs))
        self.assertNotIn('paired_action_outcomes',diagnostic_bundle('SimpleAB',pairs))
        self.assertNotIn('evidence_features',diagnostic_bundle('B',pairs))

    def test_parallel_batches_preserve_frozen_result(self):
        with tempfile.TemporaryDirectory() as d,ThreadPoolExecutor(max_workers=5) as pool:
            def execute(stage,stream,gen,label,pid,program):
                return {'score':len(program['nodes'])==1,'available':True,
                        'run':{'usage':{'logical_tokens':1},'errors':[],'features':{},'trace':[]}}
            def propose(*_):
                return json.dumps({'patches':[{'kind':'insert','index':0,'value':{'op':'solver_repair','guard':'always','scope':'whole_model'}}]})
            engine=Evolution(d,synthetic_split(),1,['B:17'],execute_scored=execute,propose=propose,
                             parallel_map=lambda f,items:list(pool.map(f,items)))
            result=engine.run({'B:17':{'schema':'workflow-v1','nodes':[]}})
            self.assertEqual(len(result['B:17']['nodes']),1)
            self.assertTrue((Path(d)/'g1_all_candidates_committed.json').exists())


class InterruptionTests(unittest.TestCase):
    def gateway(self, d, responder):
        return FormalGateway(d,plan(),offline=True,directory=Path(d)/'offline',responder=responder)

    def test_transient_failures_retry_then_quarantine_without_global_halt(self):
        for reason in ['URLError','transport_URLError','ConnectionResetError','EOFError',
                       'request_timeout_outcome_unknown','http_503']:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as d:
                calls=[]
                def respond(*_):calls.append(1);return {'error':reason}
                g=self.gateway(d,respond);g.register('a',2,65536)
                with self.assertRaisesRegex(Stopped,'request_unavailable'):g.request('a',{'instruction':'model'},'p',17)
                with g.connection() as db:
                    row=db.execute('SELECT status,reserved,charged,error FROM attempts').fetchone()
                self.assertEqual(row['status'],'exhausted');self.assertEqual(row['charged'],row['reserved']*3)
                self.assertEqual(row['error'],reason);self.assertIsNone(g.halt_reason())
                self.assertEqual(len(calls),3);self.assertEqual(g.summary()['physical_attempts'],3)

    def test_transient_retry_can_recover_and_is_fully_accounted(self):
        with tempfile.TemporaryDirectory() as d:
            replies=iter([{'error':'transport_TimeoutError'},response(model())])
            g=self.gateway(d,lambda *_:next(replies));g.register('a',1,65536)
            result=g.request('a',{'instruction':'model'},'p',17)
            self.assertEqual(result['finish_reason'],'stop');self.assertEqual(g.summary()['physical_attempts'],2)
            with g.connection() as db:
                main=db.execute('SELECT reserved,charged,status FROM attempts').fetchone()
                retries=db.execute('SELECT count(*) FROM retry_attempts WHERE ordinal>1').fetchone()[0]
            self.assertEqual(main['status'],'complete');self.assertGreater(main['charged'],main['reserved']);self.assertEqual(retries,1)

    def test_repeated_transport_failures_open_global_circuit(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d,lambda *_:{'error':'transport_TimeoutError'})
            for scope in ['a','b']:
                g.register(scope,1,65536)
                with self.assertRaisesRegex(Stopped,'request_unavailable'):g.request(scope,{'instruction':'model'},scope,17)
            g.register('c',1,65536)
            with self.assertRaisesRegex(RunInterrupted,'circuit_breaker'):
                g.request('c',{'instruction':'model'},'c',17)
            self.assertEqual(g.summary()['physical_attempts'],8);self.assertEqual(g.halt_reason(),'circuit_breaker_transport_failures')

    def test_progress_snapshot_and_html_are_secret_free(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d,lambda *_:response(model()));g.work_started('test:Base:17:0:frozen:65536:synthetic')
            g.work_finished('test:Base:17:0:frozen:65536:synthetic','complete')
            progress=json.loads((g.directory/'progress.json').read_text());page=(g.directory/'progress.html').read_text()
            self.assertEqual(progress['model'],'DeepSeek-V4-Flash');self.assertEqual(progress['work']['test:complete'],1)
            self.assertEqual(progress['max_concurrent_requests'],1)
            self.assertIn('LLM4UO',page);self.assertNotIn('api_key',page)

    def test_live_worker_classifies_network_failure_without_secret_or_network(self):
        import urllib.error
        from unittest.mock import MagicMock
        pipe=MagicMock();opener=MagicMock()
        opener.open.side_effect=urllib.error.URLError('sensitive remote diagnostic')
        with patch('llm4or.formal_gateway.load_credential',return_value='dummy'),patch(
                'llm4or.formal_gateway.urllib.request.build_opener',return_value=opener):
            live_worker(pipe,wire_body({'instruction':'model'},8192),90,196608)
        self.assertEqual(json.loads(pipe.send_bytes.call_args.args[0]),{'error':'transport_URLError'})

    def test_initial_disconnect_is_not_a_model_failure(self):
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d,lambda *_:{'error':'transport_URLError'})
            record=run_program(problem(),seed_programs()['Base'],g,'a',17,1,65536)
            self.assertEqual(record['status'],'infrastructure_unavailable')

    def test_repair_disconnect_preserves_prefix_and_quarantines_after_retries(self):
        with tempfile.TemporaryDirectory() as d:
            replies=iter([response(model())]+[{'error':'request_timeout_outcome_unknown'}]*3)
            g=self.gateway(d,lambda *_:next(replies))
            record=run_program(problem(),seed_programs()['SolverRepair'],g,'a',17,3,65536,
                               solver=lambda *_:{'status':'optimal','objective':2})
            self.assertEqual(record['status'],'infrastructure_unavailable')
            with g.connection() as db:
                rows=list(db.execute('SELECT * FROM attempts ORDER BY created'))
            self.assertEqual([r['status'] for r in rows],['complete','exhausted'])
            self.assertEqual(json.loads(rows[0]['response'])['text'],response(model())['text'])
            self.assertEqual(rows[1]['charged'],rows[1]['reserved']*3)
            before=g.summary()
            g=self.gateway(d,lambda *_:self.fail('Unexpected repeated request'))
            rerun=run_program(problem(),seed_programs()['SolverRepair'],g,'a',17,3,65536,
                              solver=lambda *_:{'status':'optimal','objective':2})
            self.assertEqual(rerun['status'],'infrastructure_unavailable')
            self.assertEqual(g.summary(),before)

    def test_crash_with_reserved_request_resumes_with_accounted_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            def crash(*_):raise KeyboardInterrupt()
            g=self.gateway(d,crash)
            with self.assertRaises(KeyboardInterrupt):
                run_program(problem(),seed_programs()['Base'],g,'a',17,1,65536)
            g=self.gateway(d,lambda *_:response(model()))
            record=run_program(problem(),seed_programs()['Base'],g,'a',17,1,65536,
                               solver=lambda *_:{'status':'optimal','objective':2})
            self.assertEqual(record['status'],'completed');self.assertEqual(g.summary()['physical_attempts'],2)

    def test_driver_never_saves_or_scores_infrastructure_failure(self):
        from scripts.run_formal import Driver
        with tempfile.TemporaryDirectory() as d:
            g=self.gateway(d,lambda *_:{'error':'ConnectionResetError'})
            driver=object.__new__(Driver);driver.gateway=g;driver.directory=g.directory
            driver.plan={'methods':{'Base':{'max_calls':1}},'evolution':{'token_cap':65536}}
            driver.public={problem()['id']:{'public':problem(),'input_sha256':payload_sha256(problem()),'input_status':'ready'}}
            with patch('scripts.run_formal.subprocess.run',side_effect=AssertionError('Scoring attempted')):
                result=driver.scored('build','Base:17',1,'inc',problem()['id'],seed_programs()['Base'])
            self.assertFalse(result['available']);self.assertTrue(list(g.directory.glob('inference/*.json')))

    def test_interrupted_proposal_cannot_be_rejected_or_open_selection(self):
        with tempfile.TemporaryDirectory() as d:
            stages=[]
            def execute(stage,*_):
                stages.append(stage)
                return {'score':True,'run':{'errors':[]}}
            def propose(*_):raise RunInterrupted('global_halt:transport_URLError')
            engine=Evolution(d,synthetic_split(),1,['B:17'],execute_scored=execute,propose=propose)
            with self.assertRaises(RunInterrupted):engine.run({'B:17':seed_programs()['B']})
            self.assertEqual(set(stages),{'build'})
            self.assertFalse(list(Path(d).glob('*frozen.json')))

    def test_legacy_network_records_cannot_produce_score_or_final_aggregate(self):
        for candidate in [None,model()]:
            record={'input_sha256':payload_sha256(problem()),'final_model':candidate,
                    'errors':[{'phase':'initial','reason':'URLError'}]}
            with self.assertRaises(RunInterrupted):require_scoreable_record(record)
            result=grade(record,problem(),{},solver=lambda *_:self.fail('Interrupted record solved'))
            self.assertIsNone(result['published_proxy_match']);self.assertFalse(result['evaluation_eligible'])
            self.assertEqual(aggregate([result])['infrastructure_unavailable'],1)

    def test_development_cli_refuses_interrupted_record_before_labels(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as d:
            record=Path(d)/'record.json'
            record.write_text(json.dumps({'problem_id':'synthetic_no_real_labels','errors':[{'reason':'URLError'}]}))
            result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/score_formal_record.py'),
                                   '--record',str(record),'--development'],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,'')
            self.assertIn('global_infrastructure_interrupted_record',result.stderr)

    def test_model_format_failure_remains_a_model_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            bad=response(model());bad['text']='{'
            g=self.gateway(d,lambda *_:bad)
            record=run_program(problem(),seed_programs()['Base'],g,'a',17,1,65536)
            self.assertEqual(record['errors'][0]['reason'],'invalid_json_response')
            require_scoreable_record(record);self.assertIsNone(g.halt_reason())


if __name__=='__main__':unittest.main()
