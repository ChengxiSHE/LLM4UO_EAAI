"""Bounded exact optimizer for a mechanically typed undirected TSP graph.

Optimality is conditional on the graph's unverified interpretation of prose.
This module never reads benchmark references or executes generated programs.
"""

from dataclasses import dataclass
from decimal import Decimal
import re

from llm4or.tsp_typed_graph import TspTypedGraph


class TspGraphSolveError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TspGraphSolveResult:
    question_sha256: str
    tour: tuple[int, ...]
    objective: Decimal
    unit: str
    semantic_status: str = 'conditional_graph_optimum'
    natural_language_accuracy_established: bool = False
    eligible_for_harness_adoption: bool = False


def _validate(graph: TspTypedGraph) -> tuple[int, dict[tuple[int, int], Decimal]]:
    if type(graph) is not TspTypedGraph:
        raise TspGraphSolveError('graph_type')
    n = len(graph.nodes)
    if n > 12:
        raise TspGraphSolveError('resource_cap')
    if (type(graph.nodes) is not tuple or n < 4
            or any(type(node) is not str or not node or len(node) > 80
                   for node in graph.nodes)
            or len(set(graph.nodes)) != n
            or type(graph.question_sha256) is not str
            or re.fullmatch(r'[0-9a-f]{64}', graph.question_sha256) is None
            or graph.semantic_status != 'unverified_public_text_interpretation'
            or graph.solver_called is not False
            or graph.unit not in ('minutes', 'meters', 'km', 'ms')):
        raise TspGraphSolveError('graph_schema')
    if type(graph.edges) is not tuple or len(graph.edges) != n * (n - 1) // 2:
        raise TspGraphSolveError('graph_inventory')
    weights = {}
    for row in graph.edges:
        if (type(row) is not tuple or len(row) != 3
                or type(row[0]) is not int or type(row[1]) is not int
                or not 0 <= row[0] < row[1] < n
                or type(row[2]) is not Decimal or not row[2].is_finite()
                or not 0 < row[2] <= 1_000_000_000
                or row[2].as_tuple().exponent < -3):
            raise TspGraphSolveError('graph_edge')
        pair = (row[0], row[1])
        if pair in weights:
            raise TspGraphSolveError('graph_inventory')
        weights[pair] = row[2]
    if len(weights) != n * (n - 1) // 2:
        raise TspGraphSolveError('graph_inventory')
    return n, weights


def solve_tsp_typed_graph(graph: TspTypedGraph) -> TspGraphSolveResult:
    """Held–Karp exact optimum with a deterministic lexicographic tie break."""
    n, weights = _validate(graph)

    def cost(i: int, j: int) -> Decimal:
        return weights[(min(i, j), max(i, j))]

    dp: dict[tuple[int, int], tuple[Decimal, tuple[int, ...]]] = {}
    for j in range(1, n):
        dp[(1 << (j - 1), j)] = (cost(0, j), (0, j))
    full = (1 << (n - 1)) - 1
    for mask in range(1, full + 1):
        if mask & (mask - 1) == 0:
            continue
        for last in range(1, n):
            bit = 1 << (last - 1)
            if not mask & bit:
                continue
            previous = mask ^ bit
            dp[(mask, last)] = min(
                (dp[(previous, prior)][0] + cost(prior, last),
                 dp[(previous, prior)][1] + (last,))
                for prior in range(1, n) if previous & (1 << (prior - 1)))
    objective, path = min((dp[(full, last)][0] + cost(last, 0),
                           dp[(full, last)][1] + (0,)) for last in range(1, n))
    return TspGraphSolveResult(graph.question_sha256, path, objective, graph.unit)


__all__ = ['TspGraphSolveError', 'TspGraphSolveResult', 'solve_tsp_typed_graph']
