"""Common exact MILP backend for the two trusted TSP graph contracts.

The frontend graph remains the proof boundary.  This module only lowers an
already typed complete graph, or the reviewed one-forbidden-edge plus XOR
graph, to a directed MTZ formulation.  Decimal edge weights are scaled to
integers before Gurobi is called and the returned tour is checked again using
the original ``Decimal`` weights.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math
import re

from .gurobi_cli_solver import VERSION as GUROBI_VERSION, execute
from .milp_schema import model as validate_model
from .tsp_constraint_skill import TspConstraintGraph
from .tsp_typed_graph import TspTypedGraph


VERSION = "tsp-common-scalable-exact-mtz-v1"
MAX_NODES = 19
MAX_EXACT_INTEGER = 2**52 - 1
UNITS = {"minutes", "meters", "km", "ms", "miles", "nm"}


class TspScalableSolveError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TspScalableSolveResult:
    question_sha256: str
    tour: tuple[int, ...]
    objective: Decimal
    unit: str
    graph_kind: str
    backend: str = GUROBI_VERSION
    semantic_status: str = "conditional_typed_graph_optimum"
    natural_language_accuracy_established: bool = False


def _arc(i: int, j: int) -> str:
    return f"x_{i:03d}_{j:03d}"


def _order(i: int) -> str:
    return f"u_{i:03d}"


def _normalize(graph) -> tuple[
    int,
    dict[tuple[int, int], Decimal],
    tuple[tuple[int, int], tuple[int, int]] | None,
    str,
]:
    if type(graph) not in {TspTypedGraph, TspConstraintGraph}:
        raise TspScalableSolveError("graph_type")
    n = len(graph.nodes)
    if not 4 <= n <= MAX_NODES:
        raise TspScalableSolveError("resource_cap")
    if (
        type(graph.nodes) is not tuple
        or len(set(graph.nodes)) != n
        or any(type(node) is not str or not node or len(node) > 80 for node in graph.nodes)
        or type(graph.question_sha256) is not str
        or re.fullmatch(r"[0-9a-f]{64}", graph.question_sha256) is None
        or graph.unit not in UNITS
        or type(graph.edges) is not tuple
    ):
        raise TspScalableSolveError("graph_schema")

    weights = {}
    for row in graph.edges:
        if (
            type(row) is not tuple
            or len(row) != 3
            or type(row[0]) is not int
            or type(row[1]) is not int
            or not 0 <= row[0] < row[1] < n
            or type(row[2]) is not Decimal
            or not row[2].is_finite()
            or not 0 < row[2] <= 1_000_000_000
            or row[2].as_tuple().exponent < -3
            or (row[0], row[1]) in weights
        ):
            raise TspScalableSolveError("graph_edge")
        weights[(row[0], row[1])] = row[2]

    all_pairs = {(i, j) for i in range(n) for j in range(i + 1, n)}
    xor_pairs = None
    if type(graph) is TspTypedGraph:
        if set(weights) != all_pairs:
            raise TspScalableSolveError("graph_inventory")
        graph_kind = "complete_undirected"
    else:
        forbidden = graph.forbidden_pair
        if (
            type(forbidden) is not tuple
            or len(forbidden) != 2
            or tuple(sorted(forbidden)) != forbidden
            or forbidden not in all_pairs
            or set(weights) != all_pairs - {forbidden}
            or type(graph.xor_pairs) is not tuple
            or len(graph.xor_pairs) != 2
            or len(set(graph.xor_pairs)) != 2
            or any(
                type(pair) is not tuple
                or len(pair) != 2
                or tuple(sorted(pair)) != pair
                or pair not in weights
                for pair in graph.xor_pairs
            )
        ):
            raise TspScalableSolveError("graph_obligations")
        xor_pairs = graph.xor_pairs
        graph_kind = "forbidden_edge_xor"
    return n, weights, xor_pairs, graph_kind


def build_tsp_milp(graph) -> tuple[dict, dict]:
    """Lower a typed graph to a bounded directed MTZ ``milp-v1`` model."""
    n, weights, xor_pairs, graph_kind = _normalize(graph)
    precision = max(0, max(-weight.as_tuple().exponent for weight in weights.values()))
    scale = 10**precision
    scaled = {pair: int(weight * scale) for pair, weight in weights.items()}
    if any(Decimal(value) != weights[pair] * scale for pair, value in scaled.items()):
        raise TspScalableSolveError("weight_scaling")
    if max(scaled.values()) * n > MAX_EXACT_INTEGER:
        raise TspScalableSolveError("weight_scaling_limit")

    variables = []
    objective = {}
    for (i, j), weight in sorted(scaled.items()):
        for left, right in ((i, j), (j, i)):
            name = _arc(left, right)
            variables.append(
                {
                    "id": name,
                    "meaning": f"directed tour arc {left} to {right}",
                    "unit": "1",
                    "domain": "binary",
                    "lower": None,
                    "upper": None,
                }
            )
            objective[name] = weight
    for i in range(1, n):
        variables.append(
            {
                "id": _order(i),
                "meaning": f"MTZ order of node {i}",
                "unit": "1",
                "domain": "continuous",
                "lower": 1,
                "upper": n - 1,
            }
        )

    constraints = []
    for i in range(n):
        constraints.append(
            {
                "id": f"out_{i:03d}",
                "coefficients": {
                    _arc(i, j): 1 for j in range(n) if (min(i, j), max(i, j)) in weights and i != j
                },
                "sense": "eq",
                "rhs": 1,
            }
        )
        constraints.append(
            {
                "id": f"in_{i:03d}",
                "coefficients": {
                    _arc(j, i): 1 for j in range(n) if (min(i, j), max(i, j)) in weights and i != j
                },
                "sense": "eq",
                "rhs": 1,
            }
        )
    for i in range(1, n):
        for j in range(1, n):
            if i == j or (min(i, j), max(i, j)) not in weights:
                continue
            constraints.append(
                {
                    "id": f"mtz_{i:03d}_{j:03d}",
                    "coefficients": {_order(i): 1, _order(j): -1, _arc(i, j): n},
                    "sense": "le",
                    "rhs": n - 1,
                }
            )
    if xor_pairs is not None:
        coefficients = {}
        for i, j in xor_pairs:
            coefficients[_arc(i, j)] = 1
            coefficients[_arc(j, i)] = 1
        constraints.append(
            {
                "id": "xor_edge_choice",
                "coefficients": coefficients,
                "sense": "eq",
                "rhs": 1,
            }
        )

    model = validate_model(
        {
            "schema": "milp-v1",
            "variables": variables,
            "constraints": constraints,
            "objective": {
                "coefficients": objective,
                "sense": "min",
                "unit": f"scaled_{graph.unit}",
                "offset": 0,
            },
        }
    )
    certificate = {
        "schema": "tsp-common-mtz-certificate-v1",
        "version": VERSION,
        "question_sha256": graph.question_sha256,
        "graph_kind": graph_kind,
        "nodes": n,
        "undirected_edges": len(weights),
        "integer_scale": scale,
        "unit": graph.unit,
        "xor_pairs": [list(pair) for pair in xor_pairs] if xor_pairs is not None else None,
        "semantic_scope": "conditional_on_typed_graph",
    }
    return model, certificate


def solve_tsp_graph_milp(
    graph,
    *,
    time_limit: float = 100.0,
    wall_seconds: float = 110.0,
) -> TspScalableSolveResult:
    """Solve and independently decode a Hamiltonian tour from the MILP point."""
    model, certificate = build_tsp_milp(graph)
    result = execute(
        {"op": "solve", "model": model},
        time_limit=time_limit,
        threads=1,
        wall_seconds=wall_seconds,
    )
    if result.get("status") != "optimal" or result.get("point") is None:
        raise TspScalableSolveError("solver_" + str(result.get("status", "unknown")))
    if result.get("point_check", {}).get("feasible") is not True:
        raise TspScalableSolveError("primal_check")

    n, weights, xor_pairs, graph_kind = _normalize(graph)
    point = result["point"]
    chosen = {
        (i, j)
        for (i, j) in (
            (i, j) for i in range(n) for j in range(n) if i != j
        )
        if point.get(_arc(i, j), 0.0) > 0.5
    }
    outgoing = {}
    incoming = {}
    for i, j in chosen:
        if i in outgoing or j in incoming:
            raise TspScalableSolveError("tour_degree")
        outgoing[i] = j
        incoming[j] = i
    if len(chosen) != n or set(outgoing) != set(range(n)) or set(incoming) != set(range(n)):
        raise TspScalableSolveError("tour_degree")

    tour = [0]
    for _ in range(n):
        tour.append(outgoing[tour[-1]])
    if tour[-1] != 0 or len(set(tour[:-1])) != n:
        raise TspScalableSolveError("tour_subcycle")

    undirected = [tuple(sorted(pair)) for pair in zip(tour, tour[1:])]
    if any(pair not in weights for pair in undirected):
        raise TspScalableSolveError("tour_edge")
    if xor_pairs is not None and sum(pair in set(undirected) for pair in xor_pairs) != 1:
        raise TspScalableSolveError("tour_xor")
    objective = sum((weights[pair] for pair in undirected), Decimal(0))
    scaled_objective = result.get("objective")
    if (
        type(scaled_objective) not in {int, float}
        or not math.isfinite(scaled_objective)
        or abs(scaled_objective - round(scaled_objective)) > 1e-6
        or Decimal(round(scaled_objective))
        != objective * certificate["integer_scale"]
    ):
        raise TspScalableSolveError("objective_decode")

    return TspScalableSolveResult(
        question_sha256=graph.question_sha256,
        tour=tuple(tour),
        objective=objective,
        unit=graph.unit,
        graph_kind=graph_kind,
    )


__all__ = [
    "MAX_NODES",
    "VERSION",
    "TspScalableSolveError",
    "TspScalableSolveResult",
    "build_tsp_milp",
    "solve_tsp_graph_milp",
]
