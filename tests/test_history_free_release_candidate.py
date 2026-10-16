import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
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
        self.assertEqual(module.RELEASE_VERSION, "v1.1.1")
        self.assertEqual(
            module.RELEASE_REF,
            "refs/llm4or-release/candidate-v1.1.1-20261016",
        )
        self.assertEqual(module.RELEASE_BRANCH, "release-candidate-v1.1.1-20261016")
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
            "experiments/optitrust_indexed_closure_20261016.json",
            "docs/OPTITRUST_INDEXED_CLOSURE_20261016.md",
            "experiments/paper_evidence_manifest_20261015.json",
            "experiments/goal_completion_audit_20261015.json",
            "docs/TOP_CONFERENCE_METHOD_ROADMAP_V2_20261016.md",
            "experiments/atomic_publisher_concurrent_cleanup_fix_audit_20261016.json",
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

    def test_surface_scan_rejects_private_paths_and_credential_shapes(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "safe.txt").write_text("aggregate evidence only")
            (root / "credential.txt").write_text("API_KEY='" + "X" * 24 + "'")
            (root / "private").mkdir()
            (root / "private" / "record.txt").write_text("not public")
            report = module._surface_scan(
                root,
                {"safe.txt", "credential.txt", "private/record.txt"},
            )
            self.assertFalse(report["passed"])
            self.assertEqual(report["path_violations"], ["private/record.txt"])
            self.assertEqual(report["credential_shaped_hits"]["assigned_secret"], ["credential.txt"])

    def test_release_date_is_explicit_in_commit_environment(self):
        module = load_module()
        environment = module._commit_environment(Path("/tmp/empty-home"), "2026-10-17")
        self.assertEqual(environment["GIT_AUTHOR_DATE"], "2026-10-17T00:00:00+08:00")
        self.assertEqual(environment["GIT_COMMITTER_DATE"], "2026-10-17T00:00:00+08:00")


if __name__ == "__main__":
    unittest.main()
