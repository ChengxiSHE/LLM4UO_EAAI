import hashlib
import unittest

from llm4or.vera_opt_evolution import apply_prefix_patch


def parent_skill():
    implementation_sha = hashlib.sha256(b"compiler").hexdigest()
    return implementation_sha, {
        "schema": "verified-typed-skill-v2", "skill_id": "selection", "version": 1,
        "parent_sha256": None, "family": "knapsack",
        "recognizer": {"kind": "casefolded_literal_v1", "required_all": [],
                       "required_any": [["revenue"]], "forbidden_any": []},
        "implementation": {"id": "declarative.selection.v1", "sha256": implementation_sha,
            "configuration": {
                "schema": "declarative-binary-selection-v4",
                "record_rule": {"line_prefixes": ["* Container "], "id_suffix": ":",
                    "numeric_fields": [
                        {"name": "resource", "position": 0, "normalizer": "identity"},
                        {"name": "value", "position": 1, "normalizer": "currency_thousands"}]},
                "scalar_rules": [{"name": "capacity", "required_any": ["capacity"],
                                  "forbidden_any": [], "numeric_position": 0}],
                "variable_domain": "binary",
                "objective": {"sense": "max", "coefficient_field": "value", "offset": 0},
                "constraints": [{"id": "capacity", "coefficient_field": "resource",
                                 "sense": "le", "rhs_scalar": "capacity"}],
                "minimum_records": 1, "maximum_records": 1000}},
        "contracts": {"input_schema": "public-problem-v1",
                      "output_schema": "trusted-solve-result-v1",
                      "semantic_contract": "binary selection"},
        "invariants": ["one binary per item"],
        "metamorphic_tests": [{"id": "permute_records", "transform": "permute",
                               "expectation": "objective unchanged"}],
        "limits": {"max_input_bytes": 10000, "max_variables": 100,
                   "max_constraints": 100, "wall_seconds": 10},
        "fallback": "unchanged_backend",
        "provenance": {"proposer": "g1", "development_manifest_sha256": "0" * 64,
                       "proposal_sha256": "1" * 64},
    }


class VeraOptEvolutionTests(unittest.TestCase):
    def test_grounded_prefix_patch_creates_linked_child(self):
        implementation_sha, parent = parent_skill()
        child = apply_prefix_patch(
            parent, {"add_record_prefixes": ["* Shipment "], "rationale": "missing prefix"},
            public_failure_text="* Shipment A: weight 2, revenue 3",
            implementation_sha256=implementation_sha, proposer="g2",
        )
        self.assertEqual(child["version"], 2)
        self.assertIsNotNone(child["parent_sha256"])
        self.assertIn("* Shipment ", child["implementation"]["configuration"]
                      ["record_rule"]["line_prefixes"])

    def test_ungrounded_prefix_is_rejected(self):
        implementation_sha, parent = parent_skill()
        with self.assertRaisesRegex(ValueError, "not_publicly_grounded"):
            apply_prefix_patch(
                parent, {"add_record_prefixes": ["* Box "], "rationale": "invented"},
                public_failure_text="* Shipment A: weight 2, revenue 3",
                implementation_sha256=implementation_sha, proposer="g2",
            )


if __name__ == "__main__":
    unittest.main()
