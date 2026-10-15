#!/usr/bin/env python3
"""Freeze an outcome-blind three-way Knapsack split from OPT-Engine canonical data."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/optengine_20261004/test_data/canonical/canonical.jsonl"
UPSTREAM = ROOT / "data/raw/optengine_20261004"
OUTPUT = ROOT / "experiments/vera_opt_generation1_split.json"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_json(value) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def role(size: int) -> str:
    if 5 <= size <= 10:
        return "development"
    if 11 <= size <= 19:
        return "promotion"
    if 20 <= size <= 30:
        return "confirmation"
    raise ValueError("unexpected_knapsack_size")


def main() -> None:
    commit = subprocess.run(
        ["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True, timeout=15,
    ).stdout.strip()
    counters = defaultdict(int)
    records = []
    for source_row, line in enumerate(SOURCE.read_text().splitlines(), 1):
        row = json.loads(line)
        if row.get("problem_class") != "Knapsack":
            continue
        size = row.get("size")
        if type(size) is not int:
            raise ValueError("invalid_size")
        within_size = counters[size]
        counters[size] += 1
        identifier = f"optengine_knapsack_s{size:02d}_i{within_size:02d}"
        records.append({
            "problem_id": identifier,
            "source_row": source_row,
            "size": size,
            "within_size_index": within_size,
            "role": role(size),
            "question_sha256": sha_bytes(row["question"].encode()),
            "answer_sha256": sha_json(row["answer"]),
        })
    counts = defaultdict(int)
    for record in records:
        counts[record["role"]] += 1
    if dict(counts) != {"development": 60, "promotion": 90, "confirmation": 110}:
        raise ValueError("unexpected_split_counts")
    value = {
        "schema": "vera-opt-generation1-split-v1",
        "role": "outcome_blind_size_block_split_for_automatic_skill_induction",
        "source": {
            "repository": "https://github.com/Cardinal-Operations/OPTEngine",
            "commit": commit,
            "file": "test_data/canonical/canonical.jsonl",
            "file_sha256": sha_bytes(SOURCE.read_bytes()),
            "license": "not_found_redistribution_blocked",
        },
        "family": "Knapsack",
        "selection": "all canonical Knapsack rows",
        "split_rule": {
            "development": "sizes 5-10",
            "promotion": "sizes 11-19",
            "confirmation": "sizes 20-30",
            "rationale": "strict extrapolation in declared problem size; no answer value used",
        },
        "counts": dict(sorted(counts.items())),
        "answer_handling": (
            "only answer hashes are stored here; proposer receives development public text only; "
            "promotion and confirmation answers remain evaluator-only"
        ),
        "records": records,
    }
    OUTPUT.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"counts": value["counts"], "output": str(OUTPUT.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
