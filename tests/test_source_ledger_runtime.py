import json
from pathlib import Path
import tempfile
import unittest

from llm4or.formal_gateway import FormalGateway
from llm4or.milp_solver import execute
from llm4or.schema import canonical
from llm4or.source_ledger_runtime import VERSION, run_source_ledger_probe
from tests.test_source_ledger import PROBLEM, ledger


class SourceLedgerRuntimeTests(unittest.TestCase):
    def test_offline_probe_exposes_all_ablation_models(self):
        initial = {
            "schema": "milp-v1",
            "variables": [{"id": "x000", "meaning": "Number of apple crates", "unit": "crates",
                           "domain": "continuous", "lower": 0, "upper": 10}],
            "constraints": [{"id": "c000", "coefficients": {"x000": 3}, "sense": "ge", "rhs": 12}],
            "objective": {"coefficients": {"x000": 5}, "sense": "min", "unit": "dollars", "offset": 0},
        }
        initial_record = {"input_sha256": __import__("llm4or.benchmark_inputs", fromlist=["payload_sha256"]).payload_sha256(PROBLEM),
                          "final_model": initial}
        plan = {
            "run_directory": "unused",
            "trajectory_token_caps": [65536],
            "limits": {"max_requests": 6, "max_total_reserved_or_reported_tokens": 1000000,
                       "max_completion_tokens": 8192, "max_input_bytes": 196608,
                       "max_output_bytes": 196608, "token_overhead_reserve": 2048,
                       "request_seconds": 10, "max_run_seconds": 60, "minimum_free_disk_bytes": 0},
            "resilience": {"max_attempts_per_request": 1, "backoff_seconds": [],
                           "circuit_breaker_consecutive_failures": 8, "max_concurrent_requests": 1},
            "matrix": {"inference_cells": 1}, "progress_stage": "v7dev",
        }
        replies = [ledger("variable_first"), ledger("constraint_first")]
        def responder(payload, body):
            value = replies.pop(0)
            return {"text": canonical(value), "prompt_tokens": 1, "completion_tokens": 1,
                    "total_tokens": 2, "finish_reason": "stop", "reported_model": "offline"}
        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path('.'), plan, offline=True, directory=directory, responder=responder)
            result = run_source_ledger_probe(PROBLEM, initial_record, gateway, "v7dev:LedgerProbe:17:ledger_case", 17, 65536, execute)
        self.assertEqual(set(result["models"]), {"Base", "V6", "DualLedger", "FullV7"})
        self.assertEqual(result["models"]["DualLedger"]["variables"][0]["domain"], "integer")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["usage"]["logical_requests"], 2)

    def test_rejected_dual_view_fails_closed_to_base_and_v6(self):
        initial = {
            "schema": "milp-v1",
            "variables": [{"id": "x000", "meaning": "Number of apple crates", "unit": "crates",
                           "domain": "continuous", "lower": 0, "upper": 10}],
            "constraints": [{"id": "c000", "coefficients": {"x000": 3}, "sense": "ge", "rhs": 12}],
            "objective": {"coefficients": {"x000": 5}, "sense": "min", "unit": "dollars", "offset": 0},
        }
        initial_record = {"input_sha256": __import__("llm4or.benchmark_inputs", fromlist=["payload_sha256"]).payload_sha256(PROBLEM),
                          "final_model": initial}
        plan = {
            "run_directory": "unused", "trajectory_token_caps": [65536],
            "limits": {"max_requests": 6, "max_total_reserved_or_reported_tokens": 1000000,
                       "max_completion_tokens": 8192, "max_input_bytes": 196608,
                       "max_output_bytes": 196608, "token_overhead_reserve": 2048,
                       "request_seconds": 10, "max_run_seconds": 60, "minimum_free_disk_bytes": 0},
            "resilience": {"max_attempts_per_request": 1, "backoff_seconds": [],
                           "circuit_breaker_consecutive_failures": 8, "max_concurrent_requests": 1},
            "matrix": {"inference_cells": 1}, "progress_stage": "v7dev",
        }
        replies = [ledger("variable_first"), ledger("constraint_first")]
        replies[1]["constraints"][0]["rhs"] = 15
        def responder(payload, body):
            value = replies.pop(0)
            return {"text": canonical(value), "prompt_tokens": 1, "completion_tokens": 1,
                    "total_tokens": 2, "finish_reason": "stop", "reported_model": "offline"}
        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path('.'), plan, offline=True, directory=directory, responder=responder)
            result = run_source_ledger_probe(PROBLEM, initial_record, gateway,
                                             "v7dev:LedgerProbe:17:ledger_case", 17, 65536, execute)
        self.assertEqual(result["models"]["DualLedger"], initial)
        self.assertEqual(result["models"]["FullV7"], result["models"]["V6"])
        self.assertEqual(result["status"], "completed_with_fallback")

    def test_helper_transport_failure_preserves_scoreable_fallback(self):
        initial = {
            "schema": "milp-v1",
            "variables": [{"id": "x000", "meaning": "Number of apple crates", "unit": "crates",
                           "domain": "continuous", "lower": 0, "upper": 10}],
            "constraints": [{"id": "c000", "coefficients": {"x000": 3}, "sense": "ge", "rhs": 12}],
            "objective": {"coefficients": {"x000": 5}, "sense": "min", "unit": "dollars", "offset": 0},
        }
        initial_record = {"input_sha256": __import__("llm4or.benchmark_inputs", fromlist=["payload_sha256"]).payload_sha256(PROBLEM),
                          "final_model": initial}
        plan = {
            "run_directory": "unused", "trajectory_token_caps": [65536],
            "limits": {"max_requests": 6, "max_total_reserved_or_reported_tokens": 1000000,
                       "max_completion_tokens": 8192, "max_input_bytes": 196608,
                       "max_output_bytes": 196608, "token_overhead_reserve": 2048,
                       "request_seconds": 10, "max_run_seconds": 60, "minimum_free_disk_bytes": 0},
            "resilience": {"max_attempts_per_request": 1, "backoff_seconds": [],
                           "circuit_breaker_consecutive_failures": 8, "max_concurrent_requests": 1},
            "matrix": {"inference_cells": 1}, "progress_stage": "v7dev",
        }
        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path('.'), plan, offline=True, directory=directory,
                                    responder=lambda *_: {"error": "transport_TimeoutError"})
            result = run_source_ledger_probe(PROBLEM, initial_record, gateway,
                                             "v7dev:LedgerProbe:17:ledger_case", 17, 65536, execute)
        self.assertTrue(result["helper_infrastructure_unavailable"])
        self.assertEqual(result["models"]["DualLedger"], initial)
        self.assertEqual(result["models"]["FullV7"], result["models"]["V6"])
        self.assertEqual(result["status"], "completed_with_fallback")


if __name__ == "__main__":
    unittest.main()
