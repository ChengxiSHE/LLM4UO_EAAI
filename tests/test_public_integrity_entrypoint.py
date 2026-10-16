import unittest

from scripts.run_clean_clone_layer_a import layer_a_commands
from scripts.run_public_integrity import build_report


class PublicIntegrityEntrypointTests(unittest.TestCase):
    def test_entrypoint_reuses_the_canonical_layer_a_contract(self):
        report = build_report(run_commands=False)
        self.assertEqual(report["expected_test_count"], 79)
        self.assertEqual(report["commands"], layer_a_commands())
        self.assertEqual(
            report["pinned_submodule"],
            "c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010",
        )
        self.assertFalse(report["executed"])


if __name__ == "__main__":
    unittest.main()
