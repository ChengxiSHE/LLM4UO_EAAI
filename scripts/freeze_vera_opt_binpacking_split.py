#!/usr/bin/env python3
"""Freeze an outcome-blind BinPacking size-extrapolation split."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/optengine_20261004/test_data/canonical/canonical.jsonl"
UPSTREAM = ROOT / "data/raw/optengine_20261004"
OUTPUT = ROOT / "experiments/vera_opt_binpacking_split.json"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_json(value) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def role(size: int) -> str:
    if 10 <= size <= 15:
        return "development"
    if 16 <= size <= 25:
        return "promotion"
    if 26 <= size <= 40:
        return "confirmation"
    raise ValueError("unexpected_binpacking_size")


def main() -> None:
    commit = subprocess.run(
        ["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], capture_output=True,
        text=True, check=True, timeout=15,
    ).stdout.strip()
    counters = defaultdict(int); records = []; unused = []
    for source_row, line in enumerate(SOURCE.read_text().splitlines(), 1):
        row = json.loads(line)
        if row.get("problem_class") != "BinPacking":
            continue
        size = row.get("size")
        if type(size) is not int:
            raise ValueError("invalid_size")
        within_size = counters[size]; counters[size] += 1
        identifier = f"optengine_binpacking_s{size:02d}_i{within_size:02d}"
        value = {
            "problem_id": identifier, "source_row": source_row, "size": size,
            "within_size_index": within_size, "question_sha256": sha_bytes(row["question"].encode()),
            "answer_sha256": sha_json(row["answer"]),
        }
        if within_size < 10:
            value["role"] = role(size); records.append(value)
        else:
            unused.append({**value, "role": "unused_reserve"})
    counts = defaultdict(int)
    for record in records:
        counts[record["role"]] += 1
    if dict(counts) != {"development": 60, "promotion": 100, "confirmation": 150} \
            or len(unused) != 310:
        raise ValueError("unexpected_split_counts")
    value = {
        "schema": "vera-opt-binpacking-split-v1",
        "role": "outcome_blind_size_block_split_for_second_family_skill_induction",
        "source": {
            "repository": "https://github.com/Cardinal-Operations/OPTEngine", "commit": commit,
            "file": "test_data/canonical/canonical.jsonl", "file_sha256": sha_bytes(SOURCE.read_bytes()),
            "license": "not_found_redistribution_blocked",
        },
        "family": "BinPacking",
        "selection": "within each size use indices 0-9; reserve indices 10-19 unused",
        "split_rule": {
            "development": "sizes 10-15, indices 0-9", "promotion": "sizes 16-25, indices 0-9",
            "confirmation": "sizes 26-40, indices 0-9", "unused_reserve": "all indices 10-19",
            "rationale": "strict extrapolation in declared item count; no answer value used",
        },
        "counts": dict(sorted(counts.items())), "unused_reserve_count": len(unused),
        "answer_handling": "only answer hashes are stored; all API inputs are answer-free public projections",
        "records": records, "unused_reserve": unused,
    }
    OUTPUT.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"counts": value["counts"], "unused": len(unused),
                      "output": str(OUTPUT.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
