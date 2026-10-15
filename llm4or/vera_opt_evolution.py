"""Typed generation-two update contract for VERA-Opt."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from .schema import digest
from .verified_skill_library import validate_skill_package


VERSION = "vera-opt-typed-evolution-controller-v1"
PROBLEM_ID = "vera_opt_generation2_structural_failure"
IMPLEMENTATION_ID = "declarative.selection.v1"

PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "add_record_prefixes": {
            "type": "array", "minItems": 1, "maxItems": 4,
            "items": {"type": "string", "minLength": 2, "maxLength": 80},
        },
        "rationale": {"type": "string", "minLength": 1, "maxLength": 1000},
    },
    "required": ["add_record_prefixes", "rationale"],
    "additionalProperties": False,
}


def instruction() -> str:
    return """You are updating an inert, typed optimization skill after a fail-closed parser trace.
The executable compiler, algebra, normalizers, recognizer, solver, and limits are frozen. You may only add the smallest missing literal item-line prefix observed in the supplied public failure example. Never emit Python, regular expressions, reference answers, objective values, new algebra, or any other fields. Preserve capitalization and the trailing space after the item kind. Return exactly the supplied JSON schema."""


def apply_prefix_patch(skill: dict[str, Any], proposal: dict[str, Any], *,
                       public_failure_text: str, implementation_sha256: str,
                       proposer: str) -> dict[str, Any]:
    validated = validate_skill_package(skill, {IMPLEMENTATION_ID: implementation_sha256})
    if validated["schema"] != "verified-typed-skill-v2" \
            or validated["implementation"]["configuration"].get("schema") \
            != "declarative-binary-selection-v4":
        raise ValueError("typed_v4_parent_required")
    if set(proposal) != {"add_record_prefixes", "rationale"}:
        raise ValueError("invalid_patch_fields")
    prefixes = proposal["add_record_prefixes"]
    if not isinstance(prefixes, list) or not 1 <= len(prefixes) <= 4 \
            or len(set(prefixes)) != len(prefixes):
        raise ValueError("invalid_patch_prefixes")
    public_lines = [line.strip().casefold() for line in public_failure_text.splitlines()]
    for prefix in prefixes:
        if not isinstance(prefix, str) or not 2 <= len(prefix) <= 80 \
                or not prefix.startswith("*") or not prefix.endswith(" ") \
                or any(ord(character) < 32 for character in prefix):
            raise ValueError("invalid_patch_prefix")
        if not any(line.startswith(prefix.casefold()) for line in public_lines):
            raise ValueError("patch_prefix_not_publicly_grounded")
    child = deepcopy(validated)
    child["version"] = validated["version"] + 1
    child["parent_sha256"] = digest(validated)
    existing = child["implementation"]["configuration"]["record_rule"]["line_prefixes"]
    child["implementation"]["configuration"]["record_rule"]["line_prefixes"] = (
        existing + [prefix for prefix in prefixes
                    if prefix.casefold() not in {value.casefold() for value in existing}]
    )
    child["provenance"] = {
        "proposer": proposer,
        "development_manifest_sha256": validated["provenance"]["development_manifest_sha256"],
        "proposal_sha256": digest(proposal),
    }
    return validate_skill_package(child, {IMPLEMENTATION_ID: implementation_sha256})


def public_failure_problem(problem: dict[str, Any], skill: dict[str, Any], reason: str) -> dict[str, Any]:
    from .benchmark_inputs import flat_input, validate_public_input
    public = validate_public_input(problem)
    config = skill["implementation"]["configuration"]
    text = (
        "Public fail-closed trace; no reference answer is included.\n"
        f"Failure reason: {reason}\n"
        "Current inert configuration:\n"
        + json.dumps(config, sort_keys=True, separators=(",", ":"))
        + "\n\nPublic problem:\n" + public["text"]
    )
    return flat_input(PROBLEM_ID, {"question": text}, "question")


__all__ = [
    "IMPLEMENTATION_ID", "PATCH_SCHEMA", "PROBLEM_ID", "VERSION",
    "apply_prefix_patch", "instruction", "public_failure_problem",
]
