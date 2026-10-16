import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from llm4or.formal_gateway import FormalGateway, validate_fresh_external_payload
from llm4or.formulationbench_same_knowledge import (
    SameKnowledgeError, build_capacity_material, load_request, offline_audit,
    parse_judgment, publish_private_requests, run_plan, score_run,
)


ROOT = Path(__file__).resolve().parents[1]
OBLIGATIONS = (
    "parameter_compatibility", "forward_feasibility", "backward_feasibility",
    "integrality_and_bounds", "index_quantifier_coverage", "objective_preservation",
)


def judgment(hashes=()):
    hashes = list(hashes)
    return {
        "schema": "llm4or-formulationbench-judgment-v1",
        "equivalent": True,
        "confidence": 80,
        "obligations": {key: "pass" for key in OBLIGATIONS},
        "evidence": {key: hashes[:1] for key in OBLIGATIONS},
    }


def response(payload, _body):
    facts = payload["view"].get("facts", [])
    if not facts:
        facts = [fact for obligation in payload["view"]["obligations"] for fact in obligation["facts"]]
    text = json.dumps(judgment([facts[0]["fact_sha256"]]), separators=(",", ":"))
    return {"text": text, "prompt_tokens": 100, "completion_tokens": 80,
            "total_tokens": 180, "finish_reason": "stop",
            "reported_model": "DeepSeek-V4-Flash"}


class SameKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.entries = build_capacity_material(ROOT)

    def test_strict_response_rejects_duplicate_unknown_missing_and_extra(self):
        allowed = {"a" * 64}
        valid = judgment(allowed)
        self.assertTrue(parse_judgment(json.dumps(valid), allowed)["equivalent"])
        duplicate = json.dumps(valid)[:-1] + ',"confidence":2}'
        with self.assertRaisesRegex(SameKnowledgeError, "duplicate_json_key"):
            parse_judgment(duplicate, allowed)
        invalid = json.loads(json.dumps(valid)); invalid["evidence"][OBLIGATIONS[0]] = ["b" * 64]
        with self.assertRaisesRegex(SameKnowledgeError, "evidence_hash"):
            parse_judgment(json.dumps(invalid), allowed)
        invalid = json.loads(json.dumps(valid)); del invalid["obligations"][OBLIGATIONS[0]]
        with self.assertRaisesRegex(SameKnowledgeError, "obligations"):
            parse_judgment(json.dumps(invalid), allowed)
        invalid = json.loads(json.dumps(valid)); invalid["free_text"] = "no"
        with self.assertRaisesRegex(SameKnowledgeError, "judgment_schema"):
            parse_judgment(json.dumps(invalid), allowed)

    def test_plan_is_eight_short_calls_same_fact_and_answer_free(self):
        self.assertEqual(self.plan["matrix"], {"capacity_cells": 8, "logical_requests": 8})
        self.assertEqual(self.plan["limits"]["max_completion_tokens"], 1024)
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"], 5)
        self.assertEqual(self.plan["resilience"]["max_attempts_per_request"], 3)
        by_case = {}
        for row in self.plan["cells"].values():
            by_case.setdefault(row["case_id"], []).append(row)
        self.assertEqual(len(by_case), 4)
        self.assertTrue(all(len(rows) == 2 and len({row["fact_multiset_sha256"] for row in rows}) == 1 for rows in by_case.values()))
        self.assertGreaterEqual(max(row["view_bytes"] for row in self.plan["cells"].values()), 61245)
        self.assertTrue(all(word not in json.dumps(self.plan).lower() for word in ('"label"', '"solution"', '"proof"', "api_key")))

    def test_gateway_accepts_only_exact_frozen_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root = temporary / "repo"; root.mkdir()
            # The request loader is independently tested in the end-to-end test.
            cell_id = sorted(self.plan["cells"])[0]
            raw = self.entries[f"requests/{cell_id}.json"]
            payload = json.loads(raw)
            scope = f"formulationbenchcapacity:FormulationBenchSameKnowledge:0:{cell_id}"
            validate_fresh_external_payload(self.plan, scope, payload, 0, 0)
            changed = json.loads(json.dumps(payload)); changed["context"]["representation"] = "changed"
            with self.assertRaisesRegex(Exception, "fresh_external_payload_changed"):
                validate_fresh_external_payload(self.plan, scope, changed, 0, 0)

    def test_offline_restart_reuses_checkpoints_and_fingerprints(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            publish_private_requests(temporary, self.entries)
            directory = temporary / "run"
            gateway = FormalGateway(ROOT, self.plan, offline=True, directory=directory, responder=response)
            first = run_plan(temporary, self.plan, directory, gateway, workers=5)
            before = gateway.summary()["physical_attempts"]
            second = run_plan(temporary, self.plan, directory, gateway, workers=5)
            after = gateway.summary()["physical_attempts"]
            self.assertEqual(first["status_counts"], {"completed": 8})
            self.assertEqual(second["new_items"], 0)
            self.assertEqual((before, after), (8, 8))
            self.assertTrue(score_run(self.plan, directory, restart_new_items=0)["capacity_gate"]["passed"])

    def test_retry_exhaustion_is_isolated_and_global_error_halts(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary); publish_private_requests(temporary, self.entries)
            isolated_plan = deepcopy(self.plan)
            isolated_plan["resilience"]["circuit_breaker_consecutive_failures"] = 99
            calls = {"n": 0}
            def unavailable(_payload, _body):
                calls["n"] += 1
                return {"error": "transport_ConnectionError"}
            gateway = FormalGateway(ROOT, isolated_plan, offline=True, directory=temporary / "retry", responder=unavailable)
            run = run_plan(temporary, isolated_plan, temporary / "retry", gateway, workers=5)
            self.assertEqual(run["status_counts"], {"infrastructure_unavailable": 8})
            self.assertLessEqual(gateway.summary()["physical_attempts"], 24)
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary); publish_private_requests(temporary, self.entries)
            def fatal(_payload, _body): return {"error": "provider_model_mismatch"}
            gateway = FormalGateway(ROOT, self.plan, offline=True, directory=temporary / "fatal", responder=fatal)
            with self.assertRaisesRegex(Exception, "global_halt"):
                run_plan(temporary, self.plan, temporary / "fatal", gateway, workers=5)

    def test_offline_audit_reconstructs_without_calls(self):
        audit = offline_audit(ROOT, self.plan, self.entries)
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["execution"]["api_calls"], 0)


if __name__ == "__main__":
    unittest.main()
