#!/usr/bin/env python3
"""Audit exact identity between mixed routing and frozen direct execution."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.mixed_skill_router import OR_DEBUG_ROUTE, TSP_ROUTE


INPUTS = {
    "bundle": (
        Path("experiments/public_projections/mixed_skill_confirmation_bundle_projection_20261015.json"),
        "da9a35dcb6b76e2289a7a9f0613384661dac80f6e96b8c3ed41ba1f5538fee65",
    ),
    "mixed": (
        Path("results/public_projections/mixed_skill_confirmation_outputs_projection_20261015.json"),
        "5f7b5860f4e50e5ce37b85e49fbd9e3b96488429bf08e779fe17c503ded1ad70",
    ),
    "or_debug_direct": (
        Path("results/public_projections/or_debug_confirmation_method_outputs_projection_20261015.json"),
        "d714e72bb9207ba7ca7146f43a196f9b6599e1e43b5ea94446fe9a60bfbbcf46",
    ),
    "tsp_direct": (
        Path("results/public_projections/tsp_constraint_confirmation_candidates_projection_20261015.json"),
        "bbd4e31ddf317df76dc7e84ce00be143ec078f159663f57fa443226610a27e23",
    ),
}
OUTPUT = Path("results/mixed_skill_confirmation_public_audit_v3_20261015.json")
EXPECTED_ROUTE = {"or_debug": OR_DEBUG_ROUTE, "tsp": TSP_ROUTE}


def _unique_map(
    rows: list[dict[str, Any]], key: str
) -> tuple[dict[str, dict[str, Any]], int, int]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid = 0
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get(key), str):
            grouped[row[key]].append(row)
        else:
            invalid += 1
    duplicates = sum(max(0, len(group) - 1) for group in grouped.values())
    return {identity: group[0] for identity, group in grouped.items()}, duplicates, invalid


def audit_identity(
    bundle_records: list[dict[str, Any]],
    mixed_records: list[dict[str, Any]],
    tsp_direct_rows: list[dict[str, Any]],
    or_debug_direct_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare mixed terminal outputs with their frozen direct counterparts."""

    bundle_by_id, duplicate_bundle, invalid_bundle = _unique_map(
        bundle_records, "record_id"
    )
    mixed_by_id, duplicate_mixed, invalid_mixed = _unique_map(
        mixed_records, "record_id"
    )
    tsp_by_id, duplicate_tsp_direct, invalid_tsp_direct = _unique_map(
        tsp_direct_rows, "problem_id"
    )
    or_by_id, duplicate_or_direct, invalid_or_direct = _unique_map(
        or_debug_direct_rows, "problem_id"
    )
    direct_by_source = {"tsp": tsp_by_id, "or_debug": or_by_id}

    families = {
        source: {
            "records": 0,
            "exact_matches": 0,
            "output_mismatches": 0,
            "route_mismatches": 0,
            "terminal_failures": 0,
            "missing_mixed_records": 0,
            "missing_direct_records": 0,
        }
        for source in ("or_debug", "tsp")
    }
    for record_id, public in bundle_by_id.items():
        source = public.get("source")
        if source not in families:
            continue
        family = families[source]
        family["records"] += 1
        mixed = mixed_by_id.get(record_id)
        if mixed is None:
            family["missing_mixed_records"] += 1
            continue
        if mixed.get("source") != source:
            family.setdefault("source_mismatches", 0)
            family["source_mismatches"] += 1
        if mixed.get("route") != EXPECTED_ROUTE[source]:
            family["route_mismatches"] += 1
        if mixed.get("status") != "complete":
            family["terminal_failures"] += 1
        direct = direct_by_source[source].get(record_id)
        if direct is None:
            family["missing_direct_records"] += 1
            continue
        expected_output_sha256 = (
            direct.get("candidate_sha256")
            if source == "tsp"
            else direct.get("evolved", {}).get("output_sha256")
        )
        if mixed.get("output_sha256") != expected_output_sha256:
            family["output_mismatches"] += 1
        elif (
            mixed.get("route") == EXPECTED_ROUTE[source]
            and mixed.get("status") == "complete"
        ):
            family["exact_matches"] += 1

    expected_ids = set(bundle_by_id)
    unexpected_mixed = len(set(mixed_by_id) - expected_ids)
    status_counts = dict(sorted(Counter(row.get("status") for row in mixed_records).items()))
    route_counts = dict(sorted(Counter(str(row.get("route")) for row in mixed_records).items()))
    for family in families.values():
        family.setdefault("source_mismatches", 0)
    totals = {
        key: sum(family[key] for family in families.values())
        for key in (
            "exact_matches",
            "missing_direct_records",
            "missing_mixed_records",
            "output_mismatches",
            "records",
            "route_mismatches",
            "source_mismatches",
            "terminal_failures",
        )
    }
    totals["terminal_failures"] = sum(
        row.get("status") != "complete" if isinstance(row, dict) else True
        for row in mixed_records
    )
    totals.update(
        {
            "duplicate_bundle_records": duplicate_bundle,
            "duplicate_direct_records": duplicate_tsp_direct + duplicate_or_direct,
            "duplicate_mixed_records": duplicate_mixed,
            "invalid_bundle_records": invalid_bundle,
            "invalid_direct_records": invalid_tsp_direct + invalid_or_direct,
            "invalid_mixed_records": invalid_mixed,
            "unexpected_mixed_records": unexpected_mixed,
        }
    )
    exact_identity_pass = (
        totals["records"] == len(bundle_records)
        and totals["exact_matches"] == totals["records"]
        and all(
            totals[key] == 0
            for key in (
                "duplicate_bundle_records",
                "duplicate_direct_records",
                "duplicate_mixed_records",
                "invalid_bundle_records",
                "invalid_direct_records",
                "invalid_mixed_records",
                "missing_direct_records",
                "missing_mixed_records",
                "output_mismatches",
                "route_mismatches",
                "source_mismatches",
                "terminal_failures",
                "unexpected_mixed_records",
            )
        )
    )
    return {
        "exact_identity_pass": exact_identity_pass,
        "families": families,
        "route_counts": route_counts,
        "status_counts": status_counts,
        "totals": totals,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or (root / OUTPUT)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite immutable audit: {output}")
    payloads = {}
    observed_hashes = {}
    for label, (relative, expected) in INPUTS.items():
        path = root / relative
        observed = _sha256(path)
        if observed != expected:
            raise ValueError(f"{label} SHA256 mismatch")
        observed_hashes[label] = observed
        payloads[label] = json.loads(path.read_text(encoding="utf-8"))

    audit = audit_identity(
        payloads["bundle"]["records"],
        payloads["mixed"]["records"],
        payloads["tsp_direct"]["skill_records"],
        payloads["or_debug_direct"]["records"],
    )
    audit.update(
        {
            "schema": "llm4or.mixed_skill_confirmation_public_audit.v1",
            "input_sha256": dict(sorted(observed_hashes.items())),
            "inherited_confirmation_endpoints": {
                "or_debug": {
                    "denominator": 2845,
                    "evolved_correct": 2752,
                    "static_correct": 828,
                },
                "tsp": {
                    "denominator": 140,
                    "skill_correct": 100,
                    "static_correct": 54,
                },
            },
            "claim_guard": {
                "accuracy_recomputed": False,
                "new_generalization_claimed": False,
                "retrospective_composition_only": True,
                "preservation_claim_allowed": bool(audit["exact_identity_pass"]),
            },
        }
    )
    if not audit["exact_identity_pass"]:
        raise RuntimeError("mixed identity gate failed")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "sha256": _sha256(output), "totals": audit["totals"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
