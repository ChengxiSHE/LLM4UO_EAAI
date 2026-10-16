import inspect
import unittest

import llm4or.indexed_milp_ir as compiler_module
from llm4or.indexed_milp_ir import compile_ir


LIMITS = {
    "variables": 200, "constraints": 500, "nonzeros": 2000,
    "serialized_bytes": 500_000, "expansion_steps": 100_000,
}


def env(name):
    return {"env": name}


def data(*path):
    return {"data": list(path)}


def op(name, *args):
    return {"op": name, "args": list(args)}


def compare(name, left, right):
    return {"compare": name, "left": left, "right": right}


def term(family, indices, coefficient, sums=(), where=True):
    return {
        "family": family, "indices": list(indices), "coefficient": coefficient,
        "sum": list(sums), "where": where,
    }


def scheduling_ir():
    activities = {"name": "i", "set": "A"}
    modes = {"name": "m", "set": "M"}
    return {
        "schema": "indexed-milp-ir-v1", "data_parameter": "instance_data",
        "sets": [
            {"id": "A", "kind": "range", "start": 0, "stop": data("n")},
            {"id": "M", "kind": "range", "start": 0, "stop": data("modes")},
            {"id": "E", "kind": "records", "path": ["edges"], "arity": 3},
        ],
        "variables": [
            {"id": "start", "meaning": "activity start", "unit": "time",
             "domain": "continuous", "forall": [activities], "where": True,
             "lower": 0, "upper": data("horizon")},
            {"id": "select", "meaning": "selected execution mode", "unit": "binary",
             "domain": "binary", "forall": [activities, modes], "where": True,
             "lower": 0, "upper": 1},
            {"id": "makespan", "meaning": "project completion", "unit": "time",
             "domain": "continuous", "forall": [], "where": True,
             "lower": 0, "upper": data("horizon")},
        ],
        "constraints": [
            {"id": "choose", "forall": [activities], "where": True,
             "terms": [term("select", [env("i"), env("m")], 1, [modes])],
             "sense": "eq", "rhs": 1},
            {"id": "precedence", "forall": [{"unpack": ["i", "j", "lag"], "set": "E"}],
             "where": True,
             "terms": [
                 term("start", [env("i")], 1), term("start", [env("j")], -1),
                 term("select", [env("i"), env("m")], data("duration", env("i"), env("m")), [modes]),
             ], "sense": "le", "rhs": op("neg", env("lag"))},
            {"id": "budget", "forall": [], "where": True,
             "terms": [term("select", [env("i"), env("m")],
                            data("cost", env("i"), env("m")), [activities, modes])],
             "sense": "le", "rhs": data("budget")},
            {"id": "completion", "forall": [activities], "where": True,
             "terms": [
                 term("start", [env("i")], 1), term("makespan", [], -1),
                 term("select", [env("i"), env("m")], data("duration", env("i"), env("m")), [modes]),
             ], "sense": "le", "rhs": 0},
        ],
        "objective": {
            "terms": [term("makespan", [], 1)], "sense": "min",
            "unit": "time", "offset": 0,
        },
    }


def distance(i, j):
    dx = op("sub", data("coordinates", i, 0), data("coordinates", j, 0))
    dy = op("sub", data("coordinates", i, 1), data("coordinates", j, 1))
    return op("sqrt", op("add", op("mul", dx, dx), op("mul", dy, dy)))


def routing_ir():
    nodes = {"name": "i", "set": "N"}
    customers = {"name": "i", "set": "C"}
    node_j = {"name": "j", "set": "N"}
    customer_j = {"name": "j", "set": "C"}
    different = compare("ne", env("i"), env("j"))
    return {
        "schema": "indexed-milp-ir-v1", "data_parameter": "instance_data",
        "sets": [
            {"id": "N", "kind": "range", "start": 0, "stop": op("add", data("n"), 1)},
            {"id": "C", "kind": "range", "start": 1, "stop": op("add", data("n"), 1)},
        ],
        "variables": [
            {"id": "arc", "meaning": "travel arc", "unit": "binary", "domain": "binary",
             "forall": [nodes, node_j], "where": different, "lower": 0, "upper": 1},
            {"id": "load", "meaning": "load after customer", "unit": "units", "domain": "continuous",
             "forall": [customers], "where": True, "lower": data("demand", op("sub", env("i"), 1)),
             "upper": data("capacity")},
            {"id": "time", "meaning": "service start", "unit": "time", "domain": "continuous",
             "forall": [nodes], "where": True, "lower": data("windows", env("i"), 0),
             "upper": data("windows", env("i"), 1)},
        ],
        "constraints": [
            {"id": "visit_out", "forall": [customers], "where": True,
             "terms": [term("arc", [env("i"), env("j")], 1, [node_j], different)],
             "sense": "eq", "rhs": 1},
            {"id": "visit_in", "forall": [{"name": "j", "set": "C"}], "where": True,
             "terms": [term("arc", [env("i"), env("j")], 1, [nodes], different)],
             "sense": "eq", "rhs": 1},
            {"id": "vehicle_limit", "forall": [], "where": True,
             "terms": [term("arc", [0, env("j")], 1, [customer_j])],
             "sense": "le", "rhs": data("vehicles")},
            {"id": "load_link", "forall": [customers, customer_j], "where": different,
             "terms": [term("load", [env("i")], 1), term("load", [env("j")], -1),
                       term("arc", [env("i"), env("j")], data("capacity"))],
             "sense": "le", "rhs": op("sub", data("capacity"), data("demand", op("sub", env("j"), 1)))},
            {"id": "time_link", "forall": [nodes, customer_j], "where": different,
             "terms": [term("time", [env("i")], 1), term("time", [env("j")], -1),
                       term("arc", [env("i"), env("j")], data("big_m"))],
             "sense": "le",
             "rhs": op("sub", op("sub", data("big_m"), data("service", env("i"))),
                       distance(env("i"), env("j")))},
        ],
        "objective": {
            "terms": [term(
                "arc", [env("i"), env("j")],
                op("add", distance(env("i"), env("j")),
                   {"if": {"condition": compare("eq", env("i"), 0),
                           "then": data("fixed_cost"), "else": 0}}),
                [nodes, node_j], different,
            )],
            "sense": "min", "unit": "distance plus deployment cost", "offset": 0,
        },
    }


class IndexedMilpIRFamilyTests(unittest.TestCase):
    def test_interpreter_source_has_no_family_router_or_existing_skill_call(self):
        source = inspect.getsource(compiler_module).lower()
        for forbidden in ("rcpsp", "vrptw", "structured_or_skills", "compile_packet"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_expands_small_multimode_precedence_model(self):
        instance = {
            "n": 2, "modes": 2, "duration": [[2, 3], [1, 4]],
            "cost": [[4, 2], [3, 1]], "edges": [[0, 1, 1]],
            "budget": 7, "horizon": 12,
        }
        result = compile_ir(instance, scheduling_ir(), LIMITS)
        self.assertEqual(result["metrics"]["variables"], 7)
        self.assertEqual(result["metrics"]["constraints"], 6)
        row = next(x for x in result["model"]["constraints"] if x["id"] == "precedence_0_1_1")
        self.assertEqual(
            row["coefficients"],
            {"select_0_0": 2.0, "select_0_1": 3.0, "start_0": 1.0, "start_1": -1.0},
        )
        self.assertEqual(row["rhs"], -1.0)

    def test_expands_small_capacitated_time_window_routing_model(self):
        instance = {
            "n": 2, "coordinates": [[0, 0], [1, 0], [0, 1]],
            "demand": [1, 1], "capacity": 2, "vehicles": 2,
            "windows": [[0, 10], [0, 8], [0, 8]],
            "service": [0, 1, 1], "big_m": 20, "fixed_cost": 5,
        }
        result = compile_ir(instance, routing_ir(), LIMITS)
        self.assertEqual(result["metrics"]["variables"], 11)
        self.assertEqual(result["metrics"]["constraints"], 11)
        objective = result["model"]["objective"]["coefficients"]
        self.assertAlmostEqual(objective["arc_0_1"], 6.0)
        self.assertAlmostEqual(objective["arc_1_2"], 2 ** 0.5)
        self.assertEqual(result["model"]["constraints"][0]["sense"], "eq")


if __name__ == "__main__":
    unittest.main()
