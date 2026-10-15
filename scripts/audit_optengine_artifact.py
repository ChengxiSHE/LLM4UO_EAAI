#!/usr/bin/env python3
"""Audit the pinned OPT-Engine artifact without exposing reference answers."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "data/raw/optengine_20261004"
OUTPUT = ROOT / "data/manifests/optengine_artifact_audit_v1.json"
FILES = (
    "test_data/canonical/canonical.jsonl",
    "test_data/perturbations/constraint_augmentation.jsonl",
    "test_data/perturbations/linguistic_complexity.jsonl",
    "test_data/perturbations/objective_perturbation.jsonl",
)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_text(value):
    return sha_bytes(value.encode())


def load_file(relative):
    path = UPSTREAM / relative
    rows = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict) or "question" not in value or "answer" not in value:
            raise ValueError(f"invalid_optengine_record:{relative}:{line_number}")
        if not isinstance(value["question"], str) or not value["question"].strip():
            raise ValueError(f"invalid_optengine_question:{relative}:{line_number}")
        if type(value["answer"]) not in (int, float):
            raise ValueError(f"invalid_optengine_answer_type:{relative}:{line_number}")
        rows.append(value)
    return path, rows


def main():
    commit = subprocess.run(
        ["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], capture_output=True,
        text=True, check=True, timeout=15,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "-C", str(UPSTREAM), "status", "--porcelain"], capture_output=True,
        text=True, check=True, timeout=15,
    ).stdout.strip()
    if dirty:
        raise ValueError("optengine_upstream_dirty")

    summaries = {}
    question_sets = {}
    total = 0
    for relative in FILES:
        path, rows = load_file(relative)
        total += len(rows)
        hashes = [sha_text(row["question"]) for row in rows]
        question_sets[relative] = set(hashes)
        optional = {}
        for key in ("experimental_type", "linguistic_complexity", "objective_type", "constraint_type"):
            if any(key in row for row in rows):
                optional[key] = dict(sorted(Counter(str(row.get(key)) for row in rows).items()))
        summaries[relative] = {
            "sha256": sha_bytes(path.read_bytes()),
            "records": len(rows),
            "unique_question_sha256": len(set(hashes)),
            "duplicate_question_records": len(hashes) - len(set(hashes)),
            "record_keys": sorted(set().union(*(row.keys() for row in rows))),
            "problem_classes": dict(sorted(Counter(str(row.get("problem_class")) for row in rows).items())),
            "answer_types_only": dict(sorted(Counter(type(row["answer"]).__name__ for row in rows).items())),
            "metadata": optional,
        }
    overlaps = {}
    for left_index, left in enumerate(FILES):
        for right in FILES[left_index + 1:]:
            overlaps[left + " :: " + right] = len(question_sets[left] & question_sets[right])
    license_files = sorted(
        str(path.relative_to(UPSTREAM)) for path in UPSTREAM.iterdir()
        if path.is_file() and ("license" in path.name.casefold() or path.name.casefold().startswith("copying"))
    )
    report = {
        "schema": "optengine-artifact-audit-v1",
        "repository": "https://github.com/Cardinal-Operations/OPTEngine",
        "commit": commit,
        "artifact_role": "candidate_fresh_transfer_benchmark_not_yet_split_or_evaluated",
        "upstream_code_executed": False,
        "reference_values_opened_for_method_design": False,
        "answer_handling": "audit checked numeric types only; future preparation must separate answer before any model-visible projection",
        "files": summaries,
        "total_records": total,
        "exact_question_overlap_counts": overlaps,
        "license_files": license_files,
        "redistribution": "blocked_pending_explicit_license" if not license_files else "requires_license_review",
        "scientific_limits": [
            "Perturbation records are derived from canonical instances and must remain in the same split group.",
            "Instance independence cannot be inferred from row count or exact-text hashes.",
            "The benchmark answer is an objective endpoint and does not alone certify semantic equivalence.",
            "No method selection or performance claim is made by this artifact audit.",
        ],
        "next_gate": "derive outcome-blind instance-family groups, audit reference generation, freeze roles, and validate the evaluator before inference",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"commit": commit, "records": total, "license_files": license_files,
                      "output": str(OUTPUT.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
