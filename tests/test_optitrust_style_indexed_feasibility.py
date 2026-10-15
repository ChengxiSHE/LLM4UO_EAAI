import json
from pathlib import Path
import tempfile
import unittest

from llm4or.formal_gateway import FormalGateway
from llm4or.optitrust_style_indexed_feasibility import (
    build_audit_from, build_plan, run_plan, score_run, selected_cases,
)
from llm4or.schema import digest


ROOT = Path(__file__).resolve().parents[1]


def scalar_ir():
    return {
        "schema": "indexed-milp-ir-v1", "data_parameter": "instance_data", "sets": [],
        "variables": [{"id": "z", "meaning": "fixed decision", "domain": "continuous",
                       "forall": [], "where": True, "lower": 0, "upper": 0, "unit": "unit"}],
        "constraints": [],
        "objective": {"terms": [], "sense": "min", "unit": "unit", "offset": 0},
    }


def responder(payload, _body):
    slot = payload["context"]["step"]
    if slot in (0, 1): text = json.dumps({"components": "bounded components"})
    elif slot in (2, 3): text = json.dumps({"formulation": "bounded formulation"})
    elif slot == 4: text = json.dumps(scalar_ir())
    else:
        candidate = payload["context"]["candidate_ir"]
        text = json.dumps({
            "schema": "optitrust-ir-review-v1", "candidate_sha256": digest(candidate),
            "verdict": "accept", "patches": [],
        })
    return {"text": text, "prompt_tokens": 50, "completion_tokens": 50,
            "total_tokens": 100, "finish_reason": "stop", "reported_model": "DeepSeek-V4-Flash"}


class IndexedFeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.plan = build_plan(ROOT)

    def test_plan_selects_one_max_public_size_case_per_family(self):
        self.assertEqual([row["id"] for row in selected_cases(ROOT)], [
            "text2opt_rcpsp_rcpsp_050", "text2opt_vrptw_vrptw_047",
        ])
        self.assertEqual(self.plan["matrix"], {
            "feasibility_cells": 2, "logical_requests": 20,
            "candidate_solves_at_most": 10,
        })
        self.assertEqual(self.plan["external_method"]["name"], "OptiTrustStyleIndexed")
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"], 2)
        self.assertEqual(self.plan["resilience"]["retryable_local_errors"], ["invalid_json_response"])
        self.assertFalse(self.plan["claim_boundary"]["benchmark_accuracy_estimated"])

    def test_offline_full_trajectory_restart_score_and_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary); directory = temporary / "run"
            gateway = FormalGateway(ROOT, self.plan, offline=True, directory=directory, responder=responder)
            solver_calls = []
            def solve(operation, **kwargs): solver_calls.append(operation); return {"status": "optimal", "objective": 0}
            first = run_plan(ROOT, self.plan, directory, gateway, solver=solve, workers=2)
            second = run_plan(ROOT, self.plan, directory, gateway, solver=solve, workers=2)
            self.assertEqual(first["status_counts"], {"completed": 2})
            self.assertEqual(second["new_items"], 0)
            self.assertEqual(gateway.summary()["physical_attempts"], 20)
            self.assertEqual(len(solver_calls), 10)
            result = score_run(self.plan, directory, restart_new_items=0)
            self.assertTrue(result["feasibility_gate"]["passed"])
            self.assertEqual(result["feasibility_gate"]["selected_consensus_cells"], 2)
            plan_path = temporary / "plan.json"; plan_path.write_text(json.dumps(self.plan))
            result_path = temporary / "result.json"; result_path.write_text(json.dumps(result))
            audit = build_audit_from(ROOT, self.plan, plan_path, directory, result_path, expected_offline=True)
            self.assertEqual(audit["status"], "passed")
            self.assertEqual(audit["execution"], {"new_provider_calls": 0, "new_solver_calls": 0})


if __name__ == "__main__": unittest.main()
