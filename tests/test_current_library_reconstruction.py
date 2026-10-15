import copy
import unittest
from pathlib import Path

from scripts.audit_current_library_reconstruction import build_reconstruction_audit


ROOT = Path(__file__).resolve().parents[1]


class CurrentLibraryReconstructionTests(unittest.TestCase):
    def test_current_manifests_reconstruct_all_public_output_identities(self):
        audit = build_reconstruction_audit(ROOT)
        self.assertTrue(audit["manifest_validation"]["passed"])
        self.assertEqual(audit["manifest_validation"]["operational_description_length_bits"], 17728)
        self.assertTrue(audit["mixed_identity"]["exact_identity_pass"])
        self.assertEqual(audit["mixed_identity"]["totals"]["records"], 2985)
        self.assertEqual(audit["mixed_identity"]["totals"]["exact_matches"], 2985)
        self.assertEqual(audit["mixed_identity"]["totals"]["output_mismatches"], 0)
        self.assertEqual(audit["mixed_identity"]["totals"]["route_mismatches"], 0)
        self.assertTrue(audit["existing_audit_equivalence"]["passed"])
        self.assertEqual(audit["safety"]["api_or_model_calls"], 0)
        self.assertFalse(audit["safety"]["restricted_bodies_read"])

    def test_equivalence_comparison_detects_changed_existing_claim_field(self):
        audit = build_reconstruction_audit(ROOT)
        changed = copy.deepcopy(audit)
        changed["mixed_identity"]["totals"]["exact_matches"] -= 1
        self.assertNotEqual(
            changed["mixed_identity"]["totals"],
            audit["mixed_identity"]["totals"],
        )


if __name__ == "__main__":
    unittest.main()
