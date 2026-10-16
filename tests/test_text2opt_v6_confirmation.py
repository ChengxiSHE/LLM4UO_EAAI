from pathlib import Path
import tempfile
import unittest

from llm4or.formal_gateway import FormalGateway
from llm4or.schema import canonical
from llm4or.source_ledger import compile_ledger
from llm4or.text2opt_v6_evaluation import evaluate_v6_confirmation
from llm4or.text2opt_v6_runtime import run_text2opt_v6_probe
from tests.test_source_ledger import PROBLEM, ledger


def plan():
    return {
        "kind": "offline_text2opt_v6_test", "run_directory": "unused",
        "trajectory_token_caps": [131072],
        "limits": {
            "max_requests": 3, "max_total_reserved_or_reported_tokens": 1000000,
            "max_completion_tokens": 16384, "max_input_bytes": 262144,
            "max_output_bytes": 262144, "token_overhead_reserve": 4096,
            "request_seconds": 10, "max_run_seconds": 60, "minimum_free_disk_bytes": 0,
        },
        "resilience": {
            "max_attempts_per_request": 1, "backoff_seconds": [],
            "circuit_breaker_consecutive_failures": 8, "max_concurrent_requests": 1,
        },
        "matrix": {"inference_cells": 1}, "progress_stage": "text2optv6",
    }


class Text2OptV6RuntimeTests(unittest.TestCase):
    def test_one_call_probe_builds_base_and_v6(self):
        base, _ = compile_ledger(PROBLEM, ledger("variable_first"), "variable_first")
        base["variables"][0]["domain"] = "continuous"
        response = {
            "text": canonical(base), "prompt_tokens": 1, "completion_tokens": 1,
            "total_tokens": 2, "finish_reason": "stop", "reported_model": "offline",
        }
        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path("."), plan(), offline=True, directory=directory,
                                    responder=lambda *_: response)
            result = run_text2opt_v6_probe(
                PROBLEM, gateway, "text2optv6:Probe:17:ledger_case", 17, 131072
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["usage"]["logical_requests"], 1)
        self.assertEqual(set(result["models"]), {"Base", "V6"})
        self.assertIsNotNone(result["models"]["Base"])
        self.assertIsNotNone(result["models"]["V6"])
        self.assertIn(result["reports"]["v6"]["status"], {"accepted", "already_compliant", "interface_insufficient"})

    def test_transport_exhaustion_marks_both_methods_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path("."), plan(), offline=True, directory=directory,
                                    responder=lambda *_: {"error": "transport_TimeoutError"})
            result = run_text2opt_v6_probe(
                PROBLEM, gateway, "text2optv6:Probe:17:ledger_case", 17, 131072
            )
        self.assertEqual(result["status"], "infrastructure_unavailable")
        self.assertEqual(result["method_infrastructure_unavailable"], {"Base": True, "V6": True})


class Text2OptV6EvaluationTests(unittest.TestCase):
    def test_pre_registered_gate_accepts_distributed_nonregressing_gain(self):
        categories = ["ra", "transport", "disaster", "jssp", "vrptw", "rcpsp", "facility"]
        entries = []
        references = {}
        for index in range(431):
            problem_id = f"p{index:03d}"
            base_correct = index >= 5
            v6_correct = True
            solved = lambda correct: {"status": "optimal", "objective": 10.0 if correct else 11.0}
            entries.append({
                "problem_id": problem_id,
                "category": categories[index % 7],
                "probe": {
                    "problem_id": problem_id, "status": "completed",
                    "solve": {"Base": solved(base_correct), "V6": solved(v6_correct)},
                    "method_infrastructure_unavailable": {"Base": False, "V6": False},
                    "reports": {"v6": {"status": "accepted"}},
                },
            })
            references[problem_id] = {"solver_status": 2, "theoretical_optimum": 10.0}
        public, private = evaluate_v6_confirmation(entries, references)
        self.assertTrue(public["confirmation_gate"]["confirmed"])
        self.assertEqual(public["comparison"]["corrections"], 5)
        self.assertEqual(public["comparison"]["regressions"], 0)
        self.assertNotIn("problem_id", str(public))
        self.assertEqual(len(private), 431)


if __name__ == "__main__":
    unittest.main()
