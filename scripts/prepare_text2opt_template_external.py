"""Prepare six capacity-compatible Text2Opt template families for confirmation.

Only public descriptions and non-outcome size/type metadata are projected.
Upstream gold programs are never executed or copied into model-visible data.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/text2opt_bench_20261003"
TEMPLATE = SOURCE / "synthetic_dataset/Template"
OUTPUT = ROOT / "data/prepared_benchmarks/text2opt_template_confirmation_v1.json"
MANIFEST = ROOT / "data/manifests/text2opt_template_confirmation_v1.json"
REVISION = "1dac06be656c41d827ef20987cf8af0b48d382a2"
CATEGORIES = (
    "transportation",
    "disaster_response",
    "jssp",
    "vrptw",
    "rcpsp",
    "modified_facility_location",
)
MAX_VARIABLES = 96
MAX_CONSTRAINTS = 192


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def canonical_sha(value):
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def normalized(value):
    return re.sub(r"\s+", " ", value).strip().lower()


def main():
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=SOURCE, check=True, capture_output=True, text=True
    ).stdout.strip()
    if revision != REVISION:
        raise ValueError("text2opt_revision_mismatch")
    rows = []
    category_stats = {}
    for category in CATEGORIES:
        files = sorted(TEMPLATE.glob(f"**/{category}/small/*.json"))
        if len(files) != 50:
            raise ValueError("unexpected_template_category_size:" + category)
        variables, constraints = [], []
        for path in files:
            value = json.loads(path.read_text())
            text = value.get("LLM_description")
            meta = value.get("meta", {})
            if not isinstance(text, str) or not text.strip():
                raise ValueError("missing_public_description:" + path.name)
            variables.append(meta.get("num_vars"))
            constraints.append(meta.get("num_constraints"))
            if not (type(meta.get("num_vars")) is int and type(meta.get("num_constraints")) is int):
                raise ValueError("missing_capacity_metadata:" + category)
            if meta["num_vars"] > MAX_VARIABLES or meta["num_constraints"] > MAX_CONSTRAINTS:
                continue
            problem_id = "text2opt_" + category + "_" + path.stem
            rows.append({
                "id": problem_id,
                "family": category,
                "source_file": str(path.relative_to(SOURCE)),
                "source_file_sha256": sha_file(path),
                "public": {
                    "id": problem_id,
                    "profile": "description_parameters_v1",
                    "text": text,
                    "parameters": [],
                    "instances": [],
                },
                "public_text_sha256": sha_bytes(text.encode()),
                "non_outcome_metadata": {
                    "problem_type": meta.get("problem_type"),
                    "optimization_type": meta.get("optimization_type"),
                    "num_vars": meta.get("num_vars"),
                    "num_constraints": meta.get("num_constraints"),
                },
            })
        if any(type(value) is not int for value in variables + constraints):
            raise ValueError("missing_capacity_metadata:" + category)
        category_stats[category] = {
            "source_records": len(files),
            "retained_records": sum(row["family"] == category for row in rows),
            "max_variables": max(variables),
            "max_constraints": max(constraints),
        }
    if len(rows) != 183 or len({row["id"] for row in rows}) != 183:
        raise ValueError("template_confirmation_size_or_id_error")
    if max(row["non_outcome_metadata"]["num_vars"] for row in rows) > MAX_VARIABLES:
        raise ValueError("template_variable_capacity_exceeded")
    if max(row["non_outcome_metadata"]["num_constraints"] for row in rows) > MAX_CONSTRAINTS:
        raise ValueError("template_constraint_capacity_exceeded")
    text_counts = Counter(normalized(row["public"]["text"]) for row in rows)
    if any(count > 1 for count in text_counts.values()):
        raise ValueError("duplicate_normalized_template_text")
    prepared = {
        "schema": "text2opt-template-confirmation-public-v1",
        "source_revision": REVISION,
        "method_development_records": 0,
        "confirmation": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(prepared, sort_keys=True, separators=(",", ":")) + "\n")
    manifest = {
        "schema": "text2opt-template-confirmation-manifest-v1",
        "source": {
            "repository": "https://github.com/SprocketLab/Text2Opt-Bench",
            "revision": REVISION,
            "license": "MIT",
            "upstream_root": "synthetic_dataset/Template",
        },
        "selection": {
            "categories": list(CATEGORIES),
            "records": len(rows),
            "category_stats": category_stats,
            "rule": (
                "Before outcome access, retain records from six standard small-tier linear/MILP categories when "
                "published metadata stay within 96 variables and 192 constraints. Exclude MIQP, nonlinear, "
                "multi-objective, large stochastic, alternate prose/capped variants, and larger records that "
                "cannot be represented reliably inside the planned structured-output budget."
            ),
            "answers_used": False,
        },
        "bindings": {
            "source_files_sha256": canonical_sha(
                [[row["source_file"], row["source_file_sha256"]] for row in rows]
            ),
            "public_texts_sha256": canonical_sha(
                [[row["id"], row["public_text_sha256"]] for row in rows]
            ),
            "prepared_public_snapshot_sha256": sha_file(OUTPUT),
        },
        "leakage_checks": {
            "duplicate_normalized_public_texts": 0,
            "gold_solution_executed": False,
            "evaluator_fields_copied_to_public_snapshot": False,
            "used_for_method_development": False,
        },
        "claim_boundary": (
            "These six upstream categories are frozen external confirmation families. Accuracy is reported both "
            "over all 183 capacity-compatible instances and by category; category-level sensitivity is mandatory."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "output": str(OUTPUT.relative_to(ROOT)),
        "records": len(rows),
        "families": len(CATEGORIES),
        "prepared_public_snapshot_sha256": manifest["bindings"]["prepared_public_snapshot_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
