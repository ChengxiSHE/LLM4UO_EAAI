#!/usr/bin/env python3
"""Validate and publish the fixed RetailOpt-190 custody projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.atomic_publisher import publish_bytes
from llm4or.retailopt190_custody import (
    RetailOptCustodyError,
    SourceIdentity,
    build_custody,
    publish_custody,
)


def _render(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--public-audit", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        identity = SourceIdentity(arguments.source_commit, arguments.dataset_sha256)
        bundle = build_custody(arguments.source_root, identity)
        result = publish_custody(arguments.custody_root, bundle.entries)
        audit_raw = _render(bundle.public_audit)
        try:
            relative = arguments.public_audit.resolve().relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RetailOptCustodyError("public_audit_outside_project") from exc
        public_result = publish_bytes(ROOT, relative, audit_raw)
        print(
            json.dumps(
                {
                    "status": "passed",
                    "custody_transaction": result.transaction_id,
                    "public_transaction": public_result.transaction_id,
                    "records": bundle.public_audit["counts"]["records"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (RetailOptCustodyError, OSError, ValueError) as exc:
        reason = type(exc).__name__
        if str(exc) and not any(character in str(exc) for character in "\n\r/\\"):
            reason = str(exc)
        print(json.dumps({"status": "failed", "reason": reason}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
