import copy
import unittest

from llm4or.run_interruption import RunInterrupted
from llm4or.schema import digest
from llm4or.verified_skill_library import (
    InvalidSkill, apply_skill_library, make_promotion_event, recognizer_matches, select_skill,
    validate_lineage, validate_skill_package,
)


IMPLEMENTATION_SHA = "1" * 64
REGISTRY = {"trusted.transport.v1": IMPLEMENTATION_SHA}


def public_problem(text="Supply Cost Matrix Source\\Dest"):
    return {"id": "example_1", "profile": "description_parameters_v1",
            "text": text, "parameters": [], "instances": []}


def package(version=1, parent=None, required_all=None):
    return {
        "schema": "verified-typed-skill-v1",
        "skill_id": "transport_skill",
        "version": version,
        "parent_sha256": parent,
        "family": "transportation",
        "recognizer": {
            "kind": "casefolded_literal_v1",
            "required_all": required_all or ["cost matrix", "source\\dest"],
            "required_any": [["supply", "capacity"]],
            "forbidden_any": ["quadratic"],
        },
        "implementation": {"id": "trusted.transport.v1", "sha256": IMPLEMENTATION_SHA},
        "contracts": {
            "input_schema": "public-problem-v1",
            "output_schema": "trusted-solve-result-v1",
            "semantic_contract": "Balanced or unbalanced linear transportation with explicit supplies and demands.",
        },
        "invariants": ["all matrix dimensions agree", "flow is nonnegative"],
        "metamorphic_tests": [{
            "id": "scale_cost", "transform": "multiply all costs by a positive scalar",
            "expectation": "objective scales by the same scalar",
        }],
        "limits": {"max_input_bytes": 100000, "max_variables": 2000,
                   "max_constraints": 5000, "wall_seconds": 30},
        "fallback": "unchanged_backend",
        "provenance": {"proposer": "development-proposer-v1",
                       "development_manifest_sha256": "2" * 64,
                       "proposal_sha256": "3" * 64},
    }


class VerifiedSkillLibraryTests(unittest.TestCase):
    def test_valid_package_is_detached_and_matches_public_text(self):
        original = package()
        validated = validate_skill_package(original, REGISTRY)
        validated["family"] = "changed"
        self.assertEqual(original["family"], "transportation")
        self.assertTrue(recognizer_matches(original, "Supply COST MATRIX Source\\Dest", REGISTRY))
        self.assertFalse(recognizer_matches(original, "Supply COST MATRIX Source\\Dest quadratic", REGISTRY))

    def test_untrusted_implementation_and_unsafe_fallback_fail_closed(self):
        candidate = package()
        candidate["implementation"]["sha256"] = "4" * 64
        with self.assertRaisesRegex(InvalidSkill, "untrusted_or_changed"):
            validate_skill_package(candidate, REGISTRY)
        candidate = package()
        candidate["fallback"] = "best_effort"
        with self.assertRaisesRegex(InvalidSkill, "unsafe_fallback"):
            validate_skill_package(candidate, REGISTRY)

    def test_ambiguous_recognizers_abstain(self):
        first = package()
        second = copy.deepcopy(first)
        second["skill_id"] = "transport_skill_2"
        self.assertIsNone(select_skill([first, second], "Supply Cost Matrix Source\\Dest", REGISTRY))

    def test_application_adopts_only_optimal_trusted_result(self):
        backend = {"status": "optimal", "objective": 99.0, "opaque": [1, 2]}
        public = public_problem()

        def solve(_public, limits):
            self.assertEqual(limits["wall_seconds"], 30)
            return {"status": "optimal", "objective": 12.5}

        report = apply_skill_library(
            public, backend, [package()], trusted_implementation_digests=REGISTRY,
            trusted_implementation_functions={"trusted.transport.v1": solve},
        )
        self.assertTrue(report["adopted"])
        self.assertEqual(report["result"]["objective"], 12.5)
        self.assertFalse(report["fallback_identity"])

    def test_application_preserves_backend_on_failure_or_ambiguity(self):
        backend = {"status": "optimal", "objective": 99.0, "opaque": [1, 2]}
        public = public_problem()

        def fail(_public, _limits):
            raise ValueError("bad parse")

        report = apply_skill_library(
            public, backend, [package()], trusted_implementation_digests=REGISTRY,
            trusted_implementation_functions={"trusted.transport.v1": fail},
        )
        self.assertFalse(report["adopted"])
        self.assertTrue(report["fallback_identity"])
        self.assertEqual(report["result"], backend)

        duplicate = copy.deepcopy(package())
        duplicate["skill_id"] = "duplicate"
        ambiguous = apply_skill_library(
            public, backend, [package(), duplicate], trusted_implementation_digests=REGISTRY,
            trusted_implementation_functions={"trusted.transport.v1": lambda *_: {"status": "optimal", "objective": 1}},
        )
        self.assertFalse(ambiguous["adopted"])
        self.assertTrue(ambiguous["fallback_identity"])

    def test_global_interruption_is_never_converted_to_abstention(self):
        def interrupted(_public, _limits):
            raise RunInterrupted("global_budget_halt")

        with self.assertRaises(RunInterrupted):
            apply_skill_library(
                public_problem(), {"status": "optimal", "objective": 99.0}, [package()],
                trusted_implementation_digests=REGISTRY,
                trusted_implementation_functions={"trusted.transport.v1": interrupted},
            )

    def test_hash_chained_lineage_requires_accepted_parent(self):
        evidence = {"static_evidence_sha256": "4" * 64,
                    "replay_evidence_sha256": "5" * 64,
                    "promotion_evidence_sha256": "6" * 64}
        first_skill = package()
        first = make_promotion_event(
            generation=1, previous_event_sha256=None, skill=first_skill,
            trusted_implementations=REGISTRY, decision="accepted", **evidence,
        )
        parent = digest(first_skill)
        second_skill = package(version=2, parent=parent, required_all=["cost matrix", "source\\dest", "demand"])
        second = make_promotion_event(
            generation=2, previous_event_sha256=first["event_sha256"], skill=second_skill,
            trusted_implementations=REGISTRY, decision="accepted", **evidence,
        )
        report = validate_lineage([first, second], REGISTRY)
        self.assertEqual(report["accepted_skills"], 2)
        broken = copy.deepcopy(second)
        broken["previous_event_sha256"] = "0" * 64
        unsigned = {key: value for key, value in broken.items() if key != "event_sha256"}
        broken["event_sha256"] = digest(unsigned)
        with self.assertRaisesRegex(InvalidSkill, "broken_promotion_chain"):
            validate_lineage([first, broken], REGISTRY)

    def test_rejected_skill_cannot_become_a_parent(self):
        evidence = {"static_evidence_sha256": "4" * 64,
                    "replay_evidence_sha256": "5" * 64,
                    "promotion_evidence_sha256": "6" * 64}
        first_skill = package()
        first = make_promotion_event(
            generation=1, previous_event_sha256=None, skill=first_skill,
            trusted_implementations=REGISTRY, decision="rejected", **evidence,
        )
        child = package(version=2, parent=digest(first_skill), required_all=["cost matrix", "demand"])
        second = make_promotion_event(
            generation=2, previous_event_sha256=first["event_sha256"], skill=child,
            trusted_implementations=REGISTRY, decision="accepted", **evidence,
        )
        with self.assertRaisesRegex(InvalidSkill, "skill_parent_not_previously_accepted"):
            validate_lineage([first, second], REGISTRY)

    def test_child_must_increment_same_skill_and_family(self):
        evidence = {"static_evidence_sha256": "4" * 64,
                    "replay_evidence_sha256": "5" * 64,
                    "promotion_evidence_sha256": "6" * 64}
        first_skill = package()
        first = make_promotion_event(
            generation=1, previous_event_sha256=None, skill=first_skill,
            trusted_implementations=REGISTRY, decision="accepted", **evidence,
        )
        bad_child = package(version=3, parent=digest(first_skill), required_all=["cost matrix", "demand"])
        second = make_promotion_event(
            generation=2, previous_event_sha256=first["event_sha256"], skill=bad_child,
            trusted_implementations=REGISTRY, decision="accepted", **evidence,
        )
        with self.assertRaisesRegex(InvalidSkill, "invalid_skill_version_ancestry"):
            validate_lineage([first, second], REGISTRY)


if __name__ == "__main__":
    unittest.main()
