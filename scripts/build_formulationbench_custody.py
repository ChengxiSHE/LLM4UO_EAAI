#!/usr/bin/env python3
"""Build a body-free source census for the fixed FormulationBench snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.atomic_publisher import publish_bytes
from llm4or.formulationbench_custody import (
    CensusCounts,
    CustodyError,
    SourceIdentity,
    build_custody_bundle,
    check_custody_bundle,
    census_source,
    publish_custody_bundle,
)


def _render(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--schema-census", action="store_true")
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--dataset-tree", required=True)
    parser.add_argument("--expected-problems", type=int, default=20)
    parser.add_argument("--expected-formulations", type=int, default=109)
    parser.add_argument("--expected-pairs", type=int, default=89)
    parser.add_argument("--expected-proofs", type=int, default=63)
    parser.add_argument("--public-audit", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        source = SourceIdentity(arguments.source_commit, arguments.dataset_tree)
        expected = CensusCounts(
            problems=arguments.expected_problems,
            formulations=arguments.expected_formulations,
            pairs=arguments.expected_pairs,
            proofs=arguments.expected_proofs,
        )
        if arguments.schema_census:
            audit = census_source(arguments.raw_root, source, expected=expected)
            mode = "schema-census"
        else:
            if arguments.custody_root is None:
                raise CustodyError("custody_root_required")
            bundle = build_custody_bundle(
                arguments.raw_root, source, expected=expected
            )
            audit = dict(bundle.public_audit)
            audit["status"] = "published_private_bundle_verified"
            if arguments.write:
                publish_custody_bundle(arguments.custody_root, bundle)
            check_custody_bundle(arguments.custody_root, bundle)
            mode = "write" if arguments.write else "check"
        payload = _render(audit)
        if arguments.check:
            try:
                observed = arguments.public_audit.read_bytes()
            except (FileNotFoundError, OSError) as exc:
                raise CustodyError("public_audit_missing_or_unsafe") from exc
            if observed != payload:
                raise CustodyError("public_audit_drift")
        else:
            arguments.public_audit.parent.mkdir(parents=True, exist_ok=True)
            publish_bytes(
                arguments.public_audit.parent,
                arguments.public_audit.name,
                payload,
            )
        print(
            json.dumps(
                {
                    "audit_sha256": hashlib.sha256(payload).hexdigest(),
                    "mode": mode,
                    "pairs": audit["counts"]["pairs"],
                    "status": "passed",
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        reason = str(exc)
        if not reason or any(character in reason for character in "\n\r"):
            reason = type(exc).__name__
        print(
            json.dumps({"reason": reason, "status": "failed"}, sort_keys=True),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
