import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_release_rights_inventory.py"


def load_module():
    spec = importlib.util.spec_from_file_location("release_rights_inventory", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleaseRightsInventoryTests(unittest.TestCase):
    def test_path_classes_are_mutually_exclusive(self):
        module = load_module()
        classes = [
            module.classify("vendor/solver-in-the-loop", "160000"),
            module.classify("data/manifests/source_manifest.json", "100644"),
            module.classify("manuscript/figures/figure1.png", "100644"),
            module.classify("llm4or/schema.py", "100644"),
        ]
        self.assertEqual(
            classes,
            ["external_submodule", "source_metadata", "generated_manuscript_artifact", "first_party_candidate"],
        )

    def test_preflight_is_read_only_and_never_claims_rights(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--preflight-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "preflight_passed")
        self.assertFalse(report["execution"]["file_contents_read"])
        self.assertFalse(report["decision"]["rights_clearance_claimed"])

    def test_inventory_binds_the_committed_source_snapshot(self):
        module = load_module()
        report = module.build_inventory(source_commit="HEAD")
        expected_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        expected_tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(
            report["source"],
            {"commit": expected_commit, "tree": expected_tree, "scope": "git_tree_at_source_commit"},
        )


if __name__ == "__main__":
    unittest.main()
