from dataclasses import replace
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from llm4or.reconstruction_publishers import (
    AdapterError,
    PUBLISHERS,
    _publish_captured,
    _verify_source,
    encode_compact,
    encode_pretty_default,
    encode_pretty_strict,
)
from llm4or import reconstruction_publishers as publisher_module


ROOT = Path(__file__).resolve().parents[1]


class ReconstructionPublisherRegistryTests(unittest.TestCase):
    def test_registry_has_exactly_the_nine_audited_sources_and_hashes(self):
        audit = json.loads(
            (
                ROOT
                / "experiments/reconstruction_publisher_solver_boundary_audit_20261015.json"
            ).read_text()
        )
        expected = {row["path"]: row["sha256"] for row in audit["publishers"]}

        self.assertEqual(len(PUBLISHERS), 9)
        self.assertEqual(
            {spec.source_path: spec.source_sha256 for spec in PUBLISHERS.values()},
            expected,
        )
        for spec in PUBLISHERS.values():
            self.assertEqual(
                hashlib.sha256((ROOT / spec.source_path).read_bytes()).hexdigest(),
                spec.source_sha256,
            )

    def test_source_pin_mismatch_fails_before_adapter_execution(self):
        spec = replace(
            PUBLISHERS["external-cohort-audit"], source_sha256="0" * 64
        )
        with self.assertRaisesRegex(AdapterError, "producer_source_sha256_mismatch"):
            _verify_source(ROOT, spec)

    def test_cli_list_reports_nine_adapters_without_running_one(self):
        completed = subprocess.run(
            [sys.executable, "scripts/publish_reconstructed_artifact.py", "--list"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertFalse(value["implicit_execution"])
        self.assertEqual(len(value["publishers"]), 9)
        self.assertEqual(
            {row["id"] for row in value["publishers"]}, set(PUBLISHERS)
        )

    def test_producer_stdout_is_suppressed_from_single_result_cli_channel(self):
        expected = {"result.json": b"{}\n"}

        def noisy_builder(root, module, spec):
            print('{"historical":"progress"}')
            return expected

        output = io.StringIO()
        with redirect_stdout(output):
            observed = publisher_module._run_builder_quietly(
                noisy_builder, ROOT, object(), PUBLISHERS["external-cohort-audit"]
            )
        self.assertEqual(observed, expected)
        self.assertEqual(output.getvalue(), "")


class ReconstructionPublisherSerializationTests(unittest.TestCase):
    def test_compact_encoder_reproduces_current_frozen_json_bytes(self):
        for relative in (
            "results/bind_fixed_common40.json",
            "results/coe_fixed_common40.json",
            "results/external_fixed_common40_summary.json",
        ):
            with self.subTest(relative=relative):
                path = ROOT / relative
                self.assertEqual(encode_compact(json.loads(path.read_text())), path.read_bytes())

    def test_pretty_encoders_preserve_historical_format_options(self):
        value = {"unicode": "路径", "values": [2, 1], "nested": {"b": 2, "a": 1}}
        strict = (
            json.dumps(
                value,
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        default = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
        self.assertEqual(encode_pretty_strict(value), strict)
        self.assertEqual(encode_pretty_default(value), default)

    def test_private_public_pair_is_one_bundle_with_exact_bytes(self):
        spec = PUBLISHERS["tsp-confirmation-candidates"]
        captured = {
            spec.outputs[0]: b'{"private":true}\n',
            spec.outputs[1]: b'{"public":true}\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = _publish_captured(root, spec, captured)
            self.assertEqual(result.created, tuple(sorted(spec.outputs)))
            for relative, payload in captured.items():
                self.assertEqual((root / relative).read_bytes(), payload)

    def test_json_markdown_pair_is_recoverable_bundle_with_exact_bytes(self):
        spec = PUBLISHERS["external-common40-summary"]
        captured = {
            "results/external_fixed_common40_summary.json": b'{"rows":[]}\n',
            "docs/EXTERNAL_FIXED_COMMON40_RESULTS.md": "# 固定结果\n".encode(),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _publish_captured(root, spec, captured)
            self.assertEqual(
                (root / "results/external_fixed_common40_summary.json").read_bytes(),
                captured["results/external_fixed_common40_summary.json"],
            )
            self.assertEqual(
                (root / "docs/EXTERNAL_FIXED_COMMON40_RESULTS.md").read_bytes(),
                captured["docs/EXTERNAL_FIXED_COMMON40_RESULTS.md"],
            )

    def test_unexpected_or_missing_capture_fails_before_publication(self):
        spec = PUBLISHERS["external-cohort-audit"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(AdapterError, "captured_output_inventory"):
                _publish_captured(root, spec, {"unexpected.json": b"{}\n"})
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
