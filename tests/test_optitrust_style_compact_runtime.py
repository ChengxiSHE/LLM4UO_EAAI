from copy import deepcopy
import json
import unittest

from llm4or.optitrust_style_compact_runtime import (
    LANGUAGES,
    STAGES,
    VERSION,
    apply_review,
    run_optitrust_style_compact,
    stage_payload,
)
from llm4or.schema import digest


def public_problem():
    return {
        "id": "synthetic_compact",
        "profile": "description_parameters_v1",
        "text": "Choose one whole item to minimize a declared cost.",
        "parameters": [],
        "instances": [],
    }


def model(offset=0):
    return {
        "schema": "milp-v1",
        "variables": [{
            "id": "x",
            "meaning": "whether the item is selected",
            "unit": "item",
            "domain": "binary",
            "lower": 0,
            "upper": 1,
        }],
        "constraints": [{
            "id": "choose",
            "coefficients": {"x": 1},
            "sense": "eq",
            "rhs": 1,
        }],
        "objective": {
            "coefficients": {"x": 1},
            "sense": "min",
            "unit": "cost",
            "offset": offset,
        },
    }


def review(candidate, verdict="accept", edits=None):
    return {
        "schema": "optitrust-review-v1",
        "candidate_sha256": digest(candidate),
        "verdict": verdict,
        "edits": [] if edits is None else edits,
    }


class FakeGateway:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.registration = None

    def register(self, scope, calls, token_cap):
        self.registration = (scope, calls, token_cap)

    def request(self, scope, payload, prefix, replicate, slot):
        self.requests.append((scope, payload, prefix, replicate, slot))
        return {"text": self.responses.pop(0)}


class CompactRuntimeTests(unittest.TestCase):
    def test_ten_fixed_slots_do_not_copy_analysis_text_into_candidate(self):
        self.assertEqual(len(STAGES), 10)
        self.assertEqual(len(LANGUAGES), 5)
        state = {
            "components": "bounded components",
            "formulation": "bounded formulation",
            "analysis_hashes": {
                "components": "a" * 64,
                "formulation": "b" * 64,
            },
            "candidate": model(),
            "candidate_sha256": digest(model()),
        }
        candidate = stage_payload(public_problem(), 4, state)
        rendered = json.dumps(candidate, sort_keys=True)
        self.assertNotIn("bounded components", rendered)
        self.assertNotIn("bounded formulation", rendered)
        self.assertEqual(candidate["context"]["analysis_hashes"], state["analysis_hashes"])
        self.assertNotIn("modeling_language", candidate["context"])
        for slot, language in enumerate(LANGUAGES, start=5):
            payload = stage_payload(public_problem(), slot, state)
            self.assertEqual(payload["context"]["modeling_language"], language)
            self.assertEqual(payload["context"]["candidate_sha256"], digest(model()))
            self.assertEqual(payload["context"]["candidate"], model())
            self.assertNotIn("components", payload["context"])
            self.assertNotIn("formulation", payload["context"])

    def test_hash_bound_accept_and_bounded_typed_repair(self):
        candidate = model()
        limits = {"variables": 10, "constraints": 10, "nonzeros": 20, "serialized_bytes": 10_000}
        accepted = apply_review(candidate, review(candidate), language="Pyomo", resource_limits=limits)
        self.assertEqual(accepted["status"], "valid")
        self.assertEqual(accepted["model"], candidate)
        repaired_review = review(candidate, "repair", [{
            "op": "replace_objective",
            "value": {"coefficients": {"x": 2}, "sense": "min", "unit": "cost", "offset": 0},
        }])
        repaired = apply_review(candidate, repaired_review, language="Gurobipy", resource_limits=limits)
        self.assertEqual(repaired["status"], "valid")
        self.assertEqual(repaired["model"]["objective"]["coefficients"], {"x": 2})
        self.assertEqual(candidate["objective"]["coefficients"], {"x": 1})

    def test_stale_hash_duplicate_target_unknown_delete_and_resource_growth_fail_closed(self):
        candidate = model()
        limits = {"variables": 1, "constraints": 1, "nonzeros": 2, "serialized_bytes": 10_000}
        stale = review(candidate); stale["candidate_sha256"] = "0" * 64
        self.assertEqual(apply_review(candidate, stale, language="Pyomo", resource_limits=limits)["reason"], "stale_candidate_hash")
        duplicate = review(candidate, "repair", [
            {"op": "replace_objective", "value": candidate["objective"]},
            {"op": "replace_objective", "value": candidate["objective"]},
        ])
        self.assertEqual(apply_review(candidate, duplicate, language="Pyomo", resource_limits=limits)["reason"], "duplicate_edit_target")
        unknown = review(candidate, "repair", [{"op": "delete_constraint", "id": "missing"}])
        self.assertEqual(apply_review(candidate, unknown, language="Pyomo", resource_limits=limits)["reason"], "unknown_constraint")
        growth = review(candidate, "repair", [{
            "op": "upsert_constraint",
            "id": "extra",
            "value": {"id": "extra", "coefficients": {"x": 1}, "sense": "le", "rhs": 1},
        }])
        self.assertEqual(apply_review(candidate, growth, language="Pyomo", resource_limits=limits)["reason"], "resource_limit")
        oversized = review(candidate, "repair", [{
            "op": "replace_variable",
            "id": "x",
            "value": {**candidate["variables"][0], "meaning": "x" * 70_000},
        }])
        self.assertEqual(apply_review(candidate, oversized, language="Pyomo", resource_limits=limits)["reason"], "review_size_limit")

    def test_reference_is_loaded_after_all_reviews_and_three_valid_views_form_majority(self):
        candidate = model()
        responses = [
            json.dumps({"components": "compact components"}),
            json.dumps({"components": "reflected components"}),
            json.dumps({"formulation": "compact formulation"}),
            json.dumps({"formulation": "reflected formulation"}),
            json.dumps(candidate),
            json.dumps(review(candidate)),
            json.dumps(review(candidate)),
            json.dumps(review(candidate)),
            json.dumps(review(candidate, "reject")),
            json.dumps({"schema": "bad-review"}),
        ]
        gateway = FakeGateway(responses)
        loaded_at = []
        solver_calls = []

        def solve(operation, **_kwargs):
            solver_calls.append(deepcopy(operation["model"]))
            return {"status": "optimal", "objective": 1}

        result = run_optitrust_style_compact(
            public_problem(), gateway, "scope", 0, 1_000_000,
            solver=solve,
            solver_config={"solve_seconds": 1, "threads": 1, "wall_seconds": 2},
            resource_limits={"variables": 10, "constraints": 10, "nonzeros": 20, "serialized_bytes": 10_000},
            reference_loader=lambda: loaded_at.append(len(gateway.requests)) or {"optimum": 1, "solver_status": 2},
        )
        self.assertEqual(gateway.registration, ("scope", 10, 1_000_000))
        self.assertEqual([request[-1] for request in gateway.requests], list(range(10)))
        self.assertEqual(loaded_at, [10])
        self.assertEqual(len(solver_calls), 3)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["author_accept"])
        self.assertEqual(result["consensus"]["votes"], 3)
        self.assertEqual([view["status"] for view in result["views"]], ["optimal", "optimal", "optimal", "rejected", "invalid"])
        self.assertNotIn("compact components", json.dumps(result))
        self.assertNotIn("compact formulation", json.dumps(result))

    def test_oversized_analysis_terminates_as_method_failure_before_candidate(self):
        gateway = FakeGateway([json.dumps({"components": "x" * 8193})])
        result = run_optitrust_style_compact(
            public_problem(), gateway, "scope", 0, 1_000_000,
            solver=lambda *_args, **_kwargs: self.fail("solver called"),
            solver_config={"solve_seconds": 1, "threads": 1, "wall_seconds": 2},
            resource_limits={"variables": 10, "constraints": 10, "nonzeros": 20, "serialized_bytes": 10_000},
            reference_loader=lambda: self.fail("reference loaded"),
        )
        self.assertEqual(result["status"], "method_failure")
        self.assertEqual(result["reason"], "decomposition_output_invalid")
        self.assertEqual(len(gateway.requests), 1)


if __name__ == "__main__":
    unittest.main()
