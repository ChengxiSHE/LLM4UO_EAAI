from copy import deepcopy
import json
import unittest

from llm4or.formal_gateway import RequestUnavailable
from llm4or.optitrust_style_indexed_runtime import (
    LANGUAGES, STAGES, VERSION, apply_ir_review,
    run_optitrust_style_indexed, stage_payload,
)
from llm4or.schema import digest


LIMITS = {
    "variables": 10, "constraints": 10, "nonzeros": 20,
    "serialized_bytes": 10_000, "expansion_steps": 2_000,
}


def public_problem():
    return {
        "id": "synthetic_indexed", "profile": "description_parameters_v1",
        "text": "Choose exactly one item with minimum declared cost.",
        "parameters": [{"symbol": "instance_data", "definition": "public structured instance", "shape": []}],
        "instances": [{"id": "instance_0000", "input": {"instance_data": {"n": 2, "cost": [3, 1]}}}],
    }


def candidate_ir(offset=0):
    return {
        "schema": "indexed-milp-ir-v1", "data_parameter": "instance_data",
        "sets": [{"id": "I", "kind": "range", "start": 0, "stop": {"data": ["n"]}}],
        "variables": [{
            "id": "x", "meaning": "chosen item", "unit": "item", "domain": "binary",
            "forall": [{"name": "i", "set": "I"}], "where": True, "lower": 0, "upper": 1,
        }],
        "constraints": [{
            "id": "choose", "forall": [], "where": True,
            "terms": [{"family": "x", "indices": [{"env": "i"}], "coefficient": 1,
                       "sum": [{"name": "i", "set": "I"}], "where": True}],
            "sense": "eq", "rhs": 1,
        }],
        "objective": {
            "terms": [{"family": "x", "indices": [{"env": "i"}],
                       "coefficient": {"data": ["cost", {"env": "i"}]},
                       "sum": [{"name": "i", "set": "I"}], "where": True}],
            "sense": "min", "unit": "cost", "offset": offset,
        },
    }


def review(ir, verdict="accept", patches=None):
    return {
        "schema": "optitrust-ir-review-v1", "candidate_sha256": digest(ir),
        "verdict": verdict, "patches": [] if patches is None else patches,
    }


class FakeGateway:
    def __init__(self, responses, unavailable_slots=()):
        self.responses = list(responses)
        self.unavailable_slots = set(unavailable_slots)
        self.requests = []
        self.registration = None

    def register(self, scope, calls, token_cap):
        self.registration = (scope, calls, token_cap)

    def request(self, scope, payload, prefix, replicate, slot):
        self.requests.append((scope, payload, prefix, replicate, slot))
        if slot in self.unavailable_slots:
            raise RequestUnavailable("request_unavailable:synthetic")
        return {"text": self.responses.pop(0)}


class IndexedRuntimeTests(unittest.TestCase):
    def test_payload_uses_compact_ir_and_hash_bound_reviews_without_analysis_text(self):
        self.assertEqual(len(STAGES), 10)
        state = {
            "components": "private components", "formulation": "private outline",
            "analysis_hashes": {
                "slot_0_components": "a" * 64, "slot_1_components": "b" * 64,
                "slot_2_formulation": "c" * 64, "slot_3_formulation": "d" * 64,
            },
            "candidate_ir": candidate_ir(), "candidate_sha256": digest(candidate_ir()),
            "canonical_admitted": True, "canonical_admission_error": None,
        }
        canonical = stage_payload(public_problem(), 4, state)
        rendered = json.dumps(canonical, sort_keys=True)
        self.assertNotIn("private components", rendered)
        self.assertNotIn("private outline", rendered)
        self.assertEqual(canonical["context"]["safe_execution_adapter"], "indexed_milp_ir_v1")
        for slot, language in enumerate(LANGUAGES, start=5):
            payload = stage_payload(public_problem(), slot, state)
            self.assertEqual(payload["context"]["modeling_language"], language)
            self.assertEqual(payload["context"]["candidate_ir"], candidate_ir())
            self.assertEqual(payload["context"]["candidate_sha256"], digest(candidate_ir()))
            self.assertTrue(payload["context"]["candidate_admitted"])
            self.assertIsNone(payload["context"]["candidate_admission_error"])

    def test_accept_and_bounded_replacement_patch_recompile_through_trusted_interpreter(self):
        data = {"n": 2, "cost": [3, 1]}
        ir = candidate_ir()
        accepted = apply_ir_review(ir, review(ir), data=data, language="Pyomo", resource_limits=LIMITS)
        self.assertEqual(accepted["status"], "valid")
        self.assertEqual(accepted["model"]["objective"]["offset"], 0.0)
        patched = review(ir, "repair", [{
            "op": "replace", "path": ["objective", "offset"], "value": 2,
        }])
        repaired = apply_ir_review(ir, patched, data=data, language="Gurobipy", resource_limits=LIMITS)
        self.assertEqual(repaired["status"], "valid")
        self.assertEqual(repaired["model"]["objective"]["offset"], 2.0)
        self.assertEqual(ir["objective"]["offset"], 0)

    def test_stale_hash_duplicate_patch_unknown_path_and_invalid_repair_fail_closed(self):
        data = {"n": 2, "cost": [3, 1]}
        ir = candidate_ir()
        stale = review(ir); stale["candidate_sha256"] = "0" * 64
        self.assertEqual(apply_ir_review(ir, stale, data=data, language="Pyomo", resource_limits=LIMITS)["reason"], "stale_candidate_hash")
        duplicate = review(ir, "repair", [
            {"op": "replace", "path": ["objective", "offset"], "value": 1},
            {"op": "replace", "path": ["objective", "offset"], "value": 2},
        ])
        self.assertEqual(apply_ir_review(ir, duplicate, data=data, language="Pyomo", resource_limits=LIMITS)["reason"], "duplicate_patch_path")
        missing = review(ir, "repair", [{"op": "replace", "path": ["missing"], "value": 1}])
        self.assertEqual(apply_ir_review(ir, missing, data=data, language="Pyomo", resource_limits=LIMITS)["reason"], "unknown_patch_path")
        invalid = review(ir, "repair", [{"op": "replace", "path": ["schema"], "value": "bad"}])
        self.assertIn("ir_schema", apply_ir_review(ir, invalid, data=data, language="Pyomo", resource_limits=LIMITS)["reason"])

    def test_unavailable_review_becomes_abstention_and_does_not_erase_canonical_ir(self):
        ir = candidate_ir()
        responses = [
            json.dumps({"components": "components"}),
            json.dumps({"components": "reflected"}),
            json.dumps({"formulation": "outline"}),
            json.dumps({"formulation": "reflected outline"}),
            json.dumps(ir),
            *[json.dumps(review(ir)) for _ in range(4)],
        ]
        gateway = FakeGateway(responses, unavailable_slots={5})
        reference_at = []
        result = run_optitrust_style_indexed(
            public_problem(), gateway, "scope", 0, 100_000,
            solver=lambda operation, **kwargs: {"status": "optimal", "objective": 1},
            solver_config={"solve_seconds": 1, "threads": 1, "wall_seconds": 2},
            resource_limits=LIMITS,
            reference_loader=lambda: reference_at.append(len(gateway.requests)) or {"optimum": 1, "solver_status": 2},
        )
        self.assertEqual(gateway.registration, ("scope", 10, 100_000))
        self.assertEqual(reference_at, [10])
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["author_accept"])
        self.assertEqual(result["review_abstentions"], 1)
        self.assertEqual([view["status"] for view in result["views"]].count("abstained"), 1)
        self.assertEqual(result["consensus"]["votes"], 4)

    def test_invalid_canonical_ir_is_method_failure_before_reference(self):
        bad = candidate_ir(); bad["schema"] = "bad"
        gateway = FakeGateway([
            json.dumps({"components": "components"}), json.dumps({"components": "reflected"}),
            json.dumps({"formulation": "outline"}), json.dumps({"formulation": "reflected"}),
            json.dumps(bad),
        ])
        result = run_optitrust_style_indexed(
            public_problem(), gateway, "scope", 0, 100_000,
            solver=lambda *_args, **_kwargs: self.fail("solver called"),
            solver_config={"solve_seconds": 1, "threads": 1, "wall_seconds": 2},
            resource_limits=LIMITS, reference_loader=lambda: self.fail("reference loaded"),
        )
        self.assertEqual(result["status"], "method_failure")
        self.assertEqual(result["reason"], "canonical_ir_invalid")
        self.assertEqual(len(gateway.requests), 5)

    def test_surface_valid_but_uncompilable_canonical_can_be_repaired_by_reviewers(self):
        bad = candidate_ir()
        good_variable = deepcopy(bad["variables"][0])
        bad["variables"][0] = {}
        patch_review = review(bad, "repair", [{
            "op": "replace", "path": ["variables", 0], "value": good_variable,
        }])
        responses = [
            json.dumps({"components": "components"}), json.dumps({"components": "reflected"}),
            json.dumps({"formulation": "outline"}), json.dumps({"formulation": "reflected"}),
            json.dumps(bad), *[json.dumps(patch_review) for _ in range(5)],
        ]
        gateway = FakeGateway(responses)
        result = run_optitrust_style_indexed(
            public_problem(), gateway, "scope", 0, 100_000,
            solver=lambda operation, **kwargs: {"status": "optimal", "objective": 1},
            solver_config={"solve_seconds": 1, "threads": 1, "wall_seconds": 2},
            resource_limits=LIMITS,
            reference_loader=lambda: {"optimum": 1, "solver_status": 2},
        )
        self.assertEqual(result["status"], "complete")
        self.assertFalse(result["canonical_admitted"])
        self.assertIsNone(result["canonical_model_sha256"])
        self.assertEqual(result["consensus"]["votes"], 5)
        self.assertTrue(result["author_accept"])


if __name__ == "__main__":
    unittest.main()
