import base64
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest

from llm4or.schema import canonical, digest
from llm4or.typed_count_skill import enumerate_candidates, verify_candidate
from scripts import freeze_prospective_acquisition_canary as freezer
from scripts import run_prospective_acquisition_canary as runner


ROOT = Path(__file__).resolve().parents[1]


def provider_envelope(candidate, *, model="DeepSeek-V4-Flash", usage=(100, 20)):
    value = {
        "model": model,
        "usage": {
            "prompt_tokens": usage[0],
            "completion_tokens": usage[1],
            "total_tokens": usage[0] + usage[1],
        },
        "choices": [{
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": canonical(candidate),
            },
        }],
    }
    return {
        "error": None,
        "global_halt": False,
        "http_status": 200,
        "envelope_base64": base64.b64encode(canonical(value).encode()).decode(),
    }


class FakeTransport:
    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = []
        self.active = 0
        self.peak = 0
        self.lock = threading.Lock()

    def __call__(self, body, expected_ca_sha256, seconds):
        request = json.loads(body)
        payload = json.loads(request["messages"][1]["content"])
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
            self.calls.append({
                "unit_id": payload["unit_id"],
                "arm": payload["arm"],
                "round": payload["round"],
                "body_sha256": runner.sha(body),
                "ca": expected_ca_sha256,
                "seconds": seconds,
            })
        try:
            time.sleep(0.01)
            return self.behavior(payload)
        finally:
            with self.lock:
                self.active -= 1


class RunProspectiveAcquisitionCanaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in freezer.INPUT_FILES:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        (self.root / "experiments").mkdir(exist_ok=True)
        (self.root / "results/private").mkdir(parents=True, exist_ok=True)
        self.frozen = freezer.freeze(self.root, created_at=time.time())
        self.bundle = json.loads((self.root / freezer.BUNDLE).read_text())
        self.plan = json.loads((self.root / freezer.PLAN).read_text())
        self.public_cases = freezer._inputs(self.root)[1]
        self.winner = next(
            candidate for candidate in enumerate_candidates()
            if verify_candidate(candidate, self.public_cases)["passed"]
        )

    def tearDown(self):
        self.temp.cleanup()

    def _read_report(self):
        return json.loads((self.root / freezer.REPORT).read_text())

    def test_peak_concurrency_five_round_barriers_and_exact_single_send(self):
        transport = FakeTransport(
            lambda payload: provider_envelope(payload["source_proposal"], usage=(11, 7))
        )
        report = runner.execute(self.root, request_once=transport)
        self.assertEqual(transport.peak, 5)
        self.assertEqual(len(transport.calls), 48)
        self.assertEqual(len({row["body_sha256"] for row in transport.calls}), 48)
        rounds = [row["round"] for row in transport.calls]
        self.assertLess(max(i for i, value in enumerate(rounds) if value == 1),
                        min(i for i, value in enumerate(rounds) if value == 2))
        self.assertLess(max(i for i, value in enumerate(rounds) if value == 2),
                        min(i for i, value in enumerate(rounds) if value == 3))
        self.assertEqual(report["accounting"]["logical_cells"], 48)
        self.assertEqual(report["accounting"]["physical_attempts_reserved"], 48)
        self.assertEqual(report["accounting"]["physical_attempts_completed"], 48)
        self.assertEqual(report["accounting"]["usage"], {
            "prompt_tokens": 528,
            "completion_tokens": 336,
            "total_tokens": 864,
        })
        self.assertEqual(report["status_counts"], {"invalid_candidate": 48})

    def test_success_skips_later_rounds_and_second_execute_is_immutable(self):
        transport = FakeTransport(lambda _: provider_envelope(self.winner))
        first = runner.execute(self.root, request_once=transport)
        self.assertEqual(len(transport.calls), 16)
        self.assertEqual(first["status_counts"], {
            "accepted_candidate": 16,
            "skipped_after_success": 32,
        })
        saved = (self.root / freezer.REPORT).read_bytes()
        second = runner.execute(
            self.root,
            request_once=lambda *_: self.fail("terminal execution must not send"),
        )
        self.assertEqual(first, second)
        self.assertEqual(saved, (self.root / freezer.REPORT).read_bytes())

    def test_orphan_reservation_is_never_resent(self):
        first = self.plan["cells"][0]
        directory = self.root / self.plan["run_directory"] / "reservations"
        directory.mkdir(parents=True)
        runner.write_new_json(
            directory / (first["cell_id"] + ".json"),
            runner.reservation_for(self.plan, first),
        )
        transport = FakeTransport(
            lambda payload: provider_envelope(payload["source_proposal"])
        )
        report = runner.execute(self.root, request_once=transport)
        self.assertEqual(len(transport.calls), 47)
        cell = next(row for row in report["cells"] if row["cell_id"] == first["cell_id"])
        self.assertEqual(cell["status"], "infrastructure_unavailable")
        self.assertEqual(cell["reason"], "orphaned_reservation_no_replay")
        self.assertEqual(report["accounting"]["physical_attempts_reserved"], 48)
        self.assertEqual(report["accounting"]["physical_attempts_completed"], 47)

    def test_local_invalid_and_transport_failures_do_not_stop_independent_work(self):
        def behavior(payload):
            if payload["round"] == 1 and payload["arm"] == "flat":
                return {"error": "transport_connection_error", "global_halt": False}
            return provider_envelope(payload["source_proposal"])

        transport = FakeTransport(behavior)
        report = runner.execute(self.root, request_once=transport)
        self.assertEqual(len(transport.calls), 48)
        self.assertEqual(report["status_counts"], {
            "infrastructure_unavailable": 8,
            "invalid_candidate": 40,
        })
        self.assertFalse(report["global_halt"]["triggered"])

    def test_global_provider_fault_halts_future_scheduling(self):
        fired = threading.Event()

        def behavior(payload):
            if not fired.is_set():
                fired.set()
                return provider_envelope(payload["source_proposal"], model="wrong-model")
            return provider_envelope(payload["source_proposal"])

        transport = FakeTransport(behavior)
        report = runner.execute(self.root, request_once=transport)
        self.assertTrue(report["global_halt"]["triggered"])
        self.assertEqual(report["global_halt"]["reason"], "provider_model_mismatch")
        self.assertLessEqual(len(transport.calls), 16)
        self.assertEqual(len(report["cells"]), 48)
        self.assertGreater(report["status_counts"].get("global_halt_not_dispatched", 0), 0)

    def test_public_report_contains_no_request_response_or_candidate_material(self):
        transport = FakeTransport(lambda _: provider_envelope(self.winner))
        report = runner.execute(self.root, request_once=transport)
        text = canonical(report).casefold()
        for prohibited in (
            "instruction", "messages", "source_proposal", "revealed_facts",
            "response_schema", "envelope_base64", "raw_content",
            "authorization", "api_key", "accepted_value", "winner",
        ):
            self.assertNotIn(prohibited, text)
        self.assertEqual(report, self._read_report())
        run = self.root / self.plan["run_directory"]
        self.assertEqual(len(list((run / "reservations").glob("*.json"))), 16)
        self.assertEqual(len(list((run / "envelopes").glob("*.json"))), 16)
        self.assertEqual(len(list((run / "candidates").glob("*.json"))), 16)

    def test_tampered_frozen_inputs_fail_before_dispatch(self):
        value = json.loads((self.root / freezer.BUNDLE).read_text())
        value["cells"][next(iter(value["cells"]))]["payload"]["round"] = 3
        (self.root / freezer.BUNDLE).write_text(canonical(value))
        transport = FakeTransport(lambda _: provider_envelope(self.winner))
        with self.assertRaisesRegex(ValueError, "bundle"):
            runner.execute(self.root, request_once=transport)
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
