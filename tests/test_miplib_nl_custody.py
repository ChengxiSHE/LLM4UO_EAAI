import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm4or.atomic_publisher import PublicationBoundaryError, PublicationConflict
from llm4or.miplib_nl_custody import (
    CustodyBundle,
    CustodyError,
    SourceIdentity,
    build_custody_bundle,
    build_materialization_audit,
    build_schema_census,
    check_custody_bundle,
    load_instance,
    publish_custody_bundle,
    resolve_data_file,
)


COMMIT = "9f14ad1782eaa547f7dad982d1edb186321ffd88"
TREE = "96132c089bbead0909c1ab9e55df59195ba8ec6f"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI = PROJECT_ROOT / "scripts/build_miplib_nl_custody.py"


def source() -> SourceIdentity:
    return SourceIdentity(commit=COMMIT, dataset_tree=TREE)


def payload(*, paths=("table.csv",)):
    return {
        "abstract_problem": "private synthetic task text",
        "parameters": {"n": 7},
        "files": {
            f"f{index}": {"path": path, "description": "private schema text"}
            for index, path in enumerate(paths)
        },
        "optimal_value": 777,
    }


def add_instance(
    dataset: Path,
    name: str = "private-instance-name",
    *,
    instance_payload=None,
    data_names=("table.csv",),
    model=True,
) -> Path:
    root = dataset / name
    data = root / "data"
    data.mkdir(parents=True)
    (root / "instance.json").write_text(
        json.dumps(payload() if instance_payload is None else instance_payload),
        encoding="utf-8",
    )
    (root / "solve.py").write_text("REFERENCE_CODE = True\n", encoding="utf-8")
    if model:
        (root / "model.md").write_text("reference model", encoding="utf-8")
    for data_name in data_names:
        (data / data_name).write_text("id,value\n1,2\n", encoding="utf-8")
    return root


class MiplibNlCustodySourceTests(unittest.TestCase):
    def test_load_instance_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "instance.json"
            path.write_text(
                '{"abstract_problem":"x","abstract_problem":"y",'
                '"parameters":{},"files":{},"optimal_value":1}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CustodyError, "duplicate_json_key"):
                load_instance(path)

    def test_load_instance_rejects_nonfinite_json(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "instance.json"
                path.write_text(
                    '{"abstract_problem":"x","parameters":{},"files":{},'
                    f'"optimal_value":{token}}}',
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(CustodyError, "nonfinite_json"):
                    load_instance(path)

    def test_load_instance_requires_exact_top_level_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "instance.json"
            value = payload()
            value["unexpected"] = "must not be copied"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(CustodyError, "top_level_keys"):
                load_instance(path)

    def test_census_requires_instance_json_and_solve_py_but_model_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            add_instance(dataset, model=False)
            census = build_schema_census(dataset, source())
            self.assertEqual(census["counts"]["instances"], 1)
            self.assertEqual(census["counts"]["model_md_present"], 0)

            (dataset / "private-instance-name" / "solve.py").unlink()
            with self.assertRaisesRegex(CustodyError, "missing_required_file"):
                build_schema_census(dataset, source())

    def test_resolve_data_file_rejects_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            instance = add_instance(dataset)
            with self.assertRaisesRegex(CustodyError, "unsafe_data_path"):
                resolve_data_file(instance, "../outside.csv")
            outside = dataset / "outside.csv"
            outside.write_text("x\n", encoding="utf-8")
            (instance / "data" / "linked.csv").symlink_to(outside)
            with self.assertRaisesRegex(CustodyError, "unsafe_data_file"):
                resolve_data_file(instance, "linked.csv")

    def test_census_rejects_special_required_file(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            instance = add_instance(dataset)
            (instance / "solve.py").unlink()
            os.mkfifo(instance / "solve.py")
            with self.assertRaisesRegex(CustodyError, "unsafe_required_file"):
                build_schema_census(dataset, source())

    def test_census_rejects_duplicate_normalized_data_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload(paths=("table.csv", "./table.csv"))
            add_instance(dataset, instance_payload=value)
            with self.assertRaisesRegex(CustodyError, "duplicate_data_path"):
                build_schema_census(dataset, source())

    def test_schema_census_is_body_free_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            add_instance(dataset)
            first = build_schema_census(dataset, source())
            second = build_schema_census(dataset, source())
            self.assertEqual(first, second)
            self.assertEqual(first["source"]["commit"], COMMIT)
            self.assertEqual(first["source"]["dataset_tree"], TREE)
            self.assertEqual(first["counts"]["instances"], 1)
            self.assertEqual(first["counts"]["instance_json"], 1)
            self.assertEqual(first["counts"]["solve_py"], 1)
            rendered = json.dumps(first, sort_keys=True)
            for forbidden in (
                "private-instance-name",
                "private synthetic task text",
                "private schema text",
                "777",
                "REFERENCE_CODE",
                "reference model",
            ):
                self.assertNotIn(forbidden, rendered)
            self.assertTrue(first["schema_paths"]["$.abstract_problem"]["string"])

    def test_schema_census_reports_unknown_field_type_without_value(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload()
            value["unexpected"] = "private unknown value"
            add_instance(dataset, instance_payload=value)
            census = build_schema_census(dataset, source())
            self.assertEqual(census["schema_paths"]["$.unexpected"], {"string": 1})
            self.assertNotIn("private unknown value", json.dumps(census, sort_keys=True))

    def test_schema_census_accepts_unrecognized_files_shape_without_values(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload()
            value["files"] = [
                {"filename": "table.csv", "private_description": "secret"}
            ]
            add_instance(dataset, instance_payload=value)
            census = build_schema_census(dataset, source())
            self.assertEqual(census["counts"]["declared_data_files"], 1)
            rendered = json.dumps(census, sort_keys=True)
            self.assertNotIn("table.csv", rendered)
            self.assertNotIn("secret", rendered)

    def test_schema_census_does_not_require_data_materialization(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            instance = add_instance(dataset)
            (instance / "data/table.csv").unlink()
            (instance / "data").rmdir()
            census = build_schema_census(dataset, source())
            self.assertEqual(census["counts"]["instances"], 1)
            self.assertEqual(census["counts"]["declared_data_files"], 1)

    def test_schema_census_reports_top_level_key_sets_without_values(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            add_instance(dataset, "with-files")
            without_files = payload(paths=())
            without_files.pop("files")
            add_instance(
                dataset,
                "without-files",
                instance_payload=without_files,
                data_names=(),
            )
            census = build_schema_census(dataset, source())
            self.assertEqual(
                census["top_level_key_sets"],
                [
                    {
                        "keys": ["abstract_problem", "files", "optimal_value", "parameters"],
                        "count": 1,
                    },
                    {
                        "keys": ["abstract_problem", "optimal_value", "parameters"],
                        "count": 1,
                    },
                ],
            )
            rendered = json.dumps(census, sort_keys=True)
            self.assertNotIn("private synthetic task text", rendered)
            self.assertNotIn("777", rendered)

    def test_error_does_not_echo_source_name_or_value(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            secret_name = "secret-instance-name"
            value = payload(paths=("../secret-answer.csv",))
            add_instance(dataset, secret_name, instance_payload=value)
            try:
                build_schema_census(dataset, source())
            except CustodyError as error:
                message = str(error)
            else:
                self.fail("expected CustodyError")
            self.assertNotIn(secret_name, message)
            self.assertNotIn("secret-answer", message)


class MiplibNlCustodyProjectionTests(unittest.TestCase):
    def test_materialization_audit_is_body_free_and_counts_path_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            add_instance(dataset, "complete")
            broken = add_instance(dataset, "broken")
            (broken / "data/table.csv").rename(broken / "data/other.csv")
            audit = build_materialization_audit(dataset, source())
            self.assertEqual(audit["status"], "failed_source_materialization")
            self.assertEqual(audit["counts"]["instances"], 2)
            self.assertEqual(audit["counts"]["exact_instances"], 1)
            self.assertEqual(audit["counts"]["mismatched_instances"], 1)
            self.assertEqual(audit["counts"]["missing_declared_data_files"], 1)
            self.assertEqual(audit["counts"]["undeclared_actual_data_files"], 1)
            rendered = json.dumps(audit, sort_keys=True)
            for forbidden in (
                "complete", "broken", "table.csv", "other.csv",
                "private synthetic task text", "777",
            ):
                self.assertNotIn(forbidden, rendered)

    def test_builds_disjoint_inference_metadata_and_evaluator_projections(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            instance = add_instance(dataset)
            bundle = build_custody_bundle(dataset, source())
            self.assertIsInstance(bundle, CustodyBundle)
            record = bundle.private_ledger["records"][0]
            opaque = record["opaque_id"]
            inference = json.loads(
                bundle.entries[f"inference/{opaque}/instance.json"]
            )
            self.assertEqual(
                set(inference), {"abstract_problem", "parameters", "files"}
            )
            self.assertNotIn("optimal_value", inference)
            self.assertEqual(
                bundle.entries[f"inference/{opaque}/data/table.csv"],
                (instance / "data/table.csv").read_bytes(),
            )
            self.assertNotIn(f"inference/{opaque}/model.md", bundle.entries)
            self.assertNotIn(f"inference/{opaque}/solve.py", bundle.entries)

            reference = json.loads(
                bundle.entries[f"evaluator/{opaque}/reference.json"]
            )
            self.assertEqual(reference["optimal_value"], 777)
            self.assertEqual(
                bundle.entries[f"evaluator/{opaque}/solve.py"],
                b"REFERENCE_CODE = True\n",
            )
            self.assertEqual(
                bundle.entries[f"evaluator/{opaque}/model.md"],
                b"reference model",
            )

            metadata = json.loads(bundle.entries[f"metadata/{opaque}.json"])
            self.assertEqual(metadata["csv"]["files"], 1)
            self.assertEqual(metadata["csv"]["rows"], 2)
            self.assertEqual(metadata["csv"]["maximum_columns"], 2)
            self.assertTrue(metadata["reference_model_present"])
            rendered_metadata = json.dumps(metadata, sort_keys=True)
            for forbidden in (
                "private synthetic task text",
                "private schema text",
                "777",
                "REFERENCE_CODE",
                "reference model",
            ):
                self.assertNotIn(forbidden, rendered_metadata)

            rendered_audit = json.dumps(bundle.public_audit, sort_keys=True)
            self.assertEqual(bundle.public_audit["counts"]["instances"], 1)
            self.assertEqual(bundle.public_audit["counts"]["model_md_present"], 1)
            self.assertNotIn("private-instance-name", rendered_audit)
            self.assertNotIn("private synthetic task text", rendered_audit)
            self.assertNotIn("777", rendered_audit)

    def test_optional_model_absence_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            add_instance(dataset, model=False)
            bundle = build_custody_bundle(dataset, source())
            record = bundle.private_ledger["records"][0]
            opaque = record["opaque_id"]
            metadata = json.loads(bundle.entries[f"metadata/{opaque}.json"])
            self.assertFalse(metadata["reference_model_present"])
            self.assertNotIn(f"evaluator/{opaque}/model.md", bundle.entries)
            self.assertEqual(bundle.public_audit["counts"]["model_md_absent"], 1)

    def test_string_optimal_value_stays_opaque_and_evaluator_only(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload()
            value["optimal_value"] = "private-reference-token"
            add_instance(dataset, instance_payload=value)
            bundle = build_custody_bundle(dataset, source())
            record = bundle.private_ledger["records"][0]
            opaque = record["opaque_id"]
            reference = json.loads(bundle.entries[f"evaluator/{opaque}/reference.json"])
            self.assertEqual(reference["optimal_value"], "private-reference-token")
            public = json.dumps(bundle.public_audit, sort_keys=True)
            metadata = bundle.entries[f"metadata/{opaque}.json"].decode("utf-8")
            self.assertNotIn("private-reference-token", public)
            self.assertNotIn("private-reference-token", metadata)

    def test_missing_files_key_with_no_data_normalizes_to_empty_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload(paths=())
            value.pop("files")
            instance = add_instance(dataset, instance_payload=value, data_names=())
            (instance / "data").rmdir()
            bundle = build_custody_bundle(dataset, source())
            record = bundle.private_ledger["records"][0]
            opaque = record["opaque_id"]
            inference = json.loads(bundle.entries[f"inference/{opaque}/instance.json"])
            self.assertEqual(inference["files"], {})
            self.assertEqual(bundle.public_audit["counts"]["declared_data_files"], 0)

    def test_missing_files_key_rejects_materialized_data(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload(paths=())
            value.pop("files")
            add_instance(dataset, instance_payload=value)
            with self.assertRaisesRegex(CustodyError, "undeclared_data_file"):
                build_custody_bundle(dataset, source())

    def test_rejects_nested_sensitive_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload()
            value["parameters"] = {"nested": {"reference_answer": 1}}
            add_instance(dataset, instance_payload=value)
            with self.assertRaisesRegex(CustodyError, "sensitive_key"):
                build_custody_bundle(dataset, source())

    def test_rejects_undeclared_data(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            instance = add_instance(dataset)
            (instance / "data/extra.csv").write_text("x\n1\n", encoding="utf-8")
            with self.assertRaisesRegex(CustodyError, "undeclared_data_file"):
                build_custody_bundle(dataset, source())

    def test_rejects_non_csv_data(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload(paths=("table.txt",))
            add_instance(
                dataset,
                instance_payload=value,
                data_names=("table.txt",),
            )
            with self.assertRaisesRegex(CustodyError, "data_extension"):
                build_custody_bundle(dataset, source())

    def test_rejects_answer_like_csv_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            instance = add_instance(dataset)
            (instance / "data/table.csv").write_text(
                "id,optimal_value\n1,2\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(CustodyError, "sensitive_csv_header"):
                build_custody_bundle(dataset, source())

    def test_accepts_empty_and_ragged_declared_csv_as_opaque_input_data(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload(paths=("empty.csv", "ragged.csv"))
            instance = add_instance(
                dataset,
                instance_payload=value,
                data_names=("empty.csv", "ragged.csv"),
            )
            (instance / "data/empty.csv").write_bytes(b"")
            (instance / "data/ragged.csv").write_text(
                "name,,\n1,2\n", encoding="utf-8"
            )
            bundle = build_custody_bundle(dataset, source())
            record = bundle.private_ledger["records"][0]
            opaque = record["opaque_id"]
            metadata = json.loads(bundle.entries[f"metadata/{opaque}.json"])
            self.assertEqual(metadata["csv"]["files"], 2)
            self.assertEqual(metadata["csv"]["rows"], 2)
            self.assertEqual(metadata["csv"]["maximum_columns"], 3)
            self.assertEqual(metadata["csv"]["ragged_files"], 1)

    def test_rejects_malformed_utf8_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            instance = add_instance(dataset)
            (instance / "data/table.csv").write_bytes(b"id,value\n1,\xff\n")
            with self.assertRaisesRegex(CustodyError, "data_not_utf8"):
                build_custody_bundle(dataset, source())

    def test_rejects_unknown_top_level_key_before_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            value = payload()
            value["answer"] = 1
            add_instance(dataset, instance_payload=value)
            with self.assertRaisesRegex(CustodyError, "top_level_keys"):
                build_custody_bundle(dataset, source())

    def test_rejects_duplicate_opaque_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            add_instance(dataset, "first")
            add_instance(dataset, "second")
            with mock.patch(
                "llm4or.miplib_nl_custody._opaque_id", return_value="a" * 64
            ):
                with self.assertRaisesRegex(CustodyError, "duplicate_opaque_identity"):
                    build_custody_bundle(dataset, source())

    def test_bundle_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            add_instance(dataset)
            first = build_custody_bundle(dataset, source())
            second = build_custody_bundle(dataset, source())
            self.assertEqual(first.entries, second.entries)
            self.assertEqual(first.private_ledger, second.private_ledger)
            self.assertEqual(first.public_audit, second.public_audit)


class MiplibNlCustodyPublicationTests(unittest.TestCase):
    def make_bundle(self, directory: str):
        dataset = Path(directory) / "dataset"
        add_instance(dataset)
        return build_custody_bundle(dataset, source())

    def test_publishes_complete_bundle_and_replays_identically(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.make_bundle(directory)
            root = Path(directory) / "custody"
            root.mkdir()
            first = publish_custody_bundle(root, bundle)
            self.assertEqual(set(first.created), set(bundle.entries))
            for relative, expected in bundle.entries.items():
                self.assertEqual((root / relative).read_bytes(), expected)
            second = publish_custody_bundle(root, bundle)
            self.assertEqual(second.created, ())
            self.assertEqual(set(second.identical), set(bundle.entries))
            check_custody_bundle(root, bundle)

    def test_publication_rejects_differing_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.make_bundle(directory)
            root = Path(directory) / "custody"
            root.mkdir()
            publish_custody_bundle(root, bundle)
            relative = next(iter(bundle.entries))
            (root / relative).write_bytes(b"different")
            with self.assertRaises(PublicationConflict):
                publish_custody_bundle(root, bundle)

    def test_failed_validation_publishes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "dataset"
            instance = add_instance(dataset)
            (instance / "data/extra.csv").write_text("x\n1\n", encoding="utf-8")
            root = Path(directory) / "custody"
            root.mkdir()
            with self.assertRaisesRegex(CustodyError, "undeclared_data_file"):
                bundle = build_custody_bundle(dataset, source())
                publish_custody_bundle(root, bundle)
            self.assertEqual(list(root.iterdir()), [])

    def test_check_is_read_only_and_detects_one_byte_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.make_bundle(directory)
            root = Path(directory) / "custody"
            root.mkdir()
            publish_custody_bundle(root, bundle)
            relative = next(
                path for path in bundle.entries if path.startswith("inference/")
            )
            path = root / relative
            changed = path.read_bytes() + b"x"
            path.write_bytes(changed)
            with self.assertRaisesRegex(CustodyError, "check_drift") as raised:
                check_custody_bundle(root, bundle)
            self.assertNotIn("private synthetic", str(raised.exception))
            self.assertEqual(path.read_bytes(), changed)

    def test_publication_rejects_symlinked_destination_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.make_bundle(directory)
            root = Path(directory) / "custody"
            root.mkdir()
            outside = Path(directory) / "outside"
            outside.mkdir()
            (root / "inference").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(PublicationBoundaryError):
                publish_custody_bundle(root, bundle)

    def test_published_inference_has_no_reference_files_or_links(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.make_bundle(directory)
            root = Path(directory) / "custody"
            root.mkdir()
            publish_custody_bundle(root, bundle)
            inference = root / "inference"
            for path in inference.rglob("*"):
                self.assertFalse(path.is_symlink())
                if path.is_file():
                    self.assertNotIn(
                        path.name, {"model.md", "solve.py", "reference.json"}
                    )
                    self.assertNotIn("evaluator", path.parts)


class MiplibNlCustodyCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.dataset = self.root / "dataset"
        add_instance(self.dataset)
        self.custody = self.root / "custody"
        self.custody.mkdir()
        self.audit = self.root / "public-audit.json"

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, mode: str, *, check=True):
        command = [
            sys.executable,
            str(CLI),
            mode,
            "--raw-root",
            str(self.dataset),
            "--custody-root",
            str(self.custody),
            "--source-commit",
            COMMIT,
            "--dataset-tree",
            TREE,
            "--public-audit",
            str(self.audit),
        ]
        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_schema_census_writes_only_body_free_audit(self):
        completed = self.run_cli("--schema-census")
        census = json.loads(self.audit.read_text())
        self.assertEqual(census["counts"]["instances"], 1)
        self.assertEqual(list(self.custody.iterdir()), [])
        visible = completed.stdout + completed.stderr + self.audit.read_text()
        for forbidden in (
            "private-instance-name",
            "private synthetic task text",
            "private schema text",
            "REFERENCE_CODE",
            "reference model",
            "777",
        ):
            self.assertNotIn(forbidden, visible)

    def test_write_then_check_is_deterministic_and_check_is_read_only(self):
        write = self.run_cli("--write")
        audit_bytes = self.audit.read_bytes()
        audit = json.loads(audit_bytes)
        self.assertEqual(audit["status"], "published_private_bundle_verified")
        self.assertEqual(audit["counts"]["instances"], 1)
        before = {
            path.relative_to(self.root).as_posix(): (path.stat().st_mtime_ns, path.read_bytes())
            for path in self.root.rglob("*")
            if path.is_file()
        }
        check = self.run_cli("--check")
        after = {
            path.relative_to(self.root).as_posix(): (path.stat().st_mtime_ns, path.read_bytes())
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)
        self.assertEqual(self.audit.read_bytes(), audit_bytes)
        visible = write.stdout + write.stderr + check.stdout + check.stderr
        self.assertNotIn("private synthetic task text", visible)
        self.assertNotIn("777", visible)

    def test_check_detects_drift_without_echoing_value(self):
        self.run_cli("--write")
        inference = next((self.custody / "inference").rglob("instance.json"))
        inference.write_text("secret changed value", encoding="utf-8")
        completed = self.run_cli("--check", check=False)
        self.assertNotEqual(completed.returncode, 0)
        visible = completed.stdout + completed.stderr
        self.assertIn("check_drift", visible)
        self.assertNotIn("secret changed value", visible)

    def test_modes_are_mutually_exclusive(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--write",
                "--check",
                "--raw-root",
                str(self.dataset),
                "--custody-root",
                str(self.custody),
                "--source-commit",
                COMMIT,
                "--dataset-tree",
                TREE,
                "--public-audit",
                str(self.audit),
            ],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
