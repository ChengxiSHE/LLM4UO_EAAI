"""Typed TSP skill for one forbidden edge plus an exactly-one edge choice.

The skill is a small proof-obligation-carrying program acquired from the
frozen public development cohort.  It admits only a sparse undirected graph
with one missing pair, a source sentence that forbids that pair, a source
sentence that requires exactly one of two present edges, and the usual closed
Hamiltonian-tour objective.  Every parameter is re-extracted from source text
at the compiler boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re

from .tsp_static_controller import run_tsp_static_controller


VERSION = "tsp-constraint-xor-skill-v1"


class TspConstraintSkillError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TspConstraintGraph:
    question_sha256: str
    nodes: tuple[str, ...]
    edges: tuple[tuple[int, int, Decimal], ...]
    forbidden_pair: tuple[int, int]
    xor_pairs: tuple[tuple[int, int], tuple[int, int]]
    unit: str
    semantic_status: str = "typed_forbidden_edge_and_exactly_one_edge"


@dataclass(frozen=True, slots=True)
class TspConstraintSolveResult:
    question_sha256: str
    tour: tuple[int, ...]
    objective: Decimal
    unit: str


_PAIR_LINE = re.compile(
    r"(?:\*[ \t]*)?(?P<left>[^:\n]{1,80}?)\s+to\s+"
    r"(?P<right>[^:\n]{1,80}?)\s*:\s*"
    r"(?P<weight>[0-9]+(?:\.[0-9]+)?)"
    r"(?:\s+(?P<unit>[A-Za-z-]+))?[ \t]*",
    re.IGNORECASE,
)
_UNITS = {
    "minute": "minutes",
    "minutes": "minutes",
    "min": "minutes",
    "meter": "meters",
    "meters": "meters",
    "km": "km",
    "kilometer": "km",
    "kilometers": "km",
    "mile": "miles",
    "miles": "miles",
    "nm": "nm",
    "millisecond": "ms",
    "milliseconds": "ms",
    "ms": "ms",
}
_FORBIDDEN_WORDS = re.compile(
    r"\b(?:unavailable|impossible|impassable|infeasible|prohibited|forbidden|"
    r"not\s+(?:possible|feasible|permitted)|"
    r"cannot\s+be\s+(?:used|utilized|constructed)|"
    r"no\b.{0,45}\bdirect\b.{0,45}\b"
    r"(?:route|road|link|connection|corridor|path|flight|travel|transit|access))\b",
    re.IGNORECASE,
)
_EXACTLY_ONE = re.compile(
    r"\b(?:exactly|precisely)\s+one\b(?!\s+time)|"
    r"\bone\b.{0,20}\bnot\s+both\b|\bmutually\s+exclusive\b",
    re.IGNORECASE,
)
_EXACT_ONCE = re.compile(
    r"(?:each|every)\b.{0,140}\b(?:precisely|exactly)\s+"
    r"(?:once|one\s+time)\b|\b(?:single\s+(?:visit|inspection))\b",
    re.IGNORECASE | re.DOTALL,
)
_RETURN = re.compile(
    r"\b(?:return(?:s|ing)?|conclud(?:e|es|ing)|complet(?:e|es|ing))\b"
    r".{0,130}\b(?:initial|origin(?:al)?|starting|same|departure)\b|"
    r"\b(?:closed[- ](?:loop|circuit)|cyclic|round[- ]trip)\b|"
    r"\bbegins?\s+and\s+ends?\b.{0,80}\b(?:same|initial|origin)\b",
    re.IGNORECASE | re.DOTALL,
)
_MINIMIZE = re.compile(
    r"\b(?:minim(?:al|ize|izes|ized|izing|um)|"
    r"most\s+(?:time[- ]efficient|efficient|fuel[- ]efficient)|optimal)\b",
    re.IGNORECASE,
)


def _label(value: str) -> str:
    return " ".join(value.strip().split())


def _span(text: str, quote: str, start_at: int = 0) -> dict:
    start = text.find(quote, start_at)
    if start < 0:
        raise TspConstraintSkillError("evidence_binding")
    return {"start": start, "end": start + len(quote), "quote": quote}


def _mentions(line: str, node: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(node) + r"(?![A-Za-z0-9])", line,
                     re.IGNORECASE) is not None


def _mentioned_pair(line: str, nodes: tuple[str, ...]) -> tuple[str, str] | None:
    mentioned = [node for node in nodes if _mentions(line, node)]
    if len(mentioned) != 2:
        return None
    return tuple(sorted(mentioned))


def _infer_header_unit(text: str) -> str | None:
    matches = set()
    for token, unit in _UNITS.items():
        if re.search(r"\b" + re.escape(token) + r"\b", text, re.IGNORECASE):
            matches.add(unit)
    return next(iter(matches)) if len(matches) == 1 else None


def _extract_tsp_constraint_candidate(
    text: str,
    expected_nodes: int,
    *,
    max_nodes: int,
    version: str,
    schema: str,
) -> dict:
    if (
        type(text) is not str
        or type(expected_nodes) is not int
        or not 4 <= expected_nodes <= max_nodes
    ):
        raise TspConstraintSkillError("input_scope")
    try:
        encoded = text.encode("utf-8")
    except UnicodeError as exc:
        raise TspConstraintSkillError("input_encoding") from exc
    if not 0 < len(encoded) <= 100_000:
        raise TspConstraintSkillError("input_scope")

    parsed = []
    pairs = set()
    units = set()
    offset = 0
    last_edge_end = -1
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        match = _PAIR_LINE.fullmatch(stripped)
        if match is not None:
            left, right = _label(match["left"]), _label(match["right"])
            if not left or not right or left.casefold() == right.casefold():
                raise TspConstraintSkillError("edge_label")
            pair = tuple(sorted((left, right)))
            if pair in pairs:
                raise TspConstraintSkillError("edge_inventory")
            pairs.add(pair)
            token = match["weight"]
            if "." in token and len(token.split(".")[1]) > 3:
                raise TspConstraintSkillError("weight_precision")
            try:
                weight = Decimal(token)
            except InvalidOperation as exc:
                raise TspConstraintSkillError("weight") from exc
            if not weight.is_finite() or not 0 < weight <= 1_000_000_000:
                raise TspConstraintSkillError("weight")
            raw_unit = match["unit"]
            unit = _UNITS.get(raw_unit.casefold()) if raw_unit else None
            if raw_unit and unit is None:
                raise TspConstraintSkillError("unit")
            if unit:
                units.add(unit)
            quote = stripped
            start = offset + line.index(stripped)
            last_edge_end = start + len(quote)
            parsed.append(
                {
                    "nodes": list(pair),
                    "weight": str(weight),
                    "evidence": {"start": start, "end": last_edge_end, "quote": quote},
                }
            )
        offset += len(line)

    nodes = tuple(sorted({node for edge in parsed for node in edge["nodes"]}))
    expected_edges = expected_nodes * (expected_nodes - 1) // 2 - 1
    if len(nodes) != expected_nodes or len(parsed) != expected_edges:
        raise TspConstraintSkillError("sparse_graph_inventory")
    all_pairs = {
        (nodes[i], nodes[j])
        for i in range(expected_nodes)
        for j in range(i + 1, expected_nodes)
    }
    missing = sorted(all_pairs - pairs)
    if len(missing) != 1:
        raise TspConstraintSkillError("missing_pair_inventory")

    if len(units) > 1:
        raise TspConstraintSkillError("unit_conflict")
    unit = next(iter(units)) if units else _infer_header_unit(text)
    if unit is None:
        raise TspConstraintSkillError("unit_missing")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    forbidden_lines = [
        line
        for line in lines
        if _FORBIDDEN_WORDS.search(line)
        and all(_mentions(line, node) for node in missing[0])
    ]
    if len(forbidden_lines) != 1:
        raise TspConstraintSkillError("forbidden_evidence")

    xor_lines = [line for line in lines if _EXACTLY_ONE.search(line)]
    if len(xor_lines) != 1:
        raise TspConstraintSkillError("xor_evidence")
    xor_line = xor_lines[0]
    xor_match = _EXACTLY_ONE.search(xor_line)
    if xor_match is None:
        raise TspConstraintSkillError("xor_evidence")
    xor_pairs = []
    xor_tail = xor_line[xor_match.end() :]
    for segment in re.split(r"\bor\b", xor_tail, flags=re.IGNORECASE):
        pair = _mentioned_pair(segment, nodes)
        if pair is not None and pair not in xor_pairs:
            xor_pairs.append(pair)
    if (
        len(xor_pairs) != 2
        or xor_pairs[0] == xor_pairs[1]
        or any(pair not in pairs for pair in xor_pairs)
    ):
        raise TspConstraintSkillError("xor_pair_binding")

    objective = lines[-1]
    exact = _EXACT_ONCE.search(objective)
    returns = _RETURN.search(objective)
    minimize = _MINIMIZE.search(objective)
    if exact is None or returns is None or minimize is None:
        raise TspConstraintSkillError("objective_evidence")
    objective_span = _span(text, objective, max(last_edge_end, 0))

    return {
        "schema": schema,
        "version": version,
        "question_sha256": hashlib.sha256(encoded).hexdigest(),
        "expected_nodes": expected_nodes,
        "nodes": list(nodes),
        "edges": sorted(parsed, key=lambda row: tuple(row["nodes"])),
        "forbidden_pair": list(missing[0]),
        "xor_pairs": [list(pair) for pair in xor_pairs],
        "unit": unit,
        "evidence": {
            "forbidden_edge": _span(text, forbidden_lines[0], max(last_edge_end, 0)),
            "exactly_one_edges": _span(text, xor_line, max(last_edge_end, 0)),
            "exact_once": {
                "start": objective_span["start"] + exact.start(),
                "end": objective_span["start"] + exact.end(),
                "quote": exact.group(0),
            },
            "return_to_start": {
                "start": objective_span["start"] + returns.start(),
                "end": objective_span["start"] + returns.end(),
                "quote": returns.group(0),
            },
            "minimize_total": {
                "start": objective_span["start"] + minimize.start(),
                "end": objective_span["start"] + minimize.end(),
                "quote": minimize.group(0),
            },
        },
        "semantics_validated": False,
        "solver_called": False,
    }


def extract_tsp_constraint_candidate(text: str, expected_nodes: int) -> dict:
    """Preserve the frozen v1 size-4--12 frontend exactly."""
    return _extract_tsp_constraint_candidate(
        text,
        expected_nodes,
        max_nodes=12,
        version=VERSION,
        schema="tsp-constraint-candidate-v1",
    )


def _canonical(value: dict) -> bytes:
    try:
        body = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise TspConstraintSkillError("candidate_type") from exc
    if len(body) > 250_000:
        raise TspConstraintSkillError("candidate_size")
    return body


def compile_tsp_constraint_skill(
    public_text: str, candidate: dict, expected_nodes: int
) -> TspConstraintGraph:
    if type(candidate) is not dict:
        raise TspConstraintSkillError("candidate_type")
    expected = extract_tsp_constraint_candidate(public_text, expected_nodes)
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


def solve_tsp_constraint_graph(graph: TspConstraintGraph) -> TspConstraintSolveResult:
    if type(graph) is not TspConstraintGraph:
        raise TspConstraintSkillError("graph_type")
    n = len(graph.nodes)
    if not 4 <= n <= 12:
        raise TspConstraintSkillError("resource_cap")
    weights = {}
    for i, j, weight in graph.edges:
        if (
            type(i) is not int
            or type(j) is not int
            or not 0 <= i < j < n
            or type(weight) is not Decimal
            or not weight.is_finite()
            or not 0 < weight <= 1_000_000_000
            or (i, j) in weights
        ):
            raise TspConstraintSkillError("graph_edge")
        weights[(i, j)] = weight
    all_pairs = {(i, j) for i in range(n) for j in range(i + 1, n)}
    if (
        set(weights) != all_pairs - {graph.forbidden_pair}
        or len(graph.xor_pairs) != 2
        or len(set(graph.xor_pairs)) != 2
        or any(pair not in weights for pair in graph.xor_pairs)
    ):
        raise TspConstraintSkillError("graph_obligations")
    xor = set(graph.xor_pairs)

    def edge(i: int, j: int):
        return (min(i, j), max(i, j))

    dp: dict[tuple[int, int, int], tuple[Decimal, tuple[int, ...]]] = {}
    for j in range(1, n):
        pair = edge(0, j)
        if pair not in weights:
            continue
        count = int(pair in xor)
        dp[(1 << (j - 1), j, count)] = (weights[pair], (0, j))
    full = (1 << (n - 1)) - 1
    for mask in range(1, full + 1):
        if mask & (mask - 1) == 0:
            continue
        for last in range(1, n):
            bit = 1 << (last - 1)
            if not mask & bit:
                continue
            previous = mask ^ bit
            for count in (0, 1):
                choices = []
                for prior in range(1, n):
                    if not previous & (1 << (prior - 1)):
                        continue
                    pair = edge(prior, last)
                    if pair not in weights:
                        continue
                    increment = int(pair in xor)
                    old_count = count - increment
                    state = dp.get((previous, prior, old_count))
                    if old_count not in (0, 1) or state is None:
                        continue
                    choices.append((state[0] + weights[pair], state[1] + (last,)))
                if choices:
                    dp[(mask, last, count)] = min(choices)
    finals = []
    for last in range(1, n):
        pair = edge(last, 0)
        if pair not in weights:
            continue
        increment = int(pair in xor)
        prior = dp.get((full, last, 1 - increment))
        if prior is not None:
            finals.append((prior[0] + weights[pair], prior[1] + (0,)))
    if not finals:
        raise TspConstraintSkillError("infeasible")
    objective, tour = min(finals)
    if not math.isfinite(float(objective)):
        raise TspConstraintSkillError("objective")
    return TspConstraintSolveResult(graph.question_sha256, tour, objective, graph.unit)


def run_tsp_constraint_cascade(public_text: str, expected_nodes: int) -> dict:
    try:
        candidate = extract_tsp_constraint_candidate(public_text, expected_nodes)
        graph = compile_tsp_constraint_skill(public_text, candidate, expected_nodes)
        solved = solve_tsp_constraint_graph(graph)
        return {
            "version": VERSION,
            "route": "constraint_xor_v1",
            "status": "optimal",
            "adopted": True,
            "question_sha256": solved.question_sha256,
            "semantic_status": graph.semantic_status,
            "semantic_evidence": candidate["evidence"],
            "tour": list(solved.tour),
            "objective": float(solved.objective),
            "objective_decimal": str(solved.objective),
            "unit": solved.unit,
            "solver_called": True,
            "natural_language_accuracy_established": False,
        }
    except TspConstraintSkillError:
        fallback = dict(run_tsp_static_controller(public_text, expected_nodes))
        fallback["route"] = (
            "canonical_static_v2" if fallback.get("adopted") is True else "none"
        )
        fallback["cascade_version"] = VERSION
        return fallback


__all__ = [
    "VERSION",
    "TspConstraintGraph",
    "TspConstraintSolveResult",
    "TspConstraintSkillError",
    "compile_tsp_constraint_skill",
    "extract_tsp_constraint_candidate",
    "run_tsp_constraint_cascade",
    "solve_tsp_constraint_graph",
]
