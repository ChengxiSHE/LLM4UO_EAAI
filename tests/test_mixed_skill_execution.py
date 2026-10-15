import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from llm4or.mixed_skill_execution import execute_mixed_record
from llm4or.mixed_skill_router import OR_DEBUG_ROUTE, TSP_ROUTE
from scripts import run_mixed_skill_confirmation as mixed_runner


class MixedSkillExecutionTests(unittest.TestCase):
    def test_delegates_tsp_and_compacts_semantic_evidence(self) -> None:
        public_text = "Thirteen public nodes."
        calls = []

        def tsp_executor(text, size):
            calls.append((text, size))
            return {
                "status": "optimal",
                "adopted": True,
                "semantic_evidence": {"b": 2, "a": 1},
            }

        record = {
            "record_id": "tsp-1",
            "source": "tsp",
            "public_envelope": {
                "public_text": public_text,
                "question_sha256": hashlib.sha256(public_text.encode()).hexdigest(),
                "size": 13,
            },
        }
        result = execute_mixed_record(
            record,
            model_root=Path("unused"),
            workspace=Path("unused"),
            tsp_executor=tsp_executor,
        )

        self.assertEqual(calls, [(public_text, 13)])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["route"], TSP_ROUTE)
        self.assertEqual(
            result["output"],
            {
                "status": "optimal",
                "adopted": True,
                "semantic_evidence_sha256": "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777",
            },
        )

    def test_delegates_or_debug_with_outer_id_only_after_routing(self) -> None:
        guard_inputs = []
        executor_rows = []
        envelope = {
            "problem_nl": "Repair a public model.",
            "model_file": "models/example.mps",
            "mps_sha256": "a" * 64,
        }

        def router(value):
            guard_inputs.append(value)
            return {"route": OR_DEBUG_ROUTE, "reason": "unique_public_guard"}

        def or_executor(row, *, model_root, workspace):
            executor_rows.append(row)
            return {"problem_id": row["problem_id"], "status": "complete"}

        result = execute_mixed_record(
            {"record_id": "or-1", "source": "or_debug", "public_envelope": envelope},
            model_root=Path("model-root"),
            workspace=Path("workspace"),
            router=router,
            or_debug_executor=or_executor,
        )

        self.assertEqual(guard_inputs, [envelope])
        self.assertNotIn("problem_id", guard_inputs[0])
        self.assertEqual(executor_rows, [{"problem_id": "or-1", **envelope}])
        self.assertEqual(result["output"], {"problem_id": "or-1", "status": "complete"})

    def test_abstention_calls_neither_executor(self) -> None:
        calls = []

        def fail_if_called(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("executor must not be called")

        result = execute_mixed_record(
            {"record_id": "bad", "source": "unknown", "public_envelope": {}},
            model_root=Path("unused"),
            workspace=Path("unused"),
            tsp_executor=fail_if_called,
            or_debug_executor=fail_if_called,
        )

        self.assertEqual(calls, [])
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["route"])

    def test_executor_exception_is_localized_without_message(self) -> None:
        public_text = "Thirteen public nodes."

        def broken_executor(text, size):
            raise RuntimeError("sensitive path must not enter output")

        result = execute_mixed_record(
            {
                "record_id": "tsp-broken",
                "source": "tsp",
                "public_envelope": {
                    "public_text": public_text,
                    "question_sha256": hashlib.sha256(public_text.encode()).hexdigest(),
                    "size": 13,
                },
            },
            model_root=Path("unused"),
            workspace=Path("unused"),
            tsp_executor=broken_executor,
        )

        self.assertEqual(result["status"], "execution_failed")
        self.assertEqual(result["reason"], "RuntimeError")
        self.assertNotIn("sensitive", str(result))

    def test_wrong_or_debug_content_hash_fails_before_solver_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "models").mkdir()
            (root / "models/example.mps").write_text("actual content", encoding="utf-8")
            result = execute_mixed_record(
                {
                    "record_id": "or-bad-hash",
                    "source": "or_debug",
                    "public_envelope": {
                        "problem_nl": "Repair a public model.",
                        "model_file": "models/example.mps",
                        "mps_sha256": "b" * 64,
                    },
                },
                model_root=root,
                workspace=root / "work",
            )

        self.assertEqual(result["route"], OR_DEBUG_ROUTE)
        self.assertEqual(result["status"], "execution_failed")
        self.assertEqual(result["reason"], "ValueError")

    def test_runner_preserves_bundle_order_and_assigns_distinct_workspaces(self) -> None:
        records = [
            {"record_id": "second", "source": "tsp", "public_envelope": {}},
            {"record_id": "first", "source": "or_debug", "public_envelope": {}},
        ]
        seen = []

        def fake_execute(record, *, model_root, workspace):
            seen.append((record["record_id"], workspace.name))
            return {"record_id": record["record_id"], "status": "complete"}

        with tempfile.TemporaryDirectory() as tmp:
            outputs = mixed_runner.run_records(
                records,
                model_root=Path(tmp) / "models",
                workspace_root=Path(tmp) / "work",
                execute=fake_execute,
                max_workers=2,
            )

        self.assertEqual([row["record_id"] for row in outputs], ["second", "first"])
        self.assertEqual({workspace for _record, workspace in seen}, {"000000", "000001"})

    def test_runner_direct_cli_can_import_project_package(self) -> None:
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "scripts/run_mixed_skill_confirmation.py", "--help"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_publication_never_replaces_a_competing_terminal_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "terminal.json"
            temporary = root / "candidate.tmp"
            output.write_text("competing", encoding="utf-8")
            temporary.write_text("candidate", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                mixed_runner.publish_new(temporary, output)

            self.assertEqual(output.read_text(encoding="utf-8"), "competing")

    def test_output_reservation_is_exclusive_and_cleaned_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "terminal.json"
            with mixed_runner.reserve_output(output):
                with self.assertRaises(FileExistsError):
                    with mixed_runner.reserve_output(output):
                        pass
            with mixed_runner.reserve_output(output):
                self.assertFalse(output.exists())

    def test_cli_rejects_root_different_from_loaded_checkout(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_mixed_skill_confirmation.py",
                    "--root",
                    tmp,
                    "--output",
                    str(Path(tmp) / "out.json"),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("must equal the loaded script checkout", completed.stderr)

    def test_code_pin_verifier_rejects_each_transitive_tsp_dependency_change(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        transitive = {
            "llm4or/gurobi_cli_solver.py",
            "llm4or/milp_schema.py",
            "llm4or/milp_solver.py",
            "llm4or/schema.py",
            "llm4or/tsp_constraint_skill.py",
            "llm4or/tsp_graph_exact.py",
            "llm4or/tsp_public_graph.py",
            "llm4or/tsp_static_controller.py",
            "llm4or/tsp_typed_graph.py",
        }
        self.assertTrue(transitive.issubset(mixed_runner.CODE_SHA256))
        for changed in sorted(transitive):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for relative in mixed_runner.CODE_SHA256:
                    destination = root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(project_root / relative, destination)
                with (root / changed).open("ab") as handle:
                    handle.write(b"\n# changed\n")

                with self.assertRaisesRegex(ValueError, changed):
                    mixed_runner.verify_code_pins(root)

    def test_git_package_contains_public_audit_prerequisites(self) -> None:
        root = Path(__file__).resolve().parents[1]
        tracked = set(
            subprocess.run(
                ["git", "ls-files", "--cached"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
        )
        required = {
            ".gitmodules",
            "experiments/or_debug_confirmation_public_bundle_20261014.json",
            "experiments/public_projections/mixed_skill_confirmation_bundle_projection_20261015.json",
            "results/public_projections/mixed_skill_confirmation_outputs_projection_20261015.json",
            "results/public_projections/or_debug_confirmation_method_outputs_projection_20261015.json",
            "results/public_projections/tsp_constraint_confirmation_candidates_projection_20261015.json",
            "results/public_projections/tsp_constraint_confirmation_public_projection_20261015.json",
            "llm4or/or_debug_evolved_skill.py",
            "llm4or/or_debug_gurobi.py",
            "llm4or/or_debug_iis_control.py",
            "llm4or/or_debug_mps.py",
            "llm4or/or_debug_mps_inspect.py",
            "llm4or/or_debug_public_runner.py",
            "llm4or/tsp_constraint_skill.py",
            "llm4or/tsp_constraint_skill_scalable.py",
            "llm4or/tsp_graph_exact.py",
            "llm4or/tsp_public_graph.py",
            "llm4or/tsp_scalable_exact.py",
            "llm4or/tsp_static_controller.py",
            "llm4or/tsp_typed_graph.py",
            "vendor/solver-in-the-loop",
        }
        public_bundle = json.loads(
            (root / "experiments/or_debug_confirmation_public_bundle_20261014.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(required - tracked, set())
        staged_submodule = subprocess.run(
            ["git", "ls-files", "--stage", "vendor/solver-in-the-loop"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(
            staged_submodule,
            "160000 c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010 0\tvendor/solver-in-the-loop",
        )
        vendor_tracked = set(
            subprocess.run(
                ["git", "-C", "vendor/solver-in-the-loop", "ls-files"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
        )
        required_models = {
            f"or_debug_bench/{row['model_file']}" for row in public_bundle["records"]
        }
        self.assertEqual(required_models - vendor_tracked, set())


if __name__ == "__main__":
    unittest.main()
