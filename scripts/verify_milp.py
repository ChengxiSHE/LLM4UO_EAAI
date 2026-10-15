"""Cross-check the MILP kernel against exact enumeration on synthetic models.

The oracle enumerates the integer and binary coordinates and eliminates ONE
continuous variable with Fraction arithmetic. It never calls any solver.
This is engineering verification, not a benchmark or an LLM experiment.
"""
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.milp_solver import execute, check_point


def oracle(m):
    best = None
    for x, b in itertools.product(range(5), range(2)):
        lo, hi = Fraction(0), Fraction(5)
        for row in m["constraints"]:
            a = row["coefficients"]
            residual = Fraction(row["rhs"] - a.get("x", 0)*x - a.get("b", 0)*b)
            slope = Fraction(a.get("z", 0))
            signs = [1, -1] if row["sense"] == "eq" else [1] if row["sense"] == "le" else [-1]
            for sign in signs:
                c, rhs = sign*slope, sign*residual
                if c > 0: hi = min(hi, rhs/c)
                elif c < 0: lo = max(lo, rhs/c)
                elif rhs < 0: lo, hi = Fraction(1), Fraction(0)
        if lo > hi: continue
        obj = m["objective"]; a = obj["coefficients"]
        minimize = obj["sense"] == "min"
        z = lo if (a.get("z", 0) >= 0) == minimize else hi
        value = a.get("x", 0)*x + a.get("b", 0)*b + a.get("z", 0)*z + obj["offset"]
        if best is None or (value < best if minimize else value > best): best = value
    return best


def main():
    rng = random.Random(20260831)
    cases = []
    for i in range(24):
        m = {"schema": "milp-v1", "variables": [
            {"id": "x", "meaning": "synthetic integer quantity", "unit": "1", "domain": "integer", "lower": 0, "upper": 4},
            {"id": "b", "meaning": "synthetic binary choice", "unit": "1", "domain": "binary", "lower": None, "upper": None},
            {"id": "z", "meaning": "synthetic continuous quantity", "unit": "1", "domain": "continuous", "lower": 0, "upper": 5}],
            "constraints": [{"id": f"r{j}", "coefficients": {k: rng.randint(-3, 3) for k in ["x", "b", "z"]},
                             "sense": rng.choice(["le", "le", "ge", "eq"]), "rhs": rng.randint(-3, 12)} for j in range(3)],
            "objective": {"coefficients": {k: rng.randint(-4, 4) for k in ["x", "b", "z"]},
                          "sense": "min" if i % 2 else "max", "unit": "synthetic_units", "offset": rng.randint(-5, 5)}}
        expected = oracle(m)
        result = execute({"op": "solve", "model": m})
        if expected is None:
            passed = result["status"] == "infeasible"
        else:
            passed = (result["status"] == "optimal"
                      and math.isclose(result["objective"], float(expected), rel_tol=1e-7, abs_tol=1e-7)
                      and check_point(m, result["point"])["feasible"])
        cases.append({"id": f"synthetic_{i:02d}", "model": m,
                      "oracle": {"status": "infeasible" if expected is None else "optimal",
                                 "exact_objective": None if expected is None else str(expected)},
                      "solver": result, "passed": bool(passed)})
    report = {"status": "passed" if all(c["passed"] for c in cases) else "failed", "seed": 20260831,
              "cases": cases, "total": len(cases), "passed": sum(c["passed"] for c in cases),
              "oracle": "Full enumeration of integer/binary coordinates plus exact rational elimination of one continuous variable",
              "optimal_cases": sum(c["oracle"]["status"] == "optimal" for c in cases),
              "infeasible_cases": sum(c["oracle"]["status"] == "infeasible" for c in cases),
              "actual_model_api_calls": 0, "benchmark_performance_claim": False}
    (ROOT / "results/milp_oracle_verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["status", "total", "passed", "optimal_cases", "infeasible_cases", "actual_model_api_calls"]}))
    if report["status"] != "passed": raise SystemExit(1)


if __name__ == "__main__": main()
