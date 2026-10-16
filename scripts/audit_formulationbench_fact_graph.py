#!/usr/bin/env python3
"""Audit Flat-K/PCK-K fact identity over an isolated inference root."""

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
from llm4or.formulationbench_fact_graph import audit_inference_root


def _render(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--dataset-tree", required=True)
    parser.add_argument("--expected-pairs", type=int, default=89)
    parser.add_argument("--public-audit", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        audit = audit_inference_root(
            arguments.inference_root,
            source_commit=arguments.source_commit,
            source_tree=arguments.dataset_tree,
            expected_pairs=arguments.expected_pairs,
        )
        raw = _render(audit)
        if arguments.write:
            arguments.public_audit.parent.mkdir(parents=True, exist_ok=True)
            publish_bytes(
                arguments.public_audit.parent, arguments.public_audit.name, raw
            )
        else:
            if arguments.public_audit.read_bytes() != raw:
                raise ValueError("same_fact_audit_drift")
        print(
            json.dumps(
                {
                    "audit_sha256": hashlib.sha256(raw).hexdigest(),
                    "mode": "write" if arguments.write else "check",
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
