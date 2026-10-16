import unittest

from scripts.run_clean_clone_layer_a import layer_a_commands
from scripts.run_public_integrity import build_report
from scripts.reconstruct_release_evidence import OUTPUT as RECONSTRUCTION_OUTPUT


class PublicIntegrityEntrypointTests(unittest.TestCase):
    def test_entrypoint_reuses_the_canonical_layer_a_contract(self):
        report = build_report(run_commands=False)
        self.assertEqual(report["expected_test_count"], 150)
        self.assertEqual(report["commands"], layer_a_commands())
        self.assertEqual(
            report["pinned_submodule"],
            "c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010",
        )
        self.assertFalse(report["executed"])
        self.assertEqual(
            str(RECONSTRUCTION_OUTPUT),
            "results/release_evidence_reconstruction_v5_20261017.json",
        )


if __name__ == "__main__":
    unittest.main()
