from pathlib import Path
import tempfile
import unittest

from llm4or.formal_gateway import FormalGateway
from llm4or.schema import canonical
from llm4or.source_indexed_runtime import run_source_indexed_probe
from tests.test_source_indexed_model import PROBLEM, grounded


BASE = {
    "schema": "milp-v1",
    "variables": [{
        "id": "x", "meaning": "Number of crates", "unit": "crates", "domain": "integer",
        "lower": 0, "upper": 100,
    }],
    "constraints": [{"id": "target", "coefficients": {"x": 0.25}, "sense": "ge", "rhs": 12}],
    "objective": {"coefficients": {"x": 5}, "sense": "min", "unit": "dollars", "offset": 0},
}


def plan():
    return {
        "run_directory": "unused", "trajectory_token_caps": [65536],
        "limits": {
            "max_requests": 6, "max_total_reserved_or_reported_tokens": 1000000,
            "max_completion_tokens": 16384, "max_input_bytes": 262144,
            "max_output_bytes": 262144, "token_overhead_reserve": 4096,
            "request_seconds": 10, "max_run_seconds": 60, "minimum_free_disk_bytes": 0,
        },
        "resilience": {
            "max_attempts_per_request": 1, "backoff_seconds": [],
            "circuit_breaker_consecutive_failures": 8, "max_concurrent_requests": 1,
        },
        "matrix": {"inference_cells": 1}, "progress_stage": "v8dev",
    }


def response(value):
    return {
        "text": canonical(value), "prompt_tokens": 1, "completion_tokens": 1,
        "total_tokens": 2, "finish_reason": "stop", "reported_model": "offline",
    }


class SourceIndexedRuntimeTests(unittest.TestCase):
    def test_valid_source_indexed_model_is_adopted(self):
        replies = [response(BASE), response(grounded())]
        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path("."), plan(), offline=True, directory=directory,
                                    responder=lambda *_: replies.pop(0))
            result = run_source_indexed_probe(
                PROBLEM, gateway, "v8dev:IndexedProbe:17:indexed_case", 17, 65536
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["models"]["FullV8"], result["models"]["SourceIndexed"])
        self.assertEqual(result["usage"]["logical_requests"], 2)

    def test_invalid_indexed_output_falls_back_to_base(self):
        bad = grounded(); bad["constraints"][0]["rhs"] = 999
        replies = [response(BASE), response(bad)]
        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path("."), plan(), offline=True, directory=directory,
                                    responder=lambda *_: replies.pop(0))
            result = run_source_indexed_probe(
                PROBLEM, gateway, "v8dev:IndexedProbe:17:indexed_case", 17, 65536
            )
        self.assertEqual(result["status"], "completed_with_fallback")
        self.assertEqual(result["models"]["FullV8"], BASE)
        self.assertIsNone(result["models"]["SourceIndexed"])

    def test_auxiliary_transport_failure_preserves_base(self):
        replies = [response(BASE), {"error": "transport_TimeoutError"}]
        with tempfile.TemporaryDirectory() as directory:
            gateway = FormalGateway(Path("."), plan(), offline=True, directory=directory,
                                    responder=lambda *_: replies.pop(0))
            result = run_source_indexed_probe(
                PROBLEM, gateway, "v8dev:IndexedProbe:17:indexed_case", 17, 65536
            )
        self.assertEqual(result["models"]["FullV8"], BASE)
        self.assertTrue(result["method_infrastructure_unavailable"]["SourceIndexed"])
        self.assertFalse(result["method_infrastructure_unavailable"]["FullV8"])


if __name__ == "__main__":
    unittest.main()
