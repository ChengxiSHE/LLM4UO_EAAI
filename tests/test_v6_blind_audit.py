import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.score_v6_blind_audit import score


def write(path,value):
    Path(path).write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')


class V6BlindAuditTests(unittest.TestCase):
    def review(self,reviewer,packet_sha,identifiers):
        return {'reviewer_id':reviewer,'packet_sha256':packet_sha,'sealed':True,'answers':[{
            'audit_id':identifier,'contract_faithfulness':'correct','preferred_complete_model':'B',
            'interface_sufficient':'yes','confidence':'high',
            'rationale':'The question requests a count of indivisible objects.'} for identifier in identifiers]}

    def run_fixture(self,families):
        temporary=tempfile.TemporaryDirectory();directory=Path(temporary.name)
        identifiers=[f'audit_{i}' for i in range(len(families))]
        write(directory/'audit_packet.json',{'items':[{'audit_id':x} for x in identifiers]})
        write(directory/'audit_key.json',{'items':[
            {'audit_id':identifier,'family_id':family,'contract_candidate_changed':True,
             'pair_mapping':{'A':'initial','B':'contract_candidate'}}
            for identifier,family in zip(identifiers,families)]})
        packet_sha=hashlib.sha256((directory/'audit_packet.json').read_bytes()).hexdigest()
        key_sha=hashlib.sha256((directory/'audit_key.json').read_bytes()).hexdigest()
        write(directory/'manifest.json',{'packet_sha256':packet_sha,'key_sha256':key_sha})
        write(directory/'reviewer_1_answers.json',self.review('r1',packet_sha,identifiers))
        write(directory/'reviewer_2_answers.json',self.review('r2',packet_sha,identifiers))
        write(directory/'adjudicator_answers.json',{'reviewer_id':None,'packet_sha256':packet_sha,'sealed':False,'answers':[]})
        result=score(directory,directory/'summary.json',directory/'manifest.json')
        return temporary,result

    def test_five_improving_families_pass_targeted_rule(self):
        temporary,result=self.run_fixture([f'family_{i}' for i in range(5)])
        self.addCleanup(temporary.cleanup)
        self.assertTrue(result['targeted_mechanism_success'])
        self.assertFalse(result['overall_benchmark_accuracy_claim_eligible'])
        self.assertNotIn('audit_0',json.dumps(result))

    def test_four_improving_families_do_not_pass_targeted_rule(self):
        temporary,result=self.run_fixture([f'family_{i}' for i in range(4)])
        self.addCleanup(temporary.cleanup)
        self.assertFalse(result['targeted_mechanism_success'])


if __name__=='__main__':unittest.main()
