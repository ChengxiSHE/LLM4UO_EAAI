import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_offline_analysis_environment.py"


def load_module():
    spec = importlib.util.spec_from_file_location("offline_analysis_environment", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class OfflineAnalysisEnvironmentTests(unittest.TestCase):
    def test_expected_environment_is_exact(self):
        module = load_module()
        self.assertEqual(module.EXPECTED_PYTHON, "3.11.16")
        self.assertEqual(
            module.EXPECTED_PACKAGES,
            {
                "numpy": "2.4.4",
                "scipy": "1.17.1",
                "jsonschema": "4.26.0",
                "scikit-learn": "1.9.0",
            },
        )

    def test_version_check_fails_closed_on_interpreter_or_package_drift(self):
        module = load_module()
        self.assertEqual(module.version_mismatches("3.11.16", module.EXPECTED_PACKAGES), {})
        self.assertIn("python", module.version_mismatches("3.11.15", module.EXPECTED_PACKAGES))
        changed = dict(module.EXPECTED_PACKAGES)
        changed["scipy"] = "0"
        self.assertIn("scipy", module.version_mismatches("3.11.16", changed))

    def test_preflight_is_dependency_free_and_tracks_every_input(self):
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


if __name__ == "__main__":
    unittest.main()
