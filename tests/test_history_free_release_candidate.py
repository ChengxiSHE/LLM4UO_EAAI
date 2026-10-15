import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_history_free_release_candidate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("history_free_release_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HistoryFreeReleaseCandidateTests(unittest.TestCase):
    def test_release_identity_is_fixed_and_has_no_restricted_paths(self):
        module = load_module()
        self.assertEqual(module.RELEASE_REF, "refs/llm4or-release/candidate-20261016")
        self.assertEqual(module.RELEASE_BRANCH, "release-candidate-20261016")
        self.assertEqual(len(module.RESTRICTED_PATHS), 6)
        self.assertNotIn("LICENSE", module.RESTRICTED_PATHS)
        for path in (
            "LICENSE",
            "LICENSE-DATA",
            "NOTICE",
            "CITATION.cff",
            ".zenodo.json",
            "experiments/authorized_release_audit_20261016.json",
            "experiments/data_code_availability_audit_v3_20261016.json",
            "docs/DATA_CODE_AVAILABILITY_AUDIT_V3_20261016.md",
            "experiments/provider_environment_preflight_audit_20261016.json",
            "llm4or/public_antchat_transport.py",
            "scripts/verify_provider_environment.py",
        ):
            self.assertIn(path, module.REQUIRED_PATHS)

    def test_preflight_is_read_only_and_tracks_all_builder_inputs(self):
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
        self.assertFalse(report["execution"]["git_ref_created"])
        self.assertFalse(report["execution"]["public_push"])

    def test_bundle_destination_must_not_exist(self):
        module = load_module()
        self.assertTrue(hasattr(module, "_copy_bundle_exclusive"))


if __name__ == "__main__":
    unittest.main()
