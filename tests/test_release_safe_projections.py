import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm4or.release_safe_projections import (
    ProjectionError,
    canonical_bytes,
    project_mixed_bundle,
    project_mixed_outputs,
    project_or_debug_evaluation,
    project_or_debug_outputs,
    project_tsp_candidates,
    project_tsp_public_input,
    publish_exclusive,
    validate_public_projection,
)


ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    raw = (ROOT / path).read_bytes()
    return json.loads(raw), raw


def recursive_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from recursive_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from recursive_keys(child)


def dotted(value, path):
    current = value
    for part in path.split("."):
        current = current[part]
    return current


class ReleaseSafeProjectionTests(unittest.TestCase):
    def test_canonical_bytes_are_mapping_order_independent_and_list_sensitive(self):
        self.assertEqual(canonical_bytes({"b": 2, "a": [1, 2]}), canonical_bytes({"a": [1, 2], "b": 2}))
        self.assertNotEqual(canonical_bytes({"a": [1, 2]}), canonical_bytes({"a": [2, 1]}))

    def test_validator_rejects_forbidden_key_at_any_depth(self):
        with self.assertRaisesRegex(ProjectionError, "forbidden_key:repair"):
            validate_public_projection({"records": [{"safe": {"repair": []}}]})

    def test_mixed_bundle_projection_is_body_free_and_complete(self):
        source, raw = load("experiments/mixed_skill_confirmation_bundle_20261014.json")
        projected = project_mixed_bundle(source, raw)
        self.assertEqual(projected["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(projected["counts"], source["counts"])
        self.assertEqual(len(projected["records"]), 2985)
        self.assertEqual(set(projected["records"][0]), {"public_envelope_sha256", "record_id", "source"})
        self.assertNotIn("public_text", set(recursive_keys(projected)))
        validate_public_projection(projected)

    def test_mixed_bundle_duplicate_identity_fails_closed(self):
        source, raw = load("experiments/mixed_skill_confirmation_bundle_20261014.json")
        broken = copy.deepcopy(source)
        broken["records"][1]["record_id"] = broken["records"][0]["record_id"]
        with self.assertRaisesRegex(ProjectionError, "duplicate_identity"):
            project_mixed_bundle(broken, raw)

    def test_or_debug_evaluation_projection_preserves_aggregates_without_repair_identity(self):
        source, raw = load("results/or_debug_confirmation_evaluation_20261014.json")
        projected = project_or_debug_evaluation(source, raw)
        self.assertEqual(projected["comparison"], source["comparison"])
        self.assertEqual(projected["confirmation_inference"], source["confirmation_inference"])
        self.assertEqual(len(projected["records"]), 2845)
        self.assertEqual(set(projected["records"][0]), {"evolved", "problem_id", "shape_group", "source_record_sha256", "static"})
        keys = set(recursive_keys(projected))
        self.assertNotIn("corrected_repair_identity", keys)
        self.assertNotIn("released_repair_identity", keys)
        validate_public_projection(projected)

    def test_or_debug_output_projection_omits_objective_and_repair(self):
        source, raw = load("results/or_debug_confirmation_method_outputs_20261014.json")
        projected = project_or_debug_outputs(source, raw)
        self.assertEqual(len(projected["records"]), 2845)
        keys = set(recursive_keys(projected))
        self.assertNotIn("repair", keys)
        self.assertNotIn("solve_objective", keys)
        self.assertIn("output_sha256", projected["records"][0]["static"])
        validate_public_projection(projected)

    def test_mixed_output_projection_preserves_route_counts_without_repair(self):
        source, raw = load("results/mixed_skill_confirmation_outputs_20261014.json")
        projected = project_mixed_outputs(source, raw)
        self.assertEqual(len(projected["records"]), 2985)
        self.assertEqual(sum(projected["route_counts"].values()), 2985)
        self.assertEqual(projected["status_counts"], source["execution"]["status_counts"])
        keys = set(recursive_keys(projected))
        self.assertNotIn("repair", keys)
        self.assertNotIn("solve_objective", keys)
        self.assertIn("output_sha256", projected["records"][0])
        validate_public_projection(projected)

    def test_tsp_public_input_projection_omits_text_and_preserves_identity(self):
        source, raw = load("results/private/tsp_constraint_confirmation_public_20261014.json")
        projected = project_tsp_public_input(source, raw)
        self.assertEqual(len(projected["records"]), 140)
        self.assertEqual(
            set(projected["records"][0]),
            {"problem_id", "public_text_sha256", "question_sha256", "size"},
        )
        self.assertNotIn("public_text", set(recursive_keys(projected)))
        self.assertTrue(projected["all_question_hashes_match_text"])
        validate_public_projection(projected)

    def test_tsp_candidate_projection_omits_candidate_objects(self):
        source, raw = load("results/private/tsp_constraint_confirmation_candidates_20261014.json")
        projected = project_tsp_candidates(source, raw)
        self.assertEqual(projected["counts"], {"skill": 140, "static": 140})
        self.assertEqual(len(projected["skill_records"]), 140)
        self.assertEqual(len(projected["static_records"]), 140)
        self.assertEqual(
            set(projected["skill_records"][0]),
            {"candidate_sha256", "problem_id", "question_sha256", "size"},
        )
        self.assertNotIn("candidate", set(recursive_keys(projected)))
        validate_public_projection(projected)

    def test_publisher_rejects_absolute_parent_and_symlink_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / "outside.json"
            with self.assertRaisesRegex(ProjectionError, "absolute_path"):
                publish_exclusive(outside, {"safe": True}, root)
            with self.assertRaisesRegex(ProjectionError, "parent_component"):
                publish_exclusive(Path("..") / "outside.json", {"safe": True}, root)
            (root / "real").mkdir()
            (root / "linked").symlink_to(root / "real", target_is_directory=True)
            with self.assertRaisesRegex(ProjectionError, "symlink_component"):
                publish_exclusive(Path("linked") / "value.json", {"safe": True}, root)

    def test_publisher_is_exclusive_and_check_mode_requires_identical_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = Path("evidence") / "value.json"
            digest = publish_exclusive(relative, {"b": 2, "a": 1}, root)
            raw = (root / relative).read_bytes()
            self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
            self.assertEqual(raw, b'{\n  "a": 1,\n  "b": 2\n}\n')
            with self.assertRaisesRegex(ProjectionError, "terminal_collision"):
                publish_exclusive(relative, {"a": 1, "b": 2}, root)
            self.assertEqual(
                publish_exclusive(relative, {"a": 1, "b": 2}, root, check=True),
                digest,
            )
            with self.assertRaisesRegex(ProjectionError, "check_mismatch"):
                publish_exclusive(relative, {"a": 2}, root, check=True)

    def test_publisher_fsyncs_file_and_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_fsync = os.fsync
            descriptors = []

            def recording_fsync(descriptor):
                descriptors.append(descriptor)
                return real_fsync(descriptor)

            with mock.patch("llm4or.release_safe_projections.os.fsync", side_effect=recording_fsync):
                publish_exclusive(Path("value.json"), {"safe": True}, root)
            self.assertGreaterEqual(len(descriptors), 2)

    def test_paper_manifest_uses_only_public_projections_for_restricted_bindings(self):
        manifest = json.loads((ROOT / "experiments/paper_evidence_manifest_20261015.json").read_text())
        restricted = {
            "experiments/mixed_skill_confirmation_bundle_20261014.json",
            "results/or_debug_confirmation_evaluation_20261014.json",
            "results/or_debug_confirmation_method_outputs_20261014.json",
            "results/mixed_skill_confirmation_outputs_20261014.json",
        }
        self.assertTrue(restricted.isdisjoint(set(json.dumps(manifest).split('"'))))

        or_entry = manifest["headline_evidence"]["or_debug_confirmation"]
        self.assertEqual(
            or_entry["artifact"],
            "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json",
        )
        self.assertEqual(
            or_entry["method_outputs"],
            "results/public_projections/or_debug_confirmation_method_outputs_projection_20261015.json",
        )
        evaluation_path = ROOT / or_entry["artifact"]
        evaluation = json.loads(evaluation_path.read_text())
        self.assertEqual(or_entry["sha256"], hashlib.sha256(evaluation_path.read_bytes()).hexdigest())
        for path, expected in or_entry["assertions"].items():
            self.assertEqual(dotted(evaluation, path), expected, path)

        mixed_entry = manifest["headline_evidence"]["mixed_public_router"]
        self.assertEqual(
            mixed_entry["bundle"],
            "experiments/public_projections/mixed_skill_confirmation_bundle_projection_20261015.json",
        )
        self.assertEqual(
            mixed_entry["outputs"],
            "results/public_projections/mixed_skill_confirmation_outputs_projection_20261015.json",
        )
        bundle = json.loads((ROOT / mixed_entry["bundle"]).read_text())
        outputs = json.loads((ROOT / mixed_entry["outputs"]).read_text())
        self.assertEqual(len(bundle["records"]), 2985)
        self.assertEqual(len(outputs["records"]), 2985)
        self.assertEqual(sum(outputs["route_counts"].values()), 2985)


if __name__ == "__main__":
    unittest.main()
