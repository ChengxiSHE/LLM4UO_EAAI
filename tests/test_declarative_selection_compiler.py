import hashlib
import unittest

from llm4or.benchmark_inputs import flat_input
from llm4or.declarative_selection_compiler import (
    DeclarativeSkillError, compile_selection_model, parse_selection_text,
    solve_declarative_selection,
)
from llm4or.verified_skill_library import apply_skill_library, validate_skill_package
from llm4or.vera_opt_proposal import package_from_proposal


CONFIG = {
    "schema": "declarative-binary-selection-v1",
    "record_rule": {
        "line_prefix": "* Container ",
        "id_suffix": ":",
        "fields": [
            {"name": "weight", "left": "volume ", "right": " cubic meters"},
            {"name": "value", "left": "revenue $", "right": ""},
        ],
    },
    "scalar_rules": [
        {"name": "capacity", "left": "maximum capacity of ", "right": " cubic meters"},
    ],
    "variable_domain": "binary",
    "objective": {"sense": "max", "coefficient_field": "value", "offset": 0},
    "constraints": [
        {"id": "capacity", "coefficient_field": "weight", "sense": "le",
         "rhs_scalar": "capacity"},
    ],
    "minimum_records": 2,
    "maximum_records": 100,
}

TEXT = """A manager selects cargo. Available containers are:
* Container A: volume 6 cubic meters, revenue $9
* Container B: volume 5 cubic meters, revenue $8
* Container C: volume 4 cubic meters, revenue $7
The plane has a maximum capacity of 10 cubic meters. Each container is either selected or not.
"""


def public_problem():
    return {"id": "k", "profile": "description_parameters_v1", "text": TEXT,
            "parameters": [], "instances": []}


class DeclarativeSelectionCompilerTests(unittest.TestCase):
    def test_parses_compiles_and_solves_inert_configuration(self):
        parsed = parse_selection_text(TEXT, CONFIG)
        self.assertEqual(len(parsed["records"]), 3)
        self.assertEqual(parsed["scalars"]["capacity"], 10)
        model = compile_selection_model(TEXT, CONFIG)
        self.assertEqual(model["objective"]["sense"], "max")
        solved = solve_declarative_selection(
            public_problem(),
            {"max_input_bytes": 10000, "max_variables": 100,
             "max_constraints": 100, "wall_seconds": 10}, CONFIG,
        )
        self.assertEqual(solved["status"], "optimal")
        self.assertAlmostEqual(solved["objective"], 16)

    def test_generated_literals_are_not_regular_expressions(self):
        changed = {**CONFIG, "record_rule": {**CONFIG["record_rule"], "line_prefix": ".*"}}
        with self.assertRaisesRegex(DeclarativeSkillError, "record_rule_not_unique"):
            parse_selection_text(TEXT, changed)

    def test_v2_package_passes_configuration_only_to_trusted_function(self):
        implementation_sha = hashlib.sha256(b"trusted-generic-compiler").hexdigest()
        package = {
            "schema": "verified-typed-skill-v2",
            "skill_id": "generated_knapsack",
            "version": 1,
            "parent_sha256": None,
            "family": "knapsack",
            "recognizer": {
                "kind": "casefolded_literal_v1",
                "required_all": ["maximum capacity of", "each container is either"],
                "required_any": [],
                "forbidden_any": [],
            },
            "implementation": {
                "id": "declarative.selection.v1",
                "sha256": implementation_sha,
                "configuration": CONFIG,
            },
            "contracts": {
                "input_schema": "public-problem-v1",
                "output_schema": "trusted-solve-result-v1",
                "semantic_contract": "Binary cargo selection under one capacity constraint.",
            },
            "invariants": ["every record creates one binary variable"],
            "metamorphic_tests": [{
                "id": "permute_items", "transform": "permute item lines",
                "expectation": "objective unchanged",
            }],
            "limits": {"max_input_bytes": 10000, "max_variables": 100,
                       "max_constraints": 100, "wall_seconds": 10},
            "fallback": "unchanged_backend",
            "provenance": {
                "proposer": "test",
                "development_manifest_sha256": "0" * 64,
                "proposal_sha256": "1" * 64,
            },
        }
        registry = {"declarative.selection.v1": implementation_sha}
        validate_skill_package(package, registry)
        report = apply_skill_library(
            public_problem(),
            {"status": "error", "objective": None}, [package],
            trusted_implementation_digests=registry,
            trusted_implementation_functions={
                "declarative.selection.v1": solve_declarative_selection,
            },
        )
        self.assertTrue(report["adopted"])
        self.assertAlmostEqual(report["result"]["objective"], 16)

    def test_proposal_configuration_is_transport_string_then_inert_json(self):
        proposal = {
            "recognizer": {"required_all": ["capacity"], "required_any": [],
                           "forbidden_any": []},
            "configuration_json": __import__("json").dumps(CONFIG),
            "semantic_contract": "binary selection",
            "invariants": ["one variable per record"],
            "metamorphic_tests": [
                {"id": "permute_records", "transform": "permute records",
                 "expectation": "objective unchanged"},
                {"id": "scale_objective", "transform": "scale objective",
                 "expectation": "objective scales"},
            ],
        }
        package = package_from_proposal(
            proposal, implementation_sha256="1" * 64,
            development_manifest_sha256="2" * 64, proposer="test",
        )
        self.assertEqual(package["implementation"]["configuration"], CONFIG)

    def test_v2_configuration_selects_one_of_bounded_literal_variants(self):
        config = {
            "schema": "declarative-binary-selection-v2",
            "record_rules": [
                {"line_prefix": "* Container ", "id_suffix": ":", "fields": [
                    {"name": "resource", "left": "volume ", "right": " cubic meters"},
                    {"name": "value", "left": "revenue $", "right": ""},
                ]},
                {"line_prefix": "* Package ", "id_suffix": ":", "fields": [
                    {"name": "resource", "left": "weight ", "right": "kg"},
                    {"name": "value", "left": "revenue $", "right": ""},
                ]},
            ],
            "scalar_rules": [{"name": "capacity", "alternatives": [
                {"left": "maximum capacity of ", "right": " cubic meters"},
                {"left": "maximum payload capacity of ", "right": " kg"},
            ]}],
            "variable_domain": "binary",
            "objective": {"sense": "max", "coefficient_field": "value", "offset": 0},
            "constraints": [{"id": "capacity", "coefficient_field": "resource",
                             "sense": "le", "rhs_scalar": "capacity"}],
            "minimum_records": 2,
            "maximum_records": 100,
        }
        alternative = """Packages:
* Package A: weight 6kg, revenue $9
* Package B: weight 5kg, revenue $8
The drone has a maximum payload capacity of 10 kg.
"""
        parsed = parse_selection_text(alternative, config)
        self.assertEqual(parsed["records"][0]["fields"]["resource"], 6)
        self.assertEqual(parsed["scalars"]["capacity"], 10)

    def test_v3_configuration_uses_typed_numeric_slots_across_surface_forms(self):
        config = {
            "schema": "declarative-binary-selection-v3",
            "record_rule": {
                "line_prefixes": ["* Container ", "* Package "],
                "id_suffix": ":",
                "numeric_fields": [
                    {"name": "resource", "position": 0},
                    {"name": "value", "position": 1},
                ],
            },
            "scalar_rules": [{
                "name": "capacity",
                "required_any": ["maximum capacity", "carry at most"],
                "forbidden_any": [],
                "numeric_position": 0,
            }],
            "variable_domain": "binary",
            "objective": {"sense": "max", "coefficient_field": "value", "offset": 0},
            "constraints": [{
                "id": "capacity", "coefficient_field": "resource",
                "sense": "le", "rhs_scalar": "capacity",
            }],
            "minimum_records": 2,
            "maximum_records": 100,
        }
        alternative = """Packages:
* Package A: weight 6kg, revenue $9,000
* Package B: weight 5kg, revenue $8,000
The drone can carry at most 10 kg.
"""
        parsed = parse_selection_text(alternative, config)
        self.assertEqual(parsed["records"][0]["fields"], {"resource": 6, "value": 9000})
        self.assertEqual(parsed["scalars"]["capacity"], 10)
        solved = solve_declarative_selection(
            flat_input("v3", {"question": alternative}, "question"),
            {"max_input_bytes": 10000, "max_variables": 100,
             "max_constraints": 100, "wall_seconds": 10},
            config,
        )
        self.assertEqual(solved["status"], "optimal")
        self.assertEqual(solved["objective"], 9000)

    def test_v4_excludes_numeric_identifier_and_normalizes_grouped_currency(self):
        config = {
            "schema": "declarative-binary-selection-v4",
            "record_rule": {
                "line_prefixes": ["* Container "], "id_suffix": ":",
                "numeric_fields": [
                    {"name": "resource", "position": 0, "normalizer": "identity"},
                    {"name": "value", "position": 1,
                     "normalizer": "currency_thousands"},
                ],
            },
            "scalar_rules": [{
                "name": "capacity", "required_any": ["capacity"],
                "forbidden_any": [], "numeric_position": 0,
            }],
            "variable_domain": "binary",
            "objective": {"sense": "max", "coefficient_field": "value", "offset": 0},
            "constraints": [{
                "id": "capacity", "coefficient_field": "resource",
                "sense": "le", "rhs_scalar": "capacity",
            }],
            "minimum_records": 2, "maximum_records": 100,
        }
        text = """* Container 1: weight 36 tons, revenue $159,000
* Container 2: weight 46 tons, revenue $73,000
The vessel has a maximum capacity of 82 tons.
"""
        parsed = parse_selection_text(text, config)
        self.assertEqual(parsed["records"][0]["id"], "1")
        self.assertEqual(parsed["records"][0]["fields"], {"resource": 36, "value": 159})
        solved = solve_declarative_selection(
            flat_input("v4", {"question": text}, "question"),
            {"max_input_bytes": 10000, "max_variables": 100,
             "max_constraints": 100, "wall_seconds": 10},
            config,
        )
        self.assertEqual(solved["objective"], 232)


if __name__ == "__main__":
    unittest.main()
