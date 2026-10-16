import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock
import ast


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_provider_environment.py"
REQUIREMENTS = ROOT / "requirements-provider.txt"


def load_module():
    spec = importlib.util.spec_from_file_location("provider_environment", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ProviderEnvironmentTests(unittest.TestCase):
    def test_public_transport_surface_is_tracked_and_private_envelope_free(self):
        source = ROOT / "llm4or" / "public_antchat_transport.py"
        completed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", str(source.relative_to(ROOT))],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertNotIn("llm4or.antchat_object_pilot_contract", imports)
        self.assertNotIn("llm4or.antchat_object_pilot_transport_v2", imports)
        text = source.read_text(encoding="utf-8").lower()
        for forbidden in ("messages", "prompt", "response_body", "api_key"):
            self.assertNotIn(forbidden, text)

    def test_provider_dependency_is_exactly_the_bound_ca_package(self):
        text = REQUIREMENTS.read_text()
        self.assertIn("certifi==2026.7.22", text)
        self.assertIn(
            "sha256:62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775",
            text,
        )

    def test_preflight_never_touches_profile_or_credential(self):
        module = load_module()
        with mock.patch.object(
            module.formal_provider,
            "check_profile_metadata",
            side_effect=AssertionError("profile metadata must not be read"),
        ), mock.patch.object(
            module.formal_provider,
            "load_credential",
            side_effect=AssertionError("credential must not be read"),
        ):
            report = module.verify_environment()
        self.assertEqual(report["status"], "passed_provider_transport_preflight")
        self.assertFalse(report["execution"]["profile_metadata_read"])
        self.assertFalse(report["execution"]["credentials_read"])
        self.assertEqual(report["execution"]["api_calls"], 0)

    def test_preflight_fails_closed_on_ca_drift(self):
        module = load_module()
        report = module.verify_environment(expected_ca_sha256="0" * 64)
        self.assertEqual(report["status"], "provider_transport_preflight_failed")
        self.assertFalse(report["checks"]["ca_sha256_matches"])

    def test_cli_check_is_json_and_credential_free(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "passed_provider_transport_preflight")
        self.assertEqual(report["model"], "DeepSeek-V4-Flash")
        self.assertEqual(report["base_url"], "https://antchat.alipay.com/v1")
        self.assertEqual(report["max_concurrency"], 5)
        self.assertFalse(report["execution"]["credentials_read"])


if __name__ == "__main__":
    unittest.main()
