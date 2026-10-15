import unittest

from llm4or.vera_opt_repair import (
    StructuralRepairError, prune_recognizer_for_public_coverage,
    repair_v3_scalar_coverage,
)


CONFIG = {
    "schema": "declarative-binary-selection-v3",
    "record_rule": {
        "line_prefixes": ["* Container "], "id_suffix": ":",
        "numeric_fields": [
            {"name": "resource", "position": 0},
            {"name": "value", "position": 1},
        ],
    },
    "scalar_rules": [{
        "name": "capacity",
        "required_any": ["has a maximum capacity of", "can carry at most"],
        "forbidden_any": [], "numeric_position": 0,
    }],
    "variable_domain": "binary",
    "objective": {"sense": "max", "coefficient_field": "value", "offset": 0},
    "constraints": [{
        "id": "capacity", "coefficient_field": "resource",
        "sense": "le", "rhs_scalar": "capacity",
    }],
    "minimum_records": 1, "maximum_records": 100,
}


QUESTIONS = [
    "* Container A: weight 3, value 5\nThe plane has a maximum capacity of 7.",
    "* Container A: weight 4, value 6\nThe vessel can carry at most 8.",
    "* Container A: weight 2, value 9\nThe plane's maximum capacity is 6.",
]


class VeraOptRepairTests(unittest.TestCase):
    def test_scalar_repair_uses_only_substrings_of_proposed_phrases(self):
        repaired, report = repair_v3_scalar_coverage(CONFIG, QUESTIONS)
        self.assertTrue(report["applied"])
        anchors = repaired["scalar_rules"][0]["required_any"]
        public_sources = " ".join(
            CONFIG["scalar_rules"][0]["required_any"] + QUESTIONS
        ).casefold()
        self.assertTrue(all(anchor in public_sources for anchor in anchors))
        self.assertEqual(len(anchors), 2)

    def test_scalar_repair_can_mine_missing_cue_from_public_text(self):
        config = {**CONFIG, "scalar_rules": [{
            **CONFIG["scalar_rules"][0],
            "required_any": ["has a maximum capacity of"],
        }]}
        repaired, report = repair_v3_scalar_coverage(config, QUESTIONS)
        self.assertTrue(report["applied"])
        self.assertEqual(len(repaired["scalar_rules"][0]["required_any"]), 2)

    def test_recognizer_prunes_uncovered_condition_but_keeps_specificity(self):
        recognizer = {
            "kind": "casefolded_literal_v1", "required_all": [],
            "required_any": [["container"], ["maximize"], ["value", "revenue"]],
            "forbidden_any": [],
        }
        repaired, report = prune_recognizer_for_public_coverage(recognizer, QUESTIONS)
        self.assertTrue(report["applied"])
        self.assertEqual(repaired["required_any"], [["container"], ["value", "revenue"]])

    def test_recognizer_refuses_unconditional_repair(self):
        recognizer = {
            "kind": "casefolded_literal_v1", "required_all": [],
            "required_any": [["missing"]], "forbidden_any": [],
        }
        with self.assertRaisesRegex(StructuralRepairError, "specificity_floor"):
            prune_recognizer_for_public_coverage(recognizer, QUESTIONS)


if __name__ == "__main__":
    unittest.main()
