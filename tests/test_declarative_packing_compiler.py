import unittest

from llm4or.benchmark_inputs import flat_input
from llm4or.declarative_packing_compiler import (
    DeclarativePackingError, compile_packing_model, parse_packing_text,
    optimal_bin_count, solve_declarative_packing, validate_configuration,
)
from llm4or.milp_solver import execute


def configuration():
    return {
        "schema": "declarative-bin-packing-v1",
        "record_rule": {
            "line_prefixes": ["* Package ", "* Box "], "id_suffix": ":",
            "numeric_fields": [{"name": "weight", "position": 0}],
        },
        "capacity_rule": {
            "name": "capacity", "required_any": ["maximum load", "carry up to"],
            "forbidden_any": [], "numeric_position": 0,
        },
        "item_weight_field": "weight", "capacity_scalar": "capacity",
        "objective": "minimize_used_bins", "assignment": "each_item_exactly_once",
        "capacity_constraint": "sum_weight_le_capacity_times_used",
        "symmetry_breaking": "used_bins_prefix", "minimum_records": 1,
        "maximum_records": 100,
    }


class DeclarativePackingCompilerTest(unittest.TestCase):
    def test_parse_compile_and_solve(self):
        text = """Items:\n* Package A: 60 pounds\n* Package B: 40 pounds\n* Box C: 70 pounds\nEach truck can carry a maximum load of 100 pounds."""
        parsed = parse_packing_text(text, configuration())
        self.assertEqual([60, 40, 70], [r["fields"]["weight"] for r in parsed["records"]])
        self.assertEqual(100, parsed["capacity"])
        model = compile_packing_model(text, configuration())
        self.assertEqual(12, len(model["variables"]))
        self.assertEqual(8, len(model["constraints"]))
        result = solve_declarative_packing(
            flat_input("p", {"question": text}, "question"),
            {"max_input_bytes": 10000, "max_variables": 1000,
             "max_constraints": 1000, "wall_seconds": 30}, configuration(),
        )
        self.assertEqual("optimal", result["status"])
        self.assertEqual(2, result["objective"])

    def test_longest_prefix_disambiguates(self):
        config = configuration()
        config["record_rule"]["line_prefixes"] = ["* Package", "* Package "]
        parsed = parse_packing_text(
            "* Package A: 10 kg\nEach truck has a maximum load of 100 kg.", config,
        )
        self.assertEqual("A", parsed["records"][0]["id"])

    def test_rejects_item_over_capacity(self):
        with self.assertRaisesRegex(DeclarativePackingError, "item_exceeds_capacity"):
            parse_packing_text(
                "* Package A: 110 kg\nEach truck has a maximum load of 100 kg.",
                configuration(),
            )

    def test_rejects_mutable_algebra(self):
        config = configuration(); config["objective"] = "maximize_used_bins"
        with self.assertRaisesRegex(DeclarativePackingError, "invalid_formulation_contract"):
            validate_configuration(config)

    def test_exact_solver_matches_milp_on_small_instances(self):
        cases = ([60, 40, 70], [51, 49, 50, 50], [35, 35, 35, 35, 30, 30],
                 [80, 20, 20, 20, 20, 20], [67, 43, 62, 38, 48, 38])
        for case_index, weights in enumerate(cases):
            lines = [f"* Package I{i}: {weight} kg" for i, weight in enumerate(weights)]
            text = "\n".join(lines + ["Each truck has a maximum load of 100 kg."])
            model = compile_packing_model(text, configuration())
            result = execute({"op": "solve", "model": model}, wall_seconds=30,
                             limits={"solve_seconds": 20, "total_seconds": 30,
                                     "node_limit": 100000, "max_queries": 1})
            self.assertEqual("optimal", result["status"], case_index)
            self.assertEqual(result["objective"], optimal_bin_count(list(weights), 100), case_index)


if __name__ == "__main__":
    unittest.main()
