import json
from pathlib import Path
import unittest

from llm4or.fresh_common38_synthesis import OUTPUT_PATH, build_synthesis
from llm4or.schema import canonical


ROOT = Path(__file__).resolve().parents[1]


class FreshCommon38SynthesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = build_synthesis(ROOT)

    def test_method_native_rows_and_family_endpoints_are_fixed(self):
        rows = {row["method"]: row for row in self.value["method_native_rows"]}
        self.assertEqual(rows["Proof-carrying compilation"]["correct"], 30)
        self.assertEqual(rows["Base"]["correct"], 0)
        self.assertEqual(rows["BIND round 1"]["correct"], 13)
        self.assertEqual(rows["BIND final"]["correct"], 13)
        self.assertEqual(rows["CoE-safe"]["correct"], 4)
        self.assertEqual(rows["Proof-carrying compilation"]["families"], {
            "rcpsp": {"correct": 12, "planned": 13},
            "vrptw": {"correct": 18, "planned": 25},
        })

    def test_paired_current_contrasts_and_holm_control(self):
        pairs = {row["comparison"]: row for row in self.value["paired_against_current"]}
        self.assertEqual((pairs["current_vs_base"]["corrections"], pairs["current_vs_base"]["regressions"]), (30, 0))
        self.assertEqual((pairs["current_vs_bind_round_one"]["corrections"], pairs["current_vs_bind_round_one"]["regressions"]), (18, 1))
        self.assertEqual((pairs["current_vs_coe_safe"]["corrections"], pairs["current_vs_coe_safe"]["regressions"]), (26, 0))
        self.assertTrue(all(row["holm_reject_0_05"] for row in pairs.values()))

    def test_equal_call_view_excludes_protocols_without_one_call_terminal(self):
        view = self.value["sensitivity_views"]["answer_blind_at_most_one_external_call"]
        self.assertEqual([row["method"] for row in view["included"]], [
            "Proof-carrying compilation", "BIND round 1", "Base",
        ])
        self.assertEqual(view["excluded"], [{
            "method": "CoE-safe",
            "reason": "official_protocol_has_no_valid_terminal_artifact_after_one_call",
        }, {
            "method": "BIND final",
            "reason": "answer_bearing_repair_can_use_more_than_one_call",
        }])

    def test_published_synthesis_reconstructs_exactly_without_new_calls(self):
        published = json.loads((ROOT / OUTPUT_PATH).read_text())
        self.assertEqual(canonical(self.value), canonical(published))
        self.assertTrue(all(value is False for value in published["privacy"].values()))


if __name__ == "__main__":
    unittest.main()
