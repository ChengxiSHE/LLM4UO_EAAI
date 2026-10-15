import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm4or.content_addressed_manifests import (
    ManifestError,
    attach_content_digest,
    canonical_manifest_bytes,
    load_content_addressed_manifest,
    operational_description_length_bits,
    publish_content_addressed_manifest,
    validate_library_manifest,
    validate_skill_manifest,
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def closure(path: str, digest: str):
    return [{"path": path, "sha256": digest}]


def skill_manifest(source_sha: str):
    role = {
        "interface": "llm4or.example.v1",
        "semantic_version": "1.0.0",
        "implementation_closure": closure("impl.py", source_sha),
    }
    body = {
        "schema": "llm4or.skill_manifest.v1",
        "skill_id": "example_skill",
        "family": "example",
        "semantic_version": "1.0.0",
        "guard": copy.deepcopy(role),
        "extractor": copy.deepcopy(role),
        "transform": copy.deepcopy(role),
        "semantic_verifier": copy.deepcopy(role),
        "resource_checker": copy.deepcopy(role),
        "provenance": {
            "authorship_mode": "human_authored",
            "parent_proposal_sha256": None,
            "construction_split_sha256": "1" * 64,
            "verifier_sha256": "2" * 64,
            "decision_sha256": "3" * 64,
        },
        "fallback_contract": {
            "target": "frozen_base",
            "zero_match": "fallback",
            "multiple_match": "fallback",
        },
        "semantic_payload": {
            "guard": {"all": [{"field": "kind", "equals": "example"}]},
            "extractor": {"fields": [{"name": "count", "type": "integer"}]},
            "transform": {"dsl": ["emit_count_variable"]},
            "semantic_verifier": {"obligations": ["count_is_integral"]},
            "resource_checker": {"max_variables": 1, "max_constraints": 2},
            "fallback": {"target": "frozen_base"},
        },
        "implementation_closure": closure("impl.py", source_sha),
        "claim_boundary": ["finite authored example family only"],
    }
    return attach_content_digest(body)


def library_manifest(skill):
    body = {
        "schema": "llm4or.library_manifest.v1",
        "library_version": "example-library-v1",
        "parent_library_sha256": None,
        "rollback_library_sha256": None,
        "skills": [
            {
                "family": skill["family"],
                "skill_id": skill["skill_id"],
                "manifest_sha256": skill["content_sha256"],
                "path": f"skills/{skill['content_sha256']}.json",
            }
        ],
        "router": {
            "interface": "llm4or.router.v1",
            "semantic_version": "1.0.0",
            "implementation_closure": skill["implementation_closure"],
            "semantic_payload": {
                "decision_rule": "exactly_one",
                "ordered_skill_ids": [skill["skill_id"]],
            },
            "exact_match_policy": "exactly_one",
            "zero_match_fallback": "frozen_base",
            "multiple_match_fallback": "frozen_base",
        },
        "verifier_closure": skill["implementation_closure"],
        "endpoint_identities": [
            {
                "endpoint_id": "example-endpoint",
                "schema": "example.endpoint.v1",
                "plan_sha256": "4" * 64,
                "evidence_sha256": "5" * 64,
            }
        ],
        "promotion_decision": {
            "status": "genesis",
            "decision_sha256": "6" * 64,
        },
        "accepted_ledger_refs": [],
        "rejected_ledger_refs": [],
        "release_boundary": ["first-party implementation only"],
        "claim_boundary": ["finite authored example family only"],
    }
    return attach_content_digest(body)


class ContentAddressedManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "impl.py").write_text("VALUE = 1\n")
        self.source_sha = sha((self.root / "impl.py").read_bytes())
        self.skill = skill_manifest(self.source_sha)
        self.library = library_manifest(self.skill)

    def tearDown(self):
        self.temp.cleanup()

    def test_digest_excludes_content_sha256_and_is_mapping_order_independent(self):
        reversed_body = dict(reversed(list(self.skill.items())))
        self.assertEqual(
            attach_content_digest(reversed_body)["content_sha256"],
            self.skill["content_sha256"],
        )
        body = {key: value for key, value in self.skill.items() if key != "content_sha256"}
        self.assertEqual(self.skill["content_sha256"], sha(canonical_manifest_bytes(body)))

    def test_skill_validation_checks_exact_fields_paths_and_hashes(self):
        validated = validate_skill_manifest(self.skill, self.root)
        self.assertEqual(validated, self.skill)

        extra = copy.deepcopy(self.skill)
        extra["unexpected"] = True
        with self.assertRaisesRegex(ManifestError, "skill_fields"):
            validate_skill_manifest(extra, self.root)

        escaped = copy.deepcopy(self.skill)
        escaped["guard"]["implementation_closure"][0]["path"] = "../impl.py"
        escaped = attach_content_digest({k: v for k, v in escaped.items() if k != "content_sha256"})
        with self.assertRaisesRegex(ManifestError, "parent_component"):
            validate_skill_manifest(escaped, self.root)

        drifted = copy.deepcopy(self.skill)
        drifted["implementation_closure"][0]["sha256"] = "f" * 64
        drifted = attach_content_digest({k: v for k, v in drifted.items() if k != "content_sha256"})
        with self.assertRaisesRegex(ManifestError, "closure_hash_mismatch"):
            validate_skill_manifest(drifted, self.root)

    def test_skill_validation_rejects_symlink_and_pointer_only_semantics(self):
        (self.root / "real.py").write_text("VALUE = 2\n")
        (self.root / "linked.py").symlink_to(self.root / "real.py")
        linked = copy.deepcopy(self.skill)
        linked["guard"]["implementation_closure"] = closure(
            "linked.py", sha((self.root / "real.py").read_bytes())
        )
        linked = attach_content_digest({k: v for k, v in linked.items() if k != "content_sha256"})
        with self.assertRaisesRegex(ManifestError, "symlink_component"):
            validate_skill_manifest(linked, self.root)

        pointer = copy.deepcopy(self.skill)
        pointer["semantic_payload"] = {"path": "knowledge.json", "sha256": "0" * 64}
        pointer = attach_content_digest({k: v for k, v in pointer.items() if k != "content_sha256"})
        with self.assertRaisesRegex(ManifestError, "semantic_payload_fields"):
            validate_skill_manifest(pointer, self.root)

        nested_pointer = copy.deepcopy(self.skill)
        nested_pointer["semantic_payload"]["guard"] = {
            "path": "knowledge.json",
            "sha256": "0" * 64,
        }
        nested_pointer = attach_content_digest(
            {k: v for k, v in nested_pointer.items() if k != "content_sha256"}
        )
        with self.assertRaisesRegex(ManifestError, "pointer_only_semantics"):
            validate_skill_manifest(nested_pointer, self.root)

    def test_skill_validation_rejects_private_body_and_answer_fields(self):
        for forbidden in ("request_body", "response_body", "evaluator_answer", "api_key"):
            broken = copy.deepcopy(self.skill)
            broken["semantic_payload"]["transform"][forbidden] = "must-not-appear"
            broken = attach_content_digest(
                {key: value for key, value in broken.items() if key != "content_sha256"}
            )
            with self.subTest(forbidden=forbidden), self.assertRaisesRegex(
                ManifestError, "forbidden_manifest_key"
            ):
                validate_skill_manifest(broken, self.root)

    def test_semantic_versions_require_three_numeric_components(self):
        broken = copy.deepcopy(self.skill)
        broken["semantic_version"] = "0"
        broken = attach_content_digest(
            {key: value for key, value in broken.items() if key != "content_sha256"}
        )
        with self.assertRaisesRegex(ManifestError, "skill_semantic_version"):
            validate_skill_manifest(broken, self.root)

    def test_library_validation_binds_sorted_skills_parent_and_rollback(self):
        skills = {self.skill["content_sha256"]: self.skill}
        self.assertEqual(validate_library_manifest(self.library, self.root, skills), self.library)

        unsorted = copy.deepcopy(self.library)
        second = copy.deepcopy(unsorted["skills"][0])
        second.update({"family": "aaa", "skill_id": "aaa_skill"})
        unsorted["skills"].append(second)
        unsorted = attach_content_digest({k: v for k, v in unsorted.items() if k != "content_sha256"})
        with self.assertRaisesRegex(ManifestError, "skills_not_sorted"):
            validate_library_manifest(unsorted, self.root, skills)

        successor = copy.deepcopy(self.library)
        successor["library_version"] = "example-library-v2"
        successor["parent_library_sha256"] = "7" * 64
        successor["rollback_library_sha256"] = None
        successor = attach_content_digest({k: v for k, v in successor.items() if k != "content_sha256"})
        with self.assertRaisesRegex(ManifestError, "successor_rollback"):
            validate_library_manifest(successor, self.root, skills)

        successor["rollback_library_sha256"] = "7" * 64
        successor = attach_content_digest(
            {key: value for key, value in successor.items() if key != "content_sha256"}
        )
        with self.assertRaisesRegex(ManifestError, "ancestor_manifests_required"):
            validate_library_manifest(successor, self.root, skills)

        valid_successor = copy.deepcopy(successor)
        valid_successor["parent_library_sha256"] = self.library["content_sha256"]
        valid_successor["rollback_library_sha256"] = self.library["content_sha256"]
        valid_successor["promotion_decision"]["status"] = "accepted"
        valid_successor = attach_content_digest(
            {key: value for key, value in valid_successor.items() if key != "content_sha256"}
        )
        self.assertEqual(
            validate_library_manifest(
                valid_successor,
                self.root,
                skills,
                ancestor_manifests={self.library["content_sha256"]: self.library},
            ),
            valid_successor,
        )

    def test_library_revalidates_bound_skill_and_ledger_bytes(self):
        tampered_skill = copy.deepcopy(self.skill)
        tampered_skill["claim_boundary"] = ["changed without a new digest"]
        with self.assertRaisesRegex(ManifestError, "content_digest_mismatch"):
            validate_library_manifest(
                self.library,
                self.root,
                {self.skill["content_sha256"]: tampered_skill},
            )

        ledger_path = self.root / "accepted.json"
        ledger_path.write_text('{"decision":"accepted"}\n')
        with_ledger = copy.deepcopy(self.library)
        with_ledger["accepted_ledger_refs"] = [
            {"path": "accepted.json", "sha256": "f" * 64}
        ]
        with_ledger = attach_content_digest(
            {key: value for key, value in with_ledger.items() if key != "content_sha256"}
        )
        with self.assertRaisesRegex(ManifestError, "ledger_hash_mismatch"):
            validate_library_manifest(
                with_ledger,
                self.root,
                {self.skill["content_sha256"]: self.skill},
            )

    def test_description_length_uses_only_semantic_payloads_and_router(self):
        first = operational_description_length_bits([self.skill], self.library["router"])
        renamed = copy.deepcopy(self.skill)
        renamed["skill_id"] = "renamed_skill"
        renamed["implementation_closure"][0]["path"] = "different.py"
        renamed = attach_content_digest({k: v for k, v in renamed.items() if k != "content_sha256"})
        self.assertEqual(first, operational_description_length_bits([renamed], self.library["router"]))

        richer = copy.deepcopy(self.skill)
        richer["semantic_payload"]["transform"]["dsl"].append("emit_balance_constraint")
        richer = attach_content_digest({k: v for k, v in richer.items() if k != "content_sha256"})
        self.assertGreater(
            operational_description_length_bits([richer], self.library["router"]), first
        )

    def test_publish_is_content_named_exclusive_durable_and_loadable(self):
        output = Path("manifests") / "skills"
        real_fsync = os.fsync
        calls = []

        def record(descriptor):
            calls.append(descriptor)
            return real_fsync(descriptor)

        with mock.patch("llm4or.content_addressed_manifests.os.fsync", side_effect=record):
            relative = publish_content_addressed_manifest(
                self.skill, output, self.root, kind="skill"
            )
        self.assertEqual(relative.name, f"{self.skill['content_sha256']}.json")
        self.assertGreaterEqual(len(calls), 2)
        loaded = load_content_addressed_manifest(relative, self.root, kind="skill")
        self.assertEqual(loaded, self.skill)
        with self.assertRaisesRegex(ManifestError, "terminal_collision"):
            publish_content_addressed_manifest(self.skill, output, self.root, kind="skill")

    def test_library_publication_requires_and_revalidates_bound_skills(self):
        skill_directory = Path("manifests") / "skills"
        skill_path = publish_content_addressed_manifest(
            self.skill, skill_directory, self.root, kind="skill"
        )
        library = copy.deepcopy(self.library)
        library["skills"][0]["path"] = skill_path.as_posix()
        library = attach_content_digest(
            {key: value for key, value in library.items() if key != "content_sha256"}
        )
        skills = {self.skill["content_sha256"]: self.skill}
        with self.assertRaisesRegex(ManifestError, "bound_skill"):
            publish_content_addressed_manifest(
                library, Path("manifests") / "libraries", self.root, kind="library"
            )
        library_path = publish_content_addressed_manifest(
            library,
            Path("manifests") / "libraries",
            self.root,
            kind="library",
            skill_manifests=skills,
        )
        self.assertEqual(
            load_content_addressed_manifest(
                library_path, self.root, kind="library", skill_manifests=skills
            ),
            library,
        )

    def test_loader_rejects_duplicate_keys_noncanonical_bytes_and_wrong_filename(self):
        directory = self.root / "manifests"
        directory.mkdir()
        duplicate = directory / ("0" * 64 + ".json")
        duplicate.write_text('{"schema":"x","schema":"y"}\n')
        with self.assertRaisesRegex(ManifestError, "duplicate_json_key"):
            load_content_addressed_manifest(duplicate.relative_to(self.root), self.root, kind="skill")

        noncanonical = directory / (self.skill["content_sha256"] + ".json")
        noncanonical.write_text(json.dumps(self.skill, indent=2) + "\n")
        with self.assertRaisesRegex(ManifestError, "noncanonical_bytes"):
            load_content_addressed_manifest(noncanonical.relative_to(self.root), self.root, kind="skill")

        wrong = directory / ("f" * 64 + ".json")
        wrong.write_bytes(canonical_manifest_bytes(self.skill))
        with self.assertRaisesRegex(ManifestError, "filename_digest_mismatch"):
            load_content_addressed_manifest(wrong.relative_to(self.root), self.root, kind="skill")


if __name__ == "__main__":
    unittest.main()
