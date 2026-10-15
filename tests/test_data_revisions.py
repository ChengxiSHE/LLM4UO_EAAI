import copy
import unittest

from llm4or.benchmark_inputs import complexor_input, payload_sha256, input_shape_issues
from llm4or.data_revisions import revise_parameter_shapes
from llm4or.schema import Invalid


class ParameterRevisionTests(unittest.TestCase):
    def fixture(self):
        p = complexor_input("case", {"description": "Supply per origin", "parameters": [
            {"symbol": "Origins", "definition": "number of origins", "shape": []},
            {"symbol": "Supply", "definition": "supply per origin", "shape": []}]},
            [{"input": {"Origins": 2, "Supply": [3, 4]}, "output": "GOLD_SENTINEL"}])
        review = {"problem_id": "case", "status": "reviewed_metadata_only", "before_sha256": payload_sha256(p),
                  "edits": [{"parameter": "Supply", "before": [], "after": ["Origins"], "rationale": "per origin",
                             "evidence": [{"quote": "Supply per origin"}]}]}
        return p, review

    def test_revise_only_metadata_and_leave_input_unchanged(self):
        p, review = self.fixture(); before = copy.deepcopy(p)
        result = revise_parameter_shapes(p, review)
        self.assertEqual(p, before)
        self.assertEqual(result["instances"], p["instances"])
        self.assertEqual(result["text"], p["text"])
        self.assertEqual(input_shape_issues(result), [])

    def test_drifted_values_cannot_receive_stale_review(self):
        p, review = self.fixture(); p["instances"][0]["input"]["Supply"][0] = 99
        with self.assertRaises(Invalid): revise_parameter_shapes(p, review)

    def test_no_value_patch_backdoor(self):
        p, review = self.fixture(); review["edits"][0]["new_input"] = [4, 5]
        with self.assertRaises(Invalid): revise_parameter_shapes(p, review)

    def test_unreviewed_and_duplicate_edits_rejected(self):
        p, review = self.fixture(); review["status"] = "proposed"
        with self.assertRaises(Invalid): revise_parameter_shapes(p, review)
        review["status"] = "reviewed_metadata_only"; review["edits"].append(review["edits"][0])
        with self.assertRaises(Invalid): revise_parameter_shapes(p, review)


if __name__ == "__main__": unittest.main()
