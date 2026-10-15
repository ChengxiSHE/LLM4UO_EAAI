import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from evaluate_pilot import align
from llm4or.fixtures import triangle
from llm4or.schema import digest
from llm4or.alignment import align_units


class MappingTests(unittest.TestCase):
    def data(self):
        reference = triangle()
        candidate = copy.deepcopy(reference)
        candidate['variables'][0]['meaning'] = 'Production of x, in tonnes'
        candidate['variables'][0]['unit'] = 'tonnes'
        candidate['variables'][0]['lower'] = 0.2
        candidate['constraints'][0]['rhs'] = 0.8
        review = {'candidate_hash':digest(candidate), 'reference_hash':digest(reference),
                  'status':'semantic_mapping_reviewed', 'rationale':'Same business quantities and unit synonyms.',
                  'variable_mapping':{'x':'x','y':'y'}, 'unit_scale':1, 'objective_scale':1}
        return candidate, reference, review

    def test_mapping_does_not_fix_wrong_constraints_or_bounds(self):
        c,r,a = self.data(); mapped = align(c,r,a)
        self.assertEqual(mapped['variables'][0]['lower'], 0.2)
        self.assertEqual(mapped['constraints'][0]['rhs'], 0.8)
        self.assertEqual(c['variables'][0]['unit'],'tonnes')

    def test_stale_mapping_rejected(self):
        c,r,a = self.data(); c['constraints'][0]['rhs'] = 0.7
        with self.assertRaises(ValueError): align(c,r,a)

    def test_many_to_one_mapping_rejected(self):
        c,r,a = self.data(); a['variable_mapping']['x'] = 'y'
        with self.assertRaises(ValueError): align(c,r,a)

    def test_unreviewed_scale_rejected(self):
        c,r,a = self.data(); a['unit_scale'] = 1000
        with self.assertRaises(ValueError): align(c,r,a)

    def test_reviewed_unit_conversion_preserves_wrong_rhs_and_objective_direction(self):
        c,r,a=self.data()
        c['objective']['sense']='min';a['candidate_hash']=digest(c)
        a.update(reference_quantity_per_candidate_unit={'x':0.5,'y':2},reference_objective_unit_per_candidate_unit=3)
        result=align_units(c,r,a)
        self.assertEqual(result['constraints'][0]['rhs'],0.8)
        self.assertEqual(result['constraints'][0]['coefficients'],{'x':2,'y':0.5})
        self.assertEqual(result['variables'][0]['lower'],0.1)
        self.assertEqual(result['objective']['sense'],'min')
        self.assertEqual(result['objective']['coefficients']['x'],6)

    def test_negative_unit_conversion_refused(self):
        c,r,a=self.data()
        a.update(reference_quantity_per_candidate_unit={'x':-1,'y':1},reference_objective_unit_per_candidate_unit=1)
        with self.assertRaises(ValueError):align_units(c,r,a)


if __name__ == '__main__': unittest.main()
