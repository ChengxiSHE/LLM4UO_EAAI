import unittest

from llm4or.external_code_adapter import extract_python_code, solve_generated_gurobi, translate_generated_gurobi
from llm4or.restricted_gurobi import (
    RestrictedCodeError, compile_gurobi_function_source, compile_gurobi_source,
    evaluate_optimization_function_source, evaluate_restricted_function_source,
)


class RestrictedGurobiTests(unittest.TestCase):
    def test_evaluates_bounded_pure_python_dynamic_program_without_exec(self):
        source = '''
def solve(values, weights, capacity):
    if not isinstance(capacity, int):
        raise TypeError("capacity")
    dp = [0] * (capacity + 1)
    for value, weight in zip(values, weights):
        for current in range(capacity, weight - 1, -1):
            dp[current] = max(dp[current], dp[current - weight] + value)
    return float(dp[capacity])
'''
        value = evaluate_restricted_function_source(
            source, "solve", {"values": [5, 7], "weights": [2, 3], "capacity": 3},
        )
        self.assertEqual(value, 7.0)

    def test_compiles_scipy_linprog_surface_to_same_ir(self):
        source = '''
from scipy.optimize import linprog
def solve(cost, demand):
    result = linprog(c=cost, A_eq=[[1, 1]], b_eq=[demand], bounds=[(0, None), (0, None)], method="highs")
    return float(result.fun)
'''
        model = compile_gurobi_function_source(
            source, "solve", {"cost": [2, 3], "demand": 4},
        )
        self.assertEqual(len(model["variables"]), 2)
        self.assertEqual(len(model["constraints"]), 1)
        self.assertEqual(model["objective"]["coefficients"], {"v000000": 2.0, "v000001": 3.0})

    def test_reproduces_postsolve_return_value_with_trusted_solver_facade(self):
        source = '''
import gurobipy as gp
from gurobipy import GRB
def solve(cap, extra=False):
    model = gp.Model()
    x = model.addVar(lb=0, ub=cap, name="x")
    model.setObjective(x, GRB.MAXIMIZE)
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        return None
    return (float(model.ObjVal), [x.X]) if extra else float(model.ObjVal)
'''
        def solver(operation):
            variable = operation["model"]["variables"][0]["id"]
            return {"status": "optimal", "objective": 3.0, "point": {variable: 3.0}}
        value = evaluate_optimization_function_source(source, "solve", {"cap": 3}, solver)
        self.assertEqual(value, 3.0)

    def test_compiles_parameterized_coe_function_and_stops_before_solution_access(self):
        source = '''
def native(capacity, profits):
    import gurobipy as gp
    from gurobipy import GRB
    m = gp.Model("native")
    x = m.addVars(len(profits), lb=[0, 0], ub=[1, 1], vtype=GRB.BINARY, name="x")
    m.setObjective(gp.quicksum(profits[i] * x[i] for i in range(len(profits))), GRB.MAXIMIZE)
    m.addConstr(gp.quicksum(x[i] for i in range(len(profits))) <= capacity)
    m.Params.OutputFlag = 0
    m.optimize()
    return m.objVal  # deliberately unsupported and therefore must never execute
'''
        result = compile_gurobi_function_source(
            source, "native", {"capacity": 1, "profits": [2, 5]},
        )
        self.assertEqual(result["objective"]["sense"], "max")
        self.assertEqual(len(result["variables"]), 2)
        self.assertEqual(len(result["constraints"]), 1)

    def test_parameterized_function_requires_exact_public_arguments(self):
        source = '''
from gurobipy import Model
def native(value):
    m = Model()
    m.optimize()
    return 0
'''
        with self.assertRaisesRegex(RestrictedCodeError, "function argument mismatch"):
            compile_gurobi_function_source(source, "native", {"wrong": 1})

    def test_translates_looped_gurobi_model_without_execution(self):
        source = '''
from gurobipy import *
def solve_problem():
    m = Model("transport")
    costs = [[2, 3], [4, 1]]
    supply = [5, 7]
    demand = [4, 8]
    x = {}
    for i in range(2):
        for j in range(2):
            x[i, j] = m.addVar(lb=0, vtype=GRB.INTEGER, name=f"x_{i}_{j}")
    m.setObjective(quicksum(costs[i][j] * x[i, j] for i in range(2) for j in range(2)), GRB.MINIMIZE)
    for i in range(2):
        m.addConstr(quicksum(x[i, j] for j in range(2)) <= supply[i])
    for j in range(2):
        m.addConstr(quicksum(x[i, j] for i in range(2)) >= demand[j])
    m.optimize()
    return m
'''
        result = compile_gurobi_source(source)
        self.assertEqual(result["schema"], "milp-v1")
        self.assertEqual(len(result["variables"]), 4)
        self.assertEqual(len(result["constraints"]), 4)
        self.assertEqual(result["objective"]["sense"], "min")
        self.assertEqual(result["objective"]["coefficients"], {
            "v000000": 2.0, "v000001": 3.0, "v000002": 4.0, "v000003": 1.0,
        })

    def test_rejects_imports_and_file_access(self):
        with self.assertRaises(RestrictedCodeError):
            compile_gurobi_source("import os\ndef solve_problem():\n return os.system('id')")
        with self.assertRaises(RestrictedCodeError):
            compile_gurobi_source("from gurobipy import *\ndef solve_problem():\n return open('/etc/passwd').read()")

    def test_rejects_dunder_escape_and_nonlinearity(self):
        with self.assertRaises(RestrictedCodeError):
            compile_gurobi_source("from gurobipy import *\ndef solve_problem():\n return ().__class__")
        with self.assertRaises(RestrictedCodeError):
            compile_gurobi_source('''
from gurobipy import *
def solve_problem():
    m = Model()
    x = m.addVar(name="x")
    m.setObjective(x * x, GRB.MINIMIZE)
    return m
''')

    def test_supports_helper_math_and_variable_bound_update(self):
        source = '''
import math
from gurobipy import *
def cap(a):
    return int(math.floor(math.sqrt(a)))
def solve_problem():
    m = Model()
    x = m.addVar(lb=0, name="x")
    x.ub = cap(81)
    m.setObjective(2 * x + 3, GRB.MAXIMIZE)
    m.addConstr(x <= 9)
    m.optimize()
    return m
'''
        result = compile_gurobi_source(source)
        self.assertEqual(result["variables"][0]["upper"], 9.0)
        self.assertEqual(result["objective"]["offset"], 3.0)
        self.assertEqual(result["objective"]["sense"], "max")

    def test_injects_json_without_real_file_access_and_supports_bulk_builders(self):
        source = '''
import json
from gurobipy import *
INSTANCE_DATA_PATH = r"/virtual/instance.json"
def solve_problem():
    with open(INSTANCE_DATA_PATH, "r") as f:
        d = json.load(f)
    m = Model("bulk")
    x = m.addVars(d["n"], vtype=GRB.BINARY, name="x")
    m.setObjective(quicksum(d["profit"][i] * x[i] for i in range(d["n"])), GRB.MAXIMIZE)
    m.addConstrs((x[i] <= d["cap"][i] for i in range(d["n"])), name="cap")
    m.optimize()
    return m
'''
        result = compile_gurobi_source(source, data_files={
            "/virtual/instance.json": {"n": 3, "profit": [2, 4, 6], "cap": [1, 0, 1]},
        })
        self.assertEqual(len(result["variables"]), 3)
        self.assertEqual(len(result["constraints"]), 3)
        self.assertEqual(result["objective"]["sense"], "max")
        self.assertEqual(result["objective"]["coefficients"]["v000002"], 6.0)

    def test_refuses_uninjected_json_path(self):
        source = '''
import json
from gurobipy import *
def solve_problem():
    with open("/etc/passwd", "r") as f:
        d = json.load(f)
    return Model(str(d))
'''
        with self.assertRaises(RestrictedCodeError):
            compile_gurobi_source(source, data_files={})

    def test_external_adapter_uses_last_code_block_and_returns_only_hashes_on_rejection(self):
        output = "first\n```python\nraise Exception('bad')\n```\nlast\n```python\nimport os\n```"
        self.assertEqual(extract_python_code(output), "import os")
        rejected = translate_generated_gurobi(output)
        self.assertEqual(rejected["status"], "rejected")
        self.assertIn("code_sha256", rejected)
        self.assertNotIn("model", rejected)
        self.assertNotIn("import os", str(rejected))

    def test_external_adapter_solves_only_compiled_model(self):
        output = '''```python
from gurobipy import *
def solve_problem():
    m = Model()
    x = m.addVar(lb=0, ub=3, vtype=GRB.INTEGER, name="x")
    m.setObjective(2*x, GRB.MAXIMIZE)
    m.optimize()
    return m
```'''
        result = solve_generated_gurobi(output)
        self.assertEqual(result["status"], "solved")
        self.assertAlmostEqual(result["solve"]["objective"], 6.0)

    def test_safe_numeric_and_collection_idioms_used_by_bind(self):
        source = '''
import math
from gurobipy import *
def solve_problem():
    d = {"cap": [1, 2], "integer": True, "optional": []}
    m = Model()
    x = {}
    for i, cap in enumerate(d["cap"][:]):
        kind = GRB.INTEGER if d.get("integer", False) else GRB.CONTINUOUS
        suffix = "x_%d" % (i % 2)
        x[i] = m.addVar(lb=0, ub=cap, vtype=kind, name=suffix)
    distance = math.hypot(3, 4)
    baseline = max((value for value in []), default=0)
    assert_flag = all(value >= 0 for value in d.keys()) if False else any(d["cap"])
    m.setObjective(distance * x[0] + baseline, GRB.MAXIMIZE)
    m.optimize()
    return m
'''
        result = compile_gurobi_source(source)
        self.assertEqual(len(result["variables"]), 2)
        self.assertEqual(result["objective"]["coefficients"]["v000000"], 5.0)

    def test_generated_missing_key_is_a_rejection_not_controller_exception(self):
        output = '''```python
from gurobipy import *
def solve_problem():
    m = Model()
    x = {(0, 0): m.addVar(name="x")}
    m.setObjective(x[0, 1], GRB.MINIMIZE)
    return m
```'''
        result = translate_generated_gurobi(output)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "restricted_runtime_error:KeyError")

    def test_addvars_accepts_per_index_bound_maps(self):
        source = '''
from gurobipy import *
def solve_problem():
    m = Model()
    keys = [(0, 0), (1, 0)]
    x = m.addVars(keys, lb={(0, 0): 1, (1, 0): 2},
                  ub={(0, 0): 3, (1, 0): 4}, vtype=GRB.CONTINUOUS, name="x")
    m.setObjective(x[0, 0] + x[1, 0], GRB.MINIMIZE)
    m.optimize()
    return m
'''
        result = compile_gurobi_source(source)
        self.assertEqual([(v["lower"], v["upper"]) for v in result["variables"]], [(1.0, 3.0), (2.0, 4.0)])

    def test_addvars_flattens_tuplelist_with_additional_axis(self):
        source = '''
from gurobipy import *
def solve_problem():
    m = Model()
    arcs = [(0, 1), (1, 0)]
    x = m.addVars(arcs, range(2), vtype=GRB.BINARY, name="x")
    m.setObjective(quicksum(x[i, j, k] for i, j in arcs for k in range(2)), GRB.MINIMIZE)
    m.optimize()
    return m
'''
        result = compile_gurobi_source(source)
        self.assertEqual(len(result["variables"]), 4)

    def test_nonsemantic_solver_hints_are_accepted_but_not_forwarded(self):
        source = '''
from gurobipy import *
def solve_problem():
    m = Model()
    x = m.addVar(lb=0, ub=1, name="x")
    m.setParam("TimeLimit", 100)
    m.setParam("MIPFocus", 1)
    m.setParam("OutputFlag", 0)
    m.setObjective(x, GRB.MINIMIZE)
    m.optimize()
    return m
'''
        result = compile_gurobi_source(source)
        self.assertEqual(result["schema"], "milp-v1")
        self.assertNotIn("parameters", result)

    def test_supports_bounded_itertools_lambdas_and_tupledict_sum(self):
        source = '''
from itertools import combinations
import gurobipy as gp
from gurobipy import GRB
def solve_problem():
    pairs = list(combinations(range(3), 2))
    pairs.sort(key=lambda pair: (pair[1], pair[0]))
    m = gp.Model()
    x = m.addVars(range(3), range(2), vtype=GRB.BINARY, name="x")
    for i in range(3):
        m.addConstr(x.sum(i, "*") == 1)
    best = min(pairs, key=lambda pair: pair[0] + pair[1])
    m.setObjective(x[best[0], 0] + x[best[1], 1], GRB.MINIMIZE)
    m.optimize()
    return float(m.ObjVal)
'''
        model = compile_gurobi_function_source(source, "solve_problem", {})
        self.assertEqual(len(model["variables"]), 6)
        self.assertEqual(len(model["constraints"]), 3)

    def test_supports_minimal_numpy_linprog_surface_without_importing_numpy(self):
        source = '''
import numpy as np
from scipy.optimize import linprog
def solve_problem():
    costs = np.array([[2, 3], [4, 1]], dtype=float)
    rows = np.zeros((2, costs.size))
    rows[0, 0:2] = 1
    rows[1, 2:4] = 1
    result = linprog(c=costs.ravel(), A_eq=rows, b_eq=np.array([1, 1]),
                     bounds=(0, None), method="highs")
    allocation = result.x.reshape(costs.shape)
    return float(allocation[0, 0])
'''
        model = compile_gurobi_function_source(source, "solve_problem", {})
        self.assertEqual(len(model["variables"]), 4)
        self.assertEqual(len(model["constraints"]), 2)
        self.assertEqual(model["objective"]["coefficients"]["v000003"], 1.0)

    def test_itertools_output_limit_fails_closed(self):
        source = '''
import itertools
def solve_problem():
    return list(itertools.permutations(range(20), 10))
'''
        with self.assertRaisesRegex(RestrictedCodeError, "itertools output limit"):
            evaluate_restricted_function_source(source, "solve_problem", {})

    def test_supports_bounded_recursive_nonlocal_search(self):
        source = '''
def solve_problem():
    best = 100
    def search(value):
        nonlocal best
        if value < best:
            best = value
        if value > 0:
            search(value - 1)
    search(4)
    return best
'''
        self.assertEqual(
            evaluate_restricted_function_source(source, "solve_problem", {}), 0,
        )


if __name__ == "__main__":
    unittest.main()
