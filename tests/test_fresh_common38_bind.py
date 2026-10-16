import json
from pathlib import Path
import tempfile
import unittest

from llm4or import fresh_common38_bind as bind


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
            "retry_attempts": 0,
            "reserved_or_reported_tokens": 3800,
            "halt": None,
        }


class FreshCommon38BindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = bind.build_plan(ROOT)

    def test_plan_binds_38_without_bodies_or_answers(self):
        self.assertEqual(len(self.plan["bindings"]), 38)
        self.assertEqual(self.plan["external_method"]["max_calls"], 3)
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"], 5)
        self.assertEqual(self.plan["resilience"]["max_attempts_per_request"], 3)
        self.assertEqual(self.plan["model"], "DeepSeek-V4-Flash")
        rendered = json.dumps(self.plan, sort_keys=True)
        for prohibited in (
            '"public_payload"', '"instance_data"', '"text"', '"objective"',
            '"point"', '"optimum"', '"api_key"',
        ):
            self.assertNotIn(prohibited, rendered)

    def test_controller_checkpoints_and_resumes_terminal_cells(self):
        calls = []

        def fake_runner(public, source, gateway, scope, replicate, token_cap,
                        prompts, reference_loader, **kwargs):
            calls.append(scope)
            reference_loader()
            return {
                "status": "completed_failure", "success": False,
                "rounds_used": 1,
                "rounds": [{
                    "round": 1, "execution_succeeded": False,
                    "status_matches": False, "objective_matches": False,
                }],
                "usage": {"logical_requests": 1, "logical_tokens": 100},
            }

        gateway = FakeGateway()
        with tempfile.TemporaryDirectory() as directory:
            first = bind.run_plan(
                ROOT, self.plan, Path(directory), gateway,
                runner=fake_runner, workers=5,
            )
            second = bind.run_plan(
                ROOT, self.plan, Path(directory), gateway,
                runner=fake_runner, workers=5,
            )
        self.assertEqual(first["terminal"], 38)
        self.assertEqual(first["new_items"], 38)
        self.assertEqual(second["new_items"], 0)
        self.assertEqual(len(calls), 38)

    def test_scoring_separates_round_one_from_answer_bearing_final(self):
        cells = []
        for index, row in enumerate(self.plan["bindings"]):
            round_one = index % 3 == 0
            final = round_one or index % 3 == 1
            rounds = [{
                "round": 1, "execution_succeeded": round_one,
                "status_matches": round_one, "objective_matches": round_one,
            }]
            if not round_one:
                rounds.append({
                    "round": 2, "execution_succeeded": final,
                    "status_matches": final, "objective_matches": final,
                })
            cells.append({
                "id": row["id"], "family": row["family"],
                "status": "completed", "record": {
                    "status": "completed_success" if final else "completed_failure",
                    "success": final, "rounds_used": len(rounds), "rounds": rounds,
                },
            })
        result = bind.score_cells(self.plan, cells, {
            "physical_attempts": 60, "retry_attempts": 2,
            "reserved_or_reported_tokens": 1234, "halt": None,
        })
        self.assertEqual(result["round_one"]["correct"], 13)
        self.assertEqual(result["final"]["correct"], 26)
        self.assertEqual(result["paired"]["corrections"], 13)
        self.assertEqual(result["paired"]["regressions"], 0)
        rendered = json.dumps(result, sort_keys=True)
        for prohibited in ('"objective"', '"point"', '"optimum"', '"code"', '"text"'):
            self.assertNotIn(prohibited, rendered)


if __name__ == "__main__":
    unittest.main()
