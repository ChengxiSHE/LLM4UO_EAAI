import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm4or.atomic_publisher import PublicationBoundaryError
from llm4or.formulationbench_custody import (
    CensusCounts,
    CustodyBundle,
    CustodyError,
    SourceIdentity,
    build_custody_bundle,
    check_custody_bundle,
    census_source,
    publish_custody_bundle,
)


COMMIT = "6f37a71e6251b11599ef42869e4268882985a8a7"
TREE = "793db197693fac5446fe1bd39aaf178fea437822"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI = PROJECT_ROOT / "scripts/build_formulationbench_custody.py"


def identity() -> SourceIdentity:
    return SourceIdentity(commit=COMMIT, dataset_tree=TREE)


def fixture(root: Path, *, proof: bool = True) -> Path:
    dataset = root / "dataset"
    dataset.mkdir(parents=True)
    for name in (
        ".gitignore",
        "AGENTS.md",
        "CLAUDE.md",
        "Common.lean",
        "LICENSE.md",
        "README.md",
        "dataset.json",
        "lake-manifest.json",
        "lakefile.toml",
        "lean-toolchain",
        "ref.bib",
    ):
        (dataset / name).write_text("private root body", encoding="utf-8")
    problem = dataset / "problems" / "p1"
    problem.mkdir(parents=True)
    (problem / "description.md").write_text(
        "private problem description", encoding="utf-8"
    )
    (problem / "problem.json").write_text(
        json.dumps(
            {
                "metadata": {"source": "private source identity"},
                "name": "private problem name",
                "np_hard": True,
                "parameters": {"n": {"type": "integer"}},
            }
        ),
        encoding="utf-8",
    )
    (problem / "data.json").write_text(
        json.dumps({"n": 7, "private_data_value": 991}), encoding="utf-8"
    )
    (problem / "solution.json").write_text(
        json.dumps({"objective": 777, "variables": {"x": 3}}),
        encoding="utf-8",
    )
    for formulation_id in ("a", "b"):
        formulation = problem / "formulations" / formulation_id
        formulation.mkdir(parents=True)
        (formulation / "formulation.json").write_text(
            json.dumps(
                {
                    "assumptions": [],
                    "constraints": [
                        {
                            "description": f"private constraint {formulation_id}",
                            "formulation": f"private algebra {formulation_id}",
                            "code": {"gurobipy": "private reference code"},
                        }
                    ],
                    "metadata": {"source": {"formulation_id": formulation_id}},
                    "objective": {
                        "description": "private objective",
                        "formulation": "private objective algebra",
                        "code": {"gurobipy": "private objective code"},
                    },
                    "parameters": {"n": {"type": "integer"}},
                    "valid": formulation_id == "a" or proof,
                    "variables": {"x": {"type": "integer"}},
                }
            ),
            encoding="utf-8",
        )
        (formulation / "gen_params.py").write_text(
            f"PRIVATE_GENERATOR_{formulation_id} = True\n", encoding="utf-8"
        )
        (formulation / "Formulation.lean").write_text(
            f"private Lean formulation {formulation_id}", encoding="utf-8"
        )
    pair = dataset / "reformulations" / "p1" / "a_b"
    pair.mkdir(parents=True)
    (pair / "map.json").write_text(
        json.dumps(
            {
                "metadata": {"source": "private pair identity"},
                "parameters": {"n": {"formulation": "n"}},
            }
        ),
        encoding="utf-8",
    )
    if proof:
        (pair / "Reformulation.lean").write_text("private proof body", encoding="utf-8")
    return dataset


def counts(*, proofs: int = 1) -> CensusCounts:
    return CensusCounts(problems=1, formulations=2, pairs=1, proofs=proofs)


class FormulationBenchSourceCensusTests(unittest.TestCase):
    def test_source_identity_requires_lowercase_sha1(self):
        with self.assertRaisesRegex(CustodyError, "invalid_source_identity"):
            SourceIdentity(commit="x", dataset_tree=TREE)

    def test_census_is_body_free_and_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory))
            audit = census_source(dataset, identity(), expected=counts())
            self.assertEqual(
                audit["counts"],
                {"formulations": 2, "pairs": 1, "problems": 1, "proofs": 1},
            )
            rendered = json.dumps(audit, sort_keys=True)
            for forbidden in (
                "private root body",
                "private problem body",
                "private formulation body",
                "private map body",
                "private proof body",
                "solution.json",
                "Reformulation.lean",
                "a_b",
            ):
                self.assertNotIn(forbidden, rendered)
            self.assertFalse(audit["privacy"]["contains_labels"])
            self.assertFalse(audit["privacy"]["contains_proof_bodies"])

    def test_census_accepts_pair_without_proof_when_expected(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory), proof=False)
            audit = census_source(dataset, identity(), expected=counts(proofs=0))
            self.assertEqual(audit["counts"]["proofs"], 0)

    def test_missing_required_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory))
            (dataset / "problems" / "p1" / "solution.json").unlink()
            with self.assertRaisesRegex(CustodyError, "missing_required_file"):
                census_source(dataset, identity(), expected=counts())

    def test_unknown_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory))
            (dataset / "problems" / "p1" / "unexpected.txt").write_text("secret")
            with self.assertRaisesRegex(CustodyError, "unknown_source_entry"):
                census_source(dataset, identity(), expected=counts())

    def test_symlink_and_special_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory))
            target = dataset / "README.md"
            required = dataset / "problems" / "p1" / "description.md"
            required.unlink()
            required.symlink_to(target)
            with self.assertRaisesRegex(CustodyError, "unsafe_source_entry"):
                census_source(dataset, identity(), expected=counts())

        if hasattr(os, "mkfifo"):
            with tempfile.TemporaryDirectory() as directory:
                dataset = fixture(Path(directory))
                required = dataset / "problems" / "p1" / "description.md"
                required.unlink()
                os.mkfifo(required)
                with self.assertRaisesRegex(CustodyError, "unsafe_source_entry"):
                    census_source(dataset, identity(), expected=counts())

    def test_pair_must_reference_existing_formulations(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory))
            pair = dataset / "reformulations" / "p1" / "a_b"
            pair.rename(pair.parent / "a_c")
            with self.assertRaisesRegex(CustodyError, "pair_side_missing"):
                census_source(dataset, identity(), expected=counts())

    def test_canonical_problem_id_collision_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory))
            source = dataset / "problems" / "p1"
            duplicate = dataset / "problems" / "p01"
            duplicate.mkdir()
            for path in source.iterdir():
                if path.is_file():
                    (duplicate / path.name).write_bytes(path.read_bytes())
            (duplicate / "formulations").mkdir()
            with self.assertRaisesRegex(CustodyError, "duplicate_problem_identity"):
                census_source(dataset, identity(), expected=counts())

    def test_errors_do_not_echo_private_names(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory))
            private_name = "do-not-echo-private-name.txt"
            (dataset / private_name).write_text("secret")
            with self.assertRaises(CustodyError) as caught:
                census_source(dataset, identity(), expected=counts())
            self.assertNotIn(private_name, str(caught.exception))


class FormulationBenchCustodyProjectionTests(unittest.TestCase):
    def test_builds_disjoint_projections_and_strips_label_side_channels(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory), proof=True)
            bundle = build_custody_bundle(dataset, identity(), expected=counts())
            self.assertIsInstance(bundle, CustodyBundle)
            record = bundle.private_ledger["records"][0]
            opaque = record["opaque_id"]

            inference_raw = bundle.entries[f"inference/{opaque}/pair.json"]
            inference = json.loads(inference_raw)
            self.assertEqual(
                set(inference),
                {
                    "formulation_a",
                    "formulation_b",
                    "opaque_id",
                    "parameter_map",
                    "problem",
                    "problem_description",
                    "schema",
                    "source_commit",
                    "source_tree",
                },
            )
            rendered = inference_raw.decode("utf-8")
            for forbidden in (
                '"valid"',
                '"code"',
                '"metadata"',
                "private reference code",
                "private objective code",
                "private_data_value",
                "991",
                "777",
                "private proof body",
                "private source identity",
                "private pair identity",
            ):
                self.assertNotIn(forbidden, rendered)

            label = json.loads(bundle.entries[f"evaluator/{opaque}/label.json"])
            self.assertTrue(label["equivalent"])
            self.assertEqual(
                bundle.entries[f"evaluator/{opaque}/solution.json"],
                (dataset / "problems/p1/solution.json").read_bytes(),
            )
            self.assertEqual(
                bundle.entries[f"evaluator/{opaque}/Reformulation.lean"],
                b"private proof body",
            )
            self.assertIn(
                f"evaluator/{opaque}/formulation_a/Formulation.lean",
                bundle.entries,
            )
            self.assertIn(
                f"evaluator/{opaque}/formulation_b/gen_params.py",
                bundle.entries,
            )

            metadata_raw = bundle.entries[f"metadata/{opaque}.json"]
            metadata = json.loads(metadata_raw)
            self.assertNotIn("proof", metadata_raw.decode("utf-8").lower())
            self.assertNotIn("label", metadata_raw.decode("utf-8").lower())
            self.assertNotIn("valid", metadata_raw.decode("utf-8").lower())
            self.assertEqual(metadata["opaque_id"], opaque)
            self.assertFalse(bundle.public_audit["privacy"]["contains_pair_labels"])

    def test_proof_presence_changes_only_evaluator_and_private_audit(self):
        with (
            tempfile.TemporaryDirectory() as positive_directory,
            tempfile.TemporaryDirectory() as negative_directory,
        ):
            positive = build_custody_bundle(
                fixture(Path(positive_directory), proof=True),
                identity(),
                expected=counts(proofs=1),
            )
            negative = build_custody_bundle(
                fixture(Path(negative_directory), proof=False),
                identity(),
                expected=counts(proofs=0),
            )
            positive_public = {
                path: raw
                for path, raw in positive.entries.items()
                if path.startswith(("inference/", "metadata/"))
            }
            negative_public = {
                path: raw
                for path, raw in negative.entries.items()
                if path.startswith(("inference/", "metadata/"))
            }
            self.assertEqual(positive_public, negative_public)
            self.assertNotEqual(
                {
                    path: raw
                    for path, raw in positive.entries.items()
                    if path.startswith("evaluator/")
                },
                {
                    path: raw
                    for path, raw in negative.entries.items()
                    if path.startswith("evaluator/")
                },
            )

    def test_opaque_collision_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = fixture(Path(directory))
            pair = dataset / "reformulations/p1/a_b"
            second = pair.parent / "b_a"
            second.mkdir()
            (second / "map.json").write_text(
                (pair / "map.json").read_text(encoding="utf-8"), encoding="utf-8"
            )
            (second / "Reformulation.lean").write_text(
                "private second proof", encoding="utf-8"
            )
            expected = CensusCounts(problems=1, formulations=2, pairs=2, proofs=2)
            with mock.patch(
                "llm4or.formulationbench_custody._opaque_pair_id",
                return_value="0" * 64,
            ), self.assertRaisesRegex(CustodyError, "duplicate_opaque_identity"):
                build_custody_bundle(dataset, identity(), expected=expected)

    def test_atomic_publication_replay_drift_and_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            bundle = build_custody_bundle(
                fixture(base / "source"), identity(), expected=counts()
            )
            root = base / "custody"
            publish_custody_bundle(root, bundle)
            check_custody_bundle(root, bundle)
            replay = publish_custody_bundle(root, bundle)
            self.assertEqual(replay.created, ())
            terminal = next(root.rglob("pair.json"))
            terminal.write_text("drift", encoding="utf-8")
            with self.assertRaisesRegex(CustodyError, "check_drift"):
                check_custody_bundle(root, bundle)

            interrupted = base / "interrupted"
            def fail_after_stage(phase: str) -> None:
                if phase == "stage_complete":
                    raise RuntimeError("synthetic interruption")

            with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                publish_custody_bundle(interrupted, bundle, _fault=fail_after_stage)
            self.assertFalse(interrupted.exists())
            self.assertFalse(any(base.glob(".interrupted.llm4or-*.tmp")))

    def test_symlinked_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            bundle = build_custody_bundle(
                fixture(base / "source"), identity(), expected=counts()
            )
            real = base / "real"
            real.mkdir()
            linked = base / "linked"
            linked.symlink_to(real, target_is_directory=True)
            with self.assertRaises(PublicationBoundaryError):
                publish_custody_bundle(linked, bundle)


class FormulationBenchCensusCliTests(unittest.TestCase):
    def test_cli_replays_identical_audit_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = fixture(root)
            output = root / "audit.json"
            command = [
                sys.executable,
                str(CLI),
                "--schema-census",
                "--raw-root",
                str(dataset),
                "--source-commit",
                COMMIT,
                "--dataset-tree",
                TREE,
                "--expected-problems",
                "1",
                "--expected-formulations",
                "2",
                "--expected-pairs",
                "1",
                "--expected-proofs",
                "1",
                "--public-audit",
                str(output),
            ]
            first = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["counts"]["pairs"], 1)
            second = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)

            (dataset / "problems" / "p1" / "gen_data.py").write_text(
                "private optional body", encoding="utf-8"
            )
            third = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
            self.assertNotEqual(third.returncode, 0)
            self.assertIn("publication_existing_bytes_differ", third.stderr)

    def test_cli_writes_and_checks_complete_custody_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = fixture(root / "source")
            custody = root / "custody"
            audit = root / "audit.json"
            common = [
                sys.executable,
                str(CLI),
                "--raw-root",
                str(dataset),
                "--custody-root",
                str(custody),
                "--source-commit",
                COMMIT,
                "--dataset-tree",
                TREE,
                "--expected-problems",
                "1",
                "--expected-formulations",
                "2",
                "--expected-pairs",
                "1",
                "--expected-proofs",
                "1",
                "--public-audit",
                str(audit),
            ]
            written = subprocess.run(
                [*common, "--write"], cwd=PROJECT_ROOT, capture_output=True, text=True
            )
            self.assertEqual(written.returncode, 0, written.stderr)
            checked = subprocess.run(
                [*common, "--check"], cwd=PROJECT_ROOT, capture_output=True, text=True
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            payload = audit.read_text(encoding="utf-8")
            self.assertIn("published_private_bundle_verified", payload)
            for forbidden in (
                "private problem description",
                "private algebra",
                "private proof body",
                '"equivalent"',
                '"solution"',
            ):
                self.assertNotIn(forbidden, payload)


if __name__ == "__main__":
    unittest.main()
