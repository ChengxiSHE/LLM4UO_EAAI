import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "audit_panel_alignment.py"


def load_module():
    spec = importlib.util.spec_from_file_location("repo_figure_alignment", MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def aligned_layout():
    return {
        "schema_version": 1,
        "backend": "test",
        "figure": {"width_pt": 300.0, "height_pt": 200.0},
        "panels": [
            {
                "id": "a",
                "bbox_pt": [20, 110, 130, 180],
                "grid_id": "g",
                "row_start": 0,
                "row_stop": 1,
                "col_start": 0,
                "col_stop": 1,
                "panel_label_anchor_pt": [1, 185],
            },
            {
                "id": "b",
                "bbox_pt": [170, 110, 280, 180],
                "grid_id": "g",
                "row_start": 0,
                "row_stop": 1,
                "col_start": 1,
                "col_stop": 2,
                "panel_label_anchor_pt": [151, 185],
            },
            {
                "id": "c",
                "bbox_pt": [20, 20, 130, 90],
                "grid_id": "g",
                "row_start": 1,
                "row_stop": 2,
                "col_start": 0,
                "col_stop": 1,
                "panel_label_anchor_pt": [1, 95],
            },
            {
                "id": "d",
                "bbox_pt": [170, 20, 280, 90],
                "grid_id": "g",
                "row_start": 1,
                "row_stop": 2,
                "col_start": 1,
                "col_stop": 2,
                "panel_label_anchor_pt": [151, 95],
            },
        ],
    }


class RepoFigureAlignmentTests(unittest.TestCase):
    def test_dependency_free_self_test_runs_from_repository(self):
        completed = subprocess.run(
            [sys.executable, str(MODULE), "--self-test"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS", completed.stdout)

    def test_aligned_layout_passes_and_shifted_layout_fails(self):
        module = load_module()
        report = module.audit_layout_manifest(aligned_layout(), require_panel_labels=True)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["summary"]["comparisons"], 4)

        shifted = json.loads(json.dumps(aligned_layout()))
        shifted["panels"][1]["bbox_pt"][1] -= 4
        shifted_report = module.audit_layout_manifest(shifted, require_panel_labels=True)
        self.assertEqual(shifted_report["verdict"], "FIX BEFORE DELIVERY")
        self.assertTrue(
            any(item["kind"] == "row-axes-misalignment" for item in shifted_report["findings"])
        )

    def test_strict_gate_blocks_missing_panel_label(self):
        module = load_module()
        layout = aligned_layout()
        del layout["panels"][1]["panel_label_anchor_pt"]
        report = module.audit_layout_manifest(layout, require_panel_labels=True)
        self.assertEqual(report["verdict"], "REVIEW REQUIRED")
        self.assertEqual(module.exit_code(report, strict=False), 0)
        self.assertEqual(module.exit_code(report, strict=True), 1)

    def test_reports_and_overlay_are_written_atomically(self):
        module = load_module()
        report = module.audit_layout_manifest(aligned_layout(), require_panel_labels=True)
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            json_path = directory / "alignment.json"
            svg_path = directory / "alignment.svg"
            module.write_json_report(report, json_path)
            module.write_overlay_svg(report, svg_path)
            self.assertEqual(json.loads(json_path.read_text())["verdict"], "PASS")
            self.assertIn("<svg", svg_path.read_text())


if __name__ == "__main__":
    unittest.main()
