"""Trusted sparse MILP kernel, with numerical certificates and bounded workers.

Only validated structured linear models run. This is NOT an arbitrary-code
sandbox. macOS uses a sampled RSS watchdog, not a hard kernel memory limit.
"""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import warnings

from .schema import Invalid, canonical, keys
from .milp_schema import (MAX_OPERATION_BYTES, business_interface, effective_bounds,
                          loads, model)

ROOT = Path(__file__).resolve().parents[1]
FEAS_TOL = 1e-7
INTEGER_TOL = 1e-6
OPT_TOL = 1e-7
DEFAULT_LIMITS = {"solve_seconds": 10.0, "total_seconds": 25.0, "node_limit": 10000, "max_queries": 128}


def _limits(limits):
    keys(limits, DEFAULT_LIMITS)
    for key, maximum in (("solve_seconds", 20), ("total_seconds", 110)):
        if type(limits[key]) not in (int, float) or not math.isfinite(limits[key]) or not 0 < limits[key] <= maximum:
            raise Invalid("invalid solver time budget")
    for key, maximum in (("node_limit", 100000), ("max_queries", 256)):
        if type(limits[key]) is not int or not 1 <= limits[key] <= maximum:
            raise Invalid("invalid node/query budget")
    return dict(limits)


class _Budget:
    def __init__(self, limits):
        self.limits = _limits(limits)
        self.deadline = time.monotonic() + limits["total_seconds"]
        self.queries = 0

    def claim(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or self.queries >= self.limits["max_queries"]:
            return None
        self.queries += 1
        return min(remaining, self.limits["solve_seconds"])


def _point_check(m, point):
    variables = {v["id"]: v for v in m["variables"]}
    if not isinstance(point, dict) or set(point) != set(variables):
        return {"feasible": False, "reason": "point_interface"}
    if any(type(x) not in (float, int) or abs(x) > 1e12 or not math.isfinite(x) for x in point.values()):
        return {"feasible": False, "reason": "point_numerical_range"}
    scaled = integer_error = 0.0
    try:
        for name, var in variables.items():
            x = point[name]
            lower, upper = effective_bounds(var)
            if lower is not None:
                scaled = max(scaled, (lower - x) / max(1, abs(lower)))
            if upper is not None:
                scaled = max(scaled, (x - upper) / max(1, abs(upper)))
            if var["domain"] != "continuous":
                integer_error = max(integer_error, abs(x - round(x)))
        for row in m["constraints"]:
            value = math.fsum(a * point[k] for k, a in row["coefficients"].items())
            residual = value - row["rhs"]
            if row["sense"] == "ge": residual = -residual
            if row["sense"] == "eq": residual = abs(residual)
            scale = max([1, abs(row["rhs"])] + [abs(a) for a in row["coefficients"].values()])
            scaled = max(scaled, residual / scale)
    except (OverflowError, ValueError):
        return {"feasible": False, "reason": "point_numerical_range"}
    return {"feasible": scaled <= FEAS_TOL and integer_error <= INTEGER_TOL,
            "max_scaled_violation": scaled, "max_integer_violation": integer_error,
            "feasibility_tolerance": FEAS_TOL, "integer_tolerance": INTEGER_TOL}


def check_point(value, point):
    """Independent arithmetic check, with no solver or reference answer access."""
    return _point_check(model(value), point)


def _interpret(m, c, raw, order):
    code = int(raw.status)
    status = {0: "optimal", 1: "limit", 2: "infeasible", 3: "unbounded", 4: "unknown"}.get(code, "unknown")
    out = {"status": status, "solver_status_code": code, "message": str(raw.message)[:500],
           "point": None, "value_min": None, "bound_min": None,
           "reported_mip_gap": None, "mip_node_count": None}
    for source, dest in (("mip_dual_bound", "bound_min"), ("mip_gap", "reported_mip_gap"), ("mip_node_count", "mip_node_count")):
        val = getattr(raw, source, None)
        if val is not None and math.isfinite(float(val)):
            out[dest] = float(val) if dest != "mip_node_count" else int(val)
    x = getattr(raw, "x", None)
    if x is not None:
        point = dict(zip(order, map(float, x)))
        check = _point_check(m, point) if len(x) == len(order) else {"feasible": False}
        out["point_check"] = check
        if check["feasible"]:
            value = math.fsum(c.get(k, 0) * point[k] for k in order)
            fun = getattr(raw, "fun", None)
            if fun is None or not math.isfinite(float(fun)) or not math.isclose(value, float(fun), abs_tol=OPT_TOL, rel_tol=OPT_TOL):
                out.update(status="numerical_error", reason="objective_recheck_failed", bound_min=None)
                return out
            out.update(point=point, value_min=value)
        else:
            out.update(status="numerical_error", reason="incumbent_recheck_failed", bound_min=None)
            return out
    if code == 0:
        if out["point"] is None or not bool(raw.success):
            out.update(status="numerical_error", reason="optimal_without_valid_incumbent", bound_min=None)
            return out
        # Continuous LPs do not expose mip_dual_bound; status 0 supplies a
        # numerical optimality certificate, never an exact symbolic proof.
        if out["bound_min"] is None:
            if any(v["domain"] != "continuous" for v in m["variables"]):
                out.update(status="unknown", reason="missing_mip_dual_bound")
                return out
            out["bound_min"] = out["value_min"]
        gap = out["value_min"] - out["bound_min"]
        tolerance = OPT_TOL * max(1, abs(out["value_min"]), abs(out["bound_min"]))
        if abs(gap) > tolerance:
            out.update(status="limit" if gap > 0 else "numerical_error", reason="optimality_bound_not_closed")
            if gap < 0: out["bound_min"] = None
    elif code == 2 and out["point"] is not None:
        out.update(status="numerical_error", reason="infeasible_with_feasible_incumbent", bound_min=None)
    if out["status"] not in {"optimal", "limit"}:
        out["bound_min"] = None
    if out["point"] is not None and out["bound_min"] is not None:
        tolerance = OPT_TOL * max(1, abs(out["value_min"]), abs(out["bound_min"]))
        if out["bound_min"] > out["value_min"] + tolerance:
            out.update(status="numerical_error", reason="invalid_dual_bound", bound_min=None)
    return out


def _optimize(m, budget, c=None, *, presolve=True):
    seconds = budget.claim()
    if seconds is None:
        return {"status": "limit", "reason": "query_or_time_budget", "point": None, "bound_min": None}
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_array
    order = sorted(v["id"] for v in m["variables"])
    index = {name: i for i, name in enumerate(order)}
    c = c if c is not None else {k: (1 if m["objective"]["sense"] == "min" else -1) * a
                                for k, a in m["objective"]["coefficients"].items()}
    by_id = {v["id"]: v for v in m["variables"]}
    lower, upper, integral = [], [], []
    for name in order:
        v = by_id[name]; lo, hi = effective_bounds(v)
        if lo is not None and hi is not None and (lo > hi or (v["domain"] != "continuous" and math.ceil(lo) > math.floor(hi))):
            return {"status": "infeasible", "reason": "empty_variable_domain", "point": None, "bound_min": None}
        lower.append(-np.inf if lo is None else lo); upper.append(np.inf if hi is None else hi)
        integral.append(int(v["domain"] != "continuous"))
    ri, ci, av, bl, bu = [], [], [], [], []
    for i, row in enumerate(m["constraints"]):
        for name, a in row["coefficients"].items():
            if a:
                ri.append(i); ci.append(index[name]); av.append(a)
        bl.append(row["rhs"] if row["sense"] in {"ge", "eq"} else -np.inf)
        bu.append(row["rhs"] if row["sense"] in {"le", "eq"} else np.inf)
    constraints = None
    if bl:
        matrix = coo_array((np.array(av, dtype=float), (np.array(ri, dtype=np.int32), np.array(ci, dtype=np.int32))),
                           shape=(len(bl), len(order))).tocsc()
        constraints = LinearConstraint(matrix, bl, bu)
    options = {"disp": False, "presolve": presolve, "time_limit": seconds, "node_limit": budget.limits["node_limit"],
               "mip_rel_gap": 0.0, "mip_abs_gap": 0.0, "threads": 1,
               "mip_feasibility_tolerance": FEAS_TOL,
               "primal_feasibility_tolerance": FEAS_TOL, "dual_feasibility_tolerance": FEAS_TOL}
    with warnings.catch_warnings():
        # SciPy forwards these fixed HiGHS options but warns they are not in its
        # short public whitelist. No user-supplied options are forwarded.
        warnings.filterwarnings("ignore", message="Unrecognized options detected.*", category=RuntimeWarning)
        raw = milp(np.array([c.get(k, 0) for k in order], dtype=float), integrality=integral,
                   bounds=Bounds(lower, upper), constraints=constraints, options=options)
    if presolve and raw.status == 4 and "unbounded or infeasible" in str(raw.message).lower():
        # A charged second solve may disambiguate HiGHS' presolve status; no
        # translation of that ambiguous status into an infeasibility label.
        retry = _optimize(m, budget, c, presolve=False)
        retry["presolve_disambiguation"] = True
        return retry
    return _interpret(m, c, raw, order)


def _solve(m, budget):
    raw = _optimize(m, budget)
    sign = 1 if m["objective"]["sense"] == "min" else -1
    offset = m["objective"]["offset"]
    out = {**raw, "objective": None, "incumbent_objective": None, "objective_bound": None,
           "bound_direction": "lower" if sign == 1 else "upper", "objective_unit": m["objective"]["unit"],
           "objective_sense": m["objective"]["sense"], "certificate_scope": "numerical_solver_status_and_rechecked_incumbent"}
    if raw.get("value_min") is not None:
        out["incumbent_objective"] = sign * raw["value_min"] + offset
        if raw["status"] == "optimal": out["objective"] = out["incumbent_objective"]
    if raw.get("bound_min") is not None:
        out["objective_bound"] = sign * raw["bound_min"] + offset
    if out["incumbent_objective"] is not None and out["objective_bound"] is not None:
        out["absolute_gap"] = abs(out["incumbent_objective"] - out["objective_bound"])
    out.pop("value_min", None); out.pop("bound_min", None)
    return out


def _inequalities(m):
    for row in m["constraints"]:
        for sign, label in ((1, "le"), (-1, "ge")):
            if row["sense"] not in {label, "eq"}: continue
            yield ({k: sign * a for k, a in row["coefficients"].items()}, sign * row["rhs"], row["id"] + ":" + label)
    for var in m["variables"]:
        lo, hi = effective_bounds(var)
        if lo is not None: yield ({var["id"]: -1}, -lo, var["id"] + ":lower")
        if hi is not None: yield ({var["id"]: 1}, hi, var["id"] + ":upper")


def _fresh_id(m, base):
    names = {v["id"] for v in m["variables"]}
    while base in names: base += "_"
    return base


def _domain_query(source, target_var, budget):
    # max d, k+d <= x_j <= k+1-d, k integral, 0<=d<=1/2.
    # A positive d provides a fractional source-feasible decision. No LP
    # relaxation of the source's OTHER integer variables is performed.
    m = deepcopy(source); j = target_var["id"]
    k = _fresh_id(m, "audit_floor")
    m["variables"].append({"id": k, "meaning": "internal floor", "unit": "1", "domain": "integer", "lower": None, "upper": None})
    d = _fresh_id(m, "audit_fraction")
    m["variables"].append({"id": d, "meaning": "internal fractional margin", "unit": "1", "domain": "continuous", "lower": 0, "upper": 0.5})
    m["constraints"] += [{"id": "audit_domain_lo", "coefficients": {j: -1, k: 1, d: 1}, "sense": "le", "rhs": 0},
                          {"id": "audit_domain_hi", "coefficients": {j: 1, k: -1, d: 1}, "sense": "le", "rhs": 1}]
    raw = _optimize(m, budget, {d: -1})
    if raw.get("point") is not None:
        point = {v["id"]: raw["point"][v["id"]] for v in source["variables"]}
        if (_point_check(source, point)["feasible"] and abs(point[j] - round(point[j])) > INTEGER_TOL):
            return {"status": "witness", "kind": "integrality", "variable": j, "point": point}
    if raw.get("bound_min") is not None and -raw["bound_min"] <= FEAS_TOL:
        return {"status": "domain_contained_within_tolerance"}
    return {"status": "unknown", "reason": "integrality_not_certified", "solver_status": raw["status"]}


def _containment(source, target, budget):
    state = _optimize(source, budget, {})
    if state.get("point") is None:
        return {"status": "unknown", "reason": "source_" + state["status"]}
    if not _point_check(target, state["point"])["feasible"]:
        return {"status": "witness", "kind": "feasibility", "point": state["point"]}
    uncertain = []; checked = 0
    by_id = {v["id"]: v for v in source["variables"]}
    for var in target["variables"]:
        if var["domain"] != "continuous" and by_id[var["id"]]["domain"] == "continuous":
            result = _domain_query(source, var, budget)
            if result["status"] == "witness": return result
            if result["status"] == "unknown": uncertain.append(result)
    for a, b, name in _inequalities(target):
        raw = _optimize(source, budget, {k: -v for k, v in a.items()})
        scale = max([1, abs(b)] + [abs(v) for v in a.values()])
        if raw.get("point") is not None:
            residual = (math.fsum(v * raw["point"][k] for k, v in a.items()) - b) / scale
            if residual > FEAS_TOL and _point_check(source, raw["point"])["feasible"]:
                return {"status": "witness", "kind": "constraint_or_bound", "point": raw["point"],
                        "violated_row": name, "scaled_residual": residual}
        upper = None if raw.get("bound_min") is None else (-raw["bound_min"] - b) / scale
        if upper is None or upper > FEAS_TOL:
            uncertain.append({"row": name, "status": raw["status"], "violation_upper_bound": upper})
        checked += 1
        if raw.get("reason") == "query_or_time_budget":
            return {"status": "unknown", "reason": "query_or_time_budget", "checked_rows": checked,
                    "uncertain_checks": uncertain[:32]}
    if uncertain:
        return {"status": "unknown", "reason": "uncertified_checks", "uncertain_checks": uncertain[:32]}
    return {"status": "contained_within_tolerance", "checked_rows": checked,
            "certificate": "global_MILP_bounds_for_every_target_inequality_and_required_domain_query",
            "tolerance": FEAS_TOL}


def _preference(left, right, budget):
    # Two decisions in the intersection. Domain intersection uses integer if
    # either model requires it; intrinsic binary bounds become explicit rows.
    variables = []; rows = []
    lvars = {v["id"]: v for v in left["variables"]}; rvars = {v["id"]: v for v in right["variables"]}
    for prefix in ("decision_x_", "decision_y_"):
        for name, lv in lvars.items():
            v = deepcopy(lv); v["id"] = prefix + name
            v.update(lower=None, upper=None, domain="integer" if lv["domain"] != "continuous" or rvars[name]["domain"] != "continuous" else "continuous")
            variables.append(v)
        for source in (left, right):
            for a, b, _ in _inequalities(source):
                rows.append({"id": "row_" + str(len(rows)), "coefficients": {prefix + k: val for k, val in a.items()}, "sense": "le", "rhs": b})
    eta = "audit_eta"
    variables.append({"id": eta, "meaning": "preference margin", "unit": "1", "domain": "continuous", "lower": 0, "upper": None})
    for source, first, second in ((left, "decision_x_", "decision_y_"), (right, "decision_y_", "decision_x_")):
        obj = source["objective"]; sign = 1 if obj["sense"] == "max" else -1
        scale = max([abs(v) for v in obj["coefficients"].values()] + [1])
        coefs = {eta: 1}
        for k, v in obj["coefficients"].items():
            coefs[first + k] = -sign * v / scale; coefs[second + k] = sign * v / scale
        rows.append({"id": "row_" + str(len(rows)), "coefficients": coefs, "sense": "le", "rhs": 0})
    m = {"variables": variables, "constraints": rows}
    raw = _optimize(m, budget, {eta: -1})
    if raw.get("point") is not None and raw["point"][eta] > FEAS_TOL:
        x = {k: raw["point"]["decision_x_" + k] for k in lvars}; y = {k: raw["point"]["decision_y_" + k] for k in lvars}
        gains = []
        for source, first, second in ((left, x, y), (right, y, x)):
            obj = source["objective"]; sign = 1 if obj["sense"] == "max" else -1
            scale = max([abs(v) for v in obj["coefficients"].values()] + [1])
            gains.append(sign * math.fsum(v * (first[k] - second[k]) for k, v in obj["coefficients"].items()) / scale)
        if all(_point_check(s, p)["feasible"] for s in (left, right) for p in (x, y)) and min(gains) > FEAS_TOL:
            return {"status": "strict_reversal", "x": x, "y": y, "normalized_margin": min(gains)}
    return {"status": "no_strict_reversal_not_equivalence" if raw["status"] == "optimal" else "unknown",
            "solver_status": raw["status"]}


def _compare(left, right, budget):
    if business_interface(left) != business_interface(right):
        return {"status": "unsupported", "reason": "business_interface_mismatch"}
    if left["objective"]["unit"] != right["objective"]["unit"]:
        return {"status": "unsupported", "reason": "objective_unit_mismatch"}
    return {"status": "compared", "left_to_right": _containment(left, right, budget),
            "right_to_left": _containment(right, left, budget), "preference": _preference(left, right, budget)}


def _dispatch(operation, limits):
    if not isinstance(operation, dict): raise Invalid("operation object")
    budget = _Budget(limits)
    if operation.get("op") == "solve":
        keys(operation, {"op", "model"}); out = _solve(model(operation["model"]), budget)
    elif operation.get("op") == "compare":
        keys(operation, {"op", "left", "right"})
        out = _compare(model(operation["left"]), model(operation["right"]), budget)
    else:
        raise Invalid("unsupported operation")
    out["solver_queries"] = budget.queries
    return out


def _worker():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    try:
        envelope = loads(sys.stdin.read(MAX_OPERATION_BYTES + 1), MAX_OPERATION_BYTES)
        keys(envelope, {"operation", "limits"})
        # Some HiGHS builds emit C-level diagnostics to stdout even with
        # ``disp=False``.  Stdout is the worker's single JSON protocol channel;
        # route native solver chatter to stderr and flush it before restoring
        # the protocol descriptor.
        saved_stdout = os.dup(1)
        try:
            os.dup2(2, 1)
            out = _dispatch(envelope["operation"], _limits(envelope["limits"]))
            try:
                import ctypes
                ctypes.CDLL(None).fflush(None)
            except (AttributeError, OSError):
                pass
        finally:
            os.dup2(saved_stdout, 1)
            os.close(saved_stdout)
        import scipy
        from scipy.optimize._highspy._core import HIGHS_VERSION_MAJOR, HIGHS_VERSION_MINOR, HIGHS_VERSION_PATCH
        out["solver_version"] = {"scipy": scipy.__version__, "highs": f"{HIGHS_VERSION_MAJOR}.{HIGHS_VERSION_MINOR}.{HIGHS_VERSION_PATCH}"}
    except (Invalid, ValueError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        out = {"status": "invalid_input", "reason": type(exc).__name__}
    print(canonical(out))


def execute(operation, *, wall_seconds=30, rss_mb=512, limits=None):
    """Run a trusted worker with no inherited credentials and bounded resources."""
    if type(wall_seconds) not in (int, float) or not math.isfinite(wall_seconds) or not 0 < wall_seconds <= 120:
        raise ValueError("wall time outside allowed range")
    if type(rss_mb) is not int or not 32 <= rss_mb <= 1024:
        raise ValueError("RSS threshold outside allowed range")
    limits = _limits(DEFAULT_LIMITS if limits is None else limits)
    try:
        encoded = canonical({"operation": operation, "limits": limits})
        if len(encoded.encode()) > MAX_OPERATION_BYTES: raise Invalid("operation size limit")
    except (ValueError, TypeError, RecursionError, OverflowError):
        return {"status": "invalid_input", "reason": "operation_serialization"}
    import psutil
    env = {"PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin", "LANG": "C.UTF-8",
           "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    launcher = f"import sys; sys.path.insert(0, {str(ROOT)!r}); from llm4or.milp_solver import _worker; _worker()"
    started = time.monotonic(); peak_rss = 0
    with tempfile.TemporaryDirectory(prefix="llm4or-milp-") as work:
        proc = subprocess.Popen([sys.executable, "-I", "-c", launcher], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                cwd=work, env=env, start_new_session=True)
        monitor = psutil.Process(proc.pid); first = True; reason = None
        while True:
            try:
                peak_rss = max(peak_rss, monitor.memory_info().rss)
            except psutil.NoSuchProcess:
                pass
            if peak_rss > rss_mb * 1024**2: reason = "rss_limit"
            if time.monotonic() - started >= wall_seconds: reason = "wall_timeout"
            if reason:
                try: os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                proc.communicate()
                result = {"status": "limit", "reason": reason}
                break
            try:
                stdout, stderr = proc.communicate(input=encoded if first else None, timeout=min(0.05, wall_seconds))
                if proc.returncode:
                    result = {"status": "unknown", "reason": "worker_failure", "returncode": proc.returncode}
                else:
                    try: result = loads(stdout, MAX_OPERATION_BYTES)
                    except Invalid: result = {"status": "unknown", "reason": "invalid_worker_output"}
                break
            except subprocess.TimeoutExpired:
                first = False
    result.update(wall_seconds=time.monotonic() - started, peak_rss_bytes_sampled=peak_rss,
                  resource_scope="trusted_numeric_worker; CPU60s; sampled_RSS; hard_AS_1GiB_on_Linux_only",
                  configured_limits={**limits, "wall_seconds": wall_seconds, "rss_mb": rss_mb})
    return result
