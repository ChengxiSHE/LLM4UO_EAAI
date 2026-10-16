"""Typed, answer-free RCPSP and VRPTW formulation skills.

The compilers consume only the common packet's public structured instance.
They implement the benchmark's declared formulation semantics and fail closed
on unknown, ambiguous, malformed, or over-budget inputs.
"""

from copy import deepcopy
import math

from .benchmark_inputs import validate_public_input
from .schema import canonical, digest
from .text2opt_template_compiler import _model, _row, _var


VERSION = "structured-or-skills-v1"
RESOURCE_CAPS = {
    "variables": 2000,
    "constraints": 10000,
    "nonzeros": 100000,
    "serialized_bytes": 4000000,
}

RCPSP_KEYS = frozenset({
    "budget", "deadlines", "mode_costs", "mode_durations",
    "mode_resource_requirements", "n_activities", "n_modes", "n_resources",
    "precedence_with_lags", "release_dates", "resource_capacities",
})
VRPTW_KEYS = frozenset({
    "customer_coordinates", "customer_demands", "depot_coordinates",
    "n_customers", "n_vehicles", "service_times", "time_windows",
    "vehicle_capacity", "vehicle_fixed_cost",
})


class StructuredSkillError(ValueError):
    """A typed route, semantic validation, or resource admission failure."""


def require(ok, code):
    if not ok:
        raise StructuredSkillError(code)


def copy_packet(packet):
    return deepcopy(packet)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _integer(value):
    return type(value) is int


def route_instance(data):
    require(type(data) is dict, "typed_route_zero")
    keys = set(data)
    matches = []
    if RCPSP_KEYS <= keys:
        matches.append("rcpsp")
    if VRPTW_KEYS <= keys:
        matches.append("vrptw")
    require(matches, "typed_route_zero")
    require(len(matches) == 1, "typed_route_multiple")
    return matches[0]


def _instance(packet):
    require(
        type(packet) is dict
        and type(packet.get("parameters")) is list
        and len(packet["parameters"]) == 1
        and type(packet["parameters"][0]) is dict
        and packet["parameters"][0].get("symbol") == "instance_data"
        and packet["parameters"][0].get("shape") == []
        and type(packet.get("instances")) is list
        and len(packet["instances"]) == 1
        and type(packet["instances"][0]) is dict
        and type(packet["instances"][0].get("input")) is dict
        and set(packet["instances"][0]["input"]) == {"instance_data"}
        and type(packet["instances"][0]["input"]["instance_data"]) is dict,
        "packet_contract",
    )
    public = validate_public_input(packet)
    require(
        len(public["parameters"]) == 1
        and public["parameters"][0].get("symbol") == "instance_data"
        and public["parameters"][0].get("shape") == []
        and len(public["instances"]) == 1
        and set(public["instances"][0]["input"]) == {"instance_data"}
        and type(public["instances"][0]["input"]["instance_data"]) is dict,
        "packet_contract",
    )
    return public["instances"][0]["input"]["instance_data"]


def route_packet(packet):
    return route_instance(_instance(packet))


def _rectangular(rows, outer, inner, predicate):
    return (
        type(rows) is list and len(rows) == outer
        and all(type(row) is list and len(row) == inner and all(predicate(x) for x in row)
                for row in rows)
    )


def _validate_rcpsp(data):
    require(set(data) == RCPSP_KEYS, "rcpsp_fields")
    n, modes, resources = data["n_activities"], data["n_modes"], data["n_resources"]
    require(_integer(n) and n > 0, "rcpsp_n_activities")
    require(_integer(modes) and modes > 0, "rcpsp_n_modes")
    require(_integer(resources) and resources > 0, "rcpsp_n_resources")
    require(_rectangular(data["mode_durations"], n, modes,
                         lambda x: _number(x) and x > 0), "rcpsp_mode_durations")
    require(_rectangular(data["mode_costs"], n, modes,
                         lambda x: _number(x) and x >= 0), "rcpsp_mode_costs")
    requirements = data["mode_resource_requirements"]
    require(type(requirements) is list and len(requirements) == n,
            "rcpsp_mode_resource_requirements")
    for activity in requirements:
        require(_rectangular(activity, modes, resources,
                             lambda x: _number(x) and x >= 0),
                "rcpsp_mode_resource_requirements")
    capacities = data["resource_capacities"]
    require(type(capacities) is list and len(capacities) == resources
            and all(_number(x) and x > 0 for x in capacities),
            "rcpsp_resource_capacities")
    releases = data["release_dates"]
    require(type(releases) is list and len(releases) == n
            and all(_number(x) and x >= 0 for x in releases), "rcpsp_release_dates")
    deadlines = data["deadlines"]
    require(type(deadlines) is list and len(deadlines) == n
            and all(x is None or (_number(x) and x >= 0) for x in deadlines),
            "rcpsp_deadlines")
    require(_number(data["budget"]) and data["budget"] >= 0, "rcpsp_budget")
    edges = data["precedence_with_lags"]
    require(type(edges) is list, "rcpsp_precedence")
    normalized = []
    seen = set()
    graph = [[] for _ in range(n)]
    for edge in edges:
        require(type(edge) is list and len(edge) == 4, "rcpsp_precedence")
        left, right, minimum, maximum = edge
        require(_integer(left) and _integer(right) and 0 <= left < n and 0 <= right < n
                and left != right and (left, right) not in seen,
                "rcpsp_precedence")
        require(_number(minimum) and minimum >= 0, "rcpsp_precedence")
        require(maximum is None or (_number(maximum) and
                (maximum == -1 or maximum >= minimum)), "rcpsp_precedence")
        seen.add((left, right)); graph[left].append(right)
        normalized.append((left, right, minimum, None if maximum == -1 else maximum))
    state = [0] * n
    def visit(node):
        require(state[node] != 1, "rcpsp_precedence_cycle")
        if state[node] == 2:
            return
        state[node] = 1
        for child in graph[node]:
            visit(child)
        state[node] = 2
    for node in range(n):
        visit(node)
    return {
        "n": n, "modes": modes, "resources": resources,
        "durations": data["mode_durations"], "costs": data["mode_costs"],
        "requirements": requirements, "capacities": capacities,
        "releases": releases, "deadlines": deadlines, "budget": data["budget"],
        "precedence": normalized,
    }


def _compile_rcpsp(data):
    data = _validate_rcpsp(data)
    n, modes, resources = data["n"], data["modes"], data["resources"]
    big_m = sum(max(row) for row in data["durations"]) + max(data["releases"]) + 10
    # The distributed structured view serializes a missing deadline as a large,
    # effectively non-binding number.  The benchmark formulation omits that
    # row; any deadline at or beyond the safe start-time upper bound is likewise
    # redundant and is normalized to the same typed absence state.
    deadlines = [None if value is None or value >= big_m else value
                 for value in data["deadlines"]]
    variables = [
        _var(f"start_{i}", f"activity {i} start", "time", "continuous",
             data["releases"][i], big_m) for i in range(n)
    ]
    variables.append(_var("makespan", "project completion", "time", "continuous", 0, big_m))
    for i in range(n):
        for mode in range(modes):
            variables.append(_var(f"mode_{i}_{mode}", f"activity {i} mode {mode}",
                                  "binary", "binary", 0, 1))
    constraints = []
    for i in range(n):
        constraints.append(_row(
            f"choose_mode_{i}", {f"mode_{i}_{mode}": 1 for mode in range(modes)}, "eq", 1,
        ))
    closure = [[False] * n for _ in range(n)]
    for left, right, minimum, maximum in data["precedence"]:
        closure[left][right] = True
        lower = {f"start_{left}": 1, f"start_{right}": -1}
        lower.update({f"mode_{left}_{mode}": data["durations"][left][mode]
                      for mode in range(modes)})
        constraints.append(_row(f"precedence_{left}_{right}", lower, "le", -minimum))
        if maximum is not None:
            upper = {f"start_{left}": -1, f"start_{right}": 1}
            upper.update({f"mode_{left}_{mode}": -data["durations"][left][mode]
                          for mode in range(modes)})
            constraints.append(_row(f"maxlag_{left}_{right}", upper, "le", maximum))
    for k in range(n):
        for i in range(n):
            for j in range(n):
                closure[i][j] = closure[i][j] or (closure[i][k] and closure[k][j])
    conflicts = []
    for i in range(n):
        for j in range(i + 1, n):
            if closure[i][j] or closure[j][i]:
                continue
            if any(data["requirements"][i][mi][r] + data["requirements"][j][mj][r]
                   > data["capacities"][r]
                   for mi in range(modes) for mj in range(modes) for r in range(resources)):
                conflicts.append((i, j))
    for i, j in conflicts:
        order = f"before_{i}_{j}"
        variables.append(_var(order, f"activity {i} before {j}", "binary", "binary", 0, 1))
        first = {f"start_{i}": 1, f"start_{j}": -1, order: big_m}
        first.update({f"mode_{i}_{mode}": data["durations"][i][mode]
                      for mode in range(modes)})
        constraints.append(_row(f"sequence_{i}_{j}", first, "le", big_m))
        second = {f"start_{j}": 1, f"start_{i}": -1, order: -big_m}
        second.update({f"mode_{j}_{mode}": data["durations"][j][mode]
                       for mode in range(modes)})
        constraints.append(_row(f"sequence_{j}_{i}", second, "le", 0))
    constraints.append(_row(
        "budget", {f"mode_{i}_{mode}": data["costs"][i][mode]
                   for i in range(n) for mode in range(modes)}, "le", data["budget"],
    ))
    for i, deadline in enumerate(deadlines):
        if deadline is not None:
            row = {f"start_{i}": 1}
            row.update({f"mode_{i}_{mode}": data["durations"][i][mode]
                        for mode in range(modes)})
            constraints.append(_row(f"deadline_{i}", row, "le", deadline))
    for i in range(n):
        row = {f"start_{i}": 1, "makespan": -1}
        row.update({f"mode_{i}_{mode}": data["durations"][i][mode]
                    for mode in range(modes)})
        constraints.append(_row(f"completion_{i}", row, "le", 0))
    return _model(variables, constraints, {"makespan": 1}, "min", "time")


def _validate_vrptw(data):
    require(set(data) == VRPTW_KEYS, "vrptw_fields")
    n, vehicles = data["n_customers"], data["n_vehicles"]
    require(_integer(n) and n > 0, "vrptw_n_customers")
    require(_integer(vehicles) and vehicles > 0, "vrptw_n_vehicles")
    require(_number(data["vehicle_capacity"]) and data["vehicle_capacity"] > 0,
            "vrptw_capacity")
    require(_number(data["vehicle_fixed_cost"]) and data["vehicle_fixed_cost"] >= 0,
            "vrptw_fixed_cost")
    require(type(data["depot_coordinates"]) is list and len(data["depot_coordinates"]) == 2
            and all(_number(x) for x in data["depot_coordinates"]), "vrptw_depot")
    require(_rectangular(data["customer_coordinates"], n, 2, _number),
            "vrptw_customer_coordinates")
    require(type(data["customer_demands"]) is list and len(data["customer_demands"]) == n
            and all(_number(x) and 0 < x <= data["vehicle_capacity"]
                    for x in data["customer_demands"]), "vrptw_customer_demands")
    require(type(data["service_times"]) is list and len(data["service_times"]) == n
            and all(_number(x) and x >= 0 for x in data["service_times"]),
            "vrptw_service_times")
    windows = data["time_windows"]
    require(_rectangular(windows, n + 1, 2, _number)
            and all(a <= b for a, b in windows), "vrptw_time_windows")
    require(windows[0][0] <= 0 <= windows[0][1], "vrptw_depot_time")
    return data


def _compile_vrptw(data):
    data = _validate_vrptw(data)
    n = data["n_customers"]
    nodes = list(range(n + 1)); customers = list(range(1, n + 1))
    coords = [data["depot_coordinates"]] + data["customer_coordinates"]
    distance = {(i, j): math.hypot(coords[i][0] - coords[j][0],
                                   coords[i][1] - coords[j][1])
                for i in nodes for j in nodes if i != j}
    big_m = data["time_windows"][0][1] + max(data["service_times"]) + max(distance.values()) + 1
    variables = []
    objective = {}
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            name = f"arc_{i}_{j}"
            variables.append(_var(name, f"travel arc {i} to {j}", "binary", "binary", 0, 1))
            objective[name] = distance[i, j] + (data["vehicle_fixed_cost"] if i == 0 else 0)
    for i in customers:
        variables.append(_var(f"load_{i}", f"load after customer {i}", "units", "continuous",
                              data["customer_demands"][i - 1], data["vehicle_capacity"]))
    for i in nodes:
        lower, upper = data["time_windows"][i]
        if i == 0:
            lower = upper = 0
        variables.append(_var(f"time_{i}", f"service start at node {i}", "time",
                              "continuous", lower, upper))
    constraints = []
    for i in customers:
        constraints.append(_row(f"visit_out_{i}",
                                {f"arc_{i}_{j}": 1 for j in nodes if j != i}, "eq", 1))
    for j in customers:
        constraints.append(_row(f"visit_in_{j}",
                                {f"arc_{i}_{j}": 1 for i in nodes if i != j}, "eq", 1))
    constraints.append(_row("vehicle_limit", {f"arc_0_{j}": 1 for j in customers},
                            "le", data["n_vehicles"]))
    capacity = data["vehicle_capacity"]
    for i in customers:
        for j in customers:
            if i == j:
                continue
            constraints.append(_row(
                f"load_link_{i}_{j}",
                {f"load_{i}": 1, f"load_{j}": -1, f"arc_{i}_{j}": capacity},
                "le", capacity - data["customer_demands"][j - 1],
            ))
    service = [0] + data["service_times"]
    for j in customers:
        for i in nodes:
            if i == j:
                continue
            constraints.append(_row(
                f"time_link_{i}_{j}",
                {f"time_{i}": 1, f"time_{j}": -1, f"arc_{i}_{j}": big_m},
                "le", big_m - service[i] - distance[i, j],
            ))
    return _model(variables, constraints, objective, "min", "distance plus deployment cost")


def compile_packet(packet):
    data = _instance(packet)
    route = route_instance(data)
    if route == "rcpsp":
        return route, _compile_rcpsp(data)
    return route, _compile_vrptw(data)


def _metrics(model):
    variables = model.get("variables")
    constraints = model.get("constraints")
    require(type(variables) is list and type(constraints) is list, "model_shape")
    variable_ids = [item.get("id") for item in variables]
    constraint_ids = [item.get("id") for item in constraints]
    require(all(type(name) is str and name for name in variable_ids)
            and len(variable_ids) == len(set(variable_ids)), "model_variables")
    require(all(type(name) is str and name for name in constraint_ids)
            and len(constraint_ids) == len(set(constraint_ids)), "model_constraints")
    known = set(variable_ids)
    require(set(model["objective"]["coefficients"]) <= known, "model_objective_reference")
    for row in constraints:
        require(type(row.get("coefficients")) is dict
                and set(row["coefficients"]) <= known
                and row.get("sense") in {"le", "ge", "eq"}
                and _number(row.get("rhs")), "model_constraint_reference")
    return {
        "variables": len(variables),
        "constraints": len(constraints),
        "nonzeros": sum(len(row["coefficients"]) for row in constraints),
        "serialized_bytes": len(canonical(model).encode("utf-8")),
    }


def compile_and_admit(packet):
    route, model = compile_packet(packet)
    metrics = _metrics(model)
    require(all(metrics[key] <= RESOURCE_CAPS[key] for key in RESOURCE_CAPS),
            "resource_admission")
    return {
        "schema": VERSION + "-admission",
        "route": route,
        "model": model,
        "model_sha256": digest(model),
        "metrics": metrics,
        "resource_caps": dict(RESOURCE_CAPS),
    }


__all__ = [
    "RESOURCE_CAPS", "VERSION", "compile_and_admit", "compile_packet",
    "copy_packet", "route_instance", "route_packet",
]
