"""Prepare a public-input-only Text2Opt-Bench external evaluation snapshot.

The upstream JSON files are treated as data.  This script never imports or
executes their ``gold_solution`` programs and never copies evaluator fields
into model-visible files.  The official train and eval directories retain
their upstream roles; template-family reuse is disclosed in the manifest.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/text2opt_bench_20261003"
RESOURCE = SOURCE / "synthetic_dataset/Unstructured/resource_allocation"
OUTPUT = ROOT / "data/prepared_benchmarks/text2opt_resource_allocation_v1.json"
MANIFEST = ROOT / "data/manifests/text2opt_resource_allocation_v1.json"
REVISION = "1dac06be656c41d827ef20987cf8af0b48d382a2"


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def canonical_sha(value):
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def normalize_text(value):
    return re.sub(r"\s+", " ", value).strip().lower()


def source_revision():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=SOURCE, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def load_partition(name):
    rows = []
    files = sorted((RESOURCE / name).glob("*.json"))
    for path in files:
        value = json.loads(path.read_text())
        text = value.get("LLM_description")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("missing_public_description:" + path.name)
        # Only public text and non-outcome size/type metadata cross this boundary.
        meta = value.get("meta", {})
        rows.append({
            "id": "text2opt_ra_" + path.stem.removeprefix("problem_"),
            "source_file": str(path.relative_to(SOURCE)),
            "source_file_sha256": sha_file(path),
            "public": {
                "id": "text2opt_ra_" + path.stem.removeprefix("problem_"),
                "profile": "description_parameters_v1",
                "text": text,
                "parameters": [],
                "instances": [],
            },
            "public_text_sha256": sha_bytes(text.encode()),
            "non_outcome_metadata": {
                "problem_type": meta.get("problem_type"),
                "num_vars": meta.get("num_vars"),
                "num_constraints": meta.get("num_constraints"),
            },
        })
    return rows


def main():
    if source_revision() != REVISION:
        raise ValueError("text2opt_revision_mismatch")
    development = load_partition("train")
    confirmation = load_partition("eval")
    if len(development) != 764 or len(confirmation) != 248:
        raise ValueError("text2opt_partition_count_mismatch")
    ids = [row["id"] for row in development + confirmation]
    if len(ids) != len(set(ids)):
        raise ValueError("text2opt_duplicate_id")
    dev_text = Counter(normalize_text(row["public"]["text"]) for row in development)
    test_text = Counter(normalize_text(row["public"]["text"]) for row in confirmation)
    overlap = set(dev_text) & set(test_text)
    if overlap:
        raise ValueError("text2opt_exact_normalized_text_overlap")
    prepared = {
        "schema": "text2opt-resource-allocation-public-v1",
        "source_revision": REVISION,
        "model_visible_fields": ["id", "profile", "text", "parameters", "instances"],
        "development": development,
        "confirmation": confirmation,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(prepared, sort_keys=True, separators=(",", ":")) + "\n")
    manifest = {
        "schema": "text2opt-resource-allocation-manifest-v1",
        "source": {
            "repository": "https://github.com/SprocketLab/Text2Opt-Bench",
            "revision": REVISION,
            "upstream_path": "synthetic_dataset/Unstructured/resource_allocation",
            "license": "MIT",
            "license_file_sha256": sha_bytes(
                subprocess.run(
                    ["git", "show", "HEAD:LICENSE"], cwd=SOURCE, check=True, capture_output=True
                ).stdout
            ),
        },
        "counts": {"development": len(development), "confirmation": len(confirmation)},
        "bindings": {
            "development_files_sha256": canonical_sha(
                [[row["source_file"], row["source_file_sha256"]] for row in development]
            ),
            "confirmation_files_sha256": canonical_sha(
                [[row["source_file"], row["source_file_sha256"]] for row in confirmation]
            ),
            "development_public_texts_sha256": canonical_sha(
                [[row["id"], row["public_text_sha256"]] for row in development]
            ),
            "confirmation_public_texts_sha256": canonical_sha(
                [[row["id"], row["public_text_sha256"]] for row in confirmation]
            ),
            "prepared_public_snapshot_sha256": sha_file(OUTPUT),
        },
        "leakage_checks": {
            "exact_normalized_text_overlap": 0,
            "gold_solution_executed": False,
            "evaluator_fields_copied_to_public_snapshot": False,
        },
        "roles": {
            "train": "available_but_not_used_for_current_method_development",
            "eval": "frozen_confirmation_only",
        },
        "claim_boundary": (
            "The official train/eval partitions share the resource-allocation template family. "
            "Eval supports instance-level external-benchmark accuracy and paired tests, not an "
            "unseen-family generalization claim. A separate family-disjoint source is required "
            "for that claim."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "counts": manifest["counts"],
        "prepared_public_snapshot_sha256": manifest["bindings"]["prepared_public_snapshot_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
