import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from llm4or import structured_or_readiness as readiness


ROOT = Path(__file__).resolve().parents[1]


class StructuredOrReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = readiness.build_audit(ROOT)

    def test_complete_exact_and_bounded(self):
        self.assertEqual(self.audit["aggregate"]["planned"], 38)
        self.assertEqual(self.audit["aggregate"]["compiled_and_admitted"], 38)
        self.assertEqual(self.audit["aggregate"]["exact_source_count_matches"], 38)
        self.assertEqual(self.audit["aggregate"]["routes"], {"rcpsp": 13, "vrptw": 25})
        self.assertEqual(len(self.audit["model_bindings"]), 38)
        self.assertTrue(self.audit["decision"]["typed_skills_ready"])
        self.assertFalse(self.audit["decision"]["ready_to_dispatch"])

    def test_binds_skill_source_and_public_packet_manifest(self):
        skill = ROOT / "llm4or/structured_or_skills.py"
        expected = hashlib.sha256(skill.read_bytes()).hexdigest()
        self.assertEqual(self.audit["skill"]["source_sha256"], expected)
        packet = ROOT / "experiments/fresh_common38_packet_readiness_20261015.json"
        self.assertEqual(self.audit["common_packet_readiness_sha256"],
                         hashlib.sha256(packet.read_bytes()).hexdigest())

    def test_public_audit_has_no_body_fields(self):
        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)
        found = set(keys(self.audit))
        prohibited = {
            "public_payload", "instance_data", "text", "llm_description",
            "gold_solution", "gurobi_result", "model", "objective",
            "coefficients", "api_key", "messages",
        }
        self.assertEqual(found & prohibited, set())

    def test_exclusive_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            readiness.publish(path, self.audit)
            self.assertEqual(json.loads(path.read_text()), self.audit)
            with self.assertRaisesRegex(ValueError, "output_exists"):
                readiness.publish(path, self.audit)


if __name__ == "__main__":
    unittest.main()
