from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from llm4or import fresh_common38_optitrust_style as optitrust
from llm4or.formal_gateway import FormalGateway, RequestUnavailable
from llm4or.fresh_common38_optitrust_style_audit import (
    build_audit_from, publish_or_check,
)
from llm4or.schema import canonical


ROOT = Path(__file__).resolve().parents[1]


class FakeGateway:
    def __init__(self):
        self.started = []
        self.finished = []

    def work_started(self, scope):
        self.started.append(scope)

    def work_finished(self, scope, status, error=None):
        self.finished.append((scope, status, error))

    def summary(self):
        return {
            "physical_attempts": 342,
            "logical_requests": 342,
            "retry_attempts": 0,
            "failed_physical_attempts": 0,
            "reserved_or_reported_tokens": 3420,
            "logical_tokens": 3420,
            "halt": None,
        }


def recursive_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from recursive_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_keys(item)


class FreshCommon38OptiTrustStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = optitrust.build_plan(ROOT)

    def test_plan_binds_38_nine_slots_three_attempts_and_five_workers(self):
        self.assertEqual(len(self.plan["bindings"]), 38)
        method = self.plan["external_method"]
        self.assertEqual(method["name"], "OptiTrustStyle")
        self.assertEqual(method["max_calls"], 9)
        self.assertEqual(len(method["stage_slots"]), 9)
        self.assertEqual(self.plan["matrix"]["logical_requests"], 342)
        self.assertEqual(self.plan["limits"]["max_requests"], 1026)
        self.assertEqual(self.plan["resilience"]["max_attempts_per_request"], 3)
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"], 5)
        self.assertEqual(self.plan["model"], "DeepSeek-V4-Flash")
        prohibited = {
            "public_payload", "instance_data", "text", "objective", "point",
            "optimum", "reference", "api_key", "components", "formulation",
        }
        self.assertTrue(prohibited.isdisjoint(set(recursive_keys(self.plan))))

    def test_controller_resumes_and_continues_after_one_exhausted_request(self):
        calls = []
        references = []
        unavailable_id = self.plan["bindings"][0]["id"]
        failure_id = self.plan["bindings"][1]["id"]

        def fake_runner(public, gateway, scope, replicate, token_cap, **kwargs):
            calls.append(scope)
            if scope.endswith(unavailable_id):
                raise RequestUnavailable("request_exhausted:synthetic")
            if scope.endswith(failure_id):
                raise ValueError("synthetic_method_failure")
            references.append(kwargs["reference_loader"]())
            return {
                "status": "completed", "author_accept": False,
                "consensus": {"status": "no_majority", "votes": 2},
                "candidates": [],
            }

        gateway = FakeGateway()
        with tempfile.TemporaryDirectory() as directory:
            first = optitrust.run_plan(
                ROOT, self.plan, Path(directory), gateway,
                runner=fake_runner, workers=5,
            )
            second = optitrust.run_plan(
                ROOT, self.plan, Path(directory), gateway,
                runner=fake_runner, workers=5,
            )
        self.assertEqual(first["terminal"], 38)
        self.assertEqual(first["new_items"], 38)
        self.assertEqual(first["status_counts"]["infrastructure_unavailable"], 1)
        self.assertEqual(first["status_counts"]["method_failure"], 1)
        self.assertEqual(first["status_counts"]["completed"], 36)
        self.assertEqual(second["new_items"], 0)
        self.assertEqual(len(calls), 38)
        self.assertEqual(len(references), 36)

    def test_plan_reconstruction_and_worker_binding_fail_closed(self):
        changed = deepcopy(self.plan)
        changed["external_method"]["stage_slots"][4]["modeling_language"] = "changed"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "plan_reconstruction"):
                optitrust.run_plan(ROOT, changed, Path(directory), FakeGateway())
            with self.assertRaisesRegex(ValueError, "worker_binding"):
                optitrust.run_plan(ROOT, self.plan, Path(directory), FakeGateway(), workers=4)

    def test_scoring_retains_full_denominator_and_is_recursively_body_free(self):
        cells = []
        for index, row in enumerate(self.plan["bindings"]):
            if index == 36:
                status, record = "method_failure", None
            elif index == 37:
                status, record = "infrastructure_unavailable", None
            else:
                status = "completed"
                record = {
                    "status": "completed", "author_accept": index < 10,
                    "consensus": {"status": "selected", "votes": 3},
                    "candidates": [{"objective": 1.0, "model_sha256": "a" * 64}],
                }
            cells.append({
                "id": row["id"], "family": row["family"],
                "status": status, "record": record,
            })
        result = optitrust.score_cells(self.plan, cells, FakeGateway().summary())
        aggregate = result["aggregate"]
        self.assertEqual(aggregate["planned"], 38)
        self.assertEqual(aggregate["correct"], 10)
        self.assertEqual(aggregate["method_failure"], 1)
        self.assertEqual(aggregate["infrastructure_unavailable"], 1)
        self.assertEqual(aggregate["accuracy"], 10 / 38)
        prohibited = {
            "request", "response", "text", "code", "objective", "point",
            "optimum", "reference", "api_key", "components", "formulation",
            "candidates",
        }
        self.assertTrue(prohibited.isdisjoint(set(recursive_keys(result))))
        rendered = json.dumps(result, sort_keys=True)
        self.assertNotIn("a" * 64, rendered)

    def test_exclusive_publisher_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            optitrust.publish_new(path, {"ok": True})
            with self.assertRaisesRegex(ValueError, "output_exists"):
                optitrust.publish_new(path, {"ok": True})

    def test_read_only_audit_reconstructs_offline_ledger_and_check_mode_bytes(self):
        model = {
            "schema": "milp-v1",
            "variables": [{
                "id": "x", "meaning": "fixed synthetic value", "unit": "unit",
                "domain": "binary", "lower": 0, "upper": 0,
            }],
            "constraints": [],
            "objective": {
                "coefficients": {}, "sense": "min", "unit": "unit", "offset": 0,
            },
        }

        def responder(payload, _body):
            stage = payload["context"]["stage"]
            if stage in {"decomposition", "decomposition_reflection"}:
                text = json.dumps({"components": "synthetic checked components"})
            elif stage in {"formulation", "formulation_reflection"}:
                text = json.dumps({"formulation": "synthetic checked formulation"})
            else:
                text = json.dumps(model)
            return {
                "text": text, "prompt_tokens": 10, "completion_tokens": 10,
                "total_tokens": 20, "finish_reason": "stop",
            }

        def solver(operation, **_kwargs):
            return {
                "status": "optimal",
                "objective": operation["model"]["objective"]["offset"],
            }

        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            directory = temporary / "offline-run"
            plan_path = temporary / "plan.json"
            result_path = temporary / "result.json"
            audit_path = temporary / "audit.json"
            plan_path.write_text(canonical(self.plan) + "\n")
            gateway = FormalGateway(
                ROOT, self.plan, offline=True, directory=directory,
                responder=responder,
            )
            summary = optitrust.run_plan(
                ROOT, self.plan, directory, gateway, solver=solver, workers=5,
            )
            self.assertEqual(summary["terminal"], 38)
            result = optitrust.score_cells(
                self.plan, optitrust.load_cells(self.plan, directory),
                optitrust.ledger_summary(directory),
            )
            result_path.write_text(canonical(result) + "\n")
            with patch(
                "llm4or.formal_gateway.load_credential",
                side_effect=AssertionError("audit touched credential"),
            ):
                audit = build_audit_from(
                    ROOT, self.plan, plan_path, directory, result_path,
                    expected_offline=True,
                )
            self.assertEqual(audit["status"], "passed")
            self.assertEqual(audit["checks"]["ledger"]["logical_slots"], 342)
            self.assertEqual(audit["checks"]["accounting"]["physical_attempts"], 342)
            self.assertEqual(
                audit["execution"], {"new_api_calls": 0, "new_solver_calls": 0},
            )
            publish_or_check(audit_path, audit, check=False)
            publish_or_check(audit_path, audit, check=True)
            audit_path.write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "audit_byte_mismatch"):
                publish_or_check(audit_path, audit, check=True)
            prohibited = {
                "request", "response", "text", "code", "objective", "point",
                "optimum", "reference", "api_key", "components", "formulation",
                "candidates",
            }
            self.assertTrue(prohibited.isdisjoint(set(recursive_keys(audit))))

    def test_cli_entrypoints_exist_and_are_plan_frozen(self):
        scripts = {
            "scripts/freeze_fresh_common38_optitrust_style.py",
            "scripts/run_fresh_common38_optitrust_style.py",
            "scripts/score_fresh_common38_optitrust_style.py",
            "scripts/audit_fresh_common38_optitrust_style.py",
        }
        self.assertTrue(all((ROOT / path).is_file() for path in scripts))
        self.assertTrue(scripts.issubset(self.plan["frozen_files"]))


if __name__ == "__main__":
    unittest.main()
