"""Public-only static TSP controller for the frozen canonical development role.

The controller accepts a narrow authored language: a complete unordered pair
table followed by one objective sentence that states minimization, exactly-one
visitation, and return to the start.  The interpretation is an authored source
contract whose benchmark fidelity must still be checked by a separate
evaluator; it is not inferred from a reference answer.
"""

from __future__ import annotations

import hashlib
import re

from .tsp_graph_exact import TspGraphSolveError, solve_tsp_typed_graph
from .tsp_public_graph import TspPublicGraphError, extract_tsp_public_graph
from .tsp_typed_graph import TspTypedGraphError, compile_tsp_public_graph


VERSION = "tsp-static-controller-v2"


class TspStaticControllerError(ValueError):
    pass


_EXACT_ONCE = re.compile(
    r"(?:each|every)\b.{0,140}\b(?:precisely|exactly)\s+"
    r"(?:once|one\s+time)\b|"
    r"\b(?:single\s+(?:visit|inspection|service\s+call))\b.{0,100}\b"
    r"(?:each|every)\b",
    re.IGNORECASE | re.DOTALL,
)
_RETURN_TO_START = re.compile(
    r"\b(?:return(?:s|ing)?|conclud(?:e|es|ing)|complet(?:e|es|ing))\b"
    r".{0,120}\b(?:initial|origin(?:al)?|starting|same|departure)\b|"
    r"\b(?:closed[- ]loop|cyclic)\b",
    re.IGNORECASE | re.DOTALL,
)
_MINIMIZE = re.compile(
    r"\b(?:minim(?:al|ize|izes|ized|izing|um)|"
    r"most\s+(?:time[- ]efficient|efficient)|optimal)\b",
    re.IGNORECASE,
)
_FORBIDDEN_MODIFIER = re.compile(
    r"\b(?:avoid|one[- ]way|asymmetric|directed|time\s+window|deadline|"
    r"precede|precedence|forbidden|prohibited|mandatory\s+order|"
    r"multiple\s+objectives?|at\s+least\s+two\s+visits?)\b|"
    r"\b(?:before|after)\s+(?:visiting|servicing|inspecting|arriving)\b|"
    r"\bmust\s+(?:be\s+)?(?:visit(?:ed)?|service(?:d)?|inspect(?:ed)?|"
    r"arriv(?:e|ed)).{0,100}\b(?:before|after)\b"
    r"(?!\s+(?:conclud|return|complet))",
    re.IGNORECASE | re.DOTALL,
)


def _span(match: re.Match[str], offset: int) -> dict:
    return {
        "start": offset + match.start(),
        "end": offset + match.end(),
        "quote": match.group(0),
    }


def build_tsp_semantic_evidence(public_text: str, expected_nodes: int) -> dict:
    """Return source-bound obligations for the narrow canonical TSP grammar."""
    try:
        candidate = extract_tsp_public_graph(public_text, expected_nodes)
    except TspPublicGraphError as exc:
        raise TspStaticControllerError("source_rejected") from exc

    modifier = _FORBIDDEN_MODIFIER.search(public_text)
    if modifier is not None:
        raise TspStaticControllerError("semantic_modifier")

    last_edge_end = max(edge["evidence"]["end"] for edge in candidate["edges"])
    tail = public_text[last_edge_end:].strip()
    if not tail:
        raise TspStaticControllerError("semantic_objective_shape")
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", tail) if part.strip()]
    if len(sentences) != 1 or sentences[0].strip() != tail:
        raise TspStaticControllerError("semantic_objective_shape")
    tail_offset = public_text.index(tail, last_edge_end)

    exact = _EXACT_ONCE.search(tail)
    if exact is None:
        raise TspStaticControllerError("semantic_exact_once")
    returns = _RETURN_TO_START.search(tail)
    if returns is None:
        raise TspStaticControllerError("semantic_return_to_start")
    minimize = _MINIMIZE.search(tail)
    if minimize is None:
        raise TspStaticControllerError("semantic_minimize_total")

    pair_count = len(candidate["edges"])
    return {
        "exact_once": _span(exact, tail_offset),
        "return_to_start": _span(returns, tail_offset),
        "minimize_total": _span(minimize, tail_offset),
        "unordered_pair_table": {
            "pair_count": pair_count,
            "expected_pair_count": expected_nodes * (expected_nodes - 1) // 2,
            "alias_policy": candidate["alias_policy"],
            "unit": candidate["unit"],
            "interpretation": "one_weight_per_unordered_pair",
        },
    }


def _question_hash(public_text) -> str | None:
    if type(public_text) is not str:
        return None
    try:
        return hashlib.sha256(public_text.encode("utf-8")).hexdigest()
    except UnicodeError:
        return None


def run_tsp_static_controller(public_text: str, expected_nodes: int) -> dict:
    """Apply the frozen public contract and solve only after semantic admission."""
    question_sha256 = _question_hash(public_text)
    try:
        evidence = build_tsp_semantic_evidence(public_text, expected_nodes)
        candidate = extract_tsp_public_graph(public_text, expected_nodes)
        graph = compile_tsp_public_graph(public_text, candidate, expected_nodes)
        solved = solve_tsp_typed_graph(graph)
    except TspStaticControllerError as exc:
        return {
            "version": VERSION,
            "status": "abstained",
            "adopted": False,
            "reason": str(exc),
            "question_sha256": question_sha256,
            "solver_called": False,
            "natural_language_accuracy_established": False,
        }
    except (TspPublicGraphError, TspTypedGraphError) as exc:
        return {
            "version": VERSION,
            "status": "abstained",
            "adopted": False,
            "reason": "source_rejected",
            "question_sha256": question_sha256,
            "solver_called": False,
            "natural_language_accuracy_established": False,
        }
    except TspGraphSolveError:
        return {
            "version": VERSION,
            "status": "unavailable",
            "adopted": False,
            "reason": "solver_rejected",
            "question_sha256": question_sha256,
            "solver_called": True,
            "natural_language_accuracy_established": False,
        }

    return {
        "version": VERSION,
        "status": "optimal",
        "adopted": True,
        "question_sha256": solved.question_sha256,
        "semantic_status": "authored_public_contract_v1",
        "semantic_evidence": evidence,
        "tour": list(solved.tour),
        "objective": float(solved.objective),
        "objective_decimal": str(solved.objective),
        "unit": solved.unit,
        "solver_called": True,
        "natural_language_accuracy_established": False,
    }


__all__ = [
    "VERSION",
    "TspStaticControllerError",
    "build_tsp_semantic_evidence",
    "run_tsp_static_controller",
]
