import unittest
from pathlib import Path


from llm4or.g08_finite_acquisition_census import build_census


ROOT = Path(__file__).resolve().parents[1]


class FiniteAcquisitionCensusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = build_census(ROOT)

    def test_complete_semantic_class_population_and_query_space(self):
        value = self.value
        self.assertEqual(value["status"], "complete_exact_finite_population_census")
        self.assertEqual(value["population"]["full_candidates"], 64)
        self.assertEqual(value["population"]["semantic_candidates"], 32)
        self.assertEqual(value["population"]["semantic_equivalence_classes"], 10)
        self.assertEqual(value["population"]["query_space"], 20977)
        self.assertEqual(sum(row["members"] for row in value["classes"]), 32)

    def test_balanced_witness_improves_budgeted_identification(self):
        arms = {row["arm"]: row for row in self.value["arms"]}
        balanced = arms["balanced_separating_witness"]
        canonical = arms["canonical_first_witness"]
        self.assertEqual(balanced["identified_within_budget"], 10)
        self.assertEqual(canonical["identified_within_budget"], 6)
        self.assertEqual(balanced["worst_queries"], 3)
        self.assertEqual(canonical["worst_queries"], 4)
        self.assertEqual(balanced["total_queries"], 26)
        self.assertEqual(canonical["total_queries"], 30)
        self.assertEqual(self.value["paired"]["balanced_only"], 4)
        self.assertEqual(self.value["paired"]["canonical_only"], 0)

    def test_every_trace_retains_target_and_strictly_shrinks(self):
        for arm in self.value["arms"]:
            for trace in arm["traces"]:
                sizes = trace["version_space_sizes"]
                self.assertEqual(sizes[0], 10)
                self.assertEqual(sizes[-1], 1)
                self.assertTrue(all(a > b for a, b in zip(sizes, sizes[1:])))
                self.assertEqual(len(trace["query_sha256"]), trace["queries"])
                self.assertEqual(len(trace["observed_labels"]), trace["queries"])

    def test_claim_and_privacy_boundaries_are_fail_closed(self):
        boundary = self.value["claim_boundary"]
        self.assertTrue(boundary["exact_only_for_frozen_semantic_classes"])
        self.assertFalse(boundary["natural_language_fact_discovery_supported"])
        self.assertFalse(boundary["resource_policy_identified_by_semantic_queries"])
        self.assertFalse(boundary["benchmark_accuracy_claimed"])
        self.assertFalse(boundary["library_promoted"])
        privacy = self.value["privacy"]
        self.assertFalse(any(privacy.values()))
        execution = self.value["execution"]
        self.assertEqual(execution["api_calls"], 0)
        self.assertEqual(execution["model_calls"], 0)
        self.assertEqual(execution["solver_calls"], 0)


if __name__ == "__main__":
    unittest.main()
