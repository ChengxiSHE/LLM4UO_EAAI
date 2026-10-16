import hashlib
import json
from pathlib import Path
import unittest

from llm4or.schema import digest
from llm4or.verified_skill_library import select_skill, skill_sha256, validate_skill_package


ROOT = Path(__file__).resolve().parents[1]


class V9GenerationZeroSkillTests(unittest.TestCase):
    def test_manifest_is_hash_bound_and_recognizes_development_families(self):
        path = ROOT / "experiments/v9_generation_zero_skill_library.json"
        manifest = json.loads(path.read_text())
        unsigned = {key: value for key, value in manifest.items() if key != "library_sha256"}
        self.assertEqual(manifest["library_sha256"], digest(unsigned))
        compiler = ROOT / manifest["compiler_source"]
        self.assertEqual(manifest["compiler_source_sha256"], hashlib.sha256(compiler.read_bytes()).hexdigest())
        registry = manifest["trusted_implementations"]
        packages = manifest["packages"]
        self.assertEqual(len(packages), 6)
        for package in packages:
            validate_skill_package(package, registry)
            self.assertEqual(manifest["package_sha256"][package["skill_id"]], skill_sha256(package, registry))

        prepared = json.loads((ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json").read_text())
        for row in prepared["development"]:
            if row["family"] == "resource_allocation":
                continue
            selected = select_skill(packages, row["public"]["text"], registry)
            self.assertIsNotNone(selected, row["id"])
            self.assertEqual(selected["family"], row["family"])


if __name__ == "__main__":
    unittest.main()
