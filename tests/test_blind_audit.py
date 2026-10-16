import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.score_v5_blind_audit import score


def write(path,value):
    Path(path).write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')


class BlindAuditTests(unittest.TestCase):
    def fixture(self,directory):
        directory=Path(directory);packet={'items':[{'audit_id':'audit_one'}]};key={'items':[
            {'audit_id':'audit_one','family_id':'family_one','contract_candidate_changed':True,
             'pair_mapping':{'A':'initial','B':'contract_candidate'}}]}
        write(directory/'audit_packet.json',packet);write(directory/'audit_key.json',key)
        packet_sha=hashlib.sha256((directory/'audit_packet.json').read_bytes()).hexdigest()
        key_sha=hashlib.sha256((directory/'audit_key.json').read_bytes()).hexdigest()
        manifest=directory/'manifest.json';write(manifest,{'packet_sha256':packet_sha,'key_sha256':key_sha})
        return packet_sha,manifest

    def review(self,identifier,packet_sha,preference='B'):
        return {'reviewer_id':identifier,'packet_sha256':packet_sha,'sealed':True,'answers':[{
            'audit_id':'audit_one','contract_faithfulness':'correct',
            'preferred_complete_model':preference,'interface_sufficient':'yes',
            'confidence':'high','rationale':'The public clause and algebra support this choice.'}]}

    def test_two_sealed_reviews_unblind_only_to_aggregate(self):
        with tempfile.TemporaryDirectory() as d:
            packet_sha,manifest=self.fixture(d);write(Path(d)/'reviewer_1_answers.json',self.review('r1',packet_sha))
            write(Path(d)/'reviewer_2_answers.json',self.review('r2',packet_sha))
            write(Path(d)/'adjudicator_answers.json',{'reviewer_id':None,'packet_sha256':packet_sha,'sealed':False,'answers':[]})
            result=score(d,Path(d)/'summary.json',manifest)
            self.assertEqual(result['counts']['changed:improvement'],1)
            self.assertEqual(result['family_counts']['families_with_improvement'],1)
            self.assertNotIn('audit_one',json.dumps(result))

    def test_disagreement_requires_distinct_sealed_adjudicator(self):
        with tempfile.TemporaryDirectory() as d:
            packet_sha,manifest=self.fixture(d);write(Path(d)/'reviewer_1_answers.json',self.review('r1',packet_sha,'B'))
            write(Path(d)/'reviewer_2_answers.json',self.review('r2',packet_sha,'A'))
            write(Path(d)/'adjudicator_answers.json',{'reviewer_id':None,'packet_sha256':packet_sha,'sealed':False,'answers':[]})
            with self.assertRaisesRegex(ValueError,'independent_adjudicator_required'):
                score(d,Path(d)/'summary.json',manifest)
            write(Path(d)/'adjudicator_answers.json',self.review('r3',packet_sha,'B'))
            result=score(d,Path(d)/'summary.json',manifest)
            self.assertTrue(result['adjudicator_used']);self.assertEqual(result['counts']['changed:improvement'],1)

    def test_same_reviewer_and_stale_packet_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            packet_sha,manifest=self.fixture(d);write(Path(d)/'reviewer_1_answers.json',self.review('r1',packet_sha))
            write(Path(d)/'reviewer_2_answers.json',self.review('r1',packet_sha))
            write(Path(d)/'adjudicator_answers.json',{'reviewer_id':None,'packet_sha256':packet_sha,'sealed':False,'answers':[]})
            with self.assertRaisesRegex(ValueError,'reviewers_must_be_distinct'):
                score(d,Path(d)/'summary.json',manifest)
            stale=self.review('r2','0'*64);write(Path(d)/'reviewer_2_answers.json',stale)
            with self.assertRaisesRegex(ValueError,'review_packet_mismatch'):
                score(d,Path(d)/'summary.json',manifest)


if __name__=='__main__':unittest.main()
