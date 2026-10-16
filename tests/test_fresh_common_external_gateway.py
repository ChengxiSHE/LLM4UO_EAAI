import unittest

from llm4or.benchmark_inputs import payload_sha256
from llm4or.formal_gateway import (
    fresh_external_scope_spec,
    validate_fresh_external_payload,
)
from llm4or.optitrust_style_runtime import LANGUAGES, STAGES, VERSION, stage_payload


PUBLIC = {
    "id": "fresh_case",
    "profile": "description_parameters_v1",
    "text": "Choose a feasible integer model.",
    "parameters": [],
    "instances": [],
}


def plan(method="BIND"):
    if method == "BIND":
        stage, calls, version = "freshbind", 3, "text2opt-bind-common-backbone-v1"
    elif method == "Base":
        stage, calls, version = "freshbase", 1, "text2opt-v9-confirmation-runtime-v1"
    elif method == "OptiTrustStyle":
        stage, calls, version = "freshoptitrust", 9, VERSION
    else:
        stage, calls, version = "freshcoe", 11, "coe-official-forward-prompts-v1"
    return {
        "kind": "fresh_common_external",
        "replicates": [0],
        "public_inputs": {PUBLIC["id"]: payload_sha256(PUBLIC)},
        "runtime_version": version,
        "external_method": {
            "name": method,
            "scope_stage": stage,
            "max_calls": calls,
            "snapshot": "current" if method == "CoE" else None,
            "stage_slots": [
                {
                    "stage": stage_name,
                    "modeling_language": LANGUAGES[index - 4] if index >= 4 else None,
                }
                for index, stage_name in enumerate(STAGES)
            ] if method == "OptiTrustStyle" else None,
        },
        "token_cap": 2_000_000,
    }


class FreshExternalContractTests(unittest.TestCase):
    def test_bind_scope_and_budget_are_exact(self):
        spec = fresh_external_scope_spec(
            plan(), "freshbind:BIND:0:fresh_case", 3, 2_000_000,
        )
        self.assertEqual(spec["problem_id"], "fresh_case")
        with self.assertRaisesRegex(Exception, "scope_not_authorized"):
            fresh_external_scope_spec(plan(), "freshbind:BIND:0:fresh_case", 2, 2_000_000)

    def test_coe_allows_eleven_slots_but_no_twelfth(self):
        p = plan("CoE")
        fresh_external_scope_spec(p, "freshcoe:CoE:0:fresh_case", 11, 2_000_000)
        with self.assertRaisesRegex(Exception, "request_slot_limit"):
            validate_fresh_external_payload(
                p, "freshcoe:CoE:0:fresh_case", self.coe_payload(), 0, 11,
            )

    def test_bind_payload_binds_public_hash_round_and_transport(self):
        p = plan()
        payload = self.bind_payload()
        validate_fresh_external_payload(p, "freshbind:BIND:0:fresh_case", payload, 0, 0)
        payload["context"]["round"] = 2
        with self.assertRaisesRegex(Exception, "payload_changed"):
            validate_fresh_external_payload(p, "freshbind:BIND:0:fresh_case", payload, 0, 0)

    def test_coe_payload_binds_snapshot_and_slot_sequence(self):
        p = plan("CoE")
        validate_fresh_external_payload(p, "freshcoe:CoE:0:fresh_case", self.coe_payload(), 0, 0)
        bad = self.coe_payload()
        bad["context"]["snapshot"] = "paper"
        with self.assertRaisesRegex(Exception, "payload_changed"):
            validate_fresh_external_payload(p, "freshcoe:CoE:0:fresh_case", bad, 0, 0)

    def test_base_payload_binds_single_answer_blind_initial_request(self):
        p = plan("Base")
        payload = self.base_payload()
        validate_fresh_external_payload(p, "freshbase:Base:0:fresh_case", payload, 0, 0)
        bad = self.base_payload()
        bad["context"] = {"repair": True}
        with self.assertRaisesRegex(Exception, "payload_changed"):
            validate_fresh_external_payload(p, "freshbase:Base:0:fresh_case", bad, 0, 0)
        with self.assertRaisesRegex(Exception, "request_slot_limit"):
            validate_fresh_external_payload(p, "freshbase:Base:0:fresh_case", payload, 0, 1)

    def test_optitrust_style_accepts_exact_nine_stage_and_language_slots(self):
        p = plan("OptiTrustStyle")
        state = {"components": "checked components", "formulation": "checked formulation"}
        for slot in range(9):
            validate_fresh_external_payload(
                p, "freshoptitrust:OptiTrustStyle:0:fresh_case",
                stage_payload(PUBLIC, slot, state), 0, slot,
            )

    def test_optitrust_style_rejects_stage_language_hash_slot_and_context_drift(self):
        p = plan("OptiTrustStyle")
        state = {"components": "checked components", "formulation": "checked formulation"}
        scope = "freshoptitrust:OptiTrustStyle:0:fresh_case"
        cases = []
        wrong_stage = stage_payload(PUBLIC, 4, state)
        wrong_stage["context"]["stage"] = "candidate_Gurobipy"
        cases.append((wrong_stage, 4))
        wrong_language = stage_payload(PUBLIC, 4, state)
        wrong_language["context"]["modeling_language"] = "Gurobipy"
        cases.append((wrong_language, 4))
        wrong_public = stage_payload(PUBLIC, 4, state)
        wrong_public["problem"] = {**PUBLIC, "text": "changed"}
        cases.append((wrong_public, 4))
        wrong_slot = stage_payload(PUBLIC, 4, state)
        cases.append((wrong_slot, 5))
        extra_context = stage_payload(PUBLIC, 4, state)
        extra_context["context"]["unexpected"] = True
        cases.append((extra_context, 4))
        for payload, slot in cases:
            with self.subTest(slot=slot, context=payload["context"]):
                with self.assertRaisesRegex(Exception, "payload_changed"):
                    validate_fresh_external_payload(p, scope, payload, 0, slot)

    def test_optitrust_style_rejects_noncanonical_frozen_slot_map(self):
        p = plan("OptiTrustStyle")
        p["external_method"]["stage_slots"][4]["stage"] = "candidate_Gurobipy"
        payload = stage_payload(
            PUBLIC, 4,
            {"components": "checked components", "formulation": "checked formulation"},
        )
        payload["context"]["stage"] = "candidate_Gurobipy"
        with self.assertRaisesRegex(Exception, "payload_changed"):
            validate_fresh_external_payload(
                p, "freshoptitrust:OptiTrustStyle:0:fresh_case", payload, 0, 4,
            )

    @staticmethod
    def bind_payload():
        return {
            "version": "text2opt-bind-common-backbone-v1",
            "instruction": "official prompt",
            "problem": PUBLIC,
            "context": {
                "method": "Text2Opt/BIND",
                "upstream_mode": "instance_data",
                "round": 1,
                "transport_adapter": "stateless_antchat_chat_completions",
            },
            "output_contract": {"code": "complete code"},
            "response_schema": {"type": "object"},
        }

    @staticmethod
    def coe_payload():
        return {
            "version": "coe-official-forward-prompts-v1",
            "instruction": "official prompt",
            "problem": PUBLIC,
            "context": {
                "method": "Chain-of-Experts",
                "snapshot": "current",
                "stage": "conductor",
                "step": 0,
            },
            "output_contract": {"text": "complete response"},
            "response_schema": {"type": "object"},
        }

    @staticmethod
    def base_payload():
        return {
            "version": "text2opt-v9-confirmation-runtime-v1",
            "instruction": "frozen direct formulation prompt",
            "problem": PUBLIC,
            "context": {},
            "output_contract": {"schema": "milp-v1"},
            "response_schema": {"type": "object"},
        }


if __name__ == "__main__":
    unittest.main()
