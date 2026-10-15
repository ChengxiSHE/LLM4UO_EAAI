"""Mechanically typed TSP graph; natural-language meaning remains unverified.

This v1 compiler pins each candidate to an exact public-text re-extraction.
It cannot execute generated code, solve a tour, or certify TSP semantics.
"""

from dataclasses import dataclass
from decimal import Decimal
import json

from llm4or.tsp_public_graph import TspPublicGraphError, extract_tsp_public_graph


class TspTypedGraphError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TspTypedGraph:
    question_sha256: str
    nodes: tuple[str, ...]
    edges: tuple[tuple[int, int, Decimal], ...]
    unit: str
    alias_policy: str
    semantic_status: str = 'unverified_public_text_interpretation'
    solver_called: bool = False


def _canonical(candidate: dict) -> bytes:
    try:
        body = json.dumps(candidate, sort_keys=True, ensure_ascii=False,
                          allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, UnicodeError) as exc:
        raise TspTypedGraphError('candidate_type') from exc
    if len(body) > 100_000:
        raise TspTypedGraphError('candidate_size')
    return body


def compile_tsp_public_graph(public_text: str, candidate: dict,
                             expected_nodes: int) -> TspTypedGraph:
    """Compile only the graph structure that a pinned v1 extractor can prove.

    A future grammar requires a new reviewed compiler version, rather than a
    model-supplied parser override at this trust boundary.
    """
    if type(candidate) is not dict:
        raise TspTypedGraphError('candidate_type')
    supplied = _canonical(candidate)
    try:
        expected = extract_tsp_public_graph(public_text, expected_nodes)
    except TspPublicGraphError as exc:
        raise TspTypedGraphError('source_rejected') from exc
    if supplied != _canonical(expected):
        raise TspTypedGraphError('candidate_mismatch')
    nodes = tuple(expected['nodes'])
    index = {node: i for i, node in enumerate(nodes)}
    edges = tuple(sorted((index[edge['nodes'][0]], index[edge['nodes'][1]],
                          Decimal(edge['weight'])) for edge in expected['edges']))
    if len(edges) != len(nodes) * (len(nodes) - 1) // 2:
        raise TspTypedGraphError('edge_inventory')
    return TspTypedGraph(question_sha256=expected['question_sha256'],
                         nodes=nodes, edges=edges, unit=expected['unit'],
                         alias_policy=expected['alias_policy'])


__all__ = ['TspTypedGraph', 'TspTypedGraphError', 'compile_tsp_public_graph']
