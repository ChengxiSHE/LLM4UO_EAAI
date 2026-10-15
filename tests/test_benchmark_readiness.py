import ast
from copy import deepcopy
import json
from pathlib import Path
import unittest

from llm4or.benchmark_inputs import payload_sha256
from llm4or.benchmark_registry import triage,load_public_registry,consistency_issues
from llm4or.reference_audit import parse_native,evaluate_bound
from llm4or.reference_builders import build_reference
from llm4or.reference_certificates import certify_discrete,certify_lp
from llm4or.milp_solver import execute
from llm4or.schema import digest,Invalid

ROOT=Path(__file__).resolve().parents[1]
def public(text='Choose whole numbers to maximize return.'):
    return dict(id='test_problem',profile='description_parameters_v1',text=text,parameters=[],instances=[])


class ReadinessTests(unittest.TestCase):
    def test_absent_keyword_never_certifies_lp(self):
        r=triage(public('Find the best plan.'))
        self.assertIsNone(r['certified_problem_type']);self.assertTrue(r['review_required'])

    def test_type_quotes_are_exact_and_not_answers(self):
        p=public('Use mixed integer linear programming, with a quadratic penalty.')
        r=triage(p);self.assertEqual(r['type_triage'],'nonlinear_or_conflicting')
        for e in r['evidence']:self.assertEqual(p['text'][e['start']:e['end']],e['quote'])
        p['answer']=7
        with self.assertRaises(Invalid):triage(p)

    def test_complete_registry_and_revision(self):
        rows=load_public_registry(ROOT)
        self.assertEqual(len(rows),1356);self.assertEqual(len({r['id'] for r in rows}),1356)
        bad={r['id'] for r in rows if r['input_status']!='ready'}
        self.assertEqual(bad,{'complexor_cut','complexor_fleet','complexor_net1','complexor_netmcol'})

    def test_cut_physical_violation_uses_only_input(self):
        p=dict(id='complexor_cut',instances=[dict(id='one',input=dict(NumPatterns=1,NumWidths=2,Widths=[60,70],NumRollsWidthPattern=[[1],[1]],RollWidth=100))])
        self.assertEqual(consistency_issues(p)[0]['used_width'],130)

    def test_strict_native_numeric(self):
        self.assertEqual(parse_native(' 1.25e2 ')['objective'],125)
        for x in [True,None,float('nan'),'profit=125','125 or 150','NaN','1,200']:
            self.assertEqual(parse_native(x)['parse_status'],'unresolved')

    def test_native_status_not_collapsed(self):
        self.assertEqual(parse_native('infeasible')['status'],'infeasible')
        self.assertEqual(parse_native('unbounded')['status'],'unbounded')
        self.assertEqual(parse_native('infeasible or unbounded')['parse_status'],'unresolved')
        self.assertEqual(parse_native('-1')['status'],'optimal')

    def test_dict_never_selects_between_multiple_objectives(self):
        self.assertEqual(parse_native({'Total profit':3,'Minimum cost':2})['parse_status'],'unresolved')
        result=parse_native({'Total profit':3,'x':2});self.assertFalse(result['field_selection_reviewed'])

    def test_singleton_output_only_explicit(self):
        self.assertEqual(parse_native([3])['parse_status'],'unresolved')
        self.assertEqual(parse_native([3],singleton_list=True)['objective'],3)
        self.assertEqual(parse_native([3,4],singleton_list=True)['parse_status'],'unresolved')

    def test_reference_binding_blocks_stale_input_without_solver(self):
        p=public(); r=dict(problem_id=p['id'],input_sha256=payload_sha256(p),audit_status='native_parsed_not_independently_certified')
        def prohibited(_):raise AssertionError('solver must not run')
        self.assertEqual(evaluate_bound(None,p,r,solver=prohibited)['grade_reason'],'reference_not_ready')
        p['text']+=' Changed.'
        self.assertEqual(evaluate_bound(None,p,r,solver=prohibited)['grade_reason'],'stale_or_wrong_input_reference')

    def test_reference_binary_oracle_refutes_wrong_optimum(self):
        m=dict(schema='milp-v1',variables=[dict(id='x',meaning='choose',unit='1',domain='binary',lower=None,upper=None)],constraints=[],objective=dict(coefficients={'x':2},sense='max',unit='1',offset=0))
        self.assertTrue(certify_discrete(m,{'status':'optimal','objective':2})['verified'])
        self.assertFalse(certify_discrete(m,{'status':'optimal','objective':3})['verified'])

    def test_lp_dual_verification_does_not_trust_fake_certificate(self):
        m=dict(schema='milp-v1',variables=[dict(id='x',meaning='amount',unit='1',domain='continuous',lower=0,upper=2)],constraints=[],objective=dict(coefficients={'x':1},sense='max',unit='1',offset=0))
        result=certify_lp(m,execute({'op':'solve','model':m}))
        self.assertTrue(result['verified'])
        def bad(_):return {'status':'optimal','point':{'dual_0':0,'dual_1':0}}
        self.assertFalse(certify_lp(m,{'status':'optimal','point':{'x':2}},bad)['verified'])

    def test_no_reference_imports_in_new_inference_modules(self):
        for file in ('milp_pipeline.py','milp_feedback.py'):
            tree=ast.parse((ROOT/'llm4or'/file).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom):self.assertNotIn('reference',node.module or '')

    def test_reference_builder_rejects_bad_cut_not_crop(self):
        r=next(r for r in load_public_registry(ROOT) if r['id']=='complexor_cut')
        with self.assertRaisesRegex(Invalid,'pattern_exceeds_roll_width'):build_reference(r['public'])

    def test_reference_builder_not_general_model_generator(self):
        with self.assertRaises(Invalid):build_reference(public())
