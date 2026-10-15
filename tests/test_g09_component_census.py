import json
from pathlib import Path
import unittest

from llm4or.g09_component_census import OUTPUT_PATH, build_census, render_markdown
from llm4or.schema import canonical


ROOT = Path(__file__).resolve().parents[1]


class G09ComponentCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = build_census(ROOT)

    def test_typed_candidate_census_is_complete_and_resource_effect_is_exact(self):
        section = self.value["admission_census"]
        self.assertEqual(section["population"], 64)
        self.assertEqual(section["unique_candidate_hashes"], 64)
        arms = {row["arm"]: row for row in section["arms"]}
        self.assertEqual((arms["full"]["admitted"], arms["full"]["unsafe_admissions"]), (1, 0))
        self.assertEqual((arms["no_semantic"]["admitted"], arms["no_semantic"]["unsafe_admissions"]), (12, 11))
        self.assertEqual((arms["no_resource"]["admitted"], arms["no_resource"]["unsafe_admissions"]), (6, 5))
        self.assertEqual(section["semantic_resource_cells"], {
            "semantic_0_resource_0": 47,
            "semantic_0_resource_1": 11,
            "semantic_1_resource_0": 5,
            "semantic_1_resource_1": 1,
        })
        self.assertEqual(section["paired_full_vs_no_semantic"], {
            "full_prevents_unsafe_admission": 11,
            "no_semantic_prevents_safe_admission": 0,
            "same_decision": 53,
        })
        self.assertEqual(section["paired_full_vs_no_resource"], {
            "full_prevents_unsafe_admission": 5,
            "no_resource_prevents_safe_admission": 0,
            "same_decision": 59,
        })
        self.assertEqual(section["semantic_identifiability"], "identified_non_nested_complete_finite_grammar")
        self.assertTrue(self.value["claim_boundary"]["semantic_gate_effect_identified_in_typed_count_grammar"])
        report = render_markdown(self.value)
        self.assertIn("Removing the semantic gate accepts 12/64", report)
        self.assertIn("11 unsafe admissions", report)
        self.assertIn("all four semantic/resource cells", report)

    def test_routing_envelope_census_covers_zero_unique_multiple_and_shifts(self):
        section = self.value["routing_census"]
        self.assertEqual(section["population"], 69)
        self.assertEqual(section["multiplicity_counts"], {"multiple": 2, "unique": 24, "zero": 43})
        policies = {row["policy"]: row for row in section["policies"]}
        self.assertEqual(policies["exactly_one"]["correct"], 69)
        self.assertEqual(policies["forced_first"]["correct"], 24)
        self.assertEqual(policies["relaxed_multiple"]["correct"], 67)
        self.assertEqual(section["paired_exactly_one_vs_forced_first"], {
            "corrections": 45, "regressions": 0, "same": 24,
        })

    def test_complexity_and_public_claim_boundaries_remain_bounded(self):
        self.assertEqual(self.value["complexity_control"]["empirical_status"], "not_estimated")
        self.assertEqual(self.value["execution"], {
            "api_calls": 0, "credentials_read": False, "model_calls": 0,
            "native_calls": 0, "solver_calls": 0, "vm_calls": 0,
        })
        rendered = json.dumps(self.value, sort_keys=True)
        for prohibited in ('"request_body"', '"response_body"', '"api_key"', '"counterexample"'):
            self.assertNotIn(prohibited, rendered)

    def test_published_census_reconstructs_exactly(self):
        published = json.loads((ROOT / OUTPUT_PATH).read_text())
        self.assertEqual(canonical(self.value), canonical(published))
        self.assertTrue(all(value is False for value in published["privacy"].values()))


if __name__ == "__main__":
    unittest.main()
