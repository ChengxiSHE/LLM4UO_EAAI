from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from llm4or.fresh_family_gate import FreshFamilyGate
from llm4or.schema import Invalid


def manifest():
    return dict(schema='reviewed-family-split-v1',review_status='reviewed',families=[
        dict(id='family_a',members=['a1','a2'],role='update_gate',review_note='Synthetic same-template variants kept together.'),
        dict(id='family_b',members=['b1'],role='update_gate',review_note='Synthetic distinct template.'),
        dict(id='test_family',members=['t1'],role='locked_test',review_note='Synthetic held-out fixture.')])


class FreshGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'gate.sqlite3';self.gate=FreshFamilyGate(self.path,manifest())
    def tearDown(self):self.tmp.cleanup()
    def test_unreviewed_lexical_components_rejected(self):
        with self.assertRaises(Invalid):FreshFamilyGate(self.path,dict(schema='benchmark-family-isolation-v1'))
    def test_duplicate_template_members_rejected(self):
        m=manifest();m['families'][1]['members'].append('a2')
        with self.assertRaises(Invalid):FreshFamilyGate(self.path,m)
    def test_test_family_cannot_be_gate(self):
        with self.assertRaises(Invalid):self.gate.reserve(1,'a'*64,'b'*64,['test_family'])
    def test_precommit_and_exact_denominator(self):
        with self.assertRaises(Invalid):self.gate.evaluate(1,'b'*64,{'family_a':[False,True]})
        self.gate.reserve(1,'a'*64,'b'*64,['family_a','family_b'])
        with self.assertRaises(Invalid):self.gate.evaluate(1,'b'*64,{'family_a':[False,True]})
        with self.assertRaises(Invalid):self.gate.evaluate(1,'c'*64,{'family_a':[False,True],'family_b':[False,True]})
    def test_freshness_survives_restart_and_failed_candidate(self):
        self.gate.reserve(1,'a'*64,'b'*64,['family_a'])
        result=self.gate.evaluate(1,'b'*64,{'family_a':[True,False]});self.assertFalse(result['accept'])
        other=FreshFamilyGate(self.path,manifest())
        with self.assertRaises(Invalid):other.reserve(2,'a'*64,'c'*64,['family_a'])
        with self.assertRaises(Invalid):other.evaluate(1,'b'*64,{'family_a':[False,True]})
        other.reserve(2,'a'*64,'c'*64,['family_b'])
    def test_split_change_cannot_reset_ledger(self):
        m=manifest();m['families'][0]['review_note']='changed'
        with self.assertRaises(Invalid):FreshFamilyGate(self.path,m)
    def test_previous_generation_must_finish_and_inherit(self):
        self.gate.reserve(1,'a'*64,'b'*64,['family_a'])
        with self.assertRaises(Invalid):self.gate.reserve(2,'a'*64,'c'*64,['family_b'])
        self.gate.evaluate(1,'b'*64,{'family_a':[True,False]})
        with self.assertRaises(Invalid):self.gate.reserve(2,'b'*64,'c'*64,['family_b'])
