import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace

from llm4or.formulationbench_fact_graph import (
    FactGraphError,
    audit_inference_root,
    parse_fact_graph,
    serialize_flat,
    serialize_pck,
    verify_same_facts,
)


def pair_payload(*, reverse: bool = False) -> dict:
    constraints_a = [
        {
            "description": "capacity",
            "explicit": True,
            "formulation": "sum_i x_i <= C",
        },
        {
            "description": "coverage",
            "explicit": True,
            "formulation": "sum_i y_i >= 1",
        },
    ]
    constraints_b = [
        {
            "description": "transformed capacity",
            "explicit": True,
            "formulation": "sum_i z_i <= C",
        }
    ]
    if reverse:
        constraints_a.reverse()
        constraints_b.reverse()
    formulation_a = {
        "variables": {
            "x": {
                "type": "integer",
                "bounds": {"lower": 0, "upper": "C"},
                "shape": ["n"],
            },
            "y": {"type": "binary", "shape": ["n", "m"]},
        },
        "parameters": {
            "n": {"type": "integer", "shape": []},
            "C": {"type": "float", "shape": []},
        },
        "objective": {
            "description": "minimize cost",
            "formulation": "min sum_i c_i x_i",
        },
        "constraints": constraints_a,
        "assumptions": [
            {"description": "positive capacity", "formulation": "C > 0"}
        ],
        "definitions": {
            "I": {"description": "index set", "formulation": "range(n)"}
        },
    }
    formulation_b = {
        "assumptions": [
            {"formulation": "C > 0", "description": "positive capacity"}
        ],
        "constraints": constraints_b,
        "definitions": {
            "J": {"formulation": "range(m)", "description": "second index"}
        },
        "objective": {
            "formulation": "min sum_i c_i z_i",
            "description": "minimize transformed cost",
        },
        "parameters": {
            "C": {"shape": [], "type": "float"},
            "n": {"shape": [], "type": "integer"},
        },
        "variables": {
            "z": {
                "bounds": {"upper": "C", "lower": 0},
                "shape": ["n"],
                "type": "integer",
            }
        },
    }
    if reverse:
        formulation_a = dict(reversed(list(formulation_a.items())))
        formulation_b = dict(reversed(list(formulation_b.items())))
    return {
        "schema": "llm4or-formulationbench-inference-pair-v1",
        "opaque_id": "a" * 64,
        "source_commit": "b" * 40,
        "source_tree": "c" * 40,
        "problem_description": "Choose bounded integer decisions.",
        "problem": {
            "np_hard": True,
            "parameters": {
                "n": {"type": "integer"},
                "C": {"type": "float"},
            },
        },
        "formulation_a": formulation_a,
        "formulation_b": formulation_b,
        "parameter_map": {
            "definitions": {
                "index_bridge": {
                    "formulation": {"forward": "i -> i", "backward": "i <- i"}
                }
            },
            "parameters": {
                "n": {
                    "formulation": {
                        "forward": {"source": "n", "target": "n"},
                        "backward": {"source": "n", "target": "n"},
                    }
                }
            },
        },
    }


class FormulationBenchFactGraphTests(unittest.TestCase):
    def test_parses_typed_semantic_units(self):
        graph = parse_fact_graph(pair_payload())
        kinds = {fact.kind for fact in graph.facts}
        self.assertEqual(
            kinds,
            {
                "assumption",
                "constraint",
                "definition",
                "mapping_definition",
                "objective",
                "parameter",
                "parameter_mapping",
                "problem_attribute",
                "problem_description",
                "variable",
            },
        )
        self.assertEqual(len(graph.opaque_id), 64)
        self.assertEqual(len(graph.graph_sha256), 64)
        self.assertTrue(any(fact.scope == "formulation_a" for fact in graph.facts))
        self.assertTrue(any(fact.scope == "formulation_b" for fact in graph.facts))

    def test_object_and_constraint_reordering_is_canonical(self):
        first = parse_fact_graph(pair_payload(reverse=False))
        second = parse_fact_graph(pair_payload(reverse=True))
        self.assertEqual(first.graph_sha256, second.graph_sha256)
        self.assertEqual(first.facts, second.facts)
        self.assertEqual(serialize_flat(first).body, serialize_flat(second).body)
        self.assertEqual(serialize_pck(first).body, serialize_pck(second).body)

    def test_nested_parameter_map_direction_is_preserved(self):
        first = parse_fact_graph(pair_payload())
        changed = pair_payload()
        changed["parameter_map"]["parameters"]["n"]["formulation"]["backward"][
            "target"
        ] = "different"
        second = parse_fact_graph(changed)
        self.assertNotEqual(first.graph_sha256, second.graph_sha256)

    def test_flat_and_pck_have_identical_facts_and_guidance(self):
        graph = parse_fact_graph(pair_payload())
        flat = serialize_flat(graph)
        pck = serialize_pck(graph)
        verify_same_facts(flat, pck)
        self.assertEqual(flat.fact_hashes, pck.fact_hashes)
        self.assertEqual(flat.guidance_sha256, pck.guidance_sha256)
        flat_payload = json.loads(flat.body)
        pck_payload = json.loads(pck.body)
        self.assertEqual(len(flat_payload["checks"]), 6)
        self.assertEqual(len(pck_payload["obligations"]), 6)

    def test_added_missing_or_changed_fact_fails_verification(self):
        graph = parse_fact_graph(pair_payload())
        flat = serialize_flat(graph)
        pck = serialize_pck(graph)

        changed_payload = json.loads(flat.body)
        changed_payload["facts"][0]["value"] = "tampered"
        changed = replace(
            flat,
            body=(
                json.dumps(changed_payload, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode("utf-8"),
        )
        with self.assertRaisesRegex(FactGraphError, "fact_hash_mismatch"):
            verify_same_facts(changed, pck)

        missing_payload = json.loads(flat.body)
        missing_payload["facts"].pop()
        missing = replace(
            flat,
            body=(
                json.dumps(missing_payload, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode("utf-8"),
        )
        with self.assertRaisesRegex(FactGraphError, "view_fact_multiset_mismatch"):
            verify_same_facts(missing, pck)

    def test_label_code_and_solution_keys_fail_closed(self):
        for key in ("valid", "code", "solution", "proof", "label"):
            with self.subTest(key=key):
                payload = pair_payload()
                payload["formulation_b"][key] = True
                with self.assertRaisesRegex(FactGraphError, "sensitive_input_key"):
                    parse_fact_graph(payload)

    def test_full_root_audit_is_body_free_and_rejects_extra_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pair = pair_payload()
            pair_root = root / pair["opaque_id"]
            pair_root.mkdir()
            (pair_root / "pair.json").write_text(
                json.dumps(pair), encoding="utf-8"
            )
            audit = audit_inference_root(
                root,
                source_commit=pair["source_commit"],
                source_tree=pair["source_tree"],
                expected_pairs=1,
            )
            self.assertEqual(audit["counts"]["verified_pairs"], 1)
            self.assertEqual(audit["counts"]["fact_multiset_mismatches"], 0)
            rendered = json.dumps(audit, sort_keys=True)
            self.assertNotIn("Choose bounded integer decisions", rendered)
            self.assertNotIn("sum_i", rendered)

            (pair_root / "unexpected.txt").write_text("private")
            with self.assertRaisesRegex(FactGraphError, "inference_pair_shape"):
                audit_inference_root(
                    root,
                    source_commit=pair["source_commit"],
                    source_tree=pair["source_tree"],
                    expected_pairs=1,
                )


if __name__ == "__main__":
    unittest.main()
