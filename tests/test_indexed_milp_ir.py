import unittest

from llm4or.indexed_milp_ir import IRCompileError, compile_ir


LIMITS = {
    "variables": 100, "constraints": 100, "nonzeros": 500,
    "serialized_bytes": 100_000, "expansion_steps": 10_000,
}


def assignment_ir():
    return {
        "schema": "indexed-milp-ir-v1",
        "data_parameter": "instance_data",
        "sets": [
            {"id": "I", "kind": "range", "start": 0, "stop": {"data": ["n"]}},
        ],
        "variables": [{
            "id": "x", "meaning": "assignment", "unit": "item",
            "domain": "binary", "forall": [{"name": "i", "set": "I"}],
            "where": True, "lower": 0, "upper": 1,
        }],
        "constraints": [{
            "id": "choose", "forall": [], "where": True,
            "terms": [{
                "family": "x", "indices": [{"env": "i"}],
                "coefficient": 1,
                "sum": [{"name": "i", "set": "I"}], "where": True,
            }],
            "sense": "eq", "rhs": 1,
        }],
        "objective": {
            "terms": [{
                "family": "x", "indices": [{"env": "i"}],
                "coefficient": {"data": ["cost", {"env": "i"}]},
                "sum": [{"name": "i", "set": "I"}], "where": True,
            }],
            "sense": "min", "unit": "cost", "offset": 0,
        },
    }


class IndexedMilpIRTests(unittest.TestCase):
    def test_compiles_indexed_assignment_and_binds_hashes_and_resources(self):
        result = compile_ir(
            {"n": 3, "cost": [4, 1, 7]}, assignment_ir(), LIMITS,
        )
        self.assertEqual(result["status"], "admitted")
        self.assertEqual(
            [row["id"] for row in result["model"]["variables"]],
            ["x_0", "x_1", "x_2"],
        )
        self.assertEqual(
            result["model"]["constraints"][0]["coefficients"],
            {"x_0": 1.0, "x_1": 1.0, "x_2": 1.0},
        )
        self.assertEqual(
            result["model"]["objective"]["coefficients"],
            {"x_0": 4.0, "x_1": 1.0, "x_2": 7.0},
        )
        self.assertEqual(result["metrics"]["variables"], 3)
        self.assertEqual(len(result["data_sha256"]), 64)
        self.assertEqual(len(result["ir_sha256"]), 64)
        self.assertEqual(len(result["model_sha256"]), 64)

    def test_record_unpack_conditionals_and_finite_aggregates(self):
        ir = assignment_ir()
        ir["sets"].append({
            "id": "E", "kind": "records", "path": ["edges"], "arity": 3,
        })
        ir["constraints"].append({
            "id": "edge", "forall": [{"unpack": ["i", "j", "cap"], "set": "E"}],
            "where": {"compare": "gt", "left": {"env": "cap"}, "right": 0},
            "terms": [
                {"family": "x", "indices": [{"env": "i"}], "coefficient": 1, "sum": [], "where": True},
                {"family": "x", "indices": [{"env": "j"}], "coefficient": 1, "sum": [], "where": True},
            ],
            "sense": "le",
            "rhs": {"if": {"condition": {"compare": "ge", "left": {"env": "cap"}, "right": 2}, "then": 1, "else": 0}},
        })
        ir["variables"][0]["upper"] = {
            "aggregate": "max", "over": [{"name": "k", "set": "I"}],
            "where": True, "value": {"data": ["bound", {"env": "k"}]},
        }
        result = compile_ir(
            {"n": 3, "cost": [4, 1, 7], "bound": [1, 1, 1], "edges": [[0, 1, 2], [1, 2, 0]]},
            ir, LIMITS,
        )
        edge = next(row for row in result["model"]["constraints"] if row["id"] == "edge_0_1_2")
        self.assertEqual(edge["coefficients"], {"x_0": 1.0, "x_1": 1.0})
        self.assertEqual(edge["rhs"], 1.0)

    def test_rejects_unknown_paths_extra_keys_division_by_zero_and_unknown_family(self):
        cases = []
        unknown_path = assignment_ir(); unknown_path["sets"][0]["stop"] = {"data": ["missing"]}; cases.append((unknown_path, "data_path"))
        extra = assignment_ir(); extra["extra"] = 1; cases.append((extra, "ir_keys"))
        divide = assignment_ir(); divide["objective"]["offset"] = {"op": "div", "args": [1, 0]}; cases.append((divide, "division_by_zero"))
        family = assignment_ir(); family["objective"]["terms"][0]["family"] = "missing"; cases.append((family, "unknown_variable_family"))
        for ir, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(IRCompileError, code):
                    compile_ir({"n": 3, "cost": [4, 1, 7]}, ir, LIMITS)

    def test_rejects_empty_extrema_noninteger_indices_and_resource_overflow(self):
        empty = assignment_ir(); empty["variables"][0]["upper"] = {
            "aggregate": "max", "over": [{"name": "i", "set": "I"}],
            "where": False, "value": 1,
        }
        with self.assertRaisesRegex(IRCompileError, "empty_aggregate"):
            compile_ir({"n": 1, "cost": [1]}, empty, LIMITS)
        noninteger = assignment_ir(); noninteger["sets"][0]["start"] = 0.5
        with self.assertRaisesRegex(IRCompileError, "range_integer"):
            compile_ir({"n": 1, "cost": [1]}, noninteger, LIMITS)
        tiny = dict(LIMITS); tiny["variables"] = 2
        with self.assertRaisesRegex(IRCompileError, "resource_variables"):
            compile_ir({"n": 3, "cost": [4, 1, 7]}, assignment_ir(), tiny)

    def test_safe_surface_shorthands_normalize_without_benchmark_knowledge(self):
        ir = assignment_ir()
        variable = ir["variables"][0]
        variable.pop("unit"); variable.pop("where"); variable.pop("lower"); variable.pop("upper")
        ir["constraints"][0].pop("forall"); ir["constraints"][0].pop("where")
        term = ir["constraints"][0]["terms"][0]
        term["indices"] = ["i"]
        term.pop("coefficient"); term.pop("where")
        ir["objective"].pop("unit"); ir["objective"].pop("offset")
        ir["objective"]["sense"] = "minimize"
        objective_term = ir["objective"]["terms"][0]
        objective_term["indices"] = [{"name": "i"}]
        objective_term["coefficient"] = {"data": ["instance_data", "cost", "i"]}
        objective_term["sum"][0]["where"] = {
            "compare": "ge", "left": "i", "right": 0,
        }
        result = compile_ir({"n": 3, "cost": [4, 1, 7]}, ir, LIMITS)
        self.assertEqual(result["model"]["variables"][0]["unit"], "unit")
        self.assertIsNone(result["model"]["variables"][0]["lower"])
        self.assertEqual(result["model"]["constraints"][0]["coefficients"], {
            "x_0": 1.0, "x_1": 1.0, "x_2": 1.0,
        })
        self.assertEqual(result["model"]["objective"]["coefficients"], {
            "x_0": 4.0, "x_1": 1.0, "x_2": 7.0,
        })
        self.assertEqual(result["model"]["objective"]["sense"], "min")
        aggregate = assignment_ir()
        aggregate["constraints"][0]["where"] = {
            "aggregate": "any", "over": [{"name": "k", "set": "I"}],
            "predicate": {"compare": "eq", "left": "k", "right": 0},
        }
        self.assertEqual(
            compile_ir({"n": 3, "cost": [4, 1, 7]}, aggregate, LIMITS)["status"],
            "admitted",
        )
        singleton = assignment_ir()
        singleton["variables"][0]["upper"] = {"data": ["i"]}
        singleton_result = compile_ir({"n": 3, "cost": [4, 1, 7]}, singleton, LIMITS)
        self.assertEqual(
            [row["upper"] for row in singleton_result["model"]["variables"]],
            [0.0, 1.0, 2.0],
        )


if __name__ == "__main__":
    unittest.main()
