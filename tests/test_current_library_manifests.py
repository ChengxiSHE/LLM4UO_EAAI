import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from llm4or.content_addressed_manifests import (
    operational_description_length_bits,
    validate_library_manifest,
    validate_skill_manifest,
)
from llm4or.current_library_manifests import (
    build_current_manifest_set,
    publish_current_manifest_set,
)


ROOT = Path(__file__).resolve().parents[1]


def recursive_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from recursive_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from recursive_keys(child)


class CurrentLibraryManifestTests(unittest.TestCase):
    def test_builds_two_answer_free_skills_and_one_genesis_library(self):
        manifest_set = build_current_manifest_set(
            ROOT, Path("artifacts/knowledge_manifests/skills")
        )
        self.assertEqual(set(manifest_set["skills"]), {"or_debug", "tsp"})
        for skill in manifest_set["skills"].values():
            self.assertEqual(validate_skill_manifest(skill, ROOT), skill)
        skills_by_digest = {
            skill["content_sha256"]: skill for skill in manifest_set["skills"].values()
        }
        self.assertEqual(
            validate_library_manifest(manifest_set["library"], ROOT, skills_by_digest),
            manifest_set["library"],
        )
        self.assertIsNone(manifest_set["library"]["parent_library_sha256"])
        self.assertIsNone(manifest_set["library"]["rollback_library_sha256"])
        self.assertEqual(manifest_set["library"]["promotion_decision"]["status"], "genesis")

        keys = set(recursive_keys(manifest_set))
        for forbidden in (
            "api_key",
            "credential",
            "evaluator_answer",
            "problem_text",
            "reference_answer",
            "request_body",
            "response_body",
            "solver_objective",
        ):
            self.assertNotIn(forbidden, keys)

    def test_manifest_semantics_bind_declared_frozen_method_boundaries(self):
        manifest_set = build_current_manifest_set(
            ROOT, Path("artifacts/knowledge_manifests/skills")
        )
        tsp = manifest_set["skills"]["tsp"]
        or_debug = manifest_set["skills"]["or_debug"]
        library = manifest_set["library"]
        self.assertEqual(tsp["semantic_payload"]["resource_checker"]["max_nodes"], 19)
        self.assertEqual(
            or_debug["semantic_payload"]["transform"]["operations"],
            [
                "remove_constraint",
                "set_coefficient",
                "set_constraint_rhs",
                "set_constraint_sense",
                "set_variable_domain",
                "set_variable_lower_bound",
            ],
        )
        self.assertEqual(
            or_debug["semantic_payload"]["resource_checker"],
            {
                "max_mps_bytes": 1000000,
                "solver_threads": 1,
                "solver_timeout_seconds": 15,
                "wall_timeout_seconds": 25,
            },
        )
        endpoint_paths = {
            endpoint["endpoint_id"]: endpoint["evidence_sha256"]
            for endpoint in library["endpoint_identities"]
        }
        self.assertEqual(
            endpoint_paths["or_debug_corrected_primary"],
            "7f83555e8b81ff15bad510b95bf7e2617d87bb139786777407704a55e10a70ca",
        )
        self.assertGreater(
            operational_description_length_bits(list(manifest_set["skills"].values()), library["router"]),
            0,
        )

    def test_every_runtime_closure_and_evidence_file_is_tracked(self):
        manifest_set = build_current_manifest_set(
            ROOT, Path("artifacts/knowledge_manifests/current/skills")
        )
        tracked = set(
            subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
        )
        closure_paths = set()
        for skill in manifest_set["skills"].values():
            closure_paths.update(item["path"] for item in skill["implementation_closure"])
            for role in ("guard", "extractor", "transform", "semantic_verifier", "resource_checker"):
                closure_paths.update(
                    item["path"] for item in skill[role]["implementation_closure"]
                )
        closure_paths.update(
            item["path"]
            for item in manifest_set["library"]["router"]["implementation_closure"]
        )
        closure_paths.update(
            item["path"] for item in manifest_set["library"]["verifier_closure"]
        )
        ledger_paths = {
            item["path"]
            for field in ("accepted_ledger_refs", "rejected_ledger_refs")
            for item in manifest_set["library"][field]
        }
        self.assertTrue(closure_paths.issubset(tracked), sorted(closure_paths - tracked))
        self.assertTrue(ledger_paths.issubset(tracked), sorted(ledger_paths - tracked))
        self.assertNotIn("llm4or/or_debug_repair_dsl.py", closure_paths)
        self.assertIn("reproduction/current_library_provenance_v1.json", tracked)

    def test_publish_then_check_reconstructs_content_named_set(self):
        temporary = Path(tempfile.mkdtemp(prefix="manifest-test-", dir=ROOT))
        try:
            relative = temporary.relative_to(ROOT)
            first = publish_current_manifest_set(ROOT, relative, check=False)
            second = publish_current_manifest_set(ROOT, relative, check=True)
            self.assertEqual(first, second)
            self.assertEqual(len(first["skill_paths"]), 2)
            for path in first["skill_paths"] + [first["library_path"]]:
                payload = json.loads((ROOT / path).read_text())
                self.assertEqual(Path(path).stem, payload["content_sha256"])
        finally:
            shutil.rmtree(temporary)


if __name__ == "__main__":
    unittest.main()
