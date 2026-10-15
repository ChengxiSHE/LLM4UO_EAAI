"""Controller-owned proposal contract for VERA-Opt's second family."""

from __future__ import annotations

import json

from .benchmark_inputs import flat_input
from .schema import digest


VERSION = "vera-opt-binpacking-proposal-controller-v1"
PROBLEM_ID = "vera_opt_binpacking_generation1"
IMPLEMENTATION_ID = "declarative.bin_packing.v1"

PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "recognizer": {
            "type": "object",
            "properties": {
                "required_all": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
                "required_any": {"type": "array", "maxItems": 8,
                                 "items": {"type": "array", "items": {"type": "string"},
                                           "minItems": 1, "maxItems": 12}},
                "forbidden_any": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            },
            "required": ["required_all", "required_any", "forbidden_any"],
            "additionalProperties": False,
        },
        "configuration_json": {"type": "string", "minLength": 2, "maxLength": 50000},
        "semantic_contract": {"type": "string", "minLength": 1, "maxLength": 2000},
        "invariants": {"type": "array", "items": {"type": "string", "minLength": 1,
                                                       "maxLength": 500},
                       "minItems": 1, "maxItems": 16},
        "metamorphic_tests": {
            "type": "array", "minItems": 2, "maxItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"enum": ["permute_items", "scale_weights_and_capacity"]},
                    "transform": {"type": "string", "minLength": 1, "maxLength": 500},
                    "expectation": {"type": "string", "minLength": 1, "maxLength": 500},
                },
                "required": ["id", "transform", "expectation"], "additionalProperties": False,
            },
        },
    },
    "required": ["recognizer", "configuration_json", "semantic_contract", "invariants",
                 "metamorphic_tests"],
    "additionalProperties": False,
}


def _proposal_records(split: dict) -> list[dict]:
    records = [record for record in split["records"] if record["role"] == "development"]
    return sorted(records, key=lambda record: (record["size"], record["within_size_index"]))


def proposal_public_problem_from_questions(questions: dict[str, str], split: dict) -> dict:
    records = _proposal_records(split)
    if any(record["problem_id"] not in questions for record in records):
        raise ValueError("proposal_question_missing")
    text = "Public development examples for one repeated optimization family. The examples contain no reference answers.\n\n" + "\n\n".join(
        f"=== EXAMPLE SIZE {record['size']} INDEX {record['within_size_index']} ===\n"
        f"{questions[record['problem_id']]}" for record in records
    )
    return flat_input(PROBLEM_ID, {"question": text}, "question")


def instruction(stage: int, previous: list[dict], feedback: list[str]) -> str:
    base = """You are proposing an inert declarative skill from answer-free public examples of one optimization family.
The executable compiler, two-index assignment formulation, verifier, and solver are fixed and trusted. You may supply only literal parser metadata and fixed symbolic contract names. Never emit Python, regular expressions, solver calls, reference answers, or instance-specific numeric constants.

configuration_json must be compact valid JSON with exactly this shape:
{"schema":"declarative-bin-packing-v1","record_rule":{"line_prefixes":["..."],"id_suffix":":","numeric_fields":[{"name":"weight","position":0}]},"capacity_rule":{"name":"capacity","required_any":["..."],"forbidden_any":["..."],"numeric_position":0},"item_weight_field":"weight","capacity_scalar":"capacity","objective":"minimize_used_bins","assignment":"each_item_exactly_once","capacity_constraint":"sum_weight_le_capacity_times_used","symmetry_breaking":"used_bins_prefix","minimum_records":1,"maximum_records":1000}

The parser strips a matching line prefix, treats text before id_suffix as the item id, and takes numeric slots only from text after id_suffix. A broad literal prefix such as "* " is allowed when the family recognizer and typed parser together remain specific. capacity_rule must select exactly one non-item line in every supplied example. Use only phrases visible in the public examples. All recognizer phrases must be casefolded. Include exactly the two metamorphic tests permute_items and scale_weights_and_capacity. The response must satisfy the supplied JSON schema."""
    if stage == 0:
        return base + "\nPropose the smallest general skill that covers every supplied public example."
    context = json.dumps({"previous_proposals": previous, "static_public_feedback": feedback},
                         sort_keys=True, separators=(",", ":"))
    return base + "\nRevise using only the answer-free controller feedback.\n" + context


def package_from_proposal(proposal: dict, *, implementation_sha256: str,
                          development_manifest_sha256: str, proposer: str) -> dict:
    configuration = json.loads(proposal["configuration_json"])
    tests = proposal["metamorphic_tests"]
    if len(tests) != 2 or {test["id"] for test in tests} != {
        "permute_items", "scale_weights_and_capacity",
    }:
        raise ValueError("required_metamorphic_tests_missing")
    return {
        "schema": "verified-typed-skill-v2", "skill_id": "optengine_binpacking_auto_g1",
        "version": 1, "parent_sha256": None, "family": "bin_packing",
        "recognizer": {"kind": "casefolded_literal_v1", **proposal["recognizer"]},
        "implementation": {"id": IMPLEMENTATION_ID, "sha256": implementation_sha256,
                           "configuration": configuration},
        "contracts": {"input_schema": "public-problem-v1",
                      "output_schema": "trusted-solve-result-v1",
                      "semantic_contract": proposal["semantic_contract"]},
        "invariants": proposal["invariants"], "metamorphic_tests": tests,
        "limits": {"max_input_bytes": 100_000, "max_variables": 20_000,
                   "max_constraints": 5_000, "wall_seconds": 60},
        "fallback": "unchanged_backend",
        "provenance": {"proposer": proposer,
                       "development_manifest_sha256": development_manifest_sha256,
                       "proposal_sha256": digest(proposal)},
    }


__all__ = ["IMPLEMENTATION_ID", "PROBLEM_ID", "PROPOSAL_SCHEMA", "VERSION", "instruction",
           "package_from_proposal", "proposal_public_problem_from_questions"]
