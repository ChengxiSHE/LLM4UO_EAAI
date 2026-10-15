import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from llm4or.formal_gateway import external_transport_worker, wire_body
from llm4or.schema import canonical


class Completed:
    returncode = 0
    stderr = b"ignored"
    stdout = canonical({
        "text": "{}", "prompt_tokens": 1, "completion_tokens": 1,
        "total_tokens": 2, "finish_reason": "stop",
        "reported_model": "DeepSeek-V4-Flash",
    }).encode()


class ExternalTransportTests(unittest.TestCase):
    def test_indexed_runtime_uses_stage_specific_completion_caps(self):
        def payload(stage):
            return {
                "version": "optitrust-style-indexed-sidecar-v3",
                "instruction": "bounded", "context": {"stage": stage},
            }
        self.assertEqual(wire_body(payload("decomposition"), 3072)["max_tokens"], 768)
        self.assertEqual(wire_body(payload("formulation_outline"), 3072)["max_tokens"], 1280)
        self.assertEqual(wire_body(payload("review_Pyomo"), 3072)["max_tokens"], 1536)
        self.assertEqual(wire_body(payload("canonical_indexed_ir"), 3072)["max_tokens"], 3072)

    def test_invokes_exact_pinned_files_with_small_environment_and_body_on_stdin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            python = root / "python"; python.write_bytes(b"pinned-python")
            worker = root / "scripts" / "worker.py"; worker.parent.mkdir(); worker.write_text("# pinned")
            plan = {
                "transport": {
                    "kind": "openai_httpx_single_attempt_v1", "python": str(python),
                    "python_sha256": hashlib.sha256(python.read_bytes()).hexdigest(),
                    "worker": "scripts/worker.py",
                },
                "frozen_files": {"scripts/worker.py": hashlib.sha256(worker.read_bytes()).hexdigest()},
            }
            calls = []
            def runner(*args, **kwargs): calls.append((args, kwargs)); return Completed()
            body = {"model": "DeepSeek-V4-Flash"}
            result = external_transport_worker(root, plan, body, 90, 32768, runner=runner)
            self.assertEqual(result["total_tokens"], 2)
            command = calls[0][0][0]
            options = calls[0][1]
            self.assertEqual(command, [str(python), str(worker.resolve()), "90", "32768"])
            self.assertEqual(options["input"], canonical(body).encode())
            self.assertEqual(set(options["env"]), {"HOME", "PATH"})
            self.assertFalse(any("proxy" in key.lower() for key in options["env"]))

    def test_timeout_is_bounded_metadata_only_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            python = root / "python"; python.write_bytes(b"pinned-python")
            worker = root / "worker.py"; worker.write_text("# pinned")
            plan = {
                "transport": {
                    "kind": "openai_httpx_single_attempt_v1", "python": str(python),
                    "python_sha256": hashlib.sha256(python.read_bytes()).hexdigest(),
                    "worker": "worker.py",
                },
                "frozen_files": {"worker.py": hashlib.sha256(worker.read_bytes()).hexdigest()},
            }
            def runner(*args, **kwargs):
                raise subprocess.TimeoutExpired(cmd="worker", timeout=95)
            result = external_transport_worker(root, plan, {}, 90, 32768, runner=runner)
            self.assertEqual(result, {"error": "transport_SubprocessTimeout", "usage_source": "unavailable"})


if __name__ == "__main__":
    unittest.main()
