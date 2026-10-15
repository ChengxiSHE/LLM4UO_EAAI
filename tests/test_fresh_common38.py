import json
from pathlib import Path
import tempfile
import unittest

from llm4or import fresh_common38 as common
from llm4or.benchmark_inputs import input_shape_issues, validate_public_input
from llm4or.schema import canonical, digest


ROOT = Path(__file__).resolve().parents[1]


class FreshCommon38Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = common.build_private_bundle(ROOT)
        cls.manifest = common.build_public_manifest(ROOT, cls.bundle)

    def test_exact_outcome_blind_selection_and_identity(self):
        rows = self.bundle["records"]
        self.assertEqual(len(rows), 38)
        self.assertEqual({family: sum(row["family"] == family for row in rows)
                          for family in common.FAMILIES}, {"rcpsp": 13, "vrptw": 25})
        self.assertEqual(len({row["id"] for row in rows}), 38)
        self.assertEqual(len({row["source_file_sha256"] for row in rows}), 38)
        self.assertEqual(len({row["public_payload_sha256"] for row in rows}), 38)
        self.assertTrue(all(row["non_outcome_metadata"]["num_vars"] > 96 or
                            row["non_outcome_metadata"]["num_constraints"] > 192
                            for row in rows))

    def test_common_payload_is_valid_text_plus_structured_data(self):
        for row in self.bundle["records"]:
            payload = validate_public_input(row["public_payload"])
            self.assertEqual(payload["profile"], "description_parameters_v1")
            self.assertEqual([p["symbol"] for p in payload["parameters"]], ["instance_data"])
            self.assertEqual(len(payload["instances"]), 1)
            self.assertEqual(input_shape_issues(payload), [])
            self.assertEqual(digest(payload), row["public_payload_sha256"])

    def test_private_projection_excludes_all_evaluator_and_model_annotations(self):
        text = canonical(self.bundle).casefold()
        for prohibited in (
            "gold_solution", "gurobi_result", "theoretical_optimum",
            "optimal_values", '"variables"', '"constraints"', "reference_answer",
        ):
            self.assertNotIn(prohibited, text)
        self.assertFalse(self.bundle["claim_boundary"]["reference_values_used_or_copied"])
        self.assertTrue(self.bundle["claim_boundary"]["source_files_contain_reference_fields"])

    def test_public_manifest_is_body_free_and_binds_every_packet(self):
        def iter_keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key
                    yield from iter_keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from iter_keys(child)

        manifest_keys = set(iter_keys(self.manifest))
        for prohibited in (
            "llm_description", "instance_data", "public_payload", "text", "gold_solution",
            "gurobi_result", "theoretical_optimum", "api_key", "messages",
        ):
            self.assertNotIn(prohibited, manifest_keys)
        self.assertEqual(self.manifest["cohort"], {
            "records": 38, "rcpsp": 13, "vrptw": 25,
            "unique_ids": 38, "unique_source_files": 38,
            "unique_public_payloads": 38, "overlap_with_prepared_183": 0,
        })
        self.assertEqual(len(self.manifest["packet_bindings"]), 38)

    def test_existing_static_compiler_coverage_is_reported_without_smoothing(self):
        readiness = self.manifest["static_compiler_readiness"]
        self.assertEqual(readiness["planned_denominator"], 38)
        self.assertEqual(readiness["compiled"], 9)
        self.assertEqual(readiness["failed"], 29)
        self.assertEqual(readiness["source_count_exact_matches"], 3)
        self.assertEqual(sum(readiness["failure_codes"].values()), 29)
        self.assertLessEqual(readiness["maximum_compiled_resources"]["variables"], 2000)
        self.assertLessEqual(readiness["maximum_compiled_resources"]["constraints"], 10000)
        self.assertLessEqual(readiness["maximum_compiled_resources"]["nonzeros"], 100000)
        self.assertLessEqual(readiness["maximum_compiled_resources"]["serialized_bytes"], 4000000)
        self.assertFalse(self.manifest["decision"]["ready_to_dispatch"])

    def test_bundle_mutation_fails_manifest_binding(self):
        changed = json.loads(canonical(self.bundle))
        changed["records"][0]["non_outcome_metadata"]["num_vars"] += 1
        with self.assertRaisesRegex(ValueError, "bundle_identity"):
            common.build_public_manifest(ROOT, changed)

    def test_exclusive_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "private.json"
            public = root / "public.json"
            common.publish_values(private, public, self.bundle, self.manifest)
            self.assertEqual(json.loads(private.read_text()), self.bundle)
            self.assertEqual(json.loads(public.read_text()), self.manifest)
            with self.assertRaisesRegex(ValueError, "output_exists"):
                common.publish_values(private, public, self.bundle, self.manifest)


if __name__ == "__main__":
    unittest.main()
