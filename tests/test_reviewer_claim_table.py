import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from llm4or.reviewer_claim_table import build_claim_table, write_claim_table


ROOT = Path(__file__).resolve().parents[1]


class ReviewerClaimTableTests(unittest.TestCase):
    def test_builds_headline_table_from_public_aggregate_sources(self):
        table = build_claim_table(ROOT)

        self.assertEqual(table["schema"], "llm4or-reviewer-claim-table-v1")
        self.assertEqual(
            set(table["source_sha256"]),
            {
                "results/tsp_constraint_confirmation_root_closure_20261014.json",
                "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json",
                "experiments/fresh_common38_common_protocol_synthesis_20261015.json",
                "results/mixed_skill_confirmation_public_audit_v3_20261015.json",
            },
        )
        self.assertEqual(table["tsp"]["control_correct"], 54)
        self.assertEqual(table["tsp"]["method_correct"], 100)
        self.assertEqual(table["tsp"]["corrections"], 46)
        self.assertEqual(table["tsp"]["regressions"], 0)

        self.assertEqual(table["or_debug"]["primary_endpoint"], "released_labels")
        self.assertEqual(table["or_debug"]["released_labels"]["method_correct"], 2236)
        self.assertEqual(table["or_debug"]["released_labels"]["corrections"], 1408)
        self.assertEqual(table["or_debug"]["source_corrected_sensitivity"]["method_correct"], 2752)
        self.assertEqual(table["or_debug"]["source_corrected_sensitivity"]["corrections"], 1924)

        self.assertEqual(
            table["fresh_common38"]["correct_by_method"],
            {
                "Proof-carrying compilation": 30,
                "Base": 0,
                "BIND round 1": 13,
                "BIND final": 13,
                "CoE-safe": 4,
            },
        )
        self.assertEqual(table["mixed_router"]["exact_matches"], 2985)
        self.assertEqual(table["mixed_router"]["output_mismatches"], 0)

        serialized = json.dumps(table, sort_keys=True)
        for forbidden in ("problem_text", "request_body", "response_body", "api_key"):
            self.assertNotIn(forbidden, serialized.lower())

    def test_write_is_deterministic_and_check_detects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "claim-table.json"
            first = write_claim_table(ROOT, output, check=False)
            second = write_claim_table(ROOT, output, check=True)
            self.assertEqual(first, second)

            output.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "claim_table_drift"):
                write_claim_table(ROOT, output, check=True)

    def test_cli_runs_from_a_clean_python_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "claim-table.json"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/build_reviewer_claim_table.py"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(output.read_text())["tsp"]["method_correct"], 100)


if __name__ == "__main__":
    unittest.main()
