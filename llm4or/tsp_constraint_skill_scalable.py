"""Versioned scalable frontend for the reviewed TSP constraint skill.

Only the admitted node range and exact backend change from v1.  The source
evidence grammar, byte-for-byte candidate recompilation, forbidden-edge/XOR
obligations, and exact static fallback remain mandatory.
"""

from __future__ import annotations

from decimal import Decimal

from .tsp_constraint_skill import (
    TspConstraintGraph,
    TspConstraintSkillError,
    _canonical,
    _extract_tsp_constraint_candidate,
)
from .tsp_public_graph import TspPublicGraphError, extract_tsp_public_graph
from .tsp_scalable_exact import TspScalableSolveError, solve_tsp_graph_milp
from .tsp_static_controller import TspStaticControllerError, build_tsp_semantic_evidence
from .tsp_typed_graph import TspTypedGraphError, compile_tsp_public_graph


VERSION = "tsp-constraint-xor-skill-v2-scalable"
MAX_NODES = 19


def extract_tsp_constraint_candidate_scalable(
    public_text: str, expected_nodes: int
) -> dict:
    return _extract_tsp_constraint_candidate(
        public_text,
        expected_nodes,
        max_nodes=MAX_NODES,
        version=VERSION,
        schema="tsp-constraint-candidate-v2-scalable",
    )


def compile_tsp_constraint_skill_scalable(
    public_text: str, candidate: dict, expected_nodes: int
) -> TspConstraintGraph:
    if type(candidate) is not dict:
        raise TspConstraintSkillError("candidate_type")
    expected = extract_tsp_constraint_candidate_scalable(public_text, expected_nodes)
    if _canonical(candidate) != _canonical(expected):
        raise TspConstraintSkillError("candidate_mismatch")
    nodes = tuple(expected["nodes"])
    index = {node: i for i, node in enumerate(nodes)}
    edges = tuple(
        sorted(
            (
                index[edge["nodes"][0]],
                index[edge["nodes"][1]],
                Decimal(edge["weight"]),
            )
            for edge in expected["edges"]
        )
    )
    forbidden = tuple(index[node] for node in expected["forbidden_pair"])
    xor_pairs = tuple(
        tuple(index[node] for node in pair) for pair in expected["xor_pairs"]
    )
    return TspConstraintGraph(
        question_sha256=expected["question_sha256"],
        nodes=nodes,
        edges=edges,
        forbidden_pair=forbidden,
        xor_pairs=xor_pairs,
        unit=expected["unit"],
    )


def _optimal(solved, route: str, semantic_status: str, evidence: dict) -> dict:
    return {
        "version": VERSION,
        "route": route,
        "status": "optimal",
        "adopted": True,
        "question_sha256": solved.question_sha256,
        "semantic_status": semantic_status,
        "semantic_evidence": evidence,
        "tour": list(solved.tour),
        "objective": float(solved.objective),
        "objective_decimal": str(solved.objective),
        "unit": solved.unit,
        "solver_called": True,
        "solver_backend": solved.backend,
        "natural_language_accuracy_established": False,
    }


def _run_static_scalable(public_text: str, expected_nodes: int) -> dict:
    try:
        evidence = build_tsp_semantic_evidence(public_text, expected_nodes)
        candidate = extract_tsp_public_graph(public_text, expected_nodes)
        graph = compile_tsp_public_graph(public_text, candidate, expected_nodes)
        solved = solve_tsp_graph_milp(graph)
        return _optimal(
            solved,
            "canonical_static_v2_scalable",
            "authored_public_contract_v1",
            evidence,
        )
    except TspStaticControllerError as exc:
        reason = str(exc)
    except (TspPublicGraphError, TspTypedGraphError):
        reason = "source_rejected"
    except TspScalableSolveError:
        return {
            "version": VERSION,
            "route": "none",
            "status": "unavailable",
            "adopted": False,
            "reason": "solver_rejected",
            "question_sha256": None,
            "solver_called": True,
            "natural_language_accuracy_established": False,
        }
    return {
        "version": VERSION,
        "route": "none",
        "status": "abstained",
        "adopted": False,
        "reason": reason,
        "question_sha256": None,
        "solver_called": False,
        "natural_language_accuracy_established": False,
    }


def run_tsp_constraint_scalable_cascade(
    public_text: str, expected_nodes: int
) -> dict:
    try:
        candidate = extract_tsp_constraint_candidate_scalable(
            public_text, expected_nodes
        )
        graph = compile_tsp_constraint_skill_scalable(
            public_text, candidate, expected_nodes
        )
        solved = solve_tsp_graph_milp(graph)
        return _optimal(
            solved,
            "constraint_xor_v2_scalable",
            graph.semantic_status,
            candidate["evidence"],
        )
    except TspConstraintSkillError:
        fallback = _run_static_scalable(public_text, expected_nodes)
        if fallback.get("question_sha256") is None and type(public_text) is str:
            import hashlib

            try:
                fallback["question_sha256"] = hashlib.sha256(
                    public_text.encode("utf-8")
                ).hexdigest()
            except UnicodeError:
                pass
        return fallback
    except TspScalableSolveError:
        return {
            "version": VERSION,
            "route": "none",
            "status": "unavailable",
            "adopted": False,
            "reason": "solver_rejected",
            "question_sha256": None,
            "solver_called": True,
            "natural_language_accuracy_established": False,
        }


__all__ = [
    "MAX_NODES",
    "VERSION",
    "compile_tsp_constraint_skill_scalable",
    "extract_tsp_constraint_candidate_scalable",
    "run_tsp_constraint_scalable_cascade",
]
