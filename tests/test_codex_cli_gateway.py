import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from llm4or.benchmark_inputs import payload_sha256
from llm4or.codex_cli_gateway import CodexCliGateway, LocalRequestFailure, run_codex_cli
from llm4or.schema import canonical
from llm4or.source_indexed_model import make_source_indexed_payload
from tests.test_source_indexed_model import PROBLEM, grounded


def plan(directory):
    return {
        "authorization_schema": "codex-cli-development-authorization-v1",
        "run_directory": str(directory),
        "codex_cli": "/Applications/ChatGPT.app/Contents/Resources/codex",
        "model": "gpt-6-luna", "reasoning_effort": "high",
        "replicates": [17], "token_cap": 65536,
        "trajectory_token_caps": [65536],
        "selection": {"records": [{"problem_id": PROBLEM["id"]}]},
        "public_inputs": {PROBLEM["id"]: payload_sha256(PROBLEM)},
        "limits": {
            "max_requests": 6, "max_total_reserved_or_reported_tokens": 1000000,
            "max_completion_tokens": 16384, "max_input_bytes": 262144,
            "max_output_bytes": 262144, "token_overhead_reserve": 4096,
            "request_seconds": 10, "max_run_seconds": 60, "minimum_free_disk_bytes": 0,
        },
        "resilience": {
            "max_attempts_per_request": 3, "backoff_seconds": [0, 0],
            "circuit_breaker_consecutive_failures": 8, "max_concurrent_requests": 1,
        },
        "frozen_files": {},
    }


def output_path(command):
    return Path(command[command.index("--output-last-message") + 1])


def wrapped(value):
    return canonical({"payload": canonical(value)})


class CodexCliGatewayTests(unittest.TestCase):
    def test_official_text_wrapper_hides_public_accounting_payload(self):
        prompts = []
        def runner(command, prompt, timeout):
            prompts.append(prompt)
            output_path(command).write_text(wrapped({"text": "answer"}))
            return {"stdout": ""}
        with tempfile.TemporaryDirectory() as root:
            spec = plan("run")
            spec["transport"] = {"prompt_envelope": "official_text_wrapper"}
            gateway = CodexCliGateway(root, spec, "unused.json", runner=runner, test_mode=True)
            scope = "v8dev:IndexedProbe:17:indexed_case"
            gateway.register(scope, 2, 65536)
            schema = {"type": "object", "properties": {"text": {"type": "string"}},
                      "required": ["text"], "additionalProperties": False}
            payload = {"version": "test", "instruction": "OFFICIAL PROMPT", "problem": PROBLEM,
                       "context": {"hidden": "metadata"}, "output_contract": {"text": "answer"},
                       "response_schema": schema}
            response = gateway.request(scope, payload, "prefix", 17, 0)
        self.assertEqual(json.loads(response["text"]), {"text": "answer"})
        self.assertTrue(prompts[0].startswith("OFFICIAL PROMPT\n\nTransport only:"))
        self.assertNotIn(PROBLEM["text"], prompts[0])
        self.assertNotIn("hidden", prompts[0])

    def test_records_usage_and_reuses_fingerprint(self):
        calls = []
        def runner(command, prompt, timeout):
            calls.append((command, prompt, timeout))
            output_path(command).write_text(wrapped(grounded()))
            return {"stdout": json.dumps({
                "type": "turn.completed",
                "usage": {"input_tokens": 100, "cached_input_tokens": 0, "output_tokens": 50},
            })}
        with tempfile.TemporaryDirectory() as root:
            gateway = CodexCliGateway(root, plan("run"), "unused.json", runner=runner, test_mode=True)
            scope = "v8dev:IndexedProbe:17:indexed_case"
            gateway.register(scope, 2, 65536)
            payload = make_source_indexed_payload(PROBLEM)
            first = gateway.request(scope, payload, "prefix", 17, 0)
            second = gateway.request(scope, payload, "prefix", 17, 0)
            self.assertEqual(first, second)
            self.assertEqual(len(calls), 1)
            self.assertEqual(gateway.summary()["physical_attempts"], 1)
            self.assertEqual(gateway.summary()["physical_reserved_or_reported_tokens"], 150)
            self.assertEqual(gateway.scope_usage(scope), {"logical_requests": 1, "logical_tokens": 150})

    def test_transient_failure_retries_and_is_charged(self):
        attempts = []
        def runner(command, prompt, timeout):
            attempts.append(1)
            if len(attempts) == 1:
                return {"error": "transport_codex_cli_timeout"}
            output_path(command).write_text(wrapped(grounded()))
            return {"stdout": json.dumps({
                "type": "turn.completed", "usage": {"input_tokens": 2, "output_tokens": 3},
            })}
        with tempfile.TemporaryDirectory() as root:
            gateway = CodexCliGateway(root, plan("run"), "unused.json", runner=runner, test_mode=True)
            scope = "v8dev:IndexedProbe:17:indexed_case"
            gateway.register(scope, 2, 65536)
            gateway.request(scope, make_source_indexed_payload(PROBLEM), "prefix", 17, 0)
            summary = gateway.summary()
            self.assertEqual(summary["physical_attempts"], 2)
            self.assertEqual(summary["retry_attempts"], 1)
            self.assertGreater(summary["physical_reserved_or_reported_tokens"], 5)

    def test_predeclared_local_format_failure_uses_bounded_attempts(self):
        attempts = []
        def runner(*_):
            attempts.append(1)
            return {"error": "invalid_json_response"}
        with tempfile.TemporaryDirectory() as root:
            spec = plan("run")
            spec["resilience"]["retryable_local_errors"] = ["invalid_json_response"]
            spec["resilience"]["max_attempts_per_request"] = 2
            gateway = CodexCliGateway(root, spec, "unused.json", runner=runner, test_mode=True)
            scope = "v8dev:IndexedProbe:17:indexed_case"
            gateway.register(scope, 2, 65536)
            with self.assertRaisesRegex(LocalRequestFailure, "method_failure:invalid_json_response"):
                gateway.request(scope, make_source_indexed_payload(PROBLEM), "prefix", 17, 0)
            self.assertEqual(len(attempts), 2)
            self.assertEqual(gateway.summary()["retry_attempts"], 1)

    def test_command_disables_tools_and_uses_ephemeral_isolated_workspace(self):
        with tempfile.TemporaryDirectory() as root:
            gateway = CodexCliGateway(root, plan("run"), "unused.json", runner=lambda *_: {}, test_mode=True)
            command = gateway._command(Path(root)/"schema.json", Path(root)/"out.json")
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertEqual(command.count("--disable"), 7)
        self.assertIn("read-only", command)
        self.assertIn('approval_policy="never"', command)
        self.assertIn("--strict-config", command)
        self.assertNotIn("--ask-for-approval", command)

    def test_cli_argument_error_is_local_and_redacted(self):
        with tempfile.TemporaryDirectory() as root:
            script = Path(root) / "bad-cli"
            script.write_text("#!/bin/sh\necho secret-detail >&2\nexit 2\n")
            script.chmod(0o700)
            result = run_codex_cli([str(script)], "ignored", 5)
        self.assertEqual(result, {"error": "codex_cli_argument_error"})

    def test_runtime_diagnostic_redacts_paths_and_token_like_strings(self):
        with tempfile.TemporaryDirectory() as root:
            script = Path(root) / "bad-runtime"
            script.write_text(
                "#!/bin/sh\necho 'failure at /Users/person/private/file "
                "abcdefghijklmnopqrstuvwxyz1234567890' >&2\nexit 1\n"
            )
            script.chmod(0o700)
            result = run_codex_cli([str(script)], "ignored", 5)
        self.assertEqual(result["error"], "codex_cli_runtime_error")
        self.assertNotIn("/Users/person", result["diagnostic"])
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890", result["diagnostic"])

    def test_imports_only_hash_bound_complete_cache_entries(self):
        with tempfile.TemporaryDirectory() as root:
            source_plan = plan("source")
            def source_runner(command, *_):
                output_path(command).write_text(wrapped(grounded()))
                return {"stdout": json.dumps({
                    "type": "turn.completed", "usage": {"input_tokens": 8, "output_tokens": 5},
                })}
            source = CodexCliGateway(
                root, source_plan, "unused.json", runner=source_runner,
                test_mode=True,
            )
            scope = "v8dev:IndexedProbe:17:indexed_case"
            source.register(scope, 2, 65536)
            payload = make_source_indexed_payload(PROBLEM)
            source.request(scope, payload, "prefix", 17, 0)
            with sqlite3.connect(source.db) as database:
                key, charged, response_hash = database.execute(
                    "SELECT key,charged,response_hash FROM requests WHERE status='complete'"
                ).fetchone()
            source_bytes = source.db.read_bytes()
            target_plan = plan("target")
            target_plan["cache_import"] = {
                "source_database": "source/requests.sqlite3",
                "source_db_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "source_plan_sha256": source.plan_hash,
                "request_count": 1, "charged": charged,
                "entries": [{"key": key, "charged": charged, "response_hash": response_hash}],
            }
            target = CodexCliGateway(
                root, target_plan, "unused.json",
                runner=lambda *_: self.fail("imported response must not dispatch"), test_mode=True,
            )
            target.register(scope, 2, 65536)
            target.request(scope, payload, "prefix", 17, 0)
            summary = target.summary()
            self.assertEqual(summary["physical_attempts"], 0)
            self.assertEqual(summary["imported_requests"], 1)
            self.assertEqual(summary["imported_charged_tokens"], charged)


if __name__ == "__main__":
    unittest.main()
