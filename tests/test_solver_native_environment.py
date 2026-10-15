import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_solver_native_environment.py"


def load_module():
    spec = importlib.util.spec_from_file_location("solver_native_environment", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SolverNativeEnvironmentTests(unittest.TestCase):
    def test_contract_constants_are_frozen(self):
        module = load_module()
        self.assertEqual(module.EXPECTED_GUROBI_VERSION, "13.0.1")
        self.assertEqual(module.EXPECTED_SUBMODULE_COMMIT, "c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010")
        self.assertEqual(module.EXPECTED_THREADS, 1)
        self.assertEqual(module.EXPECTED_SOLVER_TIMEOUT_SECONDS, 15)
        self.assertEqual(module.EXPECTED_WALL_TIMEOUT_SECONDS, 25)
        self.assertEqual(module.EXPECTED_MAX_MPS_BYTES, 1_000_000)

    def test_version_parser_fails_closed(self):
        module = load_module()
        line = "Gurobi Optimizer version 13.0.1 build v13.0.1rc0 (mac64[arm] - Darwin)"
        self.assertEqual(module.parse_gurobi_version(line), "13.0.1")
        with self.assertRaisesRegex(ValueError, "unrecognized_gurobi_version"):
            module.parse_gurobi_version("Gurobi unknown")

    def test_preflight_tracks_inputs_and_does_not_inspect_license(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--preflight-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "preflight_passed_external_license_required")
        self.assertTrue(report["all_required_paths_tracked"])
        self.assertTrue(report["submodule"]["commit_matches"])
        self.assertFalse(report["execution"]["license_file_contents_read_by_verifier"])
        self.assertFalse(report["execution"]["benchmark_dataset_contents_read"])


if __name__ == "__main__":
    unittest.main()
