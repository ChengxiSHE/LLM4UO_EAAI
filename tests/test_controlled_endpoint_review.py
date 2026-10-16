import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "controlled_endpoint_review_protocol_20261016.json"


class ControlledEndpointReviewProtocolTests(unittest.TestCase):
    def test_protocol_is_aggregate_only_and_secret_free(self):
        protocol = json.loads(PROTOCOL.read_text())
        self.assertEqual(
            protocol["status"], "frozen_dispatched_to_independent_reviewer"
        )
        self.assertEqual(set(protocol["studies"]), {"tsp", "or_debug", "fresh_common38"})
        self.assertEqual(protocol["execution_limits"]["api_or_model_calls"], 0)
        self.assertTrue(all(protocol["review_output_policy"].values()))
        serialized = PROTOCOL.read_text().casefold()
        for forbidden in (
            "api_key",
            "authorization: bearer",
            "request_body",
            "response_body",
            "reference_objective",
            "problem_text",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_every_binding_uses_a_canonical_sha256(self):
        protocol = json.loads(PROTOCOL.read_text())
        for study in protocol["studies"].values():
            self.assertGreater(study["planned"], 0)
            for binding in study["bindings"]:
                digest = binding["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)


if __name__ == "__main__":
    unittest.main()
