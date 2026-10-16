"""Trusted public-text compilers for the six structured Text2Opt families.

The parsers consume only the distributed natural-language problem statement.
They recover the annex tables and instantiate standard, auditable MILP
templates.  No benchmark answer, upstream instance dictionary, or executable
model-generated code is available to this module.
"""
import ast
import itertools
import math
import re

from .benchmark_inputs import validate_public_input
from .gateway import Stopped


VERSION = "text2opt-template-compiler-v1"
NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"


def _number(value):
    value = float(value)
    return int(value) if value.is_integer() else value


def _one(pattern, text, flags=re.I):
    match = re.search(pattern, text, flags)
    if not match:
        raise Stopped("template_parse_missing:" + pattern[:48])
    return match.group(1)


def _list_after(label, text):
    raw = _one(re.escape(label) + r"[^\n]*:\s*(\[[^\n]+\])", text)
    value = ast.literal_eval(raw)
    if not isinstance(value, list) or not value:
        raise Stopped("template_parse_list")
    return [_number(x) for x in value]


def _var(name, meaning, unit, domain="continuous", lower=0, upper=None):
    return {"id": name, "meaning": meaning, "unit": unit, "domain": domain,
            "lower": lower, "upper": upper}


def _row(name, coefficients, sense, rhs):
    return {"id": name, "coefficients": {k: v for k, v in coefficients.items() if v},
            "sense": sense, "rhs": rhs}


def _model(variables, constraints, coefficients, sense="min", unit="objective units"):
    return {"schema": "milp-v1", "variables": variables, "constraints": constraints,
            "objective": {"coefficients": coefficients, "sense": sense, "unit": unit, "offset": 0}}


def parse_transportation(text):
    tail = text[text.lower().rfind("annex"):]
    vectors = re.findall(r"(?m)^\s*(\[[^\n]+\])\s*$", tail)
    if len(vectors) < 2:
        raise Stopped("transport_vectors_missing")
    supplies = [_number(x) for x in ast.literal_eval(vectors[0])]
    demands = [_number(x) for x in ast.literal_eval(vectors[1])]
    rows = {}
    for index, body in re.findall(r"(?m)^\s*S\s*(\d+)\s*\|\s*([^\n]+)$", tail):
        rows[int(index)] = [_number(x) for x in re.findall(NUM, body)]
    costs = [rows[i] for i in range(len(supplies))]
    if len(rows) != len(supplies) or any(len(row) != len(demands) for row in costs):
        raise Stopped("transport_matrix_shape")
    return {"supplies": supplies, "demands": demands, "costs": costs}


def compile_transportation(text):
    data = parse_transportation(text)
    supplies, demands, costs = data["supplies"], data["demands"], data["costs"]
    variables = []
    objective = {}
    for i in range(len(supplies)):
        for j in range(len(demands)):
            name = f"ship_{i}_{j}"
            variables.append(_var(name, f"shipment source {i} to destination {j}", "units"))
            objective[name] = costs[i][j]
    constraints = [
        _row(f"supply_{i}", {f"ship_{i}_{j}": 1 for j in range(len(demands))}, "le", supplies[i])
        for i in range(len(supplies))
    ] + [
        _row(f"demand_{j}", {f"ship_{i}_{j}": 1 for i in range(len(supplies))}, "eq", demands[j])
        for j in range(len(demands))
    ]
    return _model(variables, constraints, objective, "min", "transport cost")


def parse_jssp(text):
    jobs = int(_one(r"Number of jobs:\s*(\d+)", text))
    machines = int(_one(r"Number of machines[^:]*:\s*(\d+)", text))
    assignments = {}
    processing = {}
    for job, body in re.findall(r"(?m)^\s*-\s*Job\s+(\d+)\s*:\s*\[([^\n]+)\]", text):
        index = int(job)-1
        if re.search(r"Machine\s+\d+", body):
            assignments[index] = [int(x) for x in re.findall(r"Machine\s+(\d+)", body)]
        else:
            values = [int(x) for x in re.findall(r"Op\d+\s*:\s*(\d+)", body)]
            if values:
                processing[index] = values
    if set(assignments) != set(range(jobs)) or set(processing) != set(range(jobs)):
        raise Stopped("jssp_job_rows")
    if any(len(assignments[j]) != machines or len(processing[j]) != machines for j in range(jobs)):
        raise Stopped("jssp_operation_shape")
    return {"jobs": jobs, "machines": machines,
            "assignments": [assignments[j] for j in range(jobs)],
            "processing": [processing[j] for j in range(jobs)]}


def compile_jssp(text):
    data = parse_jssp(text)
    n, m = data["jobs"], data["machines"]
    processing, assignment = data["processing"], data["assignments"]
    # A serial schedule is always feasible and supplies a safe, public-data-only
    # upper bound.  Earliest/latest operation bounds then make each disjunction's
    # M no larger than necessary.  This formulation is markedly easier for the
    # bounded trusted solver than the otherwise equivalent time-indexed model.
    upper = sum(sum(row) for row in processing)
    earliest = {(j, o): sum(processing[j][:o]) for j in range(n) for o in range(m)}
    latest = {(j, o): upper - sum(processing[j][o:]) for j in range(n) for o in range(m)}
    variables = [
        _var(f"start_{j}_{o}", f"job {j} operation {o} start", "time",
             "continuous", earliest[j, o], latest[j, o])
        for j in range(n) for o in range(m)
    ]
    variables.append(_var(
        "makespan", "completion time of all jobs", "time", "continuous",
        max(sum(row) for row in processing), upper,
    ))
    constraints = []
    for j in range(n):
        for o in range(m-1):
            constraints.append(_row(
                f"precedence_{j}_{o}",
                {f"start_{j}_{o+1}": 1, f"start_{j}_{o}": -1},
                "ge", processing[j][o],
            ))
        constraints.append(_row(
            f"completion_{j}",
            {"makespan": 1, f"start_{j}_{m-1}": -1},
            "ge", processing[j][m-1],
        ))
    for machine in range(m):
        operations = [(j, o) for j in range(n) for o in range(m) if assignment[j][o] == machine]
        for left_index in range(len(operations)):
            a = operations[left_index]
            for b in operations[left_index + 1:]:
                y = f"before_{a[0]}_{a[1]}__{b[0]}_{b[1]}"
                variables.append(_var(y, f"operation {a} precedes {b}", "binary", "binary", 0, 1))
                mab = latest[a] + processing[a[0]][a[1]] - earliest[b]
                mba = latest[b] + processing[b[0]][b[1]] - earliest[a]
                constraints.append(_row(
                    "order_a_" + y,
                    {f"start_{b[0]}_{b[1]}": 1, f"start_{a[0]}_{a[1]}": -1, y: -mab},
                    "ge", processing[a[0]][a[1]] - mab,
                ))
                constraints.append(_row(
                    "order_b_" + y,
                    {f"start_{a[0]}_{a[1]}": 1, f"start_{b[0]}_{b[1]}": -1, y: mba},
                    "ge", processing[b[0]][b[1]],
                ))
    return _model(variables, constraints, {"makespan": 1}, "min", "time")


def _numbered_rows(section, prefix):
    rows = {}
    for index, body in re.findall(rf"(?m)^\s*{prefix}\s*(\d+)\s*\|\s*([^\n]+)$", section):
        rows[int(index)] = [_number(x) for x in re.findall(NUM, body)]
    return rows


def parse_disaster_response(text):
    demand_blocks = re.findall(
        r"Day\s+(\d+)\s+Demands:\s*(.*?)(?=Day\s+\d+\s+(?:Demands|Depot Supplies):|Transport Costs)",
        text, re.I | re.S,
    )
    supply_blocks = re.findall(
        r"Day\s+(\d+)\s+Depot Supplies:\s*(.*?)(?=Day\s+\d+\s+Depot Supplies:|Transport Costs)",
        text, re.I | re.S,
    )
    demands = {int(day): _numbered_rows(body, "U") for day, body in demand_blocks}
    supplies = {int(day): _numbered_rows(body, "D") for day, body in supply_blocks}
    if not demands:
        demands = {0: _numbered_rows(_one(
            r"Unit Demands[^:]*:\s*(.*?)(?=Depot Supplies)", text, re.I | re.S), "U")}
    if not supplies:
        supplies = {0: _numbered_rows(_one(
            r"Depot Supplies[^:]*:\s*(.*?)(?=Transport Costs)", text, re.I | re.S), "D")}
    transport_body = _one(r"Transport Costs\s*\(Depot x Unit\):\s*(.*?)(?=Risk Costs\s*\(Depot x Unit\))", text, re.I | re.S)
    risk_body = _one(r"Risk Costs\s*\(Depot x Unit\):\s*(.*?)(?=Penalty Costs per Unit Shortage)", text, re.I | re.S)
    transport = _numbered_rows(transport_body, "D")
    risk = _numbered_rows(risk_body, "D")
    penalty = [_number(x) for x in re.findall(r"Supply\s+S\d+\s*:\s*(" + NUM + r")",
                                               _one(r"Penalty Costs[^:]*:\s*\[([^\n]+)\]", text))]
    volume = [_number(x) for x in re.findall(r"Supply\s+S\d+\s*:\s*(" + NUM + r")",
                                              _one(r"Volume per Supply Unit:\s*\[([^\n]+)\]", text))]
    fleet = re.search(r"Fleet Parameters:\s*Cost\s*(%s),\s*Capacity\s*(%s),\s*Total\s*(\d+)" % (NUM, NUM), text, re.I)
    if not fleet or not demands or set(demands) != set(supplies):
        raise Stopped("disaster_dimensions")
    days = sorted(demands); units = sorted(demands[days[0]]); depots = sorted(supplies[days[0]])
    ns = len(demands[days[0]][units[0]])
    if days != list(range(len(days))) or units != list(range(len(units))) or depots != list(range(len(depots))):
        raise Stopped("disaster_indices")
    if len(penalty) != ns or len(volume) != ns:
        raise Stopped("disaster_supply_shape")
    if any(set(demands[t]) != set(units) or any(len(row) != ns for row in demands[t].values()) for t in days):
        raise Stopped("disaster_demand_shape")
    if any(set(supplies[t]) != set(depots) or any(len(row) != ns for row in supplies[t].values()) for t in days):
        raise Stopped("disaster_supply_shape")
    if set(transport) != set(depots) or set(risk) != set(depots) or any(
            len(transport[d]) != len(units) or len(risk[d]) != len(units) for d in depots):
        raise Stopped("disaster_cost_shape")
    return {"demands": demands, "supplies": supplies, "transport": transport, "risk": risk,
            "penalty": penalty, "volume": volume, "vehicle_cost": _number(fleet.group(1)),
            "vehicle_capacity": _number(fleet.group(2)), "total_vehicles": int(fleet.group(3))}


def compile_disaster_response(text, selected_days=None):
    data = parse_disaster_response(text)
    days = sorted(data["demands"]) if selected_days is None else list(selected_days)
    if not days or any(day not in data["demands"] for day in days):
        raise Stopped("disaster_day_selection")
    units = sorted(data["demands"][0]); depots = sorted(data["supplies"][0])
    supplies = range(len(data["penalty"])); variables = []; objective = {}; constraints = []
    for t in days:
        day_vehicle_bits = []
        for u in units:
            for s in supplies:
                name = f"short_{u}_{s}_{t}"
                variables.append(_var(name, f"unit {u} supply {s} shortage day {t}", "units"))
                objective[name] = data["penalty"][s]
        for d in depots:
            for u in units:
                route = f"vehicle_{d}_{u}_{t}_0"
                max_load = sum(min(data["supplies"][t][d][s], data["demands"][t][u][s]) * data["volume"][s]
                               for s in supplies)
                vehicle_upper = max(1, math.ceil(max_load / data["vehicle_capacity"] - 1e-12))
                vehicle_upper = min(data["total_vehicles"], vehicle_upper)
                vehicle_bits = [f"vehicle_{d}_{u}_{t}_{k}" for k in range(vehicle_upper)]
                day_vehicle_bits.extend(vehicle_bits)
                for k, vehicle in enumerate(vehicle_bits):
                    variables.append(_var(vehicle, f"vehicle {k+1} depot {d} unit {u} day {t}",
                                          "binary", "binary", 0, 1))
                    objective[vehicle] = data["vehicle_cost"] + (data["risk"][d][u] if k == 0 else 0)
                    if k:
                        constraints.append(_row(f"vehicle_order_{d}_{u}_{t}_{k}",
                                                {vehicle: 1, vehicle_bits[k-1]: -1}, "le", 0))
                for s in supplies:
                    flow = f"flow_{d}_{u}_{s}_{t}"
                    variables.append(_var(flow, f"supply {s} depot {d} unit {u} day {t}", "units"))
                    objective[flow] = data["transport"][d][u]
                load = {f"flow_{d}_{u}_{s}_{t}": data["volume"][s] for s in supplies}
                load.update({vehicle: -data["vehicle_capacity"] for vehicle in vehicle_bits})
                constraints.append(_row(f"vehicle_load_{d}_{u}_{t}", load, "le", 0))
                for s in supplies:
                    # A public-data-derived bound closes the fixed-charge LP
                    # relaxation without changing any feasible shipment.
                    bound = min(data["supplies"][t][d][s],
                                sum(data["demands"][t][uu][s] for uu in units))
                    constraints.append(_row(
                        f"flow_route_{d}_{u}_{s}_{t}",
                        {f"flow_{d}_{u}_{s}_{t}": 1, route: -bound}, "le", 0,
                    ))
        constraints.append(_row(f"fleet_{t}",
                                {name: 1 for name in day_vehicle_bits},
                                "le", data["total_vehicles"]))
        for d in depots:
            for s in supplies:
                constraints.append(_row(f"stock_{d}_{s}_{t}",
                                        {f"flow_{d}_{u}_{s}_{t}": 1 for u in units},
                                        "le", data["supplies"][t][d][s]))
        for u in units:
            for s in supplies:
                coefs = {f"flow_{d}_{u}_{s}_{t}": 1 for d in depots}; coefs[f"short_{u}_{s}_{t}"] = 1
                # Every term has a strictly positive objective coefficient, so
                # the upstream >= row is tight at every optimum.  Encoding the
                # equivalent equality removes a large, irrelevant relaxation.
                constraints.append(_row(f"demand_{u}_{s}_{t}", coefs, "eq", data["demands"][t][u][s]))
    return _model(variables, constraints, objective, "min", "operational cost")


def parse_facility(text):
    facilities = {int(i): (_number(x), _number(y)) for i, x, y in re.findall(
        rf"(?m)^\s*-\s*F(\d+)\s*:\s*\(({NUM}),\s*({NUM})\)", text
    )}
    customers = {int(i): (_number(x), _number(y)) for i, x, y in re.findall(
        rf"(?m)^\s*-\s*C(\d+)\s*:\s*\(({NUM}),\s*({NUM})\)", text
    )}
    capacities = [_number(x) for x in ast.literal_eval(_one(
        r"Facility capacities(?:\s*\(units\))?\s*:\s*(\[[^\n]+\])", text
    ))]
    demands = [_number(x) for x in ast.literal_eval(_one(
        r"Customer demands(?:\s*\(units\))?\s*:\s*(\[[^\n]+\])", text
    ))]
    fixed_match = re.search(r"Facility fixed[^:\n]*:\s*(\[[^\n]+\])", text, re.I)
    if not fixed_match:
        fixed_match = re.search(r"Fixed opening costs:\s*(\[[^\n]+\])", text, re.I)
    if not fixed_match:
        raise Stopped("facility_fixed_costs")
    fixed = [_number(x) for x in ast.literal_eval(fixed_match.group(1))]
    rate = _number(_one(r"Transport rate[^:]*:\s*\$?\s*(" + NUM + r")", text))
    if set(facilities) != set(range(len(capacities))) or set(customers) != set(range(len(demands))):
        raise Stopped("facility_coordinate_shape")
    if len(fixed) != len(capacities):
        raise Stopped("facility_vector_shape")
    modifiers = []
    match = re.search(r"(?:at most|no more than)\s+(\d+)\s+distribution centers", text, re.I)
    if match:
        modifiers.append(("max_open", int(match.group(1))))
    match = re.search(r"no distribution center may fulfill more than\s+(\d+(?:\.\d+)?)%", text, re.I)
    if match:
        modifiers.append(("demand_cap", float(match.group(1))))
    match = re.search(r"If\s+F(\d+)\s+is activated,\s*F(\d+)\s+must also be activated", text, re.I)
    if match:
        modifiers.append(("facility_linking", (int(match.group(1)), int(match.group(2)))))
    match = re.search(r"mutual exclusivity between F(\d+) and F(\d+)", text, re.I)
    if match:
        modifiers.append(("anti_affinity", (int(match.group(1)), int(match.group(2)))))
    match = re.search(r"Every opened facility must handle at least\s+(" + NUM + r")\s+units", text, re.I)
    if match:
        modifiers.append(("min_throughput", _number(match.group(1))))
    match = re.search(r"fixed activation costs[^\n]*must not exceed\s*\$?\s*(" + NUM + r")", text, re.I)
    if match:
        modifiers.append(("budget_cap", _number(match.group(1))))
    return {"facility_coordinates": [facilities[i] for i in range(len(facilities))],
            "customer_coordinates": [customers[i] for i in range(len(customers))],
            "capacities": capacities, "demands": demands, "fixed": fixed,
            "rate": rate, "modifiers": modifiers}


def compile_facility(text):
    data = parse_facility(text)
    nf, nc = len(data["capacities"]), len(data["demands"])
    variables = [_var(f"open_{i}", f"facility {i} active", "binary", "binary", 0, 1)
                 for i in range(nf)]
    objective = {f"open_{i}": data["fixed"][i] for i in range(nf)}
    for i in range(nf):
        x1, y1 = data["facility_coordinates"][i]
        for j in range(nc):
            name = f"ship_{i}_{j}"
            variables.append(_var(name, f"shipment facility {i} customer {j}", "units"))
            x2, y2 = data["customer_coordinates"][j]
            objective[name] = data["rate"] * math.hypot(x1-x2, y1-y2)
    constraints = [
        _row(f"demand_{j}", {f"ship_{i}_{j}": 1 for i in range(nf)}, "eq", data["demands"][j])
        for j in range(nc)
    ]
    for i in range(nf):
        coefficients = {f"ship_{i}_{j}": 1 for j in range(nc)}
        coefficients[f"open_{i}"] = -data["capacities"][i]
        constraints.append(_row(f"capacity_{i}", coefficients, "le", 0))
    total = sum(data["demands"])
    for kind, value in data["modifiers"]:
        if kind == "max_open":
            constraints.append(_row("max_open", {f"open_{i}": 1 for i in range(nf)}, "le", value))
        elif kind == "demand_cap":
            for i in range(nf):
                constraints.append(_row(
                    f"demand_cap_{i}", {f"ship_{i}_{j}": 1 for j in range(nc)},
                    "le", value / 100 * total,
                ))
        elif kind == "facility_linking":
            dependent, hub = value
            constraints.append(_row("facility_linking", {f"open_{dependent}": 1, f"open_{hub}": -1}, "le", 0))
        elif kind == "anti_affinity":
            a, b = value
            constraints.append(_row("anti_affinity", {f"open_{a}": 1, f"open_{b}": 1}, "le", 1))
        elif kind == "min_throughput":
            for i in range(nf):
                coefficients = {f"ship_{i}_{j}": 1 for j in range(nc)}
                coefficients[f"open_{i}"] = -value
                constraints.append(_row(f"min_throughput_{i}", coefficients, "ge", 0))
        elif kind == "budget_cap":
            constraints.append(_row("budget_cap", {f"open_{i}": data["fixed"][i] for i in range(nf)}, "le", value))
    return _model(variables, constraints, objective, "min", "total delivered cost")


def parse_vrptw(text):
    text = text[text.lower().rfind("annex"):]
    depot_match = re.search(r"Depot location(?:\s*\(coordinates\))?\s*:\s*\((%s),\s*(%s)\)" % (NUM, NUM), text, re.I)
    if not depot_match:
        raise Stopped("vrptw_depot")
    depot = (_number(depot_match.group(1)), _number(depot_match.group(2)))
    closing = _number(_one(r"Depot (?:latest return time(?:\s*\(closing time\))?|closing time(?:\s*\(latest return\))?)\s*:\s*(" + NUM + r")", text))
    location_block = _one(r"Customer Locations[^\n]*\n(.*?)(?=\s*-\s*[^\n]*Customer Demands)", text, re.I | re.S)
    demand_block = _one(r"Customer Demands[^\n]*\n(.*?)(?=\s*-\s*[^\n]*Customer Time Windows)", text, re.I | re.S)
    window_block = _one(r"Customer Time Windows[^\n]*\n(.*?)(?=\s*-\s*[^\n]*Service Times)", text, re.I | re.S)
    service_block = _one(r"Service Times[^\n]*\n(.*?)(?=\s*-\s*Vehicle capacity)", text, re.I | re.S)
    locations = {int(i): (_number(x), _number(y)) for i, x, y in re.findall(
        rf"C(\d+)\s*:\s*\(({NUM}),\s*({NUM})\)", location_block
    )}
    demands = {int(i): _number(v) for i, v in re.findall(rf"C(\d+)\s*:\s*({NUM})\s+units", demand_block)}
    windows = {int(i): (_number(a), _number(b)) for i, a, b in re.findall(
        rf"C(\d+)\s*:\s*\[({NUM}),\s*({NUM})\]", window_block
    )}
    service = {int(i): _number(v) for i, v in re.findall(rf"C(\d+)\s*:\s*({NUM})", service_block)}
    customers = sorted(locations)
    if customers != list(range(1, len(customers)+1)) or any(set(rows) != set(customers)
            for rows in (demands, windows, service)):
        raise Stopped("vrptw_customer_shape")
    return {"depot": depot, "closing": closing, "locations": locations, "demands": demands,
            "windows": windows, "service": service,
            "capacity": _number(_one(r"Vehicle capacity(?:\s*\(units\))?\s*:\s*(" + NUM + r")", text)),
            "vehicles": int(_one(r"Number of (?:identical )?vehicles available:\s*(\d+)", text)),
            "fixed": _number(_one(r"Fixed (?:deployment )?cost per vehicle(?: used)?(?:\s*\([^)]*\))?\s*:\s*(" + NUM + r")", text))}


def compile_vrptw(text):
    data = parse_vrptw(text); customers = sorted(data["locations"]); nodes = [0] + customers
    coords = {0: data["depot"], **data["locations"]}
    distance = {(i, j): math.hypot(coords[i][0]-coords[j][0], coords[i][1]-coords[j][1])
                for i in nodes for j in nodes if i != j}
    # Enumerate only routes that satisfy the public capacity and timing rules,
    # then solve an exact set-partitioning master problem.  Small benchmark
    # instances yield tens, rather than thousands, of columns and avoid the
    # weak big-M relaxation of an arc formulation.
    routes = []
    def extend(sequence, remaining, load, service_start):
        if sequence:
            last = sequence[-1]
            if service_start + data["service"][last] + distance[last, 0] <= data["closing"] + 1e-9:
                routes.append(tuple(sequence))
        last = sequence[-1] if sequence else 0
        departure = service_start + (data["service"][last] if sequence else 0)
        for customer in remaining:
            new_load = load + data["demands"][customer]
            if new_load > data["capacity"] + 1e-9:
                continue
            start = max(data["windows"][customer][0], departure + distance[last, customer])
            if start <= data["windows"][customer][1] + 1e-9:
                extend(sequence + [customer], [x for x in remaining if x != customer], new_load, start)
    extend([], customers, 0, 0)
    if not routes or len(routes) > 1999:
        raise Stopped("vrptw_route_enumeration_capacity")
    variables = []; objective = {}
    for index, route in enumerate(routes):
        name = f"route_{index}"
        variables.append(_var(name, "vehicle route " + "-".join(map(str, route)), "binary", "binary", 0, 1))
        path = (0,) + route + (0,)
        objective[name] = data["fixed"] + sum(distance[path[k], path[k+1]] for k in range(len(path)-1))
    constraints = [
        _row(f"visit_{customer}", {f"route_{index}": 1 for index, route in enumerate(routes)
                                    if customer in route}, "eq", 1)
        for customer in customers
    ]
    constraints.append(_row("vehicle_count", {f"route_{index}": 1 for index in range(len(routes))},
                            "le", data["vehicles"]))
    return _model(variables, constraints, objective, "min", "distance plus deployment cost")


def parse_rcpsp(text):
    text = text[text.lower().rfind("annex"):]
    n = int(_one(r"Number of activities:\s*(\d+)", text))
    nr = int(_one(r"Number of (?:renewable )?(?:resource types|resources):\s*(\d+)", text))
    nm = int(_one(r"(?:Modes|Number of execution modes) per activity:\s*(\d+)", text))
    capacities = {int(i)-1: _number(v) for i, v in re.findall(rf"Resource\s+(\d+)\s*:\s*({NUM})\s+units", text)}
    duration_block = _one(r"Execution Mode Durations[^\n]*\n(.*?)(?=\s*-\s*[^\n]*Resource Requirements per Mode)", text, re.I | re.S)
    durations = {}
    for activity, body in re.findall(r"Activity\s+(\d+)\s*:\s*\[([^\n]+)\]", duration_block):
        durations[int(activity)] = [_number(v) for _, v in re.findall(r"Mode\s+(\d+)\s*:\s*(" + NUM + r")", body)]
    requirement_block = _one(r"Resource Requirements per Mode[^\n]*\n(.*?)(?=\s*-\s*[^\n]*Execution Mode Costs)", text, re.I | re.S)
    requirements = {}
    for activity, mode, body in re.findall(r"Activity\s+(\d+),\s*Mode\s+(\d+)\s*:\s*\[([^\n]+)\]", requirement_block):
        requirements[int(activity), int(mode)-1] = [_number(v) for _, v in re.findall(r"R(\d+)\s*:\s*(" + NUM + r")", body)]
    cost_block = _one(r"Execution Mode Costs[^\n]*\n(.*?)(?=\s*-\s*(?:Total budget|Project budget))", text, re.I | re.S)
    costs = {}
    for activity, body in re.findall(r"Activity\s+(\d+)\s*:\s*\[([^\n]+)\]", cost_block):
        costs[int(activity)] = [_number(v) for _, v in re.findall(r"Mode\s+(\d+)\s*:\s*(" + NUM + r")", body)]
    precedence_block = _one(r"Precedence Dependencies[^\n]*\n(.*?)(?=\s*-\s*[^\n]*Earliest Start Times)", text, re.I | re.S)
    precedence = []
    for left, right, rest in re.findall(r"Activity\s+(\d+)\s*→\s*Activity\s+(\d+)([^\n]*)", precedence_block):
        minimum = re.search(r"min delay\s*=\s*(" + NUM + r")", rest, re.I)
        maximum = re.search(r"max delay\s*=\s*(" + NUM + r")", rest, re.I)
        precedence.append((int(left), int(right), _number(minimum.group(1)) if minimum else 0,
                           _number(maximum.group(1)) if maximum else None))
    release_block = _one(r"Earliest Start Times[^\n]*\n(.*?)(?=\s*-\s*[^\n]*Completion Deadlines)", text, re.I | re.S)
    releases = {int(i): _number(v) for i, v in re.findall(r"Activity\s+(\d+)\s*:\s*(" + NUM + r")", release_block)}
    deadline_block = text[text.lower().rfind("completion deadlines"):]
    deadlines = {}
    for i, body in re.findall(r"Activity\s+(\d+)\s*:\s*([^\n]+)", deadline_block):
        match = re.search(r"must finish by time\s*(" + NUM + r")", body, re.I)
        deadlines[int(i)] = _number(match.group(1)) if match else None
    if set(capacities) != set(range(nr)) or set(durations) != set(range(n)) or set(costs) != set(range(n)):
        raise Stopped("rcpsp_vector_shape")
    if set(releases) != set(range(n)) or set(deadlines) != set(range(n)):
        raise Stopped("rcpsp_timing_shape")
    if any(len(durations[i]) != nm or len(costs[i]) != nm for i in range(n)) or any(
            len(requirements.get((i, m), [])) != nr for i in range(n) for m in range(nm)):
        raise Stopped("rcpsp_mode_shape")
    return {"activities": n, "resources": nr, "modes": nm, "capacities": capacities,
            "durations": durations, "requirements": requirements, "costs": costs,
            "budget": _number(_one(r"(?:Total budget cap for mode selection|Total budget|Project budget(?: cap)?):\s*(" + NUM + r")", text)),
            "precedence": precedence, "releases": releases, "deadlines": deadlines}


def compile_rcpsp(text):
    data = parse_rcpsp(text); n = data["activities"]; nm = data["modes"]
    horizon = sum(max(data["durations"][i]) for i in range(n)) + max(data["releases"].values())
    variables = [_var(f"start_{i}", f"activity {i} start", "time", "continuous",
                      data["releases"][i], horizon) for i in range(n)]
    variables.append(_var("makespan", "project completion", "time", "continuous", 0, horizon))
    for i in range(n):
        for mode in range(nm):
            variables.append(_var(f"mode_{i}_{mode}", f"activity {i} mode {mode+1}", "binary", "binary", 0, 1))
    constraints = []
    for i in range(n):
        constraints.append(_row(f"choose_mode_{i}", {f"mode_{i}_{mode}": 1 for mode in range(nm)}, "eq", 1))
        completion = {"makespan": 1, f"start_{i}": -1}
        completion.update({f"mode_{i}_{mode}": -data["durations"][i][mode] for mode in range(nm)})
        constraints.append(_row(f"completion_{i}", completion, "ge", 0))
        if data["deadlines"][i] is not None:
            deadline = {f"start_{i}": 1}
            deadline.update({f"mode_{i}_{mode}": data["durations"][i][mode] for mode in range(nm)})
            constraints.append(_row(f"deadline_{i}", deadline, "le", data["deadlines"][i]))
    constraints.append(_row("budget", {f"mode_{i}_{mode}": data["costs"][i][mode]
                                        for i in range(n) for mode in range(nm)}, "le", data["budget"]))
    closure = [[False] * n for _ in range(n)]
    for left, right, minimum, maximum in data["precedence"]:
        closure[left][right] = True
        coefs = {f"start_{right}": 1, f"start_{left}": -1}
        coefs.update({f"mode_{left}_{mode}": -data["durations"][left][mode] for mode in range(nm)})
        constraints.append(_row(f"precedence_{left}_{right}", coefs, "ge", minimum))
        if maximum is not None:
            upper = {f"start_{right}": 1, f"start_{left}": -1}
            upper.update({f"mode_{left}_{mode}": -data["durations"][left][mode] for mode in range(nm)})
            constraints.append(_row(f"maxlag_{left}_{right}", upper, "le", maximum))
    for k in range(n):
        for i in range(n):
            for j in range(n):
                closure[i][j] = closure[i][j] or (closure[i][k] and closure[k][j])
    for i in range(n):
        for j in range(i+1, n):
            if closure[i][j] or closure[j][i]:
                continue
            conflict = any(data["requirements"][i, mi][r] + data["requirements"][j, mj][r] > data["capacities"][r]
                           for mi in range(nm) for mj in range(nm) for r in range(data["resources"]))
            if not conflict:
                continue
            order = f"before_{i}_{j}"
            variables.append(_var(order, f"activity {i} before {j}", "binary", "binary", 0, 1))
            # order=1 activates i before j; order=0 activates j before i.
            first = {f"start_{j}": 1, f"start_{i}": -1, order: -horizon}
            first.update({f"mode_{i}_{mode}": -data["durations"][i][mode] for mode in range(nm)})
            constraints.append(_row(f"sequence_{i}_{j}", first, "ge", -horizon))
            second = {f"start_{i}": 1, f"start_{j}": -1, order: horizon}
            second.update({f"mode_{j}_{mode}": -data["durations"][j][mode] for mode in range(nm)})
            constraints.append(_row(f"sequence_{j}_{i}", second, "ge", 0))
    return _model(variables, constraints, {"makespan": 1}, "min", "time")


def solve_jssp_exact(text, max_nodes=2_000_000):
    """Enumerate Giffler--Thompson active schedules with admissible bounds."""
    data = parse_jssp(text); n = data["jobs"]; m = data["machines"]
    assignment = data["assignments"]; processing = data["processing"]
    best = sum(map(sum, processing)); nodes = 0; memo = set()
    # Deterministic dispatch schedules provide a strong incumbent without any
    # answer access. n<=6 in the frozen small-instance cohort.
    for priority in itertools.permutations(range(n)):
        rank = {job: index for index, job in enumerate(priority)}
        next_op = [0] * n; job_ready = [0] * n; machine_ready = [0] * m
        while any(value < m for value in next_op):
            choices = []
            for job in range(n):
                operation = next_op[job]
                if operation < m:
                    machine = assignment[job][operation]
                    choices.append((max(job_ready[job], machine_ready[machine]), rank[job], job))
            start, _, job = min(choices); operation = next_op[job]; machine = assignment[job][operation]
            finish = start + processing[job][operation]
            job_ready[job] = finish; machine_ready[machine] = finish; next_op[job] += 1
        best = min(best, max(job_ready))

    def search(next_op, job_ready, machine_ready):
        nonlocal best, nodes
        nodes += 1
        if nodes > max_nodes:
            raise Stopped("jssp_exact_node_limit")
        lower = max(
            [0] + job_ready
            + [job_ready[j] + sum(processing[j][next_op[j]:]) for j in range(n)]
            + [machine_ready[k] + sum(
                processing[j][operation] for j in range(n) for operation in range(next_op[j], m)
                if assignment[j][operation] == k
            ) for k in range(m)]
        )
        if lower >= best:
            return
        if all(value == m for value in next_op):
            best = min(best, max(job_ready)); return
        key = (tuple(next_op), tuple(job_ready), tuple(machine_ready))
        if key in memo:
            return
        memo.add(key)
        available = []
        for job in range(n):
            operation = next_op[job]
            if operation < m:
                machine = assignment[job][operation]
                start = max(job_ready[job], machine_ready[machine])
                available.append((start + processing[job][operation], start, job, operation, machine))
        pivot = min(available)
        conflict = [item for item in available if item[4] == pivot[4] and item[1] < pivot[0]]
        for _, start, job, operation, machine in sorted(conflict, key=lambda item: (item[0], item[2])):
            new_next = next_op.copy(); new_jobs = job_ready.copy(); new_machines = machine_ready.copy()
            finish = start + processing[job][operation]
            new_next[job] += 1; new_jobs[job] = finish; new_machines[machine] = finish
            search(new_next, new_jobs, new_machines)

    search([0] * n, [0] * n, [0] * m)
    return {"status": "optimal", "objective": best, "certificate": "complete_active_schedule_enumeration",
            "search_nodes": nodes, "memo_states": len(memo), "algorithm": "giffler_thompson_branch_and_bound_v1"}


def solve_rcpsp_exact(text, max_nodes=2_000_000):
    """Exact mode enumeration and disjunctive-graph branch and bound."""
    data = parse_rcpsp(text); n = data["activities"]; nm = data["modes"]
    reach = [[False] * n for _ in range(n)]
    for left, right, _, _ in data["precedence"]:
        reach[left][right] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
    conflicts = []
    for i in range(n):
        for j in range(i+1, n):
            if reach[i][j] or reach[j][i]:
                continue
            if any(data["requirements"][i, mi][r] + data["requirements"][j, mj][r] > data["capacities"][r]
                   for mi in range(nm) for mj in range(nm) for r in range(data["resources"])):
                conflicts.append((i, j))
    best = math.inf; nodes = 0; feasible_mode_assignments = 0

    def propagate(edges, durations):
        starts = [float(data["releases"][i]) for i in range(n)]
        for _ in range(n):
            changed = False
            for left, right, weight in edges:
                value = starts[left] + weight
                if value > starts[right] + 1e-9:
                    starts[right] = value; changed = True
            if not changed:
                break
        else:
            return None  # positive cycle in lower-bound difference constraints
        if any(data["deadlines"][i] is not None
               and starts[i] + durations[i] > data["deadlines"][i] + 1e-9 for i in range(n)):
            return None
        return starts

    def branch(edges, durations):
        nonlocal best, nodes
        nodes += 1
        if nodes > max_nodes:
            raise Stopped("rcpsp_exact_node_limit")
        starts = propagate(edges, durations)
        if starts is None:
            return
        lower = max(starts[i] + durations[i] for i in range(n))
        if lower >= best - 1e-9:
            return
        choice = None; overlap = -1
        for i, j in conflicts:
            if starts[i] < starts[j] + durations[j] - 1e-9 and starts[j] < starts[i] + durations[i] - 1e-9:
                amount = min(starts[i] + durations[i], starts[j] + durations[j]) - max(starts[i], starts[j])
                if amount > overlap:
                    choice = (i, j); overlap = amount
        if choice is None:
            best = lower; return
        i, j = choice
        branch(edges + [(i, j, durations[i])], durations)
        branch(edges + [(j, i, durations[j])], durations)

    for modes in itertools.product(range(nm), repeat=n):
        if sum(data["costs"][i][modes[i]] for i in range(n)) > data["budget"] + 1e-9:
            continue
        feasible_mode_assignments += 1
        durations = [data["durations"][i][modes[i]] for i in range(n)]
        if max(data["releases"][i] + durations[i] for i in range(n)) >= best:
            continue
        edges = []
        for left, right, minimum, maximum in data["precedence"]:
            edges.append((left, right, durations[left] + minimum))
            if maximum is not None:
                edges.append((right, left, -(durations[left] + maximum)))
        branch(edges, durations)
    if not math.isfinite(best):
        return {"status": "infeasible", "objective": None, "certificate": "complete_mode_and_orientation_enumeration",
                "search_nodes": nodes, "feasible_mode_assignments": feasible_mode_assignments}
    return {"status": "optimal", "objective": best, "certificate": "complete_mode_and_orientation_enumeration",
            "search_nodes": nodes, "feasible_mode_assignments": feasible_mode_assignments,
            "conflict_pairs": len(conflicts), "algorithm": "disjunctive_graph_branch_and_bound_v1"}


def solve_template_problem(problem):
    """Reference-free trusted solve path selected only from public text."""
    from .milp_solver import execute
    public = validate_public_input(problem); text = public["text"]; family = detect_template_family(text)
    if family == "jssp":
        return solve_jssp_exact(text)
    if family == "rcpsp":
        return solve_rcpsp_exact(text)
    if family == "disaster_response":
        data = parse_disaster_response(text); parts = []
        for day in sorted(data["demands"]):
            solved = execute({"op": "solve", "model": compile_disaster_response(text, [day])},
                             wall_seconds=30,
                             limits={"solve_seconds": 20, "total_seconds": 24,
                                     "node_limit": 100000, "max_queries": 1})
            if solved.get("status") != "optimal":
                return {"status": solved.get("status", "unknown"), "objective": None,
                        "reason": "disaster_day_" + str(day) + "_" + solved.get("reason", "solve_failure")}
            parts.append(solved["objective"])
        return {"status": "optimal", "objective": math.fsum(parts),
                "certificate": "independent_day_milp_optima", "day_objectives": parts}
    return execute({"op": "solve", "model": compile_template_problem(public)}, wall_seconds=30,
                   limits={"solve_seconds": 20, "total_seconds": 24,
                           "node_limit": 100000, "max_queries": 1})


def detect_template_family(text):
    signatures = {
        "transportation": ("Cost Matrix", "Source\\Dest"),
        "jssp": ("Number of jobs:", "Machine Assignments", "Processing Times"),
        "disaster_response": ("Risk Costs (Depot x Unit)", "Fleet Parameters:", "Penalty Costs per Unit Shortage"),
        "modified_facility_location": ("Facility capacities", "Customer demands", "Transport rate"),
        "vrptw": ("Customer Time Windows", "Vehicle capacity", "Fixed", "cost per vehicle"),
        "rcpsp": ("Execution Mode Durations", "Resource Requirements per Mode", "Precedence Dependencies"),
    }
    matches = [family for family, phrases in signatures.items() if all(phrase.lower() in text.lower() for phrase in phrases)]
    if len(matches) != 1:
        raise Stopped("unsupported_or_ambiguous_text2opt_template_family")
    return matches[0]


def compile_template_problem(problem):
    public = validate_public_input(problem); family = detect_template_family(public["text"])
    if family == "transportation":
        return compile_transportation(public["text"])
    if family == "jssp":
        return compile_jssp(public["text"])
    if family == "disaster_response":
        return compile_disaster_response(public["text"])
    if family == "modified_facility_location":
        return compile_facility(public["text"])
    if family == "vrptw":
        return compile_vrptw(public["text"])
    if family == "rcpsp":
        return compile_rcpsp(public["text"])
    raise AssertionError("unreachable_template_family")


__all__ = [
    "VERSION", "compile_disaster_response", "compile_facility", "compile_jssp", "compile_rcpsp",
    "compile_template_problem", "compile_transportation", "compile_vrptw", "detect_template_family", "parse_disaster_response",
    "parse_facility", "parse_jssp", "parse_rcpsp", "parse_transportation", "parse_vrptw",
    "solve_jssp_exact", "solve_rcpsp_exact", "solve_template_problem",
]
