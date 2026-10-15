from pathlib import Path
import tempfile
import unittest

from llm4or.formal_gateway import FormalGateway
from llm4or.schema import canonical
from llm4or.source_ledger import compile_ledger
from llm4or.text2opt_runtime import run_text2opt_probe
from tests.test_source_ledger import PROBLEM, ledger


class Text2OptRuntimeTests(unittest.TestCase):
    def test_three_call_probe_exposes_frozen_ablation_models(self):
        base, _ = compile_ledger(PROBLEM, ledger("variable_first"), "variable_first")
        base["variables"][0]["domain"] = "continuous"
        plan = {
            "kind": "offline_text2opt_test",
            "run_directory": "unused",
            "trajectory_token_caps": [131072],
            "limits": {
                "max_requests": 9, "max_total_reserved_or_reported_tokens": 1000000,
                "max_completion_tokens": 16384, "max_input_bytes": 262144,
                "max_output_bytes": 262144, "token_overhead_reserve": 4096,
                "request_seconds": 10, "max_run_seconds": 60, "minimum_free_disk_bytes": 0,
            },
            "resilience": {
                "max_attempts_per_request": 1, "backoff_seconds": [],
                "circuit_breaker_consecutive_failures": 8, "max_concurrent_requests": 1,
            },
            "matrix": {"inference_cells": 1}, "progress_stage": "text2opt",
        }

        def responder(payload, body):
            view = payload["context"].get("view")
            value = ledger(view) if view else base
            return {
                "text": canonical(value), "prompt_tokens": 1, "completion_tokens": 1,
                "total_tokens": 2, "finish_reason": "stop", "reported_model": "offline",
            }

        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path("."), plan, offline=True, directory=directory, responder=responder)
            result = run_text2opt_probe(
                PROBLEM, gateway, "text2opt:Probe:17:ledger_case", 17, 131072
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["usage"]["logical_requests"], 3)
        self.assertEqual(set(result["models"]), {"Base", "V6", "DualLedger", "FullV7"})
        self.assertEqual(result["models"]["Base"]["variables"][0]["domain"], "continuous")
        self.assertEqual(result["models"]["FullV7"]["variables"][0]["domain"], "integer")


if __name__ == "__main__":
    unittest.main()
