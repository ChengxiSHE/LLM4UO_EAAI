from copy import deepcopy
import json
import tempfile
import unittest

from llm4or.benchmark_inputs import payload_sha256
from llm4or.gateway import Gateway,Limits,MockReply
from llm4or.milp_feedback import (compile_record,compile_record_v2,apply_teacher_edits,
                                  repair_gate,repair_gate_v2)
from llm4or.milp_pipeline import make_payload,run_milp_problem
from llm4or.milp_contracts import validate_output
from llm4or.milp_solver import execute
from llm4or.schema import Invalid,digest
from llm4or.semantic_decision import build_catalog,compile_decision,compile_consensus,validate_decision


def fixture(domain='integer',sense='max',row=False):
    return dict(schema='milp-v1',variables=[dict(id='x',meaning='number of objects',unit='item',domain=domain,lower=0,upper=2)],
                constraints=[dict(id='cap',coefficients={'x':1},sense='le',rhs=0)] if row else [],
                objective=dict(coefficients={'x':1},sense=sense,unit='items',offset=0))


def problem():return dict(id='synthetic_gate',profile='description_parameters_v1',text='Choose whole items. The count is at most two.',parameters=[],instances=[])


def raw_record(initial,teacher,kind,target,point=0):
    p=problem()
    return dict(schema='teacher-milp-v1',status='repair',input_sha256=payload_sha256(p),
                model_hashes=dict(initial=digest(initial),teacher=digest(teacher)),quote=dict(field='text',text=p['text'],start=0,end=len(p['text'])),
                interpretation='An unverified interpretation.',edits=[dict(kind=kind,target=target)],positive_examples=[{'x':point}])


class FeedbackTests(unittest.TestCase):
    def compile(self,a,b,kind,target,point=0):
        evidence=execute({'op':'compare','left':a,'right':b})
        return compile_record(raw_record(a,b,kind,target,point),problem(),a,b,evidence)

    def test_integer_repair_with_identical_optimum(self):
        a,b=fixture('continuous'),fixture('integer');p=self.compile(a,b,'domain','x')
        r=repair_gate(problem(),a,b,b,p)
        self.assertEqual(r['status'],'accepted_relative_to_evidence')
        self.assertFalse(p['interpretation_used_as_verified_fact'])

    def test_integer_to_continuous_not_blind_integerization(self):
        a,b=fixture('integer'),fixture('continuous');p=self.compile(a,b,'domain','x',.5)
        self.assertEqual(repair_gate(problem(),a,b,b,p)['status'],'accepted_relative_to_evidence')

    def test_add_missing_row(self):
        a,b=fixture(),fixture(row=True);p=self.compile(a,b,'row','cap')
        self.assertEqual(repair_gate(problem(),a,b,b,p)['status'],'accepted_relative_to_evidence')

    def test_delete_overrestriction(self):
        a,b=fixture(row=True),fixture();p=self.compile(a,b,'row','cap',1)
        self.assertEqual(repair_gate(problem(),a,b,b,p)['status'],'accepted_relative_to_evidence')

    def test_objective_reversal_repair(self):
        a,b=fixture(sense='max'),fixture(sense='min');p=self.compile(a,b,'objective','objective')
        self.assertEqual(repair_gate(problem(),a,b,b,p)['status'],'accepted_relative_to_evidence')

    def test_domain_edit_cannot_change_bounds(self):
        a,b=fixture('continuous'),fixture();p=self.compile(a,b,'domain','x');bad=deepcopy(b);bad['variables'][0]['upper']=3
        self.assertEqual(repair_gate(problem(),a,b,bad,p)['reason'],'write_scope_or_teacher_fragment_violation')

    def test_packet_tampering_and_stale_input(self):
        a,b=fixture(),fixture(row=True);p=self.compile(a,b,'row','cap');bad=deepcopy(p);bad['positive_examples']=[]
        self.assertEqual(repair_gate(problem(),a,b,b,bad)['reason'],'packet_modified')
        q=problem();q['text']+=' New instance.'
        self.assertEqual(repair_gate(q,a,b,b,p)['reason'],'stale_evidence')

    def test_fabricated_or_irrelevant_witness_rejected(self):
        a,b=fixture(),fixture(row=True);raw=raw_record(a,b,'row','cap')
        with self.assertRaises(Invalid):compile_record(raw,problem(),a,b,{'left_to_right':{'status':'witness','point':{'x':0}}})
        with self.assertRaises(Invalid):compile_record(raw,problem(),a,b,{'status':'compared'})

    def test_quote_and_positive_example_rechecked(self):
        a,b=fixture(),fixture(row=True);e=execute({'op':'compare','left':a,'right':b});raw=raw_record(a,b,'row','cap')
        raw['quote']['text']='made up'
        with self.assertRaises(Invalid):compile_record(raw,problem(),a,b,e)
        raw=raw_record(a,b,'row','cap',1)
        with self.assertRaises(Invalid):compile_record(raw,problem(),a,b,e)

    def test_v2_deterministically_binds_unique_quote_and_applies_edits(self):
        a,b=fixture('continuous'),fixture('integer');e=execute({'op':'compare','left':a,'right':b})
        raw=raw_record(a,b,'domain','x');raw['quote'].update(field='missing',start=99,end=100)
        packet=compile_record_v2(raw,problem(),a,b,e)
        self.assertEqual(packet['quote'],{'field':'text','text':problem()['text'],'start':0,'end':len(problem()['text'])})
        proposal=apply_teacher_edits(problem(),a,b,packet)
        self.assertEqual(proposal,b)
        self.assertEqual(repair_gate(problem(),a,b,proposal,packet)['status'],'accepted_relative_to_evidence')

    def test_v2_quote_binding_rejects_ambiguity(self):
        p=problem();p['text']='same same';a,b=fixture('continuous'),fixture('integer')
        raw=raw_record(a,b,'domain','x');raw.update(input_sha256=payload_sha256(p),
            model_hashes={'initial':digest(a),'teacher':digest(b)},quote={'field':'text','text':'same','start':0,'end':4})
        with self.assertRaisesRegex(Invalid,'uniquely'):compile_record_v2(raw,p,a,b,execute({'op':'compare','left':a,'right':b}))

    def test_v2_clause_gate_accepts_demonstrated_repair(self):
        a,b=fixture('continuous'),fixture('integer');packet=self.compile(a,b,'domain','x')
        tests={'schema':'clause-tests-v1','input_sha256':payload_sha256(problem()),
               'tests':[{'kind':'feasibility','point':{'x':.5},'expected_feasible':False},
                        {'kind':'feasibility','point':{'x':1},'expected_feasible':True}]}
        result=repair_gate_v2(problem(),a,b,b,packet,tests)
        self.assertEqual(result['status'],'accepted_relative_to_evidence')
        self.assertEqual((result['clause_tests_passed'],result['clause_tests_total']),(2,2))

    def test_v2_clause_gate_rejects_numerically_valid_harmful_repair(self):
        correct,faulty=fixture('integer'),fixture('continuous');packet=self.compile(correct,faulty,'domain','x',.5)
        tests={'schema':'clause-tests-v1','input_sha256':payload_sha256(problem()),
               'tests':[{'kind':'feasibility','point':{'x':.5},'expected_feasible':False}]}
        result=repair_gate_v2(problem(),correct,faulty,faulty,packet,tests)
        self.assertEqual(result['status'],'rejected');self.assertEqual(result['reason'],'clause_test_failed')

    def test_v2_clause_gate_rejects_stale_suite(self):
        a,b=fixture('continuous'),fixture('integer');packet=self.compile(a,b,'domain','x')
        tests={'schema':'clause-tests-v1','input_sha256':'0'*64,
               'tests':[{'kind':'feasibility','point':{'x':.5},'expected_feasible':False}]}
        self.assertEqual(repair_gate_v2(problem(),a,b,b,packet,tests)['reason'],'stale_clause_tests')

    def test_semantic_decision_compiler_owns_mechanical_fields(self):
        a,b=fixture('continuous'),fixture('integer');e=execute({'op':'compare','left':a,'right':b})
        catalog=build_catalog(problem(),a,b,e);self.assertEqual(len(catalog['candidates']),1)
        raw={'schema':'semantic-decision-v1','status':'reviewed',
             'decisions':[{'candidate_id':'candidate_0','verdict':'teacher','quote_text':'whole items',
                           'interpretation':'The count must be integral.'}]}
        compiled=compile_decision(validate_decision(raw,catalog),problem(),a,b,e,catalog)
        proposal=apply_teacher_edits(problem(),a,b,compiled['packet'])
        result=repair_gate_v2(problem(),a,b,proposal,compiled['packet'],compiled['clause_tests'])
        self.assertEqual(result['status'],'accepted_relative_to_evidence')
        self.assertNotIn('start',raw['decisions'][0]);self.assertNotIn('edits',raw)

    def test_semantic_decision_can_retain_initial_or_abstain(self):
        a,b=fixture('continuous'),fixture('integer');e=execute({'op':'compare','left':a,'right':b});catalog=build_catalog(problem(),a,b,e)
        raw={'schema':'semantic-decision-v1','status':'reviewed',
             'decisions':[{'candidate_id':'candidate_0','verdict':'initial','quote_text':'whole items',
                           'interpretation':'Synthetic retention decision.'}]}
        self.assertEqual(compile_decision(raw,problem(),a,b,e,catalog)['packet']['status'],'unresolved')
        raw={'schema':'semantic-decision-v1','status':'unresolved','decisions':[]}
        self.assertEqual(compile_decision(raw,problem(),a,b,e,catalog)['packet']['reason'],'semantic_abstention')

    def test_semantic_catalog_does_not_treat_generated_row_names_as_identity(self):
        a,b=fixture(),fixture(row=True);e=execute({'op':'compare','left':a,'right':b});catalog=build_catalog(problem(),a,b,e)
        self.assertEqual(catalog['candidates'],[]);self.assertEqual(catalog['unmatched_rows_omitted'],1)

    def test_semantic_consensus_requires_two_teacher_votes(self):
        a,b=fixture('continuous'),fixture('integer');e=execute({'op':'compare','left':a,'right':b});catalog=build_catalog(problem(),a,b,e)
        teacher={'schema':'semantic-decision-v1','status':'reviewed','decisions':[{
            'candidate_id':'candidate_0','verdict':'teacher','quote_text':'whole items','interpretation':'Integer.'}]}
        initial=deepcopy(teacher);initial['decisions'][0]['verdict']='initial'
        self.assertEqual(compile_consensus(teacher,initial,problem(),a,b,e,catalog)['packet']['reason'],
                         'no_unanimous_teacher_clause')
        compiled=compile_consensus(teacher,teacher,problem(),a,b,e,catalog)
        self.assertEqual(compiled['packet']['status'],'repair');self.assertEqual(compiled['packet']['consensus_reviews'],2)

    def test_solver_limit_rolls_back(self):
        a,b=fixture(),fixture(row=True);p=self.compile(a,b,'row','cap')
        result=repair_gate(problem(),a,b,b,p,solver=lambda op:{'status':'limit'})
        self.assertEqual(result['retained_model'],a);self.assertEqual(result['reason'],'proposal_not_certified_optimal')

    def test_teacher_interface_does_not_force_initial_domains(self):
        p=make_payload(problem(),'teacher_model',interface=[{'id':'x','meaning':'number','unit':'items'}],objective_unit='items')
        self.assertNotIn('domain',p['context']['interface'][0])

    def test_whole_source_record_rejected_before_request(self):
        p=problem();p['reference']={'objective':999}
        with self.assertRaises(Invalid):make_payload(p,'initial')

    def test_machine_response_contract_rejects_request_envelope(self):
        with self.assertRaises(Invalid):validate_output(make_payload(problem(),'initial'))

    def test_sparse_contract_does_not_silently_accept_unknown_variables(self):
        m=fixture();m['objective']['coefficients']['unknown']=3
        with self.assertRaises(Invalid):validate_output(m)

    def test_offline_pipeline_uses_shared_ledger_and_rolls_back_bad_patch(self):
        a,b=fixture('continuous'),fixture();raw=raw_record(a,b,'domain','x');bad=deepcopy(b);bad['objective']['offset']=99
        replies={k:MockReply(text=json.dumps(v)) for k,v in {'initial':a,'baseline_repair':a,'teacher_model':b,'teacher_feedback':raw,'semantic_repair':bad}.items()}
        with tempfile.TemporaryDirectory() as d:
            gateway=Gateway(d,Limits(requests=5,per_problem=5,input_bytes=100000,output_bytes=100000))
            out=run_milp_problem(problem(),gateway,replies)
            self.assertEqual(out['semantic_final'],a);self.assertEqual(out['repair_gate']['status'],'rejected')
            import sqlite3
            with sqlite3.connect(gateway.db) as db:self.assertEqual(db.execute('SELECT count(*) FROM attempts').fetchone()[0],5)

    def test_old_live_authorization_cannot_enable_new_pipeline(self):
        class FakeLive:
            mode='approved_live_old'
        with self.assertRaises(Invalid):run_milp_problem(problem(),FakeLive(),{})


if __name__=='__main__':unittest.main()
