import copy
import itertools
import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from llm4or.schema import Invalid, canonical
from llm4or.milp_schema import MAX_VARS, model
from llm4or.milp_solver import (_interpret, _solve, _Budget, DEFAULT_LIMITS, execute, check_point)
from llm4or.milp_evaluator import evaluate, evaluate_against_label, evaluate_batch, summarize


def variable(name, domain="continuous", lower=0, upper=1):
    return {"id": name, "meaning": name + " business quantity", "unit": "item",
            "domain": domain, "lower": lower, "upper": upper}


def formulation(variables=None, constraints=None, coefficients=None, sense="max", offset=0):
    return {"schema": "milp-v1", "variables": variables if variables is not None else [variable("x", "integer", 0, 2)],
            "constraints": constraints or [], "objective": {"coefficients": coefficients if coefficients is not None else {"x": 1},
                                                             "sense": sense, "offset": offset, "unit": "dollar"}}


def row(name, coefficients, sense, rhs):
    return {"id": name, "coefficients": coefficients, "sense": sense, "rhs": rhs}


class MilpSchemaTests(unittest.TestCase):
    def test_lp_protocol_is_not_implicitly_changed(self):
        m = formulation(); m["schema"] = "lp-v1"
        with self.assertRaises(Invalid): model(m)
        from llm4or.schema import model as old_model
        with self.assertRaises(Invalid): old_model(formulation())

    def test_sparse_coefficients_and_size_extension(self):
        m = formulation([variable("x" + str(i)) for i in range(80)], coefficients={"x0": 1})
        self.assertEqual(len(model(m)["variables"]), 80)

    def test_strict_domains_no_implicit_rounding(self):
        for domain in ("boolean", "semiinteger", 1, "Integer", ["integer"]):
            with self.assertRaises(Invalid): model(formulation([variable("x", domain)]))

    def test_unknown_or_duplicate_variable_rejected(self):
        with self.assertRaises(Invalid): model(formulation(coefficients={"ghost": 1}))
        with self.assertRaises(Invalid): model(formulation([variable("x"), variable("x")]))

    def test_duplicate_keys_and_nonfinite(self):
        with self.assertRaises(Invalid): model('{"schema":"milp-v1","schema":"milp-v1"}')
        for bad in (float("nan"), float("inf"), True, 10**1000):
            with self.assertRaises(Invalid): model(formulation(coefficients={"x": bad}))

    def test_tiny_coefficients_not_silently_dropped(self):
        with self.assertRaises(Invalid): model(formulation(coefficients={"x": 1e-12}))

    def test_bound_and_dimension_limits(self):
        with self.assertRaises(Invalid): model(formulation([variable("x", lower=2, upper=1)]))
        with self.assertRaises(Invalid): model(formulation([variable("x" + str(i)) for i in range(MAX_VARS + 1)], coefficients={}))

    def test_no_generated_code_or_extra_solver_options(self):
        m = formulation(); m["code"] = "raise RuntimeError()"
        with self.assertRaises(Invalid): model(m)
        self.assertEqual(execute({"op": "solve", "model": formulation(), "options": {"mip_rel_gap": 1}})["status"], "invalid_input")


class MilpSolveTests(unittest.TestCase):
    def test_integer_optimum_not_relaxation_or_rounded_solution(self):
        m = formulation([variable("x", "integer", 0, None)], [row("cap", {"x": 2}, "le", 3)], offset=7)
        result = execute({"op": "solve", "model": m})
        self.assertEqual(result["status"], "optimal")
        self.assertEqual(result["objective"], 8)
        self.assertEqual(result["objective_bound"], 8)
        self.assertEqual(result["bound_direction"], "upper")
        m["variables"][0]["domain"] = "continuous"
        self.assertEqual(execute({"op": "solve", "model": m})["objective"], 8.5)

    def test_binary_intrinsic_bounds(self):
        m = formulation([variable("x", "binary", None, None)])
        r = execute({"op": "solve", "model": m})
        self.assertEqual(r["objective"], 1)
        self.assertFalse(check_point(m, {"x": 2})["feasible"])
        self.assertFalse(check_point(m, {"x": 0.5})["feasible"])

    def test_mixed_fixed_cost_with_fractional_continuous_quantity(self):
        m = formulation([variable("q", "continuous", 3.5, None), variable("open", "binary", None, None)],
                        [row("cap", {"q": 1, "open": -6}, "le", 0)], {"q": 1, "open": 2}, "min", -10)
        r = execute({"op": "solve", "model": m})
        self.assertEqual(r["status"], "optimal")
        self.assertAlmostEqual(r["objective"], -4.5)
        self.assertEqual(r["objective_bound"], r["objective"])
        self.assertEqual(r["bound_direction"], "lower")
        self.assertEqual(r["point"], {"q": 3.5, "open": 1})

    def test_negative_free_variable_not_default_nonnegative(self):
        m = formulation([variable("x", "integer", None, None)], [row("e", {"x": 1}, "eq", -3)])
        self.assertEqual(execute({"op": "solve", "model": m})["objective"], -3)

    def test_zero_row_and_integer_only_infeasibility(self):
        for m in (formulation(constraints=[row("impossible", {}, "ge", 1)]),
                  formulation([variable("x", "integer", 0, 1)], [row("half", {"x": 1}, "eq", 0.5)]),
                  formulation([variable("x", "binary", 2, 3)]),
                  formulation([variable("x", "integer", 0.1, 0.9)])):
            self.assertEqual(execute({"op": "solve", "model": m})["status"], "infeasible")

    def test_unbounded_not_infeasible(self):
        m = formulation([variable("x", "integer", None, None)])
        r = execute({"op": "solve", "model": m})
        # HiGHS can report an ambiguous presolve result as status 4; it must
        # never be translated to infeasible or assigned a finite optimum.
        self.assertIn(r["status"], {"unbounded", "unknown"})
        self.assertIsNone(r["objective"])

    def test_assignment_matches_exhaustive_permutation_oracle(self):
        costs = [[8, 2, 5], [1, 7, 3], [6, 4, 9]]
        vs = [variable(f"a_{i}_{j}", "binary", None, None) for i in range(3) for j in range(3)]
        rows = [row(f"worker_{i}", {f"a_{i}_{j}": 1 for j in range(3)}, "eq", 1) for i in range(3)]
        rows += [row(f"job_{j}", {f"a_{i}_{j}": 1 for i in range(3)}, "eq", 1) for j in range(3)]
        m = formulation(vs, rows, {f"a_{i}_{j}": costs[i][j] for i in range(3) for j in range(3)}, "min")
        oracle = min(sum(costs[i][p[i]] for i in range(3)) for p in itertools.permutations(range(3)))
        r = execute({"op": "solve", "model": m})
        self.assertEqual(r["objective"], oracle)
        self.assertTrue(check_point(m, r["point"])["feasible"])

    def test_knapsack_matches_full_integer_enumeration(self):
        m = formulation([variable("a", "integer", 0, 4), variable("b", "integer", 0, 4), variable("c", "binary", None, None)],
                        [row("weight", {"a": 3, "b": 2, "c": 5}, "le", 11)], {"a": 4, "b": 3, "c": 9})
        oracle = max(4*a+3*b+9*c for a,b,c in itertools.product(range(5),range(5),range(2)) if 3*a+2*b+5*c<=11)
        self.assertEqual(execute({"op": "solve", "model": m})["objective"], oracle)

    def test_larger_sparse_model(self):
        vs = [variable("x" + str(i), "binary", None, None) for i in range(100)]
        m = formulation(vs, [row("choose", {v["id"]: 1 for v in vs}, "eq", 10)],
                        {"x"+str(i): i+1 for i in range(100)}, "min")
        self.assertEqual(execute({"op": "solve", "model": m})["objective"], 55)

    def test_worker_timeout_and_memory_monitor(self):
        self.assertEqual(execute({"op": "solve", "model": formulation()}, wall_seconds=0.001)["reason"], "wall_timeout")
        self.assertEqual(execute({"op": "solve", "model": formulation()}, rss_mb=32)["reason"], "rss_limit")


class MilpStatusTests(unittest.TestCase):
    def raw(self, status=0, point=None, value=1, bound=1, gap=0):
        return SimpleNamespace(status=status, success=status==0, message="synthetic solver result",
                               x=[1] if point is None else point, fun=value,
                               mip_dual_bound=bound, mip_gap=gap, mip_node_count=2)

    def test_limit_preserves_incumbent_without_optimal_score(self):
        raw = self.raw(status=1, bound=0.2, gap=0.8)
        internal = _interpret(formulation(), {"x": 1}, raw, ["x"])
        self.assertEqual(internal["status"], "limit")
        with patch("llm4or.milp_solver._optimize", return_value=internal):
            r = _solve(formulation(sense="min", offset=10), _Budget(DEFAULT_LIMITS))
        self.assertIsNone(r["objective"])
        self.assertEqual(r["incumbent_objective"], 11)
        self.assertEqual(r["objective_bound"], 10.2)

    def test_false_optimal_fractional_incumbent_rejected(self):
        r = _interpret(formulation(), {"x": 1}, self.raw(point=[0.5], value=0.5, bound=0.5), ["x"])
        self.assertEqual(r["status"], "numerical_error")
        self.assertIsNone(r["bound_min"])

    def test_open_gap_under_optimal_status_not_accepted(self):
        r = _interpret(formulation(), {"x": 1}, self.raw(bound=0, gap=1), ["x"])
        self.assertEqual(r["status"], "limit")

    def test_inconsistent_dual_bound_rejected(self):
        r = _interpret(formulation(), {"x": 1}, self.raw(bound=2), ["x"])
        self.assertEqual(r["status"], "numerical_error")

    def test_unknown_solver_status_not_infeasibility(self):
        raw = self.raw(status=4); raw.x = None; raw.fun = None
        self.assertEqual(_interpret(formulation(), {"x": 1}, raw, ["x"])["status"], "unknown")


class MilpComparisonTests(unittest.TestCase):
    def test_continuous_vs_integer_same_optimum_has_fractional_witness(self):
        integer = formulation([variable("x", "integer", 0, 1)])
        continuous = copy.deepcopy(integer); continuous["variables"][0]["domain"] = "continuous"
        r = execute({"op": "compare", "left": continuous, "right": integer})
        self.assertEqual(r["left_to_right"]["status"], "witness")
        self.assertEqual(r["right_to_left"]["status"], "contained_within_tolerance")
        w = r["left_to_right"]["point"]
        self.assertTrue(check_point(continuous, w)["feasible"])
        self.assertFalse(check_point(integer, w)["feasible"])

    def test_continuous_fixed_integer_is_not_false_domain_error(self):
        a = formulation([variable("x", "continuous", 1, 1)])
        b = formulation([variable("x", "integer", 1, 1)])
        r = execute({"op": "compare", "left": a, "right": b})
        self.assertEqual(r["left_to_right"]["status"], "contained_within_tolerance")

    def test_omission_and_overrestriction_with_same_integer_optimum(self):
        a = formulation([variable("x", "binary", None, None), variable("y", "binary", None, None)], coefficients={"x": 1})
        b = copy.deepcopy(a); b["constraints"] = [row("shared", {"x": 1, "y": 1}, "le", 1)]
        r = execute({"op": "compare", "left": a, "right": b})
        self.assertEqual(r["left_to_right"]["status"], "witness")
        self.assertEqual(r["right_to_left"]["status"], "contained_within_tolerance")

    def test_scaled_reordered_redundant_integer_formulations(self):
        a = formulation([variable("x", "integer", 0, 2), variable("y", "continuous", 0, 1)],
                        [row("cap", {"x": 1, "y": 1}, "le", 2)])
        b = copy.deepcopy(a); b["variables"].reverse()
        b["constraints"] = [row("renamed", {"x": 3, "y": 3}, "le", 6), row("redundant", {"x": 1}, "le", 5)]
        r = execute({"op": "compare", "left": a, "right": b})
        self.assertTrue(all(r[k]["status"] == "contained_within_tolerance" for k in ["left_to_right", "right_to_left"]))

    def test_opposite_preferences_checked_with_integer_decisions(self):
        a = formulation([variable("x", "binary", None, None), variable("y", "binary", None, None)],
                        [row("one", {"x": 1, "y": 1}, "eq", 1)], {"x": 2, "y": 1})
        b = copy.deepcopy(a); b["objective"]["coefficients"] = {"x": 1, "y": 2}
        r = execute({"op": "compare", "left": a, "right": b})
        self.assertEqual(r["preference"]["status"], "strict_reversal")

    def test_query_budget_cannot_certify_equivalence(self):
        m = formulation()
        r = execute({"op": "compare", "left": m, "right": m}, limits={**DEFAULT_LIMITS, "max_queries": 1})
        self.assertEqual(r["left_to_right"]["status"], "unknown")
        self.assertEqual(r["right_to_left"]["status"], "unknown")

    def test_unaligned_business_variables_unsupported(self):
        m = formulation(); n = copy.deepcopy(m); n["variables"][0]["meaning"] = "another quantity"
        self.assertEqual(execute({"op": "compare", "left": m, "right": n})["status"], "unsupported")


class MilpEvaluationTests(unittest.TestCase):
    def test_objective_match_not_semantic_success(self):
        a = formulation([variable("x", "binary", None, None), variable("y", "binary", None, None)], coefficients={"x": 1})
        b = copy.deepcopy(a); b["constraints"] = [row("cap", {"x": 1, "y": 1}, "le", 1)]
        r = evaluate(a, b)
        self.assertTrue(r["benchmark_success"])
        self.assertEqual(r["formulation_check"], "different")

    def test_matching_infeasible_is_status_only(self):
        m = formulation(constraints=[row("impossible", {}, "ge", 1)])
        r = evaluate(m, m)
        self.assertTrue(r["benchmark_success"])
        self.assertIsNone(r["objective_match_proxy"])
        self.assertEqual(r["formulation_check"], "unknown")

    def test_input_ambiguity_prevents_scoring_without_deleting_row(self):
        def forbidden(_): raise AssertionError("solver should not run")
        r = evaluate(formulation(), formulation(), solver=forbidden, input_status="unresolved_input_semantics")
        self.assertEqual(summarize([r])["success_rate_full_denominator"], 0)
        self.assertEqual(r["grade_reason"], "input_ambiguity")

    def test_invalid_candidate_not_dropped(self):
        r = evaluate("print('model')", formulation(), compare_formulation=False)
        self.assertFalse(r["benchmark_success"])
        self.assertEqual(summarize([r])["total_planned"], 1)

    def test_limit_with_matching_incumbent_is_unresolved(self):
        def solver(op):
            r = {"status": "optimal", "objective": 2, "objective_sense": "max", "objective_unit": "dollar"}
            if op["model"]["objective"]["offset"] == 1:
                r.update(status="limit", objective=None, incumbent_objective=2)
            return r
        r = evaluate(formulation(offset=1), formulation(), solver=solver, compare_formulation=False)
        self.assertIsNone(r["benchmark_success"])

    def test_reference_label_is_not_sent_to_solver(self):
        seen = []
        def solver(op):
            seen.append(op)
            return {"status": "optimal", "objective": 2, "objective_sense": "max", "objective_unit": "dollar"}
        label = {"schema": "optimization-reference-v1", "status": "optimal", "objective": 2,
                 "objective_sense": "max", "objective_unit": "dollar",
                 "provenance": {"source_sha256": "a"*64, "review_status": "audited", "review_note": "GOLD_SENTINEL"}}
        r = evaluate_against_label(formulation(), label, solver=solver)
        self.assertTrue(r["benchmark_success"])
        self.assertNotIn("GOLD_SENTINEL", canonical(seen))
        label["provenance"]["review_status"] = "unreviewed"
        r = evaluate_against_label(formulation(), label, solver=lambda op: self.fail("unreviewed label caused solve"))
        self.assertIsNone(r["benchmark_success"])

    def test_all_outcomes_in_denominator(self):
        rows = [{"benchmark_success": x, "denominator_included": True} for x in [True, False, None, None]]
        self.assertEqual(summarize(rows)["success_rate_full_denominator"], 0.25)
        self.assertEqual(summarize(rows)["unresolved"], 2)

    def test_batch_missing_outputs_and_unresolved_inputs_retained(self):
        planned = [{"id": "missing_output", "input_status": "ready"},
                   {"id": "no_reference", "input_status": "ready"},
                   {"id": "ambiguous", "input_status": "unresolved_input_semantics"}]
        result = evaluate_batch(planned, {}, {"missing_output": {"kind": "model", "value": formulation()}})
        self.assertEqual(result["summary"]["total_planned"], 3)
        self.assertEqual(result["summary"]["incorrect_proxy"], 1)
        self.assertEqual(result["summary"]["unresolved"], 2)

    def test_batch_duplicate_denominator_and_unplanned_inputs_rejected(self):
        entry = {"id": "p", "input_status": "ready"}
        with self.assertRaises(Invalid): evaluate_batch([entry, entry], {}, {})
        with self.assertRaises(Invalid): evaluate_batch([entry], {"unknown": formulation()}, {})

    def test_nonclosed_reference_cannot_mark_candidate_success(self):
        def solver(op): return {"status": "limit", "incumbent_objective": 2}
        result = evaluate(formulation(), formulation(), solver=solver, compare_formulation=False)
        self.assertIsNone(result["benchmark_success"])
        self.assertEqual(result["grade_reason"], "reference_not_certified")

    def test_matching_unbounded_label_is_separate_from_infeasible(self):
        label = {"schema": "optimization-reference-v1", "status": "unbounded", "objective": None,
                 "objective_sense": "max", "objective_unit": "dollar",
                 "provenance": {"source_sha256": "b"*64, "review_status": "audited", "review_note": "synthetic reference"}}
        result = evaluate_against_label(formulation(), label, solver=lambda op: {"status": "infeasible"})
        self.assertFalse(result["benchmark_success"])


if __name__ == "__main__": unittest.main()
