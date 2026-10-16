import json
import unittest

from llm4or import typed_count_skill
from llm4or.typed_count_skill import (
    build_partial_models,
    enumerate_candidates,
    model_accepts,
    oracle_partial,
    render_knowledge,
    synthesize,
    validate_candidate,
    verify_candidate,
)


def correct_candidate():
    return {
        "schema": "typed-partial-count-skill-v1",
        "count_targets": "prefix_0_through_n",
        "tail_role": "fixed_parameter",
        "counted_scope": "whole_vector",
        "relation": "count_equals_cell",
        "bound_strategy": "ordinary_conservation",
        "zero_tail_policy": "union_exception",
        "resource_policy": "compiler_exact",
    }


class GrammarOracleTests(unittest.TestCase):
    def test_candidate_is_strict_and_detached(self):
        original = correct_candidate()
        clean = validate_candidate(original)
        self.assertEqual(clean, original)
        self.assertIsNot(clean, original)
        clean["tail_role"] = "count_target"
        self.assertEqual(original["tail_role"], "fixed_parameter")

        mutations = []
        extra = correct_candidate()
        extra["extra"] = "x"
        mutations.append(extra)
        missing = correct_candidate()
        missing.pop("relation")
        mutations.append(missing)
        wrong_schema = correct_candidate()
        wrong_schema["schema"] = "other"
        mutations.append(wrong_schema)
        wrong_enum = correct_candidate()
        wrong_enum["tail_role"] = "unknown"
        mutations.append(wrong_enum)
        boolean = correct_candidate()
        boolean["resource_policy"] = True
        mutations.append(boolean)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_candidate(value)

    def test_enumerates_exactly_the_finite_grammar(self):
        candidates = enumerate_candidates()
        self.assertEqual(len(candidates), 64)
        self.assertEqual(len({repr(sorted(c.items())) for c in candidates}), 64)
        self.assertEqual(candidates, enumerate_candidates())
        self.assertIn(correct_candidate(), candidates)

    def test_direct_oracle_handles_exception_tail_and_bounds(self):
        self.assertTrue(oracle_partial(1, 0, [2, 0, 0]))
        self.assertFalse(oracle_partial(1, 0, [1, 1, 0]))
        self.assertFalse(oracle_partial(1, 2, [0, 0, 2]))
        self.assertFalse(oracle_partial(1, 2, [1, 0, 2]))

        invalid = [
            (True, 0, [2, 0, 0]),
            (0, 0, [0, 0]),
            (1, -1, [2, 0, -1]),
            (1, 0, [2, False, 0]),
            (1, 0, [2, 0]),
            (1, 0, [2, 0, 1]),
        ]
        for n, m, vector in invalid:
            with self.subTest(n=n, m=m, vector=vector):
                with self.assertRaises(ValueError):
                    oracle_partial(n, m, vector)


class ModelConstructionTests(unittest.TestCase):
    def candidate(self, **changes):
        value = correct_candidate()
        value.update(changes)
        return value

    def test_zero_tail_union_keeps_ordinary_and_exception(self):
        models = build_partial_models(correct_candidate(), 1, 0)
        self.assertEqual(len(models), 2)
        self.assertFalse(model_accepts(models[0], [2, 0, 0]))
        self.assertTrue(model_accepts(models[1], [2, 0, 0]))

        ordinary = build_partial_models(
            self.candidate(zero_tail_policy="ordinary_only"), 1, 0
        )
        self.assertEqual(len(ordinary), 1)
        self.assertFalse(model_accepts(ordinary[0], [2, 0, 0]))

    def test_scope_tail_and_relation_choices_change_semantics(self):
        valid = [1, 2, 1, 0]
        self.assertTrue(oracle_partial(2, 0, valid))

        whole = build_partial_models(correct_candidate(), 2, 0)
        self.assertTrue(any(model_accepts(model, valid) for model in whole))

        prefix = build_partial_models(
            self.candidate(counted_scope="count_target_prefix"), 2, 0
        )
        self.assertFalse(any(model_accepts(model, valid) for model in prefix))

        high_tail_valid = [1, 2, 1, 0, 6]
        self.assertTrue(oracle_partial(3, 6, high_tail_valid))
        tail_target = build_partial_models(
            self.candidate(tail_role="count_target"), 3, 6
        )
        self.assertFalse(any(model_accepts(model, high_tail_valid)
                             for model in tail_target))

        truth_valid = [1, 2, 2, 0, 1]
        self.assertTrue(oracle_partial(3, 1, truth_valid))
        truth = build_partial_models(
            self.candidate(relation="truth_iff_count"), 3, 1
        )
        self.assertFalse(any(model_accepts(model, truth_valid) for model in truth))

    def test_declared_and_conservation_bounds_are_distinct(self):
        broad = build_partial_models(
            self.candidate(bound_strategy="declared_length"), 3, 1
        )[0]
        narrow = build_partial_models(correct_candidate(), 3, 1)[0]
        self.assertEqual(broad["domains"][0], {"lower": 0, "upper": 5})
        self.assertEqual(narrow["domains"][0], {"lower": 0, "upper": 3})
        self.assertGreater(
            sum(item["upper"] - item["lower"] + 1 for item in broad["domains"]),
            sum(item["upper"] - item["lower"] + 1 for item in narrow["domains"]),
        )

    def test_model_membership_fails_closed(self):
        model = build_partial_models(correct_candidate(), 3, 1)[0]
        self.assertFalse(model_accepts(model, [1, 2, 2, 0, 0]))
        self.assertFalse(model_accepts(model, [1, 2, 2, 0, 2]))
        for vector in ([1, 2], [1, 2, 2, False, 1]):
            with self.subTest(vector=vector):
                with self.assertRaises(ValueError):
                    model_accepts(model, vector)


class SynthesisTests(unittest.TestCase):
    PUBLIC_CASES = [
        {"n": 27, "m": 5},
        {"n": 40, "m": 12},
        {"n": 12, "m": 4},
        {"n": 3, "m": 0},
        {"n": 5, "m": 1},
    ]

    def candidate(self, **changes):
        value = correct_candidate()
        value.update(changes)
        return value

    def test_correct_candidate_passes_semantics_and_exact_resources(self):
        report = verify_candidate(correct_candidate(), self.PUBLIC_CASES)
        self.assertTrue(report["passed"])
        self.assertTrue(report["semantic"]["passed"])
        self.assertGreater(report["semantic"]["assignments_checked"], 10_000)
        self.assertTrue(report["resources"]["passed"])
        self.assertEqual(len(report["resources"]["cases"]), 5)
        n40 = next(row for row in report["resources"]["cases"]
                   if (row["n"], row["m"]) == (40, 12))
        self.assertLessEqual(n40["totals"]["domain_indicators"], 1500)
        self.assertGreater(n40["totals"]["compiled_columns"], 0)
        self.assertGreater(n40["totals"]["compiled_rows"], 0)

    def test_every_wrong_axis_is_rejected(self):
        wrong = {
            "tail": self.candidate(tail_role="count_target"),
            "scope": self.candidate(counted_scope="count_target_prefix"),
            "relation": self.candidate(relation="truth_iff_count"),
            "bounds": self.candidate(bound_strategy="declared_length"),
            "exception": self.candidate(zero_tail_policy="ordinary_only"),
            "resource": self.candidate(resource_policy="estimate_only"),
        }
        for name, candidate in wrong.items():
            with self.subTest(name=name):
                report = verify_candidate(candidate, self.PUBLIC_CASES)
                self.assertFalse(report["passed"])
                self.assertIsNotNone(report["failure_code"])
                if report["semantic"]["counterexample"] is not None:
                    self.assertNotIn("vector", report["semantic"]["counterexample"])

    def test_broad_domains_hit_exact_n40_resource_limit(self):
        report = verify_candidate(
            self.candidate(bound_strategy="declared_length"), self.PUBLIC_CASES
        )
        self.assertFalse(report["passed"])
        self.assertEqual(report["failure_code"], "resource_model_rejected")
        self.assertIn("domain_indicator_limit", report["resources"]["error"])

    def test_component_measurement_runs_both_gates_without_short_circuit(self):
        self.assertTrue(hasattr(typed_count_skill, "measure_candidate_components"))
        semantic_failure = self.candidate(zero_tail_policy="ordinary_only")
        sequential = verify_candidate(semantic_failure, self.PUBLIC_CASES)
        self.assertFalse(sequential["semantic"]["passed"])
        self.assertEqual(
            sequential["resources"]["error"],
            "not_checked_after_semantic_failure",
        )

        measured = typed_count_skill.measure_candidate_components(
            semantic_failure,
            self.PUBLIC_CASES,
        )
        self.assertFalse(measured["semantic"]["passed"])
        self.assertTrue(measured["resources"]["passed"])
        self.assertEqual(measured["gate_cell"], "semantic_0_resource_1")
        self.assertFalse(measured["safe_admission"])

    def test_synthesis_is_deterministic_and_duplicates_fail_closed(self):
        first = synthesize(self.PUBLIC_CASES)
        second = synthesize(list(reversed(self.PUBLIC_CASES)))
        self.assertEqual(first, second)
        self.assertEqual(first["grammar_size"], 64)
        self.assertEqual(first["survivor_count"], 1)
        self.assertEqual(first["selected"], correct_candidate())

        with self.assertRaises(ValueError):
            synthesize(self.PUBLIC_CASES + [dict(self.PUBLIC_CASES[0])])

    def test_rendered_knowledge_is_bounded_and_has_no_benchmark_identity(self):
        text = render_knowledge(correct_candidate())
        value = json.loads(text)
        self.assertEqual(value["schema"], "typed-partial-count-knowledge-v1")
        self.assertEqual(value["candidate"], correct_candidate())
        self.assertLess(len(text.encode("utf-8")), 10_000)
        forbidden = {"public_id", "family_id", "benchmark_row_id", "solution_vector"}

        def visit(item):
            if isinstance(item, dict):
                self.assertTrue(forbidden.isdisjoint(item))
                for child in item.values():
                    visit(child)
            elif isinstance(item, list):
                for child in item:
                    visit(child)

        visit(value)


if __name__ == "__main__":
    unittest.main()
