import csv
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from llm4or.retailopt190_custody import (
    RetailOptCustodyError,
    SourceIdentity,
    build_custody,
    publish_custody,
)


COMMIT = "d809c6bbeb42cb99b0564c41bfb8f331f0156b9d"
FAMILY_ARCHETYPES = {1: 4, 2: 6, 3: 4, 4: 6, 5: 4, 6: 4, 7: 6, 8: 4}


def _dataset_sha(root: Path) -> str:
    return hashlib.sha256((root / "retailopt_190.jsonl").read_bytes()).hexdigest()


def fixture(root: Path) -> Path:
    (root / "scenarios" / "prompts").mkdir(parents=True)
    (root / "scenarios" / "data").mkdir(parents=True)
    (root / "solvers").mkdir()
    (root / "eval").mkdir()
    for name, body in {
        "LICENSE": "ReLoop Research and Education License v1.0",
        "README.md": "MIT badge",
        "DATASET_CARD.md": "CC-BY-4.0",
    }.items():
        (root / name).write_text(body)
    (root / "solvers" / "universal_retail_solver.py").write_text("REFERENCE = True\n")
    rows = []
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=["scenario", "status", "objective", "objective_numeric", "time_sec"],
    )
    writer.writeheader()
    for family, count in FAMILY_ARCHETYPES.items():
        for archetype_number in range(count):
            archetype = f"a{archetype_number}"
            for variant in range(5):
                source_id = f"retail_f{family}_{archetype}_v{variant}"
                data = {"name": source_id, "private_value": 1000 + variant}
                data_text = json.dumps(data, sort_keys=True)
                schema = f"[SCENARIO]\n{source_id}\n[BUSINESS DESCRIPTION]\nprivate schema {family} {archetype}"
                full = schema + "\n[DATA]\n" + data_text
                status = "OPTIMAL (TL)" if family == 6 and archetype_number == 0 else "OPTIMAL"
                objective = float(family * 100 + archetype_number * 10 + variant)
                rows.append(
                    {
                        "scenario_id": source_id,
                        "prompt_schema": schema,
                        "prompt_full": full,
                        "data": data_text,
                        "reference_status": status,
                        "reference_objective": objective,
                    }
                )
                prompts = root / "scenarios" / "prompts"
                (prompts / f"{source_id}.scenario.txt").write_text(schema)
                (prompts / f"{source_id}.full.txt").write_text(full)
                (prompts / f"{source_id}.base.txt").write_text(schema)
                (root / "scenarios" / "data" / f"{source_id}.json").write_text(json.dumps(data))
                writer.writerow(
                    {
                        "scenario": source_id,
                        "status": status,
                        "objective": str(objective),
                        "objective_numeric": str(objective),
                        "time_sec": "0.1",
                    }
                )
    (root / "retailopt_190.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    (root / "eval" / "benchmark_results.csv").write_text(csv_buffer.getvalue())
    return root


class RetailOptCustodyTests(unittest.TestCase):
    def test_builds_disjoint_body_free_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            bundle = build_custody(root, SourceIdentity(COMMIT, _dataset_sha(root)))
            self.assertEqual(bundle.public_audit["counts"]["records"], 190)
            self.assertEqual(bundle.public_audit["counts"]["archetypes"], 38)
            rendered = json.dumps(bundle.public_audit, sort_keys=True)
            self.assertNotIn("private schema", rendered)
            self.assertNotIn("private_value", rendered)
            self.assertNotIn("reference_objective\"", rendered)
            self.assertFalse(bundle.public_audit["privacy"]["contains_problem_bodies"])
            self.assertEqual(len(bundle.entries), 571)

    def test_hash_and_projection_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            identity = SourceIdentity(COMMIT, _dataset_sha(root))
            (root / "scenarios" / "prompts" / "retail_f1_a0_v0.full.txt").write_text("changed")
            with self.assertRaisesRegex(RetailOptCustodyError, "prompt_projection_mismatch"):
                build_custody(root, identity)
            with self.assertRaisesRegex(RetailOptCustodyError, "dataset_hash_mismatch"):
                build_custody(root, SourceIdentity(COMMIT, "0" * 64))

    def test_duplicate_identity_nonfinite_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            rows = [json.loads(line) for line in (root / "retailopt_190.jsonl").read_text().splitlines()]
            rows[1]["scenario_id"] = rows[0]["scenario_id"]
            (root / "retailopt_190.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
            with self.assertRaisesRegex(RetailOptCustodyError, "scenario_identity"):
                build_custody(root, SourceIdentity(COMMIT, _dataset_sha(root)))

        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            path = root / "LICENSE"
            path.unlink()
            path.symlink_to(root / "README.md")
            with self.assertRaisesRegex(RetailOptCustodyError, "unsafe_source_file"):
                build_custody(root, SourceIdentity(COMMIT, _dataset_sha(root)))

    def test_publish_is_replay_safe_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as source_directory, tempfile.TemporaryDirectory() as output_directory:
            root = fixture(Path(source_directory))
            bundle = build_custody(root, SourceIdentity(COMMIT, _dataset_sha(root)))
            first = publish_custody(output_directory, bundle.entries)
            second = publish_custody(output_directory, bundle.entries)
            self.assertEqual(first.transaction_id, second.transaction_id)
            self.assertEqual(len(first.created), 571)
            self.assertEqual(len(second.identical), 571)

    def test_source_identity_is_strict(self):
        with self.assertRaisesRegex(RetailOptCustodyError, "invalid_source_commit"):
            SourceIdentity("x", "0" * 64)
        with self.assertRaisesRegex(RetailOptCustodyError, "invalid_dataset_sha256"):
            SourceIdentity(COMMIT, "x")


if __name__ == "__main__":
    unittest.main()
