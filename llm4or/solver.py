"""Trusted LP kernel: shared variables, continuous domains, numerical certificates.

Public entry point uses a disposable process. No generated Python is executed.
On macOS limits are dimensions, single-thread kernels, CPU and wall time; this is
not an arbitrary-code sandbox or a hard RSS limit.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .schema import canonical, interface, model

TOL = 1e-7
ROOT = Path(__file__).resolve().parents[1]


def execute(operation, wall_seconds=40):
    if not 0 < wall_seconds <= 120:
        raise ValueError("solver wall limit outside allowed range")
    env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
           "MKL_NUM_THREADS": "1"}
    start = time.monotonic()
    try:
        run = subprocess.run([sys.executable, "-m", "llm4or.solver"],
                             input=canonical(operation), text=True, capture_output=True,
                             cwd=ROOT, env=env, timeout=wall_seconds)
        if run.returncode:
            return {"status": "unknown", "reason": "worker_failure", "returncode": run.returncode}
        result = json.loads(run.stdout)
    except subprocess.TimeoutExpired:
        result = {"status": "unknown", "reason": "wall_timeout"}
    result["wall_seconds"] = time.monotonic() - start
    return result


def matrices(m, order=None):
    order = order or sorted(v["id"] for v in m["variables"])
    rows, rhs, names = [], [], []

    def add(a, b, name):
        scale = max([abs(b)] + [abs(v) for v in a]) or 1.0
        rows.append([v / scale for v in a])
        rhs.append(b / scale)
        names.append(name)

    for row in m["constraints"]:
        a = [row["coefficients"][v] for v in order]
        if row["sense"] in {"le", "eq"}:
            add(a, row["rhs"], row["id"] + ":le")
        if row["sense"] in {"ge", "eq"}:
            add([-v for v in a], -row["rhs"], row["id"] + ":ge")
    for var in m["variables"]:
        for side, sign in (("upper", 1), ("lower", -1)):
            if var[side] is not None:
                a = [0.0] * len(order)
                a[order.index(var["id"])] = sign
                add(a, sign * var[side], var["id"] + ":" + side)
    return order, rows, rhs, names


def _lp(c, rows, rhs):
    from scipy.optimize import linprog
    result = linprog(c, A_ub=rows or None, b_ub=rhs or None,
                     bounds=[(None, None)] * len(c), method="highs",
                     options={"time_limit": 20, "primal_feasibility_tolerance": 1e-8,
                              "dual_feasibility_tolerance": 1e-8})
    status = {0: "optimal", 1: "limit", 2: "infeasible", 3: "unbounded",
              4: "numerical_error"}.get(result.status, "unknown")
    if not result.success:
        return {"status": status}
    x = result.x.tolist()
    if not _feasible(x, rows, rhs):
        return {"status": "numerical_error"}
    return {"status": "optimal", "point": x, "value": float(result.fun)}


def _feasible(x, rows, rhs):
    import math
    return all(math.isfinite(v) for v in x) and all(
        sum(a * v for a, v in zip(row, x)) - b <= TOL for row, b in zip(rows, rhs))


def solve(m):
    order, a, b, _ = matrices(m)
    obj = m["objective"]
    sign = 1 if obj["sense"] == "min" else -1
    c = [sign * obj["coefficients"][v] for v in order]
    result = _lp(c, a, b)
    if result["status"] == "optimal":
        result["objective"] = sign * result.pop("value") + obj["offset"]
        result["point"] = dict(zip(order, result["point"]))
    return result


def containment(source, target):
    order, sa, sb, _ = matrices(source)
    _, ta, tb, names = matrices(target, order)
    n = len(order)
    state = _lp([0] * n, sa, sb)
    if state["status"] != "optimal":
        return {"status": "unknown", "reason": "source_" + state["status"]}
    # Bound the whole domain before issuing an absence certificate. Do not
    # manufacture a box from an optimum or silently truncate an unbounded set.
    bounded = True
    for i in range(n):
        for sign in (-1, 1):
            c = [0] * n
            c[i] = sign
            r = _lp(c, sa, sb)
            if r["status"] != "optimal":
                bounded = False
    unknown_rows = []
    for row, b, name in zip(ta, tb, names):
        r = _lp([-v for v in row], sa, sb)
        if r["status"] != "optimal":
            unknown_rows.append({"row": name, "status": r["status"]})
            continue
        residual = sum(v * x for v, x in zip(row, r["point"])) - b
        if residual > TOL and _feasible(r["point"], sa, sb):
            return {"status": "witness", "point": dict(zip(order, r["point"])),
                    "violated_row": name, "normalized_residual": residual}
    if unknown_rows or not bounded:
        return {"status": "unknown", "reason": "unbounded_or_uncertified_domain",
                "unknown_rows": unknown_rows}
    return {"status": "contained_within_tolerance", "tolerance": TOL}


def preference(left, right):
    order, a, b, _ = matrices(left)
    _, ra, rb, _ = matrices(right, order)
    a, b = a + ra, b + rb
    n = len(order)
    ca = [left["objective"]["coefficients"][v] * (1 if left["objective"]["sense"] == "max" else -1) for v in order]
    cb = [right["objective"]["coefficients"][v] * (1 if right["objective"]["sense"] == "max" else -1) for v in order]
    ca = [v / (max(map(abs, ca)) or 1) for v in ca]
    cb = [v / (max(map(abs, cb)) or 1) for v in cb]
    rows = [r + [0] * (n + 1) for r in a] + [[0] * n + r + [0] for r in a]
    bounds = b + b
    rows += [[-v for v in ca] + ca + [1], cb + [-v for v in cb] + [1], [0] * (2*n) + [-1]]
    bounds += [0, 0, 0]
    r = _lp([0] * (2*n) + [-1], rows, bounds)
    if r["status"] != "optimal":
        return {"status": "unknown", "reason": r["status"]}
    eta = r["point"][-1]
    if eta > TOL:
        return {"status": "strict_reversal", "x": dict(zip(order, r["point"][:n])),
                "y": dict(zip(order, r["point"][n:2*n])), "normalized_margin": eta}
    return {"status": "no_strict_reversal_not_equivalence"}


def compare(left, right):
    if interface(left) != interface(right):
        return {"status": "unsupported", "reason": "business_interface_mismatch"}
    if left["objective"]["unit"] != right["objective"]["unit"]:
        return {"status": "unsupported", "reason": "objective_unit_mismatch"}
    return {"status": "compared", "left_to_right": containment(left, right),
            "right_to_left": containment(right, left), "preference": preference(left, right)}


def entails(m, clause):
    """Check a linear clause against the entire feasible set, including bounds."""
    from copy import deepcopy
    target = deepcopy(m)
    for var in target["variables"]:
        var["lower"], var["upper"] = None, None
    target["constraints"] = [clause]
    target = model(target)
    return containment(m, target)


def _worker():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    try:
        from .schema import loads, keys
        op = loads(sys.stdin.read(100_001))
        if op.get("op") == "solve":
            keys(op, {"op", "model"})
            out = solve(model(op["model"]))
        elif op.get("op") == "compare":
            keys(op, {"op", "left", "right"})
            out = compare(model(op["left"]), model(op["right"]))
        elif op.get("op") == "entails":
            keys(op, {"op", "model", "clause"})
            out = entails(model(op["model"]), op["clause"])
        else:
            raise ValueError("unsupported operation")
    except (ValueError, KeyError, TypeError, OverflowError):
        out = {"status": "invalid_input"}
    print(canonical(out))


if __name__ == "__main__":
    _worker()
