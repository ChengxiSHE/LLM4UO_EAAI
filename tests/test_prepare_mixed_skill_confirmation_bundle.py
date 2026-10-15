import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import prepare_mixed_skill_confirmation_bundle as prepare


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


class PrepareMixedSkillConfirmationBundleTests(unittest.TestCase):
    def _fixture_root(self, base: Path) -> tuple[str, str]:
        tsp_rows = [
            {
                "problem_id": "tsp-1",
                "public_text": "Thirteen public nodes.",
                "question_sha256": hashlib.sha256(b"Thirteen public nodes.").hexdigest(),
                "size": 13,
            },
            {
                "problem_id": "tsp-2",
                "public_text": "Fourteen public nodes.",
                "question_sha256": hashlib.sha256(b"Fourteen public nodes.").hexdigest(),
                "size": 14,
            },
        ]
        or_rows = [
            {
                "problem_id": "or-1",
                "problem_nl": "Repair a public model.",
                "model_file": "models/or-1.mps",
                "mps_sha256": "1" * 64,
            },
            {
                "problem_id": "or-2",
                "problem_nl": "Repair another public model.",
                "model_file": "models/or-2.mps",
                "mps_sha256": "2" * 64,
            },
        ]
        tsp_hash = _write_json(base / prepare.TSP_PUBLIC_PATH, {"rows": tsp_rows})
        or_hash = _write_json(base / prepare.OR_DEBUG_PUBLIC_PATH, {"records": or_rows})
        return tsp_hash, or_hash

    def test_builds_exact_public_envelopes_and_deterministic_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tsp_hash, or_hash = self._fixture_root(root)
            with patch.object(prepare, "TSP_PUBLIC_SHA256", tsp_hash), patch.object(
                prepare, "OR_DEBUG_PUBLIC_SHA256", or_hash
            ):
                first = prepare.build_bundle(root)
                second = prepare.build_bundle(root)

        self.assertEqual(first, second)
        self.assertEqual(len(first["records"]), 4)
        self.assertEqual(first["counts"], {"or_debug": 2, "total": 4, "tsp": 2})
        self.assertRegex(first["mixed_order_sha256"], r"^[0-9a-f]{64}$")
        for record in first["records"]:
            self.assertEqual(set(record), {"public_envelope", "record_id", "source"})
            if record["source"] == "tsp":
                self.assertEqual(
                    set(record["public_envelope"]),
                    {"public_text", "question_sha256", "size"},
                )
            else:
                self.assertEqual(record["source"], "or_debug")
                self.assertEqual(
                    set(record["public_envelope"]),
                    {"model_file", "mps_sha256", "problem_nl"},
                )

    def test_public_records_contain_no_hidden_or_evaluator_fields(self) -> None:
        forbidden = {
            "answer",
            "correct",
            "expected",
            "iis",
            "label",
            "optimum",
            "reference",
            "repair",
            "target",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tsp_hash, or_hash = self._fixture_root(root)
            with patch.object(prepare, "TSP_PUBLIC_SHA256", tsp_hash), patch.object(
                prepare, "OR_DEBUG_PUBLIC_SHA256", or_hash
            ):
                bundle = prepare.build_bundle(root)

        for record in bundle["records"]:
            keys = {key.lower() for key in record["public_envelope"]}
            self.assertTrue(keys.isdisjoint(forbidden))

    def test_rejects_source_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tsp_hash, or_hash = self._fixture_root(root)
            with patch.object(prepare, "TSP_PUBLIC_SHA256", "0" * 64), patch.object(
                prepare, "OR_DEBUG_PUBLIC_SHA256", or_hash
            ):
                with self.assertRaisesRegex(ValueError, "TSP public source SHA256 mismatch"):
                    prepare.build_bundle(root)


if __name__ == "__main__":
    unittest.main()
