"""Compile a typed RetailOpt short decision into a Gurobi model.

This is a first-party implementation of the public RetailOpt specification.  It
does not load the upstream reference solver or reference objectives.  Both
experimental arms use this exact compiler; only their short decisions differ.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

from .retailopt190_knowledge import gold_decision, parse_decision


class RetailCompileError(ValueError):
    pass


def _number(value: Any, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise RetailCompileError(reason)
    return float(value)


def _mapping(value: Any, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RetailCompileError(reason)
    return value


def _sequence(value: Any, reason: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise RetailCompileError(reason)
    return value


def validate_data(data: Mapping[str, Any]) -> None:
    required = {
        "cold_capacity", "cold_usage", "constraints", "costs", "demand_curve",
        "demand_share", "labor_cap", "labor_usage", "lead_time", "locations",
        "name", "network", "periods", "production_cap", "products", "return_rate",
        "shelf_life",
    }
    if not isinstance(data, Mapping) or set(data) != required | ({"description"} if "description" in data else set()):
        raise RetailCompileError("data_keys")
    periods = data["periods"]
    if isinstance(periods, bool) or not isinstance(periods, int) or periods <= 0:
        raise RetailCompileError("periods")
    products = _sequence(data["products"], "products")
    locations = _sequence(data["locations"], "locations")
    if len(set(products)) != len(products) or len(set(locations)) != len(locations) or not all(isinstance(x, str) and x for x in products + locations):
        raise RetailCompileError("entity_identity")
    for key in (
        "cold_capacity", "cold_usage", "constraints", "costs", "demand_curve",
        "demand_share", "labor_cap", "labor_usage", "lead_time", "network",
        "production_cap", "return_rate", "shelf_life",
    ):
        _mapping(data[key], key)


def compile_model(
    data: Mapping[str, Any],
    decision_value: Mapping[str, Any],
    selected_skill_ids: Iterable[str],
    *,
    time_limit_seconds: float = 60.0,
    mip_gap: float = 0.01,
    output_flag: int = 0,
):
    """Return a Gurobi model defined by one validated short decision."""

    validate_data(data)
    selected = tuple(selected_skill_ids)
    answers = parse_decision(decision_value, selected)
    defaults = gold_decision(selected)
    answer = lambda key: answers.get(key, defaults.get(key))
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as exc:
        raise RetailCompileError("gurobipy_unavailable") from exc

    T = int(data["periods"])
    products = list(data["products"])
    locations = list(data["locations"])
    shelf_life = {p: int(data["shelf_life"][p]) for p in products}
    if any(value <= 0 for value in shelf_life.values()):
        raise RetailCompileError("shelf_life")
    lead_time = {p: int(data["lead_time"].get(p, 0) or 0) for p in products}
    constraints = data["constraints"]
    costs = data["costs"]
    network = data["network"]
    sub_edges = [tuple(edge) for edge in network.get("sub_edges", [])]
    trans_edges = [tuple(edge) for edge in network.get("trans_edges", [])]
    if any(len(edge) != 2 or edge[0] not in products or edge[1] not in products for edge in sub_edges):
        raise RetailCompileError("sub_edges")
    if any(len(edge) != 2 or edge[0] not in locations or edge[1] not in locations for edge in trans_edges):
        raise RetailCompileError("trans_edges")

    moq = _number(constraints.get("moq", 0) or 0, "moq")
    pack_size = int(constraints.get("pack_size", 1) or 1)
    budget = constraints.get("budget_per_period")
    waste_limit = constraints.get("waste_limit_pct")
    fixed_cost = _number(costs.get("fixed_order", 0) or 0, "fixed_order")
    trans_cost = _number(costs.get("transshipment", 0) or 0, "transshipment_cost")

    model = gp.Model("retail_short_decision")
    model.Params.OutputFlag = int(output_flag)
    model.Params.Threads = 1
    model.Params.Seed = 0
    model.Params.TimeLimit = float(time_limit_seconds)
    model.Params.MIPGap = float(mip_gap)

    integer_orders = answer("pack_size") == "order_is_integer" and pack_size > 1
    Q: dict[tuple[str, str, int], Any] = {}
    z: dict[tuple[str, str, int], Any] = {}
    n: dict[tuple[str, str, int], Any] = {}
    I: dict[tuple[str, str, int, int], Any] = {}
    y: dict[tuple[str, str, int, int], Any] = {}
    W: dict[tuple[str, str, int], Any] = {}
    L: dict[tuple[str, str, int], Any] = {}
    X: dict[tuple[str, str, str, int], Any] = {}
    S: dict[tuple[str, str, str, int], Any] = {}
    for p in products:
        for l in locations:
            for t in range(1, T + 1):
                Q[p, l, t] = model.addVar(lb=0.0, vtype=GRB.INTEGER if integer_orders else GRB.CONTINUOUS, name=f"Q_{p}_{l}_{t}")
                if pack_size > 1 and not integer_orders:
                    n[p, l, t] = model.addVar(lb=0.0, vtype=GRB.INTEGER, name=f"n_{p}_{l}_{t}")
                if moq > 0 or fixed_cost > 0:
                    z[p, l, t] = model.addVar(vtype=GRB.BINARY, name=f"z_{p}_{l}_{t}")
                for r in range(1, shelf_life[p] + 1):
                    I[p, l, t, r] = model.addVar(lb=0.0, name=f"I_{p}_{l}_{t}_{r}")
                    y[p, l, t, r] = model.addVar(lb=0.0, name=f"y_{p}_{l}_{t}_{r}")
                W[p, l, t] = model.addVar(lb=0.0, name=f"W_{p}_{l}_{t}")
                L[p, l, t] = model.addVar(lb=0.0, name=f"L_{p}_{l}_{t}")
    for p in products:
        for src, dst in trans_edges:
            for t in range(1, T + 1):
                X[p, src, dst, t] = model.addVar(lb=0.0, name=f"X_{p}_{src}_{dst}_{t}")
    for p_from, p_to in sub_edges:
        for l in locations:
            for t in range(1, T + 1):
                S[p_from, p_to, l, t] = model.addVar(lb=0.0, name=f"S_{p_from}_{p_to}_{l}_{t}")
    model.update()

    big_m = 1_000_000.0
    activation = answer("order_activation")
    pack_choice = answer("pack_size")
    for p in products:
        for l in locations:
            for t in range(1, T + 1):
                if pack_size > 1:
                    if pack_choice == "order_equals_pack_size_times_nonnegative_integer":
                        model.addConstr(Q[p, l, t] == pack_size * n[p, l, t])
                    elif pack_choice == "order_at_least_pack_size":
                        model.addConstr(Q[p, l, t] >= pack_size)
                    elif pack_choice != "order_is_integer":
                        raise RetailCompileError("pack_choice")
                if (p, l, t) in z:
                    if activation in ("lower_and_upper_link", "upper_link_only"):
                        model.addConstr(Q[p, l, t] <= big_m * z[p, l, t])
                    if moq > 0 and activation in ("lower_and_upper_link", "lower_link_only"):
                        model.addConstr(Q[p, l, t] >= moq * z[p, l, t])

    lead_choice = answer("lead_time") or "arrives_in_period_s_plus_lead_time"

    def arrival(p: str, l: str, t: int):
        lag = lead_time[p]
        if lead_choice == "arrives_in_period_s_plus_lead_time":
            order_period = t - lag
        elif lead_choice == "arrives_same_period":
            order_period = t
        elif lead_choice == "arrives_in_period_s_minus_lead_time":
            order_period = t + lag
        else:
            raise RetailCompileError("lead_time_choice")
        return Q[p, l, order_period] if 1 <= order_period <= T else 0.0

    trans_choice = answer("transshipment") or "incoming_minus_outgoing"

    def trans_net(p: str, l: str, t: int):
        incoming = gp.quicksum(X[p, src, l, t] for src, dst in trans_edges if dst == l)
        outgoing = gp.quicksum(X[p, l, dst, t] for src, dst in trans_edges if src == l)
        if trans_choice == "incoming_minus_outgoing":
            return incoming - outgoing
        if trans_choice == "incoming_only":
            return incoming
        if trans_choice == "outgoing_minus_incoming":
            return outgoing - incoming
        raise RetailCompileError("transshipment_choice")

    returns_choice = answer("returns") or "previous_period_sales_times_return_rate"

    def returns(p: str, l: str, t: int):
        rate = _number(data["return_rate"].get(p, 0) or 0, "return_rate")
        if rate == 0:
            return 0.0
        if returns_choice == "previous_period_sales_times_return_rate":
            if t <= 1:
                return 0.0
            return rate * gp.quicksum(y[p, l, t - 1, r] for r in range(1, shelf_life[p] + 1))
        if returns_choice == "same_period_sales_times_return_rate":
            return rate * gp.quicksum(y[p, l, t, r] for r in range(1, shelf_life[p] + 1))
        if returns_choice == "previous_period_orders_times_return_rate":
            return rate * (Q[p, l, t - 1] if t > 1 else 0.0)
        raise RetailCompileError("returns_choice")

    fresh_choice = answer("fresh_inflow")
    aging_choice = answer("aging")
    waste_choice = answer("waste")
    for p in products:
        sl = shelf_life[p]
        for l in locations:
            for r in range(1, sl):
                model.addConstr(I[p, l, 1, r] == 0.0)
            for t in range(1, T + 1):
                base = arrival(p, l, t) + trans_net(p, l, t) + returns(p, l, t)
                if fresh_choice == "arrivals_net_transshipment_lagged_returns_only":
                    fresh = base
                elif fresh_choice == "arrivals_plus_prior_inventory":
                    fresh = base + (gp.quicksum(I[p, l, t - 1, r] for r in range(1, sl + 1)) if t > 1 else 0.0)
                elif fresh_choice == "arrivals_minus_current_sales":
                    fresh = base - gp.quicksum(y[p, l, t, r] for r in range(1, sl + 1))
                else:
                    raise RetailCompileError("fresh_inflow_choice")
                model.addConstr(I[p, l, t, sl] == fresh)
                for r in range(1, sl + 1):
                    model.addConstr(y[p, l, t, r] <= I[p, l, t, r])
                if waste_choice == "oldest_bucket_residual_after_sales":
                    model.addConstr(W[p, l, t] == I[p, l, t, 1] - y[p, l, t, 1])
                elif waste_choice == "all_unsold_inventory":
                    model.addConstr(W[p, l, t] == gp.quicksum(I[p, l, t, r] - y[p, l, t, r] for r in range(1, sl + 1)))
                elif waste_choice == "lost_sales":
                    model.addConstr(W[p, l, t] == L[p, l, t])
                else:
                    raise RetailCompileError("waste_choice")
            for t in range(1, T):
                for r in range(1, sl):
                    if aging_choice == "shift_after_sales_from_fresher_bucket":
                        rhs = I[p, l, t, r + 1] - y[p, l, t, r + 1]
                    elif aging_choice == "shift_before_sales":
                        rhs = I[p, l, t, r + 1]
                    elif aging_choice == "copy_same_bucket_after_sales":
                        rhs = I[p, l, t, r] - y[p, l, t, r]
                    else:
                        raise RetailCompileError("aging_choice")
                    model.addConstr(I[p, l, t + 1, r] == rhs)

    demand: dict[tuple[str, str, int], float] = {}
    total_demand = 0.0
    for p in products:
        curve = list(data["demand_curve"][p])
        if not curve:
            raise RetailCompileError("demand_curve")
        if len(curve) < T:
            curve.extend([curve[-1]] * (T - len(curve)))
        for l in locations:
            share = _number(data["demand_share"].get(l, 1 / len(locations)), "demand_share")
            for t in range(1, T + 1):
                value = _number(curve[t - 1], "demand_curve") * share
                demand[p, l, t] = value
                total_demand += value

    direction = answer("substitution_direction") or "from_demand_is_fulfilled_by_to_inventory"
    if direction == "from_demand_is_fulfilled_by_to_inventory":
        outgoing_edges = {p: [q for left, q in sub_edges if left == p] for p in products}
        incoming_edges = {p: [q for q, right in sub_edges if right == p] for p in products}
        outbound_expr = lambda p, l, t: gp.quicksum(S[p, q, l, t] for q in outgoing_edges[p])
        inbound_expr = lambda p, l, t: gp.quicksum(S[q, p, l, t] for q in incoming_edges[p])
    elif direction == "from_inventory_fulfills_to_demand":
        outgoing_edges = {p: [q for q, right in sub_edges if right == p] for p in products}
        incoming_edges = {p: [q for left, q in sub_edges if left == p] for p in products}
        outbound_expr = lambda p, l, t: gp.quicksum(S[q, p, l, t] for q in outgoing_edges[p])
        inbound_expr = lambda p, l, t: gp.quicksum(S[p, q, l, t] for q in incoming_edges[p])
    else:
        raise RetailCompileError("substitution_direction_choice")

    demand_choice = answer("demand_balance")
    cap_choice = answer("substitution_demand_cap") or "total_outbound_no_more_than_original_demand"
    binding_choice = answer("substitution_inventory_binding") or "total_inbound_no_more_than_actual_sales_of_receiving_product"
    for p in products:
        for l in locations:
            for t in range(1, T + 1):
                sales = gp.quicksum(y[p, l, t, r] for r in range(1, shelf_life[p] + 1))
                outbound = outbound_expr(p, l, t)
                inbound = inbound_expr(p, l, t)
                if cap_choice == "total_outbound_no_more_than_original_demand":
                    model.addConstr(outbound <= demand[p, l, t])
                elif cap_choice == "each_edge_no_more_than_total_inventory":
                    for q in outgoing_edges[p]:
                        expression = S[p, q, l, t] if (p, q, l, t) in S else S[q, p, l, t]
                        model.addConstr(expression <= gp.quicksum(I[p, l, t, r] for r in range(1, shelf_life[p] + 1)))
                elif cap_choice != "unbounded":
                    raise RetailCompileError("substitution_cap_choice")
                if demand_choice == "sales_plus_lost_equals_original_plus_inbound_minus_outbound":
                    model.addConstr(sales + L[p, l, t] == demand[p, l, t] + inbound - outbound)
                elif demand_choice == "sales_plus_lost_equals_original":
                    model.addConstr(sales + L[p, l, t] == demand[p, l, t])
                elif demand_choice == "sales_equals_original_plus_outbound":
                    model.addConstr(sales == demand[p, l, t] + outbound)
                else:
                    raise RetailCompileError("demand_balance_choice")
                if binding_choice == "total_inbound_no_more_than_actual_sales_of_receiving_product":
                    model.addConstr(inbound <= sales)
                elif binding_choice == "inbound_no_more_than_lost_sales":
                    model.addConstr(inbound <= L[p, l, t])
                elif binding_choice != "no_inventory_binding":
                    raise RetailCompileError("substitution_binding_choice")

    capacity_choice = answer("production_capacity")
    labor_choice = answer("labor_capacity") or "actual_sales"
    budget_choice = answer("budget") or "purchase_cost_times_orders_plus_active_fixed_order_costs"
    for t in range(1, T + 1):
        for p in products:
            caps = list(data["production_cap"][p])
            capacity = _number(caps[t - 1] if t <= len(caps) else caps[-1], "production_cap")
            if capacity_choice == "delivered_inflow_aggregated_over_locations":
                use = gp.quicksum(arrival(p, l, t) for l in locations)
            elif capacity_choice == "orders_placed_same_period":
                use = gp.quicksum(Q[p, l, t] for l in locations)
            elif capacity_choice == "sales":
                use = gp.quicksum(y[p, l, t, r] for l in locations for r in range(1, shelf_life[p] + 1))
            else:
                raise RetailCompileError("production_capacity_choice")
            model.addConstr(use <= capacity)
        for l in locations:
            if labor_choice == "actual_sales":
                labor = gp.quicksum(_number(data["labor_usage"].get(p, 0) or 0, "labor_usage") * gp.quicksum(y[p, l, t, r] for r in range(1, shelf_life[p] + 1)) for p in products)
            elif labor_choice == "orders_placed":
                labor = gp.quicksum(_number(data["labor_usage"].get(p, 0) or 0, "labor_usage") * Q[p, l, t] for p in products)
            elif labor_choice == "start_inventory":
                labor = gp.quicksum(_number(data["labor_usage"].get(p, 0) or 0, "labor_usage") * gp.quicksum(I[p, l, t, r] for r in range(1, shelf_life[p] + 1)) for p in products)
            else:
                raise RetailCompileError("labor_choice")
            caps = list(data["labor_cap"][l])
            model.addConstr(labor <= _number(caps[t - 1] if t <= len(caps) else caps[-1], "labor_cap"))
            cold = gp.quicksum(_number(data["cold_usage"].get(p, 0) or 0, "cold_usage") * gp.quicksum(I[p, l, t, r] for r in range(1, shelf_life[p] + 1)) for p in products)
            model.addConstr(cold <= _number(data["cold_capacity"][l], "cold_capacity"))
        if budget is not None:
            if budget_choice == "purchase_cost_times_orders_plus_active_fixed_order_costs":
                spend = gp.quicksum(Q[p, l, t] * _number(costs["purchasing"].get(p, 0) or 0, "purchasing") for p in products for l in locations)
                if fixed_cost and z:
                    spend += gp.quicksum(fixed_cost * z[p, l, t] for p in products for l in locations if (p, l, t) in z)
            elif budget_choice == "purchase_cost_times_arrivals":
                spend = gp.quicksum(arrival(p, l, t) * _number(costs["purchasing"].get(p, 0) or 0, "purchasing") for p in products for l in locations)
            elif budget_choice == "sales_revenue":
                spend = gp.quicksum(gp.quicksum(y[p, l, t, r] for r in range(1, shelf_life[p] + 1)) for p in products for l in locations)
            else:
                raise RetailCompileError("budget_choice")
            model.addConstr(spend <= _number(budget, "budget"))

    waste_choice_limit = answer("waste_limit") or "total_waste_over_horizon_le_fraction_of_total_demand"
    if waste_limit is not None:
        fraction = _number(waste_limit, "waste_limit")
        if waste_choice_limit == "total_waste_over_horizon_le_fraction_of_total_demand":
            model.addConstr(gp.quicksum(W[p, l, t] for p in products for l in locations for t in range(1, T + 1)) <= fraction * total_demand)
        elif waste_choice_limit == "each_period_waste_le_fraction_of_period_demand":
            for t in range(1, T + 1):
                period_demand = sum(demand[p, l, t] for p in products for l in locations)
                model.addConstr(gp.quicksum(W[p, l, t] for p in products for l in locations) <= fraction * period_demand)
        elif waste_choice_limit == "waste_cost_le_fraction_of_purchase_cost":
            model.addConstr(gp.quicksum(_number(costs["waste"].get(p, 0) or 0, "waste_cost") * W[p, l, t] for p in products for l in locations for t in range(1, T + 1)) <= fraction * gp.quicksum(_number(costs["purchasing"].get(p, 0) or 0, "purchasing") * Q[p, l, t] for p in products for l in locations for t in range(1, T + 1)))
        else:
            raise RetailCompileError("waste_limit_choice")

    holding_choice = answer("holding_cost")
    purchase_choice = answer("purchase_cost")
    fixed_choice = answer("fixed_order_cost") or "once_per_active_product_location_period"
    objective = gp.LinExpr()
    for p in products:
        buy = _number(costs["purchasing"].get(p, 0) or 0, "purchasing")
        hold = _number(costs["inventory"].get(p, 0) or 0, "inventory_cost")
        waste_cost = _number(costs["waste"].get(p, 0) or 0, "waste_cost")
        lost_cost = _number(costs["lost_sales"].get(p, 0) or 0, "lost_cost")
        for l in locations:
            for t in range(1, T + 1):
                if purchase_choice == "orders_placed":
                    objective += buy * Q[p, l, t]
                elif purchase_choice == "delivered_arrivals":
                    objective += buy * arrival(p, l, t)
                elif purchase_choice == "sales":
                    objective += buy * gp.quicksum(y[p, l, t, r] for r in range(1, shelf_life[p] + 1))
                else:
                    raise RetailCompileError("purchase_cost_choice")
                if holding_choice == "post_sales_nonexpiring_inventory":
                    objective += hold * gp.quicksum(I[p, l, t, r] - y[p, l, t, r] for r in range(2, shelf_life[p] + 1))
                elif holding_choice == "all_start_inventory":
                    objective += hold * gp.quicksum(I[p, l, t, r] for r in range(1, shelf_life[p] + 1))
                elif holding_choice == "fresh_arrivals":
                    objective += hold * I[p, l, t, shelf_life[p]]
                else:
                    raise RetailCompileError("holding_cost_choice")
                objective += waste_cost * W[p, l, t] + lost_cost * L[p, l, t]
                if fixed_cost and (p, l, t) in z:
                    if fixed_choice == "once_per_active_product_location_period":
                        objective += fixed_cost * z[p, l, t]
                    elif fixed_choice == "per_ordered_unit":
                        objective += fixed_cost * Q[p, l, t]
                    elif fixed_choice == "once_per_product_over_horizon":
                        if t == 1:
                            objective += fixed_cost * z[p, l, t]
                    else:
                        raise RetailCompileError("fixed_cost_choice")
    if trans_edges and trans_cost:
        objective += trans_cost * gp.quicksum(X[p, src, dst, t] for p in products for src, dst in trans_edges for t in range(1, T + 1))
    model.setObjective(objective, GRB.MINIMIZE)
    return model


def solve_model(model) -> dict[str, Any]:
    try:
        import gurobipy as gp
    except ImportError as exc:
        raise RetailCompileError("gurobipy_unavailable") from exc
    model.optimize()
    status = int(model.Status)
    if status == gp.GRB.OPTIMAL:
        label = "OPTIMAL"
    elif status == gp.GRB.TIME_LIMIT and model.SolCount > 0:
        label = "OPTIMAL (TL)"
    elif status == gp.GRB.INFEASIBLE:
        label = "INFEASIBLE"
    elif status == gp.GRB.UNBOUNDED:
        label = "UNBOUNDED"
    elif status == gp.GRB.INF_OR_UNBD:
        label = "INF_OR_UNBD"
    else:
        label = f"CODE_{status}"
    return {
        "status": label,
        "status_code": status,
        "objective": float(model.ObjVal) if model.SolCount > 0 else None,
        "objective_bound": float(model.ObjBound) if model.SolCount > 0 else None,
        "solution_count": int(model.SolCount),
        "variables": int(model.NumVars),
        "constraints": int(model.NumConstrs),
        "nonzeros": int(model.NumNZs),
    }


__all__ = ["RetailCompileError", "compile_model", "solve_model", "validate_data"]
