"""Outcome-blind structural repair for declarative VERA-Opt proposals.

The repair controller may inspect public development text and parser failures,
but never reference objectives or benchmark answers.  It can only weaken
literal recognizers by deletion and replace scalar phrases with shorter
literal anchors grounded in public development text.  Executable code,
algebra, and solver settings remain frozen.
"""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import re
from typing import Any

from .declarative_selection_compiler import (
    CONFIG_SCHEMA_V3, CONFIG_SCHEMA_V4, NUMERIC, parse_selection_text,
    validate_configuration,
)
from .schema import digest


VERSION = "vera-opt-outcome-blind-structural-repair-v2"
_WORD = re.compile(r"[a-z][a-z0-9'-]*")
_NON_ANCHORS = {
    "about", "after", "before", "from", "have", "into", "maximum", "must",
    "that", "their", "there", "these", "this", "those", "with", "without",
}


class StructuralRepairError(ValueError):
    pass


def _all_parse(questions: list[str], configuration: dict[str, Any]) -> bool:
    try:
        for question in questions:
            parse_selection_text(question, configuration)
    except (ValueError, KeyError, TypeError, ArithmeticError):
        return False
    return True


def _anchors(phrases: list[str], questions: list[str], prefixes: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    sources = list(phrases)
    for question in questions:
        for raw_line in question.splitlines():
            line = raw_line.strip()
            if any(line.casefold().startswith(prefix.casefold()) for prefix in prefixes):
                continue
            match = NUMERIC.search(line)
            if match is not None:
                # Scalar cues must occur before the value.  Text after it often
                # describes the objective and would create an unsafe shortcut.
                sources.append(line[:match.start()].casefold())
    for phrase in sources:
        tokens = _WORD.findall(phrase.casefold())
        candidates = [phrase.casefold()]
        candidates.extend(
            token for token in tokens
            if len(token) >= 5 and token not in _NON_ANCHORS
        )
        for left in range(len(tokens)):
            for width in (2, 3):
                value = " ".join(tokens[left:left + width])
                if len(value.split()) == width:
                    candidates.append(value)
        for value in set(candidates):
            counts[value] = counts.get(value, 0) + 1
    # Frequent, semantically specific anchors are tried before longer templates.
    return sorted(counts, key=lambda value: (-counts[value], -len(value), value))[:64]


def repair_v3_scalar_coverage(configuration: dict[str, Any], questions: list[str]) \
        -> tuple[dict[str, Any], dict[str, Any]]:
    """Find a bounded literal relaxation that parses every public question."""
    original = validate_configuration(deepcopy(configuration))
    if original["schema"] not in {CONFIG_SCHEMA_V3, CONFIG_SCHEMA_V4}:
        raise StructuralRepairError("typed_configuration_required")
    if not questions or any(not isinstance(question, str) for question in questions):
        raise StructuralRepairError("public_questions_required")
    if _all_parse(questions, original):
        return original, {"applied": False, "changes": [], "version": VERSION}

    repaired = deepcopy(original)
    changes = []
    for index, rule in enumerate(repaired["scalar_rules"]):
        phrases = list(rule["required_any"])
        anchors = _anchors(phrases, questions, repaired["record_rule"]["line_prefixes"])
        selected = None
        for width in range(1, min(3, len(anchors)) + 1):
            for candidate in combinations(anchors, width):
                trial = deepcopy(repaired)
                trial["scalar_rules"][index]["required_any"] = list(candidate)
                if _all_parse(questions, trial):
                    selected = list(candidate)
                    repaired = trial
                    break
            if selected is not None:
                break
        if selected is None:
            raise StructuralRepairError("no_bounded_scalar_repair")
        changes.append({
            "scalar": rule["name"],
            "before_sha256": digest(phrases),
            "after_sha256": digest(selected),
            "anchor_count": len(selected),
        })
    validate_configuration(repaired)
    if not _all_parse(questions, repaired):
        raise StructuralRepairError("repair_did_not_cover_public_questions")
    return repaired, {"applied": True, "changes": changes, "version": VERSION}


def prune_recognizer_for_public_coverage(recognizer: dict[str, Any], questions: list[str]) \
        -> tuple[dict[str, Any], dict[str, Any]]:
    """Delete only predicates contradicted by public development examples."""
    folded = [question.casefold() for question in questions]
    repaired = deepcopy(recognizer)
    repaired["required_all"] = [
        phrase for phrase in recognizer["required_all"]
        if all(phrase in question for question in folded)
    ]
    repaired["required_any"] = [
        list(group) for group in recognizer["required_any"]
        if all(any(phrase in question for phrase in group) for question in folded)
    ]
    repaired["forbidden_any"] = [
        phrase for phrase in recognizer["forbidden_any"]
        if all(phrase not in question for question in folded)
    ]
    positive_groups = len(repaired["required_all"]) + len(repaired["required_any"])
    # One public-text prefilter plus the typed parser's independent record and
    # scalar checks is the minimum admissible conjunction.  Zero positives
    # would turn the package into an unconditional matcher and is forbidden.
    if positive_groups < 1:
        raise StructuralRepairError("recognizer_specificity_floor")
    return repaired, {
        "applied": repaired != recognizer,
        "before_sha256": digest(recognizer),
        "after_sha256": digest(repaired),
        "positive_groups": positive_groups,
        "version": VERSION,
    }


def repair_candidate_package(package: dict[str, Any], questions: list[str]) \
        -> tuple[dict[str, Any], dict[str, Any]]:
    repaired = deepcopy(package)
    configuration, scalar_report = repair_v3_scalar_coverage(
        repaired["implementation"]["configuration"], questions,
    )
    recognizer, recognizer_report = prune_recognizer_for_public_coverage(
        repaired["recognizer"], questions,
    )
    repaired["implementation"]["configuration"] = configuration
    repaired["recognizer"] = recognizer
    return repaired, {
        "version": VERSION,
        "scalar": scalar_report,
        "recognizer": recognizer_report,
        "before_sha256": digest(package),
        "after_sha256": digest(repaired),
        "answer_access": False,
    }


__all__ = [
    "StructuralRepairError", "VERSION", "prune_recognizer_for_public_coverage",
    "repair_candidate_package", "repair_v3_scalar_coverage",
]
