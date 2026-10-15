import copy
import hashlib
import json
import unittest

from llm4or.mixed_skill_router import OR_DEBUG_ROUTE, TSP_ROUTE
from scripts.audit_mixed_skill_confirmation import audit_identity


class AuditMixedSkillConfirmationTests(unittest.TestCase):
    @staticmethod
    def _digest(value):
        raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def _fixtures(self):
        bundle = [
            {"record_id": "tsp-1", "source": "tsp", "public_envelope_sha256": "a" * 64},
            {"record_id": "or-1", "source": "or_debug", "public_envelope_sha256": "b" * 64},
        ]
        tsp_output = {"status": "optimal", "value": 7}
        or_output = {"problem_id": "or-1", "status": "complete"}
        tsp_direct = [
            {"problem_id": "tsp-1", "candidate_sha256": self._digest(tsp_output)}
        ]
        or_direct = [
            {
                "problem_id": "or-1",
                "evolved": {"output_sha256": self._digest(or_output)},
            }
        ]
        mixed = [
            {
                "record_id": "tsp-1",
                "source": "tsp",
                "route": TSP_ROUTE,
                "status": "complete",
                "output_sha256": self._digest(tsp_output),
            },
            {
                "record_id": "or-1",
                "source": "or_debug",
                "route": OR_DEBUG_ROUTE,
                "status": "complete",
                "output_sha256": self._digest(or_output),
            },
        ]
        return bundle, mixed, tsp_direct, or_direct

    def test_fully_equal_fixture_passes_identity_gate(self) -> None:
        audit = audit_identity(*self._fixtures())

        self.assertTrue(audit["exact_identity_pass"])
        self.assertEqual(audit["totals"]["exact_matches"], 2)
        self.assertEqual(audit["totals"]["route_mismatches"], 0)
        self.assertEqual(audit["totals"]["missing_mixed_records"], 0)

    def test_one_tsp_output_mismatch_fails_identity_gate(self) -> None:
        bundle, mixed, tsp_direct, or_direct = self._fixtures()
        mixed[0]["output_sha256"] = "c" * 64

        audit = audit_identity(bundle, mixed, tsp_direct, or_direct)

        self.assertFalse(audit["exact_identity_pass"])
        self.assertEqual(audit["families"]["tsp"]["output_mismatches"], 1)

    def test_one_or_debug_output_mismatch_fails_identity_gate(self) -> None:
        bundle, mixed, tsp_direct, or_direct = self._fixtures()
        mixed[1]["output_sha256"] = "d" * 64

        audit = audit_identity(bundle, mixed, tsp_direct, or_direct)

        self.assertFalse(audit["exact_identity_pass"])
        self.assertEqual(audit["families"]["or_debug"]["output_mismatches"], 1)

    def test_missing_mixed_record_is_counted(self) -> None:
        bundle, mixed, tsp_direct, or_direct = self._fixtures()

        audit = audit_identity(bundle, mixed[:1], tsp_direct, or_direct)

        self.assertFalse(audit["exact_identity_pass"])
        self.assertEqual(audit["totals"]["missing_mixed_records"], 1)

    def test_duplicate_mixed_record_is_counted(self) -> None:
        bundle, mixed, tsp_direct, or_direct = self._fixtures()
        mixed.append(copy.deepcopy(mixed[0]))

        audit = audit_identity(bundle, mixed, tsp_direct, or_direct)

        self.assertFalse(audit["exact_identity_pass"])
        self.assertEqual(audit["totals"]["duplicate_mixed_records"], 1)

    def test_invalid_mixed_record_cannot_be_silently_dropped(self) -> None:
        bundle, mixed, tsp_direct, or_direct = self._fixtures()
        mixed.append(
            {
                "record_id": None,
                "source": None,
                "route": None,
                "status": "execution_failed",
                "reason": "invalid_outer_record",
            }
        )

        audit = audit_identity(bundle, mixed, tsp_direct, or_direct)

        self.assertFalse(audit["exact_identity_pass"])
        self.assertEqual(audit["totals"]["invalid_mixed_records"], 1)
        self.assertEqual(audit["totals"]["terminal_failures"], 1)

    def test_mixed_source_mismatch_fails_identity_gate(self) -> None:
        bundle, mixed, tsp_direct, or_direct = self._fixtures()
        mixed[0]["source"] = "or_debug"

        audit = audit_identity(bundle, mixed, tsp_direct, or_direct)

        self.assertFalse(audit["exact_identity_pass"])
        self.assertEqual(audit["totals"]["source_mismatches"], 1)


if __name__ == "__main__":
    unittest.main()
