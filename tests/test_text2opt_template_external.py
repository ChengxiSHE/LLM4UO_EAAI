import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Text2OptTemplateExternalTests(unittest.TestCase):
    def test_six_frozen_families_and_public_only_projection(self):
        manifest_path = ROOT / "data/manifests/text2opt_template_confirmation_v1.json"
        snapshot_path = ROOT / "data/prepared_benchmarks/text2opt_template_confirmation_v1.json"
        if not manifest_path.exists() or not snapshot_path.exists():
            self.skipTest("external template snapshot has not been prepared")
        from scripts.prepare_text2opt_template_external import sha_file

        manifest = json.loads(manifest_path.read_text())
        snapshot = json.loads(snapshot_path.read_text())
        self.assertEqual(manifest["selection"]["records"], 183)
        self.assertEqual(len(manifest["selection"]["categories"]), 6)
        self.assertEqual(manifest["bindings"]["prepared_public_snapshot_sha256"], sha_file(snapshot_path))
        self.assertEqual(snapshot["method_development_records"], 0)
        self.assertEqual(len(snapshot["confirmation"]), 183)
        for row in snapshot["confirmation"]:
            self.assertEqual(set(row["public"]), {"id", "profile", "text", "parameters", "instances"})
            self.assertNotIn("gold_solution", row)
            self.assertNotIn("gurobi_result", row)


if __name__ == "__main__":
    unittest.main()
