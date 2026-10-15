import json
from pathlib import Path
import unittest

from llm4or.g09_library_complexity_census import (
    OUTPUT_PATH,
    build_census,
    render_markdown,
)
from llm4or.schema import canonical


ROOT = Path(__file__).resolve().parents[1]


class G09LibraryComplexityCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = build_census(ROOT)

    def test_population_is_complete_and_common_pool_is_fixed(self):
        population = self.value["population"]
        self.assertEqual(population["optional_shadow_guards"], 6)
        self.assertEqual(population["candidate_libraries"], 64)
        self.assertEqual(population["calibration_episodes"], 64)
        self.assertEqual(population["routing_envelopes"], 69)
        self.assertEqual(population["unique_candidate_hashes"], 64)
        self.assertEqual(population["unique_episode_hashes"], 64)
        self.assertTrue(population["same_candidate_pool_every_episode"])
        self.assertTrue(population["code_frozen_before_episode_labels"])

    def test_mdl_selector_improves_exact_finite_endpoint(self):
        arms = {row["arm"]: row for row in self.value["arms"]}
        mdl = arms["proof_constrained_mdl"]
        control = arms["proof_only_frozen_hash"]
        self.assertEqual(mdl["fully_correct_libraries"], 64)
        self.assertEqual(control["fully_correct_libraries"], 1)
        self.assertEqual(mdl["routing_decisions_correct"], 4416)
        self.assertEqual(control["routing_decisions_correct"], 4284)
        self.assertEqual(self.value["paired"], {
            "mdl_only_fully_correct": 63,
            "control_only_fully_correct": 0,
            "both_fully_correct": 1,
            "neither_fully_correct": 0,
            "mdl_routing_corrections": 132,
            "mdl_routing_regressions": 0,
            "same_routing_decision_correctness": 4284,
        })

    def test_prefix_code_and_claim_boundaries_are_explicit(self):
        code = self.value["prefix_code"]
        self.assertEqual(code["membership_header_bits"], 6)
        self.assertTrue(code["prefix_free"])
        self.assertTrue(code["label_independent"])
        self.assertFalse(self.value["inference"]["sampling_based_p_value"])
        self.assertTrue(self.value["claim_boundary"]["bounded_complexity_effect_identified"])
        self.assertFalse(self.value["claim_boundary"]["natural_library_distribution_generalization"])
        self.assertFalse(self.value["claim_boundary"]["current_authored_library_length_measured"])
        report = render_markdown(self.value)
        self.assertIn("63 fully correct library selections", report)
        self.assertIn("complete authored shadow-guard grammar", report)

    def test_published_census_reconstructs_and_is_privacy_safe(self):
        published = json.loads((ROOT / OUTPUT_PATH).read_text())
        self.assertEqual(canonical(self.value), canonical(published))
        self.assertTrue(all(value is False for value in published["privacy"].values()))
        self.assertEqual(published["execution"], {
            "api_calls": 0,
            "credentials_read": False,
            "model_calls": 0,
            "native_calls": 0,
            "solver_calls": 0,
            "vm_calls": 0,
        })


if __name__ == "__main__":
    unittest.main()
