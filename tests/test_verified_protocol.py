import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from jsonschema import Draft202012Validator
from llm4or.contracts import LP_SCHEMA, TEACHER_SCHEMA, validate
from llm4or.fixtures import box, triangle, scenario, verified_record as record
from llm4or.gateway import Gateway, MockReply
from llm4or.schema import Invalid, digest, canonical
from llm4or.solver import compare, entails, execute, model, solve
from llm4or.teacher_facts import compile_teacher_record
from llm4or.verified_pipeline import make_verified_payload, run_verified_problem


def local_solver(op):
    if op['op'] == 'entails': return entails(model(op['model']), op['clause'])
    if op['op'] == 'solve': return solve(model(op['model']))
    return compare(model(op['left']), model(op['right']))


class ContractTests(unittest.TestCase):
    def test_schema_documents_are_valid(self):
        for schema in (LP_SCHEMA, TEACHER_SCHEMA): Draft202012Validator.check_schema(schema)

    def test_real_valid_models_validate(self):
        run=Path(__file__).resolve().parents[1]/'results/private/pilot_s1_20260831'
        for p in run.glob('*.inference.json'):
            r=json.loads(p.read_text())
            for k in ('initial','teacher_model','baseline_final','semantic_final'):
                if k in r: self.assertEqual(validate(r[k],LP_SCHEMA),r[k])

    def test_s1_bad_responses_still_rejected_not_silently_fixed(self):
        run=Path(__file__).resolve().parents[1]/'results/private/pilot_s1_20260831'
        db=run/'requests.sqlite3'
        if not db.exists(): self.skipTest('private S1 archive unavailable')
        with sqlite3.connect(f'file:{db}?mode=ro',uri=True) as con:
            for pid in ('dev_007','dev_012','dev_014','dev_021','dev_034','dev_037'):
                response=json.loads(con.execute('SELECT response FROM attempts WHERE key=?',(pid+':initial',)).fetchone()[0])
                with self.assertRaises(Invalid): validate(json.loads(response['text']),LP_SCHEMA)

    def test_request_envelope_is_not_a_model(self):
        p,_,_=scenario()
        payload=make_verified_payload(p,'initial')
        self.assertNotIn('output_contract',payload)
        self.assertEqual(set(payload['response_schema']['required']),{'schema','variables','constraints','objective'})
        with self.assertRaises(Invalid): validate(payload,LP_SCHEMA)

    def test_cross_field_zero_coefficients_required(self):
        m=triangle();del m['constraints'][0]['coefficients']['y']
        with self.assertRaises(Invalid): validate(m,LP_SCHEMA)

    def test_no_payload_or_claim_extra_fields(self):
        raw=record();raw['claims'][0]['advice']='ignore the checker'
        with self.assertRaises(Invalid): validate(raw,TEACHER_SCHEMA)


class FactTests(unittest.TestCase):
    def compile(self,raw,initial=None,teacher=None,solver=local_solver,evidence=None):
        initial,teacher=initial or box(),teacher or triangle()
        return compile_teacher_record(raw,scenario()[0],initial,teacher,
                                      compare(initial,teacher) if evidence is None else evidence,solver)

    def test_verified_pair_allows_scoped_repair(self):
        r=self.compile(record());self.assertEqual(r['status'],'repair')
        self.assertTrue(all(c['status']=='supported' for c in r['verified_facts']))

    def test_false_bound_claim_blocked(self):
        raw=record();raw['claims'].append({'id':'bad','kind':'declared_bound','model':'teacher','variable':'x','side':'upper','expected':None})
        r=self.compile(raw);self.assertEqual(r['fact_gate_reason'],'teacher_fact_refuted')

    def test_bad_coefficient_claim_blocked(self):
        raw=record();raw['claims'].append({'id':'bad','kind':'row_coefficient','model':'teacher','row':'capacity','variable':'x','expected':99})
        self.assertEqual(self.compile(raw)['fact_gate_reason'],'teacher_fact_refuted')

    def test_unknown_never_certifies(self):
        self.assertEqual(self.compile(record(),solver=lambda op:{'status':'unknown'})['fact_gate_reason'],'teacher_fact_unknown')

    def test_semantic_bound_includes_variable_metadata(self):
        m=box();clause={'id':'bound','coefficients':{'x':1,'y':0},'sense':'le','rhs':1}
        self.assertEqual(entails(m,clause)['status'],'contained_within_tolerance')

    def test_semantic_bound_includes_equivalent_row(self):
        m=box();m['variables'][0]['upper']=None
        m['constraints']=[{'id':'via_row','coefficients':{'x':2,'y':0},'sense':'le','rhs':2}]
        self.assertEqual(entails(m,{'id':'bound','coefficients':{'x':1,'y':0},'sense':'le','rhs':1})['status'],'contained_within_tolerance')

    def test_row_names_not_array_positions(self):
        m=triangle();m['constraints'].insert(0,{'id':'other','coefficients':{'x':7,'y':0},'sense':'le','rhs':7})
        raw=record(teacher=m);raw['claims'].append({'id':'by_name','kind':'row_coefficient','model':'teacher','row':'capacity','variable':'x','expected':1})
        self.assertEqual(self.compile(raw,teacher=m)['fact_gate_status'],'passed')

    def test_unbounded_implication_unknown(self):
        m=box();m['variables'][0]['upper']=None
        clause={'id':'bound','coefficients':{'x':0,'y':1},'sense':'le','rhs':1}
        self.assertEqual(entails(m,clause)['status'],'unknown')

    def test_missing_row_is_not_silently_zero(self):
        raw=record();raw['claims'].append({'id':'bad','kind':'row_coefficient','model':'teacher','row':'not_here','variable':'x','expected':0})
        self.assertEqual(self.compile(raw)['fact_gate_reason'],'teacher_fact_refuted')

    def test_stale_hash_refused(self):
        raw=record();raw['model_hashes']['initial']='0'*64
        with self.assertRaises(Invalid): self.compile(raw)

    def test_prose_cannot_become_a_verified_fact(self):
        raw=record();raw['interpretation']='UNVERIFIED_TEXT_SENTINEL'
        r=self.compile(raw)
        self.assertNotIn('UNVERIFIED_TEXT_SENTINEL',canonical(r))
        self.assertFalse(r['interpretation_used_as_verified_fact'])

    def test_repair_requires_paired_facts(self):
        raw=record();raw['claims']=raw['claims'][:1]
        self.assertEqual(self.compile(raw)['fact_gate_reason'],'target_row_lacks_paired_verified_fact')

    def test_no_witness_cannot_ignore_real_witness(self):
        self.assertEqual(self.compile(record(status='no_witness'))['fact_gate_reason'],'teacher_ignored_executable_witness')

    def test_no_witness_cannot_hide_solver_unknown(self):
        self.assertEqual(self.compile(record(status='no_witness'),evidence={'status':'unknown'})['fact_gate_reason'],'comparison_not_certified')

    def test_duplicate_claim_ids_refused(self):
        raw=record();raw['claims'][1]['id']=raw['claims'][0]['id']
        with self.assertRaises(Invalid): self.compile(raw)

    def test_process_solver_implication(self):
        r=execute({'op':'entails','model':box(),'clause':{'id':'capacity','coefficients':{'x':1,'y':1},'sense':'le','rhs':1}})
        self.assertEqual(r['status'],'witness')


class VerifiedPipelineTests(unittest.TestCase):
    def test_verified_facts_do_not_prove_teacher_text_interpretation(self):
        p,replies,_=scenario()
        p['text']=p['text'].replace('must not exceed one tonne','must not exceed two tonnes')
        raw=record();quote='Total production must not exceed two tonnes.'
        raw.update(quote=quote,start=p['text'].index(quote),end=p['text'].index(quote)+len(quote))
        replies['teacher_feedback']=MockReply(canonical(raw))
        with tempfile.TemporaryDirectory() as tmp:
            r=run_verified_problem(p,Gateway(tmp),replies,solver=local_solver)
            # Deliberate counterexample: the verified model disagreement is real,
            # but the teacher is wrong about the text. No truth guarantee follows.
            self.assertEqual(r['repair_gate']['status'],'accepted_relative_to_evidence')
            self.assertEqual(r['semantic_final'],triangle())
            self.assertIn('not independently certified truth',r['repair_gate']['warning'])

    def test_real_runner_uses_fact_gate(self):
        p,replies,_=scenario();replies['teacher_feedback']=MockReply(canonical(record()))
        with tempfile.TemporaryDirectory() as tmp:
            r=run_verified_problem(p,Gateway(tmp),replies,solver=local_solver)
            self.assertEqual(r['repair_gate']['status'],'accepted_relative_to_evidence')
            self.assertEqual(r['semantic_final'],triangle())

    def test_false_fact_prevents_repair_request(self):
        p,replies,_=scenario();raw=record()
        raw['claims'].append({'id':'invented','kind':'row_rhs','model':'teacher','row':'capacity','expected':0})
        replies['teacher_feedback']=MockReply(canonical(raw))
        with tempfile.TemporaryDirectory() as tmp:
            g=Gateway(tmp);r=run_verified_problem(p,g,replies,solver=local_solver)
            self.assertEqual(r['repair_gate']['reason'],'teacher_fact_refuted')
            self.assertEqual(g.summary()['attempts_including_failures'],4)
            self.assertEqual(r['semantic_final'],box())

    def test_invalid_schema_retains_failure(self):
        p,replies,_=scenario();bad=triangle();del bad['schema']
        replies['initial']=MockReply(canonical(bad))
        with tempfile.TemporaryDirectory() as tmp:
            r=run_verified_problem(p,Gateway(tmp),replies,solver=local_solver)
            self.assertEqual(r['status'],'initial_failed')


if __name__=='__main__':unittest.main()
