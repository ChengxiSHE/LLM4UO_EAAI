import json
from pathlib import Path
import tempfile
import unittest

from llm4or.formal_gateway import FormalGateway, validate_fresh_external_payload
from llm4or.optitrust_style_indexed_capacity import (
    build_audit_from, build_plan, capacity_payload, run_plan, score_run, selected_cases,
)


ROOT = Path(__file__).resolve().parents[1]


def scalar_ir():
    return {
        "schema": "indexed-milp-ir-v1", "data_parameter": "instance_data",
        "sets": [],
        "variables": [{
            "id": "z", "meaning": "synthetic fixed decision", "unit": "unit",
            "domain": "continuous", "forall": [], "where": True,
            "lower": 0, "upper": 0,
        }],
        "constraints": [],
        "objective": {"terms": [], "sense": "min", "unit": "unit", "offset": 0},
    }


def responder(payload, body):
    assert payload["context"]["stage"] == "canonical_indexed_ir"
    assert body["max_tokens"] == 3072
    text = json.dumps(scalar_ir(), separators=(",", ":"))
    return {
        "text": text, "prompt_tokens": 100, "completion_tokens": 200,
        "total_tokens": 300, "finish_reason": "stop",
        "reported_model": "DeepSeek-V4-Flash",
    }


class IndexedCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = build_plan(ROOT)

    def test_selection_is_outcome_blind_generic_extrema_union(self):
        cases = selected_cases(ROOT)
        self.assertEqual(
            [row["id"] for row in cases],
            [
                "text2opt_rcpsp_rcpsp_050",
                "text2opt_vrptw_vrptw_047",
                "text2opt_vrptw_vrptw_049",
            ],
        )
        self.assertTrue(all(set(row) == {
            "id", "family", "public", "public_input_sha256", "selection_reasons",
            "public_bytes", "recursive_nodes", "max_list_length",
        } for row in cases))
        self.assertTrue(all("reference" not in json.dumps(row).lower() for row in cases))

    def test_plan_binds_three_single_requests_and_preparation_transport(self):
        self.assertEqual(self.plan["external_method"]["name"], "OptiTrustStyleIndexedCapacity")
        self.assertEqual(self.plan["matrix"], {"capacity_cells": 3, "logical_requests": 3})
        self.assertEqual(self.plan["limits"]["max_completion_tokens"], 3072)
        self.assertEqual(self.plan["limits"]["max_output_bytes"], 32768)
        self.assertEqual(self.plan["limits"]["max_requests"], 9)
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"], 3)
        self.assertEqual(self.plan["resilience"]["retryable_local_errors"], ["invalid_json_response"])
        self.assertEqual(self.plan["transport"]["kind"], "openai_httpx_single_attempt_v1")
        self.assertIn(".venv-preparation/bin/python", self.plan["transport"]["python"])
        self.assertFalse(self.plan["claim_boundary"]["benchmark_accuracy_estimated"])

    def test_formal_gateway_accepts_only_exact_capacity_payload(self):
        case = selected_cases(ROOT)[0]
        scope = "optitrustindexedcapacity:OptiTrustStyleIndexedCapacity:0:" + case["id"]
        payload = capacity_payload(case["public"])
        spec = validate_fresh_external_payload(self.plan, scope, payload, 0, 0)
        self.assertEqual(spec["problem_id"], case["id"])
        changed = json.loads(json.dumps(payload))
        changed["context"]["safe_execution_adapter"] = "changed"
        with self.assertRaisesRegex(Exception, "fresh_external_payload_changed"):
            validate_fresh_external_payload(self.plan, scope, changed, 0, 0)

    def test_offline_run_restart_score_and_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            directory = temporary / "run"
            gateway = FormalGateway(
                ROOT, self.plan, offline=True, directory=directory, responder=responder,
            )
            first = run_plan(ROOT, self.plan, directory, gateway, workers=3)
            before = gateway.summary()["physical_attempts"]
            second = run_plan(ROOT, self.plan, directory, gateway, workers=3)
            after = gateway.summary()["physical_attempts"]
            self.assertEqual(first["status_counts"], {"completed": 3})
            self.assertEqual(first["new_items"], 3)
            self.assertEqual(second["new_items"], 0)
            self.assertEqual((before, after), (3, 3))
            result = score_run(self.plan, directory, restart_new_items=0)
            self.assertTrue(result["capacity_gate"]["passed"])
            self.assertEqual(result["capacity_gate"]["received_candidates"], 3)
            self.assertEqual(result["capacity_gate"]["admitted_candidates"], 3)
            self.assertEqual(result["capacity_gate"]["maximum_completion_tokens"], 200)
            plan_path = temporary / "plan.json"; plan_path.write_text(json.dumps(self.plan))
            result_path = temporary / "result.json"; result_path.write_text(json.dumps(result))
            audit = build_audit_from(ROOT, self.plan, plan_path, directory, result_path, expected_offline=True)
            self.assertEqual(audit["status"], "passed")
            self.assertEqual(audit["execution"], {"new_provider_calls": 0, "new_solver_calls": 0})

    def test_plan_scoped_invalid_json_retry_uses_second_attempt_without_global_halt(self):
        counts = {}
        def flaky(payload, body):
            problem_id = payload["problem"]["id"]
            counts[problem_id] = counts.get(problem_id, 0) + 1
            text = "{" if counts[problem_id] == 1 else json.dumps(scalar_ir(), separators=(",", ":"))
            return {
                "text": text, "prompt_tokens": 100, "completion_tokens": 20,
                "total_tokens": 120, "finish_reason": "stop",
                "reported_model": "DeepSeek-V4-Flash",
            }
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            gateway = FormalGateway(
                ROOT, self.plan, offline=True, directory=directory, responder=flaky,
            )
            run = run_plan(ROOT, self.plan, directory, gateway, workers=3)
            self.assertEqual(run["status_counts"], {"completed": 3})
            self.assertEqual(gateway.summary()["physical_attempts"], 6)
            self.assertEqual(gateway.summary()["retry_attempts"], 3)
            self.assertIsNone(gateway.halt_reason())


if __name__ == "__main__":
    unittest.main()
