from copy import deepcopy
import unittest

from llm4or.benchmark_inputs import payload_sha256, validate_public_input
from llm4or.schema import Invalid
from llm4or.source_indexed_model import compile_source_indexed, make_source_indexed_payload, numeric_ledger


TEXT = "Buy 0 to 100 crates. Each costs 5 dollars and gives 25% of a target. Meet at least 12 points."
PROBLEM = validate_public_input({
    "id": "indexed_case", "profile": "description_parameters_v1", "text": TEXT,
    "parameters": [], "instances": [],
})


def token(raw):
    return next(item["id"] for item in numeric_ledger(PROBLEM)["entries"] if item["raw"] == raw)


def direct(raw, transform="identity"):
    return {"source": token(raw), "transform": transform}


def grounded():
    return {
        "schema": "source-indexed-milp-v1",
        "input_sha256": payload_sha256(PROBLEM),
        "variables": [{
            "id": "x", "meaning": "Number of crates", "unit": "crates", "domain": "integer",
            "lower": direct("0"), "upper": direct("100"),
        }],
        "constraints": [{
            "id": "target", "coefficients": {"x": direct("25%", "percent_fraction")},
            "sense": "ge", "rhs": direct("12"),
        }],
        "objective": {
            "coefficients": {"x": direct("5")}, "sense": "min", "unit": "dollars",
            "offset": {"structural": 0},
        },
    }


class SourceIndexedModelTests(unittest.TestCase):
    def test_numeric_ledger_is_deterministic_and_span_bound(self):
        value = numeric_ledger(PROBLEM)
        self.assertEqual([item["id"] for item in value["entries"]], [f"n{i:05d}" for i in range(5)])
        for item in value["entries"]:
            self.assertEqual(TEXT[item["start"]:item["end"]], item["raw"])
        self.assertEqual(value, numeric_ledger(PROBLEM))

    def test_compile_resolves_direct_percentage_and_structural_values(self):
        value, report = compile_source_indexed(PROBLEM, grounded())
        self.assertEqual(value["variables"][0]["upper"], 100)
        self.assertEqual(value["constraints"][0]["coefficients"]["x"], 0.25)
        self.assertEqual(value["objective"]["offset"], 0)
        self.assertEqual(report["input_sha256"], payload_sha256(PROBLEM))

    def test_unknown_source_and_invalid_percentage_fail_closed(self):
        bad = grounded(); bad["objective"]["coefficients"]["x"]["source"] = "n99999"
        with self.assertRaisesRegex(Invalid, "unknown_source"):
            compile_source_indexed(PROBLEM, bad)
        bad = grounded(); bad["objective"]["coefficients"]["x"]["transform"] = "percent_fraction"
        with self.assertRaisesRegex(Invalid, "nonpercentage_fraction"):
            compile_source_indexed(PROBLEM, bad)

    def test_sum_is_recomputed_and_literal_numbers_are_rejected(self):
        value = grounded()
        value["constraints"][0]["rhs"] = {
            "terms": [direct("100"), direct("12", "negative")]
        }
        compiled, _ = compile_source_indexed(PROBLEM, value)
        self.assertEqual(compiled["constraints"][0]["rhs"], 88)
        bad = grounded(); bad["constraints"][0]["rhs"] = 12
        with self.assertRaisesRegex(Invalid, "expression_shape"):
            compile_source_indexed(PROBLEM, bad)

    def test_payload_contains_host_ledger_and_schema(self):
        value = make_source_indexed_payload(PROBLEM)
        self.assertEqual(value["context"]["numeric_source_ledger"], numeric_ledger(PROBLEM))
        self.assertEqual(value["response_schema"]["properties"]["schema"]["const"], "source-indexed-milp-v1")
        self.assertNotIn("answer", str(value).lower())

    def test_stale_input_and_unbounded_structural_constant_are_rejected(self):
        bad = grounded(); bad["input_sha256"] = "0" * 64
        with self.assertRaisesRegex(Invalid, "stale_input"):
            compile_source_indexed(PROBLEM, bad)
        bad = grounded(); bad["objective"]["offset"] = {"structural": 2}
        with self.assertRaisesRegex(Invalid, "structural_constant"):
            compile_source_indexed(PROBLEM, bad)


if __name__ == "__main__":
    unittest.main()
