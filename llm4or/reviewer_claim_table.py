"""Rebuild the paper's headline aggregate table from public evidence only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SOURCE_PATHS = (
    "results/tsp_constraint_confirmation_root_closure_20261014.json",
    "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json",
    "experiments/fresh_common38_common_protocol_synthesis_20261015.json",
    "results/mixed_skill_confirmation_public_audit_v3_20261015.json",
)


def _read(root: Path, relative: str) -> tuple[dict[str, Any], str]:
    payload = (root / relative).read_bytes()
    return json.loads(payload), hashlib.sha256(payload).hexdigest()


def _paired(record: dict[str, Any]) -> dict[str, int]:
    return {
        "control_correct": record["static_correct"],
        "method_correct": record["evolved_correct"],
        "corrections": record["corrections"],
        "regressions": record["regressions"],
        "both_wrong": record["both_wrong"],
    }


def build_claim_table(root: Path) -> dict[str, Any]:
    root = Path(root)
    loaded = {path: _read(root, path) for path in SOURCE_PATHS}
    tsp = loaded[SOURCE_PATHS[0]][0]["result"]
    or_debug = loaded[SOURCE_PATHS[1]][0]["comparison"]
    common = loaded[SOURCE_PATHS[2]][0]
    router = loaded[SOURCE_PATHS[3]][0]

    return {
        "schema": "llm4or-reviewer-claim-table-v1",
        "source_sha256": {path: loaded[path][1] for path in SOURCE_PATHS},
        "tsp": {
            "denominator": tsp["denominator"],
            "control_correct": tsp["static_correct"],
            "method_correct": tsp["skill_correct"],
            "corrections": tsp["corrections"],
            "regressions": tsp["regressions"],
        },
        "or_debug": {
            "denominator": or_debug["records"],
            "primary_endpoint": "released_labels",
            "released_labels": _paired(or_debug["released_primary"]),
            "source_corrected_sensitivity": _paired(or_debug["corrected_primary"]),
        },
        "fresh_common38": {
            "denominator": common["cohort"]["planned"],
            "correct_by_method": {
                row["method"]: row["correct"] for row in common["method_native_rows"]
            },
            "paired_against_current": [
                {
                    "comparison": row["comparison"],
                    "corrections": row["corrections"],
                    "regressions": row["regressions"],
                }
                for row in common["paired_against_current"]
            ],
            "claim_boundary": common["claim_boundary"],
        },
        "mixed_router": {
            "records": router["totals"]["records"],
            "exact_matches": router["totals"]["exact_matches"],
            "route_mismatches": router["totals"]["route_mismatches"],
            "output_mismatches": router["totals"]["output_mismatches"],
            "terminal_failures": router["totals"]["terminal_failures"],
        },
        "privacy": {
            "aggregate_only": True,
            "contains_credentials": False,
            "contains_evaluator_answers": False,
            "contains_item_level_outputs": False,
            "contains_task_bodies": False,
        },
        "claim_boundary": [
            "The TSP and OR-Debug rows compare complete authored systems against frozen controls; they do not isolate the causal contribution of representation, verification, routing, or promotion.",
            "The common-38 rows are frozen implementation outcomes under unequal construction and inference budgets, not a broad algorithmic leaderboard.",
            "The mixed-router row is an identity reconstruction and does not rescore benchmark accuracy.",
        ],
    }


def write_claim_table(root: Path, output: Path, *, check: bool) -> bytes:
    payload = (json.dumps(build_claim_table(root), indent=2, sort_keys=True) + "\n").encode()
    output = Path(output)
    if check:
        if not output.exists() or output.read_bytes() != payload:
            raise ValueError("claim_table_drift")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return payload
