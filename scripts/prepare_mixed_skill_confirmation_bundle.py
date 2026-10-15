#!/usr/bin/env python3
"""Prepare the immutable public-only mixed TSP/OR-Debug bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


TSP_PUBLIC_PATH = Path("results/private/tsp_constraint_confirmation_public_20261014.json")
OR_DEBUG_PUBLIC_PATH = Path("experiments/or_debug_confirmation_public_bundle_20261014.json")
OUTPUT_PATH = Path("experiments/mixed_skill_confirmation_bundle_20261014.json")

TSP_PUBLIC_SHA256 = "7c5635e8b78fa2f5d7647890bd8d6199c00e28a128c1c55a1b48f43af12d2fc8"
OR_DEBUG_PUBLIC_SHA256 = "d8e1fadb173ddd9e3ccbd2052ed84d52c47d33d0497245fe74fc00c7773c5383"

_TSP_PUBLIC_FIELDS = ("public_text", "question_sha256", "size")
_OR_DEBUG_PUBLIC_FIELDS = ("model_file", "mps_sha256", "problem_nl")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_pinned(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    raw = path.read_bytes()
    observed = _sha256_bytes(raw)
    if observed != expected_sha256:
        raise ValueError(
            f"{label} source SHA256 mismatch: expected {expected_sha256}, got {observed}"
        )
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} source must be a JSON object")
    return payload


def _record(problem_id: Any, source: str, row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(problem_id, str) or not problem_id:
        raise ValueError(f"{source} row has invalid problem_id")
    if any(field not in row for field in fields):
        raise ValueError(f"{source} row is missing public fields")
    return {
        "record_id": problem_id,
        "source": source,
        "public_envelope": {field: row[field] for field in fields},
    }


def build_bundle(root: Path) -> dict[str, Any]:
    root = Path(root)
    tsp = _load_pinned(root / TSP_PUBLIC_PATH, TSP_PUBLIC_SHA256, "TSP public")
    or_debug = _load_pinned(
        root / OR_DEBUG_PUBLIC_PATH, OR_DEBUG_PUBLIC_SHA256, "OR-Debug public"
    )
    tsp_rows = tsp.get("rows")
    or_rows = or_debug.get("records")
    if not isinstance(tsp_rows, list) or not isinstance(or_rows, list):
        raise ValueError("public sources must contain row lists")

    records = [
        _record(row.get("problem_id"), "tsp", row, _TSP_PUBLIC_FIELDS)
        for row in tsp_rows
        if isinstance(row, dict)
    ]
    records.extend(
        _record(row.get("problem_id"), "or_debug", row, _OR_DEBUG_PUBLIC_FIELDS)
        for row in or_rows
        if isinstance(row, dict)
    )
    expected_count = len(tsp_rows) + len(or_rows)
    if len(records) != expected_count:
        raise ValueError("public source contains a non-object row")

    def sort_key(record: dict[str, Any]) -> tuple[str, str]:
        receipt = _sha256_bytes(_canonical_bytes(record["public_envelope"]))
        return receipt, record["record_id"]

    records.sort(key=sort_key)
    return {
        "schema": "llm4or.mixed_skill_confirmation_bundle.v1",
        "custody": "public_envelopes_only_no_reference_answers",
        "source_sha256": {
            "or_debug": OR_DEBUG_PUBLIC_SHA256,
            "tsp": TSP_PUBLIC_SHA256,
        },
        "counts": {
            "or_debug": len(or_rows),
            "total": len(records),
            "tsp": len(tsp_rows),
        },
        "mixed_order_sha256": _sha256_bytes(_canonical_bytes(records)),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or (root / OUTPUT_PATH)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable bundle: {output}")
    bundle = build_bundle(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    print(_sha256_bytes(output.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
