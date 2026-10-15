import base64
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest

from llm4or.schema import canonical
from llm4or.typed_count_skill import enumerate_candidates, verify_candidate
from scripts import audit_prospective_acquisition_canary as auditor
from scripts import freeze_prospective_acquisition_canary as freezer
from scripts import run_prospective_acquisition_canary as runner


ROOT = Path(__file__).resolve().parents[1]


def envelope(candidate, usage=(90, 10)):
    value = {
        "model": "DeepSeek-V4-Flash",
        "usage": {
            "prompt_tokens": usage[0],
            "completion_tokens": usage[1],
            "total_tokens": sum(usage),
        },
        "choices": [{
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": canonical(candidate)},
        }],
    }
    return {
        "error": None,
        "global_halt": False,
        "http_status": 200,
        "envelope_base64": base64.b64encode(canonical(value).encode()).decode(),
    }


class AuditProspectiveAcquisitionCanaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in freezer.INPUT_FILES:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        (self.root / "experiments").mkdir(exist_ok=True)
        (self.root / "results/private").mkdir(parents=True, exist_ok=True)
        freezer.freeze(self.root, created_at=time.time())
        self.bundle = json.loads((self.root / freezer.BUNDLE).read_text())
        self.plan = json.loads((self.root / freezer.PLAN).read_text())
        cases = freezer._inputs(self.root)[1]
        self.winner = next(
            candidate for candidate in enumerate_candidates()
            if verify_candidate(candidate, cases)["passed"]
        )
        self.treatment_wins = {
            row["unit_id"] for row in self.bundle["units"][:2]
        }

    def tearDown(self):
        self.temp.cleanup()

    def _run_gate_pass(self):
        def request_once(body, _ca, _seconds):
            payload = json.loads(json.loads(body)["messages"][1]["content"])
            if (payload["arm"] == "separating_witness" and
                    payload["unit_id"] in self.treatment_wins):
                return envelope(self.winner)
            return envelope(payload["source_proposal"])
        return runner.execute(self.root, request_once=request_once)

    def test_recomputes_full_eight_pair_gate_and_exact_accounting(self):
        result = self._run_gate_pass()
        audit = auditor.build_audit(self.root)
        self.assertEqual(len(audit["paired_units"]), 8)
        self.assertEqual(audit["paired_counts"], {
            "treatment_only": 2,
            "flat_only": 0,
            "both": 0,
            "neither": 6,
        })
        self.assertTrue(audit["engineering_gate"]["passed"])
        self.assertEqual(
            audit["progression_decision"],
            "eligible_to_prepare_stage2_preregistration_not_authorized_to_dispatch",
        )
        self.assertEqual(audit["accounting"], result["accounting"])
        self.assertTrue(all(row["denominator_included"] for row in audit["paired_units"]))
        self.assertTrue(all(row["flat"]["logical_cells"] == 3 and
                            row["separating_witness"]["logical_cells"] == 3
                            for row in audit["paired_units"]))

    def test_gate_function_keeps_neither_and_unavailable_in_denominator(self):
        pairs = [
            {"unit_id": f"u{i}", "flat_success": False,
             "treatment_success": i < 2, "global_safety_failure": False}
            for i in range(8)
        ]
        gate = auditor.evaluate_gate(pairs)
        self.assertEqual(gate["counts"], {
            "treatment_only": 2, "flat_only": 0, "both": 0, "neither": 6,
        })
        self.assertTrue(gate["passed"])
        pairs[2]["flat_success"] = True
        self.assertFalse(auditor.evaluate_gate(pairs)["passed"])
        pairs[2]["flat_success"] = False
        pairs[7]["global_safety_failure"] = True
        self.assertFalse(auditor.evaluate_gate(pairs)["passed"])

    def test_private_candidate_or_envelope_tamper_is_rejected(self):
        self._run_gate_pass()
        run = self.root / self.plan["run_directory"]
        target = next((run / "candidates").glob("*.json"))
        value = json.loads(target.read_text())
        value["verification"]["passed"] = not value["verification"]["passed"]
        target.write_text(canonical(value))
        with self.assertRaisesRegex(ValueError, "candidate"):
            auditor.build_audit(self.root)

    def test_terminal_join_tamper_is_rejected(self):
        self._run_gate_pass()
        run = self.root / self.plan["run_directory"]
        target = next((run / "cells").glob("*.json"))
        value = json.loads(target.read_text())
        value["arm"] = "separating_witness" if value["arm"] == "flat" else "flat"
        target.write_text(canonical(value))
        with self.assertRaisesRegex(ValueError, "terminal"):
            auditor.build_audit(self.root)

    def test_public_audit_is_body_free_exclusive_and_canary_bounded(self):
        self._run_gate_pass()
        audit = auditor.publish(self.root)
        text = canonical(audit).casefold()
        for prohibited in (
            "instruction", "messages", "source_proposal", "revealed_facts",
            "response_schema", "envelope_base64", "accepted_value", "api_key",
            "authorization", "solved_vector", "reference_answer", "winner_hash",
        ):
            self.assertNotIn(prohibited, text)
        self.assertEqual(audit["claim_boundary"], {
            "engineering_canary_only": True,
            "automatic_acquisition_efficacy_claimed": False,
            "confirmatory_effect_claimed": False,
            "benchmark_accuracy_claimed": False,
            "library_promotion_performed": False,
        })
        saved = (self.root / freezer.AUDIT).read_bytes()
        with self.assertRaisesRegex(ValueError, "audit_output_exists"):
            auditor.publish(self.root)
        self.assertEqual(saved, (self.root / freezer.AUDIT).read_bytes())


if __name__ == "__main__":
    unittest.main()
