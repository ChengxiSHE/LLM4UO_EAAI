import json
from pathlib import Path
import tempfile
import unittest

from llm4or import fresh_common38_coe as coe


ROOT = Path(__file__).resolve().parents[1]


class FakeGateway:
    def __init__(self):
        self.started = []
        self.finished = []

    def work_started(self, scope):
        self.started.append(scope)

    def work_finished(self, scope, status, error=None):
        self.finished.append((scope, status, error))

    def summary(self):
        return {
            "physical_attempts": 418, "retry_attempts": 0,
            "reserved_or_reported_tokens": 4180, "halt": None,
        }


class FreshCommon38CoETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = coe.build_plan(ROOT)

    def test_plan_binds_current_snapshot_text_only_view_without_bodies(self):
        self.assertEqual(len(self.plan["bindings"]), 38)
        self.assertEqual(self.plan["external_method"]["snapshot"], "current")
        self.assertEqual(self.plan["external_method"]["max_calls"], 11)
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"], 5)
        rendered = json.dumps(self.plan, sort_keys=True)
        for prohibited in (
            '"public_payload"', '"instance_data"', '"text"', '"objective"',
            '"point"', '"optimum"', '"code_example"', '"api_key"',
        ):
            self.assertNotIn(prohibited, rendered)

    def test_controller_checkpoints_and_resumes(self):
        calls = []

        def fake_runner(public, native, function_name, gateway, scope, replicate,
                        token_cap, prompts, reference_loader, **kwargs):
            calls.append(scope)
            self.assertEqual(public["parameters"], [])
            self.assertEqual(public["instances"], [])
            reference_loader()
            return {
                "status": "completed", "author_accept": False,
                "tolerance_accept": False, "adapter_supported": False,
                "steps": [], "usage": {"logical_requests": 11, "logical_tokens": 100},
            }

        gateway = FakeGateway()
        with tempfile.TemporaryDirectory() as directory:
            first = coe.run_plan(
                ROOT, self.plan, Path(directory), gateway,
                runner=fake_runner, workers=5,
            )
            second = coe.run_plan(
                ROOT, self.plan, Path(directory), gateway,
                runner=fake_runner, workers=5,
            )
        self.assertEqual(first["terminal"], 38)
        self.assertEqual(first["new_items"], 38)
        self.assertEqual(second["new_items"], 0)
        self.assertEqual(len(calls), 38)

    def test_full_denominator_scoring_keeps_method_failures(self):
        cells = []
        for index, row in enumerate(self.plan["bindings"]):
            if index == 37:
                cells.append({
                    "id": row["id"], "family": row["family"],
                    "status": "method_failure", "record": None,
                })
            else:
                correct = index < 10
                cells.append({
                    "id": row["id"], "family": row["family"],
                    "status": "completed", "record": {
                        "author_accept": correct, "tolerance_accept": correct,
                        "adapter_supported": True,
                    },
                })
        result = coe.score_cells(self.plan, cells, {
            "physical_attempts": 418, "retry_attempts": 0,
            "reserved_or_reported_tokens": 1234, "halt": None,
        })
        self.assertEqual(result["aggregate"]["planned"], 38)
        self.assertEqual(result["aggregate"]["correct"], 10)
        self.assertEqual(result["aggregate"]["method_failure"], 1)
        self.assertEqual(result["aggregate"]["accuracy"], 10 / 38)
        rendered = json.dumps(result, sort_keys=True)
        for prohibited in ('"objective"', '"point"', '"optimum"', '"code"', '"text"'):
            self.assertNotIn(prohibited, rendered)

    def test_zero_correct_is_reported_explicitly(self):
        cells = [{
            "id": row["id"], "family": row["family"],
            "status": "method_failure", "record": None,
        } for row in self.plan["bindings"]]
        result = coe.score_cells(self.plan, cells, {})
        self.assertEqual(result["aggregate"]["correct"], 0)
        self.assertEqual(result["tolerance_secondary"]["correct"], 0)


if __name__ == "__main__":
    unittest.main()
