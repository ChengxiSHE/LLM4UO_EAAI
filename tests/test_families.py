import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from llm4or.families import group_candidates, public_inventory
from llm4or.schema import validate_public

ROOT=Path(__file__).resolve().parents[1]


class FamilyTests(unittest.TestCase):
    def test_number_variants_grouped_without_answers(self):
        records=[{'id':'a','text':'Make 20 chairs with 70 hours.'},
                 {'id':'b','text':'Make 90 chairs with 30 hours.'},
                 {'id':'c','text':'Blend vitamin supplements for nutrition.'}]
        groups,membership,edges=group_candidates(records)
        self.assertEqual(membership['a'],membership['b'])
        self.assertNotEqual(membership['a'],membership['c'])
        self.assertTrue(any(e['reason']=='number_masked_exact' for e in edges))

    def test_named_problem_quarantine_survives_low_lexical_similarity(self):
        records=[{'id':'a','text':'Wilson Creek Farm: wheat, labor, acres.'},
                 {'id':'b','text':'Plan water consumption of soybeans at Wilson Creek Farm.'}]
        _,membership,edges=group_candidates(records,threshold=1)
        self.assertEqual(membership['a'],membership['b'])
        self.assertTrue(any(e['reason']=='reviewed_named_problem:wilson_crop' for e in edges))

    def test_membership_stable_under_input_order(self):
        r=[{'id':'a','text':'Wilson Creek Farm with 30 acres'},
           {'id':'b','text':'Wilson Creek Farm with 50 acres'},
           {'id':'c','text':'Nutrition vitamins'}]
        self.assertEqual(group_candidates(r)[1],group_candidates(r[::-1])[1])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            group_candidates([{'id':'a','text':'alpha'},{'id':'a','text':'beta'}])

    def test_empty_and_tokenless_inputs(self):
        self.assertEqual(group_candidates([]),([],{},[]))
        self.assertEqual(len(group_candidates([{'id':'a','text':'?'},{'id':'b','text':'!'}])[0]),2)

    def test_public_inventory_projects_labels_and_code_away(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'fixture.json'
            path.write_text(json.dumps([{'question':'Public question','answer':'SECRET_ANSWER',
                                        'code':'DO_NOT_EXECUTE','type':'linear-table'}]))
            manifest={'records':[{'local_path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]}
            records=public_inventory(root,manifest)
            self.assertEqual(records[0]['text'],'Public question')
            self.assertNotIn('SECRET_ANSWER',json.dumps(records))
            self.assertNotIn('DO_NOT_EXECUTE',json.dumps(records))
            path.write_text('[]')
            with self.assertRaises(ValueError): public_inventory(root,manifest)

    def test_prepared_inputs_and_quarantine_consistent(self):
        path=ROOT/'data/next_development/manifest.json'
        if not path.exists(): self.skipTest('development preparation has not run')
        manifest=json.loads(path.read_text())
        audit=json.loads((ROOT/'data/next_development/family_audit.json').read_text())
        public=[validate_public(json.loads(line)) for line in (ROOT/'data/next_development/public/problems.jsonl').read_text().splitlines()]
        self.assertEqual({p['id'] for p in public},{e['id'] for e in manifest['entries']})
        by_id={r['id']:r for r in audit['records']}
        quarantine={r['candidate_component'] for r in audit['records'] if r['split_status']=='quarantine_development'}
        for entry in manifest['entries']:
            self.assertEqual(by_id[entry['source_public_id']]['split_status'],'quarantine_development')
            self.assertFalse(entry['approved_for_api'])
        for row in audit['records']:
            if row['candidate_component'] in quarantine:
                self.assertEqual(row['split_status'],'quarantine_development')
            if row['source_path'].endswith('nl4opt__nl4opt-competition/generation_data/dev.jsonl'):
                self.assertEqual(row['split_status'],'quarantine_development')
        self.assertFalse(audit['formal_test_split_created'])


if __name__=='__main__':unittest.main()
