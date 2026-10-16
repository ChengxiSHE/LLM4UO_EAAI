import hashlib
import unittest

from llm4or.mixed_skill_router import (
    OR_DEBUG_ROUTE,
    TSP_ROUTE,
    route_public_envelope,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MixedSkillRouterTests(unittest.TestCase):
    def test_routes_complete_tsp_public_envelope(self) -> None:
        public_text = "Visit each of 13 locations exactly once and return."
        envelope = {
            "public_text": public_text,
            "size": 13,
            "question_sha256": _sha256(public_text),
        }

        self.assertEqual(
            route_public_envelope(envelope),
            {"route": TSP_ROUTE, "reason": "unique_public_guard"},
        )

    def test_routes_complete_or_debug_public_envelope(self) -> None:
        envelope = {
            "problem_nl": "Repair the declared binary variable domain.",
            "model_file": "models/example.mps",
            "mps_sha256": "a" * 64,
        }

        self.assertEqual(
            route_public_envelope(envelope),
            {"route": OR_DEBUG_ROUTE, "reason": "unique_public_guard"},
        )

    def test_abstains_on_empty_and_partial_envelopes(self) -> None:
        for envelope in ({}, {"public_text": "x", "size": 13}):
            with self.subTest(envelope=envelope):
                self.assertEqual(
                    route_public_envelope(envelope),
                    {"route": None, "reason": "no_unique_public_guard"},
                )

    def test_abstains_on_union_shaped_envelope(self) -> None:
        public_text = "A 13-node routing problem."
        envelope = {
            "public_text": public_text,
            "size": 13,
            "question_sha256": _sha256(public_text),
            "problem_nl": "Repair this model.",
            "model_file": "models/example.mps",
            "mps_sha256": "b" * 64,
        }

        self.assertEqual(
            route_public_envelope(envelope),
            {"route": None, "reason": "no_unique_public_guard"},
        )

    def test_abstains_on_tsp_hash_mismatch(self) -> None:
        envelope = {
            "public_text": "A 13-node routing problem.",
            "size": 13,
            "question_sha256": "0" * 64,
        }

        self.assertIsNone(route_public_envelope(envelope)["route"])

    def test_abstains_on_unsafe_or_debug_paths(self) -> None:
        for model_file in ("/tmp/example.mps", "models/../example.mps"):
            with self.subTest(model_file=model_file):
                envelope = {
                    "problem_nl": "Repair this model.",
                    "model_file": model_file,
                    "mps_sha256": "c" * 64,
                }
                self.assertIsNone(route_public_envelope(envelope)["route"])

    def test_problem_id_is_not_an_accepted_guard_feature(self) -> None:
        public_text = "A 13-node routing problem."
        envelope = {
            "problem_id": "tsp-obvious-family-label",
            "public_text": public_text,
            "size": 13,
            "question_sha256": _sha256(public_text),
        }

        self.assertEqual(
            route_public_envelope(envelope),
            {"route": None, "reason": "no_unique_public_guard"},
        )

    def test_abstains_on_invalid_sizes_and_hash_syntax(self) -> None:
        for size in (True, 12, 20):
            text = "A routing problem."
            with self.subTest(size=size):
                self.assertIsNone(
                    route_public_envelope(
                        {
                            "public_text": text,
                            "size": size,
                            "question_sha256": _sha256(text),
                        }
                    )["route"]
                )

        self.assertIsNone(
            route_public_envelope(
                {
                    "problem_nl": "Repair this model.",
                    "model_file": "models/example.mps",
                    "mps_sha256": "A" * 64,
                }
            )["route"]
        )


if __name__ == "__main__":
    unittest.main()
