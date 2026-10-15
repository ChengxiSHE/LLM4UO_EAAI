#!/usr/bin/env python3
"""Materialize or verify the four fixed release-safe evidence projections."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.release_safe_projections import (  # noqa: E402
    ProjectionError,
    project_mixed_bundle,
    project_mixed_outputs,
    project_or_debug_evaluation,
    project_or_debug_outputs,
    project_tsp_candidates,
    project_tsp_public_input,
    publish_exclusive,
)


PROJECTIONS = (
    (
        "experiments/mixed_skill_confirmation_bundle_20261014.json",
        "944757ee0ef04111c3ff921e32f321385787c102a528bba6165c00addd4dafbb",
        "experiments/public_projections/mixed_skill_confirmation_bundle_projection_20261015.json",
        project_mixed_bundle,
    ),
    (
        "results/or_debug_confirmation_evaluation_20261014.json",
        "04342d960613c01d3e354d742e39eec5949a90a53ca06fe0c6e30b6be057b66e",
        "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json",
        project_or_debug_evaluation,
    ),
    (
        "results/or_debug_confirmation_method_outputs_20261014.json",
        "9ab4058fd9f641f96279d5880820c13cbf7277af779fc42c62503ddd4c7d27ec",
        "results/public_projections/or_debug_confirmation_method_outputs_projection_20261015.json",
        project_or_debug_outputs,
    ),
    (
        "results/mixed_skill_confirmation_outputs_20261014.json",
        "719d0d739ef98723baeea58d00355c0a4eba44e5ae1cb267a10dd5f0a12f67d1",
        "results/public_projections/mixed_skill_confirmation_outputs_projection_20261015.json",
        project_mixed_outputs,
    ),
    (
        "results/private/tsp_constraint_confirmation_public_20261014.json",
        "7c5635e8b78fa2f5d7647890bd8d6199c00e28a128c1c55a1b48f43af12d2fc8",
        "results/public_projections/tsp_constraint_confirmation_public_projection_20261015.json",
        project_tsp_public_input,
    ),
    (
        "results/private/tsp_constraint_confirmation_candidates_20261014.json",
        "f114fff73ff3c80cc557b7642a336a417a8bb1b85609f862cd2260dbad0c6627",
        "results/public_projections/tsp_constraint_confirmation_candidates_projection_20261015.json",
        project_tsp_candidates,
    ),
)


def build(*, check: bool) -> dict[str, str]:
    published = {}
    for source_name, expected_sha256, target_name, projector in PROJECTIONS:
        raw = (ROOT / source_name).read_bytes()
        actual_sha256 = hashlib.sha256(raw).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ProjectionError(f"source_hash_mismatch:{source_name}")
        try:
            source = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProjectionError(f"invalid_source_json:{source_name}") from exc
        projection = projector(source, raw)
        published[target_name] = publish_exclusive(
            Path(target_name), projection, ROOT, check=check
        )
    return published


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build(check=args.check)
    print(json.dumps({"artifacts": result, "mode": "check" if args.check else "write"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
