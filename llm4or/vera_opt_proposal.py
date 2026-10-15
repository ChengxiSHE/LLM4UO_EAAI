"""Controller-owned proposal contract for VERA-Opt generation one."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .benchmark_inputs import flat_input
from .schema import digest


VERSION = "vera-opt-proposal-controller-v5"
PROBLEM_ID = "vera_opt_knapsack_generation1"
IMPLEMENTATION_ID = "declarative.selection.v1"


PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "recognizer": {
            "type": "object",
            "properties": {
                "required_all": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
                "required_any": {
                    "type": "array", "maxItems": 8,
                    "items": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
                },
                "forbidden_any": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            },
            "required": ["required_all", "required_any", "forbidden_any"],
            "additionalProperties": False,
        },
        "configuration_json": {"type": "string", "minLength": 2, "maxLength": 50000},
        "semantic_contract": {"type": "string", "minLength": 1, "maxLength": 2000},
        "invariants": {
            "type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 500},
            "minItems": 1, "maxItems": 16,
        },
        "metamorphic_tests": {
            "type": "array", "minItems": 2, "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"enum": ["permute_records", "scale_objective"]},
                    "transform": {"type": "string", "minLength": 1, "maxLength": 500},
                    "expectation": {"type": "string", "minLength": 1, "maxLength": 500},
                },
                "required": ["id", "transform", "expectation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["recognizer", "configuration_json", "semantic_contract", "invariants", "metamorphic_tests"],
    "additionalProperties": False,
}


def source_rows(source_path: Path, split: dict) -> dict[str, dict]:
    wanted = {record["source_row"]: record for record in split["records"]}
    rows = {}
    for line_number, line in enumerate(source_path.read_text().splitlines(), 1):
        if line_number not in wanted:
            continue
        row = json.loads(line)
        meta = wanted[line_number]
        if hashlib.sha256(row["question"].encode()).hexdigest() != meta["question_sha256"]:
            raise ValueError("question_hash_drift")
        if digest(row["answer"]) != meta["answer_sha256"]:
            raise ValueError("answer_hash_drift")
        rows[meta["problem_id"]] = row
    if len(rows) != len(wanted):
        raise ValueError("split_source_rows_missing")
    return rows


def proposal_public_problem(source_path: Path, split: dict) -> dict:
    rows = source_rows(source_path, split)
    representatives = _proposal_records(split)
    text = (
        "Public development examples for one repeated optimization family. "
        "The examples contain no reference answers.\n\n"
        + "\n\n".join(
            f"=== EXAMPLE SIZE {record['size']} ===\n{rows[record['problem_id']]['question']}"
            for record in representatives
        )
    )
    return flat_input(PROBLEM_ID, {"question": text}, "question")


def proposal_public_problem_from_questions(questions: dict[str, str], split: dict) -> dict:
    representatives = _proposal_records(split)
    if any(record["problem_id"] not in questions for record in representatives):
        raise ValueError("proposal_question_missing")
    text = (
        "Public development examples for one repeated optimization family. "
        "The examples contain no reference answers.\n\n"
        + "\n\n".join(
            f"=== EXAMPLE SIZE {record['size']} ===\n{questions[record['problem_id']]}"
            for record in representatives
        )
    )
    return flat_input(PROBLEM_ID, {"question": text}, "question")


def _proposal_records(split: dict) -> list[dict]:
    records = [
        record for record in split["records"]
        if record["role"] == "development"
    ]
    records.sort(key=lambda record: (record["size"], record["within_size_index"]))
    return records


def instruction(stage: int, previous: list[dict], feedback: list[str]) -> str:
    base = """You are proposing an inert, declarative optimization skill from public development examples.
The executable compiler is fixed and trusted. You may supply only literal delimiters and algebraic field references; never emit Python, regular expressions, solver calls, reference answers, or numerical constants copied from one instance.

The configuration_json value must be valid compact JSON, not Markdown. It must have this exact typed numeric-slot shape:
{"schema":"declarative-binary-selection-v4","record_rule":{"line_prefixes":["..."],"id_suffix":":","numeric_fields":[{"name":"resource","position":0,"normalizer":"identity"},{"name":"value","position":1,"normalizer":"currency_thousands"}]},"scalar_rules":[{"name":"capacity","required_any":["..."],"forbidden_any":["..."],"numeric_position":0}],"variable_domain":"binary","objective":{"sense":"max or min","coefficient_field":"value","offset":0},"constraints":[{"id":"capacity","coefficient_field":"resource","sense":"le or eq or ge","rhs_scalar":"capacity"}],"minimum_records":1,"maximum_records":1000}
The parser extracts numbers from each matching item line in textual order. Scalar rules select exactly one line that contains at least one required_any phrase, no forbidden_any phrase, and the requested numeric slot. Use only phrases seen across the supplied public development examples. Do not enumerate full templates or put control characters in strings.
The trusted currency_thousands normalizer maps comma-grouped dollar amounts such as $159,000 to 159 benchmark-thousand units while leaving plain values and K-suffixed values unchanged. Use identity for resource and currency_thousands for value.
Use casefolded recognizer phrases. All recognizer phrases must already be lowercase. Include exactly two metamorphic tests with unique ids permute_records and scale_objective. The response must satisfy the supplied JSON schema."""
    if stage == 0:
        return base + "\nPropose the smallest general skill that covers all supplied examples."
    context = json.dumps({"previous_proposals": previous, "static_feedback": feedback},
                         sort_keys=True, separators=(",", ":"))
    return base + (
        "\nRevise the prior proposal using only the controller's static feedback. "
        "Do not infer or request benchmark answers.\n" + context
    )


def package_from_proposal(proposal: dict, *, implementation_sha256: str,
                          development_manifest_sha256: str, proposer: str) -> dict:
    proposal_sha256 = digest(proposal)
    configuration = json.loads(proposal["configuration_json"])
    if not isinstance(configuration, dict):
        raise ValueError("configuration_object_required")
    tests = proposal["metamorphic_tests"]
    if {test["id"] for test in tests} != {"permute_records", "scale_objective"} \
            or len(tests) != 2:
        raise ValueError("required_metamorphic_tests_missing")
    return {
        "schema": "verified-typed-skill-v2",
        "skill_id": "optengine_knapsack_auto_g1",
        "version": 1,
        "parent_sha256": None,
        "family": "knapsack",
        "recognizer": {"kind": "casefolded_literal_v1", **proposal["recognizer"]},
        "implementation": {
            "id": IMPLEMENTATION_ID,
            "sha256": implementation_sha256,
            "configuration": configuration,
        },
        "contracts": {
            "input_schema": "public-problem-v1",
            "output_schema": "trusted-solve-result-v1",
            "semantic_contract": proposal["semantic_contract"],
        },
        "invariants": proposal["invariants"],
        "metamorphic_tests": tests,
        "limits": {
            "max_input_bytes": 100_000,
            "max_variables": 1_000,
            "max_constraints": 100,
            "wall_seconds": 30,
        },
        "fallback": "unchanged_backend",
        "provenance": {
            "proposer": proposer,
            "development_manifest_sha256": development_manifest_sha256,
            "proposal_sha256": proposal_sha256,
        },
    }


__all__ = [
    "IMPLEMENTATION_ID", "PROBLEM_ID", "PROPOSAL_SCHEMA", "VERSION", "instruction",
    "package_from_proposal", "proposal_public_problem", "proposal_public_problem_from_questions",
    "source_rows",
]
