from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from llm4or.formal_gateway import FormalGateway
from llm4or.optitrust_style_compact_canary import (
    RESOURCE_LIMITS,
    build_audit_from,
    build_plan,
    run_plan,
    score_run,
    synthetic_cases,
)
from llm4or.schema import digest


ROOT = Path(__file__).resolve().parents[1]


def candidate_for(problem):
    return {
        "schema": "milp-v1",
        "variables": [{
            "id": "x", "meaning": "synthetic decision", "unit": "unit",
            "domain": "binary", "lower": 0, "upper": 1,
        }],
        "constraints": [],
        "objective": {
            "coefficients": {}, "sense": "min", "unit": "synthetic",
            "offset": 0,
        },
    }


def responder(payload, _body):
    slot = payload["context"]["step"]
    if slot in (0, 1):
        text = json.dumps({"components": "bounded synthetic components"})
    elif slot in (2, 3):
        text = json.dumps({"formulation": "bounded synthetic formulation"})
    elif slot == 4:
        text = json.dumps(candidate_for(payload["problem"]))
    else:
        candidate = payload["context"]["candidate"]
        text = json.dumps({
            "schema": "optitrust-review-v1",
            "candidate_sha256": digest(candidate),
            "verdict": "accept",
            "edits": [],
        })
    return {
        "text": text, "prompt_tokens": 10, "completion_tokens": 10,
        "total_tokens": 20, "finish_reason": "stop",
        "reported_model": "DeepSeek-V4-Flash",
    }


class CompactCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = build_plan(ROOT)

    def test_plan_freezes_four_nonbenchmark_inputs_and_capacity_limits(self):
        self.assertEqual(len(synthetic_cases()), 4)
        self.assertEqual(len(self.plan["public_inputs"]), 4)
        self.assertEqual(self.plan["matrix"], {
            "inference_cells": 4, "logical_requests": 40,
            "candidate_solves_at_most": 20,
        })
        self.assertEqual(self.plan["limits"]["max_requests"], 120)
        self.assertEqual(self.plan["resilience"]["max_attempts_per_request"], 3)
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"], 4)
        self.assertEqual(self.plan["resource_limits"], RESOURCE_LIMITS)
        self.assertEqual(self.plan["claim_boundary"]["benchmark_accuracy_estimated"], False)

    def test_offline_capacity_gate_restart_and_independent_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "run"
            gateway = FormalGateway(
                ROOT, self.plan, offline=True, directory=directory,
                responder=responder,
            )
            solver_calls = []

            def solve(operation, **_kwargs):
                solver_calls.append(deepcopy(operation))
                return {"status": "optimal", "objective": 0.0}

            first = run_plan(
                ROOT, self.plan, directory, gateway, solver=solve, workers=4,
            )
            before = gateway.summary()["physical_attempts"]
            second = run_plan(
                ROOT, self.plan, directory, gateway, solver=solve, workers=4,
            )
            after = gateway.summary()["physical_attempts"]
            self.assertEqual(first["terminal"], 4)
            self.assertEqual(first["new_items"], 4)
            self.assertEqual(first["status_counts"], {"completed": 4})
            self.assertEqual(second["new_items"], 0)
            self.assertEqual((before, after), (40, 40))
            result = score_run(self.plan, directory, restart_new_items=0)
            self.assertTrue(result["capacity_gate"]["passed"])
            self.assertEqual(result["capacity_gate"]["logical_slots"], 40)
            self.assertEqual(result["capacity_gate"]["infrastructure_unavailable"], 0)
            result_path = Path(tmp) / "result.json"
            result_path.write_text(json.dumps(result, sort_keys=True))
            plan_path = Path(tmp) / "plan.json"
            plan_path.write_text(json.dumps(self.plan, sort_keys=True))
            audit = build_audit_from(
                ROOT, self.plan, plan_path, directory, result_path,
                expected_offline=True,
            )
            self.assertEqual(audit["status"], "passed")
            self.assertEqual(audit["execution"], {
                "new_provider_calls": 0, "new_solver_calls": 0,
            })
            self.assertEqual(len(solver_calls), 20)


if __name__ == "__main__":
    unittest.main()
