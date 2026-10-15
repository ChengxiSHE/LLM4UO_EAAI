import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Text2OptV8SplitTests(unittest.TestCase):
    def test_grouped_split_is_bound_disjoint_and_exposures_are_development_only(self):
        split_path = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
        manifest = json.loads((ROOT / "data/manifests/text2opt_v8_grouped_split_v1.json").read_text())
        split = json.loads(split_path.read_text())
        self.assertEqual(sha(split_path), manifest["bindings"]["prepared_split_sha256"])
        self.assertEqual((len(split["development"]), len(split["confirmation"])), (70, 401))
        development = {row["id"] for row in split["development"]}
        confirmation = {row["id"] for row in split["confirmation"]}
        self.assertFalse(development & confirmation)
        self.assertTrue(set(manifest["manual_outcome_exposures"]) <= development)
        self.assertFalse(set(manifest["manual_outcome_exposures"]) & confirmation)
        self.assertTrue(all("small_prose" not in row["source_file"] and "small_capped" not in row["source_file"]
                            for row in split["development"] + split["confirmation"]))

    def test_retired_v6_plan_had_zero_public_actionability(self):
        audit = json.loads((ROOT / "results/text2opt_v6_confirmation_actionability_audit.json").read_text())
        authorization = json.loads((ROOT / "experiments/text2opt_v6_confirmation_run_authorization.json").read_text())
        self.assertEqual(audit["overall"]["records"], 431)
        self.assertEqual(audit["overall"]["any_v6_public_trigger"], 0)
        self.assertFalse(audit["outcomes_read"])
        self.assertEqual(audit["api_requests"], 0)
        self.assertEqual(authorization["status"], "retired_pre_authorization_actionability_zero")
        self.assertFalse(authorization["further_api_calls_authorized"])


if __name__ == "__main__":
    unittest.main()
