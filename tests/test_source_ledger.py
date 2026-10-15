from copy import deepcopy
import unittest

from llm4or.benchmark_inputs import payload_sha256, validate_public_input
from llm4or.milp_solver import execute
from llm4or.schema import Invalid
from llm4or.source_ledger import apply_dual_view_consensus, compile_dual_view_consensus, compile_ledger, make_ledger_payload


TEXT = (
    "Choose whole crates of apples. Each crate costs 5 dollars and contributes 3 nutrition points. "
    "Buy from 0 up to 10 crates. Achieve at least 12 nutrition points. Minimize total cost."
)
PROBLEM = validate_public_input({
    "id": "ledger_case",
    "profile": "description_parameters_v1",
    "text": TEXT,
    "parameters": [],
    "instances": [],
})


def quote(fragment):
    start = TEXT.index(fragment)
    return {"text": fragment, "start": start, "end": start + len(fragment)}


def ledger(view):
    return {
        "schema": "source-ledger-v1",
        "view": view,
        "input_sha256": payload_sha256(PROBLEM),
        "variables": [{
            "id": "x000",
            "meaning": "Number of apple crates",
            "unit": "crates",
            "domain": "integer",
            "lower": 0,
            "upper": 10,
            "objective_coefficient": 5,
            "quote": quote("Each crate costs 5 dollars and contributes 3 nutrition points. Buy from 0 up to 10 crates."),
        }],
        "constraints": [{
            "id": "c000",
            "coefficients": {"x000": 3},
            "sense": "ge",
            "rhs": 12,
            "quote": quote("Each crate costs 5 dollars and contributes 3 nutrition points. Buy from 0 up to 10 crates. Achieve at least 12 nutrition points."),
        }],
        "objective": {
            "sense": "min",
            "unit": "dollars",
            "offset": 0,
            "quote": quote("Choose whole crates of apples. Each crate costs 5 dollars"),
        },
    }


class SourceLedgerTests(unittest.TestCase):
    def test_payload_separates_views(self):
        a = make_ledger_payload(PROBLEM, "variable_first")
        b = make_ledger_payload(PROBLEM, "constraint_first")
        self.assertNotEqual(a["instruction"], b["instruction"])
        self.assertEqual(a["context"]["input_sha256"], payload_sha256(PROBLEM))

    def test_compile_requires_exact_quote_and_numeric_grounding(self):
        compiled, report = compile_ledger(PROBLEM, ledger("variable_first"), "variable_first")
        self.assertEqual(compiled["variables"][0]["domain"], "integer")
        self.assertEqual(report["view"], "variable_first")
        bad = ledger("variable_first")
        bad["constraints"][0]["rhs"] = 13
        with self.assertRaisesRegex(Invalid, "number_not_in_quote"):
            compile_ledger(PROBLEM, bad, "variable_first")

    def test_zero_objective_coefficient_is_canonical_absence(self):
        value = ledger("variable_first")
        value["variables"][0]["objective_coefficient"] = 0
        value["variables"][0]["quote"] = quote("Buy from 0 up to 10 crates.")
        compiled, _ = compile_ledger(PROBLEM, value, "variable_first")
        self.assertEqual(compiled["objective"]["coefficients"], {})

    def test_dual_view_consensus_repairs_and_disagreement_abstains(self):
        initial, _ = compile_ledger(PROBLEM, ledger("variable_first"), "variable_first")
        initial = deepcopy(initial)
        initial["variables"][0]["domain"] = "continuous"
        repaired, report = apply_dual_view_consensus(
            PROBLEM, initial, ledger("variable_first"), ledger("constraint_first"), execute
        )
        self.assertTrue(report["accepted"])
        self.assertEqual(repaired["variables"][0]["domain"], "integer")
        disagreement = ledger("constraint_first")
        disagreement["objective"]["sense"] = "max"
        retained, report = apply_dual_view_consensus(
            PROBLEM, initial, ledger("variable_first"), disagreement, execute
        )
        self.assertFalse(report["accepted"])
        self.assertEqual(report["status"], "views_disagree")
        self.assertEqual(retained, initial)

    def test_consensus_can_recover_without_an_initial_model(self):
        recovered, report = compile_dual_view_consensus(
            PROBLEM, ledger("variable_first"), ledger("constraint_first"), execute
        )
        self.assertTrue(report["accepted"])
        self.assertEqual(recovered["variables"][0]["domain"], "integer")


if __name__ == "__main__":
    unittest.main()
