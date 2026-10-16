import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Text2OptExternalTests(unittest.TestCase):
    def test_manifest_and_public_snapshot_are_bound(self):
        manifest_path = ROOT / "data/manifests/text2opt_resource_allocation_v1.json"
        snapshot_path = ROOT / "data/prepared_benchmarks/text2opt_resource_allocation_v1.json"
        if not manifest_path.exists() or not snapshot_path.exists():
            self.skipTest("external snapshot has not been prepared")
        from scripts.prepare_text2opt_external import sha_file

        manifest = json.loads(manifest_path.read_text())
        snapshot = json.loads(snapshot_path.read_text())
        self.assertEqual(manifest["counts"], {"development": 764, "confirmation": 248})
        self.assertEqual(manifest["bindings"]["prepared_public_snapshot_sha256"], sha_file(snapshot_path))
        self.assertEqual(len(snapshot["development"]), 764)
        self.assertEqual(len(snapshot["confirmation"]), 248)
        for row in snapshot["development"] + snapshot["confirmation"]:
            self.assertEqual(
                set(row["public"]), {"id", "profile", "text", "parameters", "instances"}
            )
            self.assertNotIn("gold_solution", row)
            self.assertNotIn("gurobi_result", row)


if __name__ == "__main__":
    unittest.main()
