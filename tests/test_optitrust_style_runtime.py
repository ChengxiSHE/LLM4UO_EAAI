import json
import unittest

from llm4or.optitrust_style_runtime import (
    LANGUAGES,
    STAGES,
    run_optitrust_style,
    stage_payload,
    strict_majority,
)


def public_problem():
    return {
        "id": "synthetic_rcpsp_001",
        "profile": "description_parameters_v1",
        "text": "Schedule two jobs to minimize the completion time.",
        "parameters": [],
        "instances": [],
    }


def model(offset):
    return {
        "schema": "milp-v1",
        "variables": [{
            "id": "x", "meaning": "selected amount", "unit": "job",
            "domain": "integer", "lower": 0, "upper": 1,
        }],
        "constraints": [],
        "objective": {
            "coefficients": {}, "sense": "min", "unit": "time",
            "offset": offset,
        },
    }


class FakeGateway:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.registration = None

    def register(self, scope, calls, tokens):
        self.registration = (scope, calls, tokens)

    def request(self, scope, payload, prefix, replicate, slot):
        self.requests.append((scope, payload, prefix, replicate, slot))
        return {"text": self.responses[slot]}


class OptiTrustStyleRuntimeTests(unittest.TestCase):
    def test_stage_payloads_keep_original_problem_and_fixed_slot_mapping(self):
        state = {
            "components": "components-v2",
            "formulation": "formulation-v2",
        }
        observed = []
        for slot in range(9):
            payload = stage_payload(public_problem(), slot, state)
            self.assertEqual(payload["problem"], public_problem())
            self.assertEqual(payload["context"]["step"], slot)
            observed.append(payload["context"]["stage"])
            self.assertEqual(
                payload["context"]["method"],
                "OptiTrust-style-safe-sidecar",
            )
        self.assertEqual(observed, list(STAGES))
        self.assertEqual(
            [
                stage_payload(public_problem(), slot, state)["context"]["modeling_language"]
                for slot in range(4, 9)
            ],
            list(LANGUAGES),
        )
        self.assertEqual(
            stage_payload(public_problem(), 2, state)["context"]["components"],
            "components-v2",
        )
        self.assertEqual(
            stage_payload(public_problem(), 4, state)["context"]["formulation"],
            "formulation-v2",
        )

    def test_strict_majority_accepts_three_matching_optima_and_two_invalid(self):
        result = strict_majority([
            {"language": "Pyomo", "status": "optimal", "objective": 10.0},
            {"language": "Gurobipy", "status": "optimal", "objective": 10.000001},
            {"language": "DOcplex", "status": "invalid", "objective": None},
            {"language": "CVXPY", "status": "optimal", "objective": 10.0},
            {"language": "PySCIPOpt", "status": "invalid", "objective": None},
        ], rtol=1e-5, atol=1e-6)
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["votes"], 3)
        self.assertEqual(result["languages"], ["CVXPY", "Gurobipy", "Pyomo"])
        self.assertEqual(result["objective"], 10.0)

    def test_strict_majority_rejects_two_two_one_split(self):
        result = strict_majority([
            {"language": "Pyomo", "status": "optimal", "objective": 10.0},
            {"language": "Gurobipy", "status": "optimal", "objective": 10.0},
            {"language": "DOcplex", "status": "optimal", "objective": 11.0},
            {"language": "CVXPY", "status": "optimal", "objective": 11.0},
            {"language": "PySCIPOpt", "status": "optimal", "objective": 12.0},
        ], rtol=1e-5, atol=1e-6)
        self.assertEqual(result, {
            "status": "no_majority", "votes": 2, "objective": None,
            "languages": [],
        })

    def test_malformed_decomposition_fails_before_later_slots_or_reference(self):
        gateway = FakeGateway(["not-json"] + [json.dumps(model(10))] * 8)
        loaded_at = []

        result = run_optitrust_style(
            public_problem(), gateway, "scope", 0, 999,
            solver=lambda operation, **kwargs: {"status": "optimal", "objective": 10},
            solver_config={"solve_seconds": 1, "threads": 1, "wall_seconds": 2},
            reference_loader=lambda: loaded_at.append(len(gateway.requests)) or {
                "optimum": 10, "solver_status": 2,
            },
        )

        self.assertEqual(result["status"], "method_failure")
        self.assertEqual(result["reason"], "decomposition_output_invalid")
        self.assertEqual([request[-1] for request in gateway.requests], [0])
        self.assertEqual(loaded_at, [])

    def test_candidate_schema_rejection_continues_and_reference_loads_after_slot_eight(self):
        responses = [
            json.dumps({"components": "components-v1"}),
            json.dumps({"components": "components-v2"}),
            json.dumps({"formulation": "formulation-v1"}),
            json.dumps({"formulation": "formulation-v2"}),
            json.dumps(model(10)),
            json.dumps(model(10)),
            json.dumps({"schema": "bad-model"}),
            json.dumps(model(10)),
            json.dumps(model(12)),
        ]
        gateway = FakeGateway(responses)
        loaded_at = []

        def solve(operation, **kwargs):
            return {
                "status": "optimal",
                "objective": operation["model"]["objective"]["offset"],
            }

        result = run_optitrust_style(
            public_problem(), gateway, "scope", 0, 999,
            solver=solve,
            solver_config={"solve_seconds": 1, "threads": 1, "wall_seconds": 2},
            reference_loader=lambda: loaded_at.append(len(gateway.requests)) or {
                "optimum": 10, "solver_status": 2,
            },
        )

        self.assertEqual(gateway.registration, ("scope", 9, 999))
        self.assertEqual([request[-1] for request in gateway.requests], list(range(9)))
        self.assertEqual(loaded_at, [9])
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["author_accept"])
        self.assertEqual(result["consensus"]["votes"], 3)
        self.assertEqual(
            [candidate["status"] for candidate in result["candidates"]],
            ["optimal", "optimal", "invalid", "optimal", "optimal"],
        )
        self.assertNotIn("components-v2", json.dumps(result))
        self.assertNotIn("formulation-v2", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
