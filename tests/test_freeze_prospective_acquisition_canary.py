import json
from pathlib import Path
import shutil
import tempfile
import unittest

from llm4or.schema import canonical, digest
from scripts import freeze_prospective_acquisition_canary as freezer


ROOT = Path(__file__).resolve().parents[1]


class FreezeProspectiveAcquisitionCanaryTests(unittest.TestCase):
    def test_bundle_and_plan_bind_exact_cells_and_matched_facts(self):
        bundle = freezer.build_bundle(ROOT)
        plan = freezer.build_plan(ROOT, bundle, created_at=1_800_000_000)

        self.assertEqual(len(bundle["units"]), 8)
        self.assertEqual(len(bundle["cells"]), 48)
        self.assertEqual(len(plan["cells"]), 48)
        self.assertEqual(len({row["cell_id"] for row in plan["cells"]}), 48)
        self.assertEqual(len({row["request_key"] for row in plan["cells"]}), 48)
        for unit in bundle["units"]:
            for round_number in (1, 2, 3):
                flat = bundle["cells"][freezer.cell_id(unit["unit_id"], "flat", round_number)]
                treatment = bundle["cells"][
                    freezer.cell_id(unit["unit_id"], "separating_witness", round_number)
                ]
                self.assertEqual(
                    flat["payload"]["revealed_facts"],
                    treatment["payload"]["revealed_facts"],
                )
        self.assertEqual(plan["model"], "DeepSeek-V4-Flash")
        self.assertEqual(plan["base_url"], "https://antchat.alipay.com/v1")
        self.assertEqual(plan["limits"]["max_concurrent_requests"], 5)
        self.assertEqual(plan["limits"]["max_logical_requests"], 48)
        self.assertEqual(plan["limits"]["max_physical_attempts"], 48)
        self.assertEqual(plan["limits"]["max_attempts_per_request"], 1)
        self.assertEqual(plan["private_bundle_sha256"], digest(bundle))
        self.assertEqual(plan["approved_program"], "A_staged_multi_unit_program")
        self.assertIn(freezer.APPROVAL, plan["source_sha256"])

    def test_public_plan_contains_no_payload_or_prohibited_result_fields(self):
        bundle = freezer.build_bundle(ROOT)
        plan = freezer.build_plan(ROOT, bundle, created_at=1_800_000_000)
        text = canonical(plan).casefold()
        for token in (
            '"instruction"',
            '"source_proposal"',
            '"revealed_facts"',
            '"response_schema"',
            '"accepted_value"',
            '"winner"',
            '"minimum_repair"',
            '"benchmark_answer"',
            '"solved_vector"',
            '"reference_answer"',
            '"api_key"',
        ):
            self.assertNotIn(token, text)

    def test_build_plan_rejects_any_bundle_mutation(self):
        bundle = freezer.build_bundle(ROOT)
        changed = json.loads(json.dumps(bundle))
        first = sorted(changed["cells"])[0]
        changed["cells"][first]["payload"]["revealed_facts"][0]["statement"] += " mutation"
        with self.assertRaises(ValueError):
            freezer.build_plan(ROOT, changed, created_at=1_800_000_000)

    def test_freeze_uses_exclusive_outputs_and_is_idempotently_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in freezer.INPUT_FILES:
                source = ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            (root / "experiments").mkdir(exist_ok=True)
            (root / "results/private").mkdir(parents=True, exist_ok=True)

            result = freezer.freeze(root, created_at=1_800_000_000)

            self.assertEqual(result["state"], "frozen")
            plan = json.loads((root / freezer.PLAN).read_text())
            bundle = json.loads((root / freezer.BUNDLE).read_text())
            self.assertEqual(plan["private_bundle_sha256"], digest(bundle))
            self.assertEqual(result["plan_sha256"], digest(plan))
            with self.assertRaises(ValueError):
                freezer.freeze(root, created_at=1_800_000_001)


if __name__ == "__main__":
    unittest.main()
