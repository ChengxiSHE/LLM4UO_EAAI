import json
from pathlib import Path
import tempfile
import unittest

from llm4or import fresh_common38_base as base


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
            "physical_attempts": 38,
            "logical_requests": 38,
            "retry_attempts": 0,
            "failed_physical_attempts": 0,
            "reserved_or_reported_tokens": 3800,
            "logical_tokens": 3800,
            "halt": None,
        }


class FreshCommon38BaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = base.build_plan(ROOT)

    def test_plan_binds_one_answer_blind_call_for_38_identities(self):
        self.assertEqual(len(self.plan["bindings"]), 38)
        self.assertEqual(self.plan["external_method"], {
            "name": "Base", "scope_stage": "freshbase", "max_calls": 1,
            "answer_blind": True,
        })
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"], 5)
        self.assertEqual(self.plan["resilience"]["max_attempts_per_request"], 3)
        self.assertEqual(self.plan["model"], "DeepSeek-V4-Flash")
        rendered = json.dumps(self.plan, sort_keys=True)
        for prohibited in (
            '"public_payload"', '"text"', '"objective"', '"point"',
            '"optimum"', '"api_key"',
        ):
            self.assertNotIn(prohibited, rendered)

    def test_controller_checkpoints_and_resumes_terminal_cells(self):
        calls = []

        def fake_runner(public, gateway, scope, replicate, token_cap, **kwargs):
            calls.append(scope)
            return {
                "status": "optimal", "model_sha256": "a" * 64,
                "objective": 0.0, "point": {}, "reason": None,
            }

        gateway = FakeGateway()
        with tempfile.TemporaryDirectory() as directory:
            first = base.run_plan(
                ROOT, self.plan, Path(directory), gateway,
                runner=fake_runner, workers=5,
            )
            second = base.run_plan(
                ROOT, self.plan, Path(directory), gateway,
                runner=fake_runner, workers=5,
            )
        self.assertEqual(first["terminal"], 38)
        self.assertEqual(first["new_items"], 38)
        self.assertEqual(second["new_items"], 0)
        self.assertEqual(len(calls), 38)

    def test_scoring_uses_full_denominator_and_hides_answers(self):
        cells = []
        references = {}
        for index, row in enumerate(self.plan["bindings"]):
            correct = index < 9
            cells.append({
                "id": row["id"], "family": row["family"],
                "status": "completed", "error": None,
                "record": {
                    "status": "optimal", "objective": float(index if correct else index + 1),
                    "model_sha256": "a" * 64,
                },
            })
            references[row["id"]] = {"solver_status": 2, "optimum": float(index)}
        result = base.score_cells(self.plan, cells, references, FakeGateway().summary())
        self.assertEqual(result["aggregate"]["planned"], 38)
        self.assertEqual(result["aggregate"]["correct"], 9)
        self.assertEqual(len(result["rows"]), 38)
        rendered = json.dumps(result, sort_keys=True)
        for prohibited in ('"objective"', '"point"', '"optimum"', '"text"'):
            self.assertNotIn(prohibited, rendered)


if __name__ == "__main__":
    unittest.main()
