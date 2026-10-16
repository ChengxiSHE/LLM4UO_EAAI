import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconstruct_figures.py"
REQUIREMENTS = ROOT / "requirements-figures.txt"
SOURCE_DATA = (
    "manuscript/source_data/figure2_endpoint_summary.csv",
    "manuscript/source_data/figure2_group_summary.csv",
    "manuscript/source_data/figure2_router_identity.csv",
    "manuscript/source_data/figure2_tsp_by_size.csv",
)


def load_module():
    spec = importlib.util.spec_from_file_location("figure_reconstruction", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FigureReconstructionTests(unittest.TestCase):
    def test_figure_environment_is_fully_version_pinned(self):
        expected = {
            "PyMuPDF==1.26.5",
            "contourpy==1.3.2",
            "cycler==0.12.1",
            "fonttools==4.65.0",
            "kiwisolver==1.5.1",
            "matplotlib==3.10.7",
            "numpy==2.2.6",
            "packaging==26.3",
            "pillow==12.3.0",
            "pyparsing==3.3.3",
            "python-dateutil==2.9.0.post0",
            "six==1.17.0",
        }
        actual = {
            line.strip()
            for line in REQUIREMENTS.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertEqual(actual, expected)

    def test_all_figure_source_data_are_tracked(self):
        completed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", *SOURCE_DATA],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_timestamp_normalization_does_not_mask_content_changes(self):
        module = load_module()
        svg_a = (
            b'<dc:date>2026-10-15T16:00:00</dc:date>'
            b'<path id="m0123456789"/><use xlink:href="#m0123456789"/><text>A</text>'
        )
        svg_b = (
            b'<dc:date>2026-10-16T17:00:00</dc:date>'
            b'<path id="mabcdef0123"/><use xlink:href="#mabcdef0123"/><text>A</text>'
        )
        svg_c = (
            b'<dc:date>2026-10-16T17:00:00</dc:date>'
            b'<path id="mabcdef0123"/><use xlink:href="#mabcdef0123"/><text>B</text>'
        )
        self.assertEqual(module.normalize_svg(svg_a), module.normalize_svg(svg_b))
        self.assertNotEqual(module.normalize_svg(svg_a), module.normalize_svg(svg_c))

        pdf_a = b"/CreationDate (D:20261015160000+08'00') /Payload (A)"
        pdf_b = b"/CreationDate (D:20261016170000+08'00') /Payload (A)"
        pdf_c = b"/CreationDate (D:20261016170000+08'00') /Payload (B)"
        self.assertEqual(module.normalize_pdf(pdf_a), module.normalize_pdf(pdf_b))
        self.assertNotEqual(module.normalize_pdf(pdf_a), module.normalize_pdf(pdf_c))

    def test_preflight_is_dependency_free_and_body_free(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--preflight-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "preflight_passed")
        self.assertTrue(report["all_required_paths_tracked"])
        self.assertFalse(report["execution"]["credentials_read"])
        self.assertFalse(report["execution"]["request_or_response_bodies_read"])

    def test_normalization_policy_names_every_ignored_field(self):
        module = load_module()
        self.assertEqual(
            module.normalization_policy(),
            {
                "pdf": ["CreationDate"],
                "svg": ["dc:date", "Matplotlib internal m/p identifier names"],
                "png": [],
                "tiff": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
