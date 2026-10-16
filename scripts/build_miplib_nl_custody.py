#!/usr/bin/env python3
"""Build or verify body-separated custody for the fixed MIPLIB-NL snapshot."""

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
from llm4or.miplib_nl_custody import (
    CustodyError,
    SourceIdentity,
    build_custody_bundle,
    build_schema_census,
    check_custody_bundle,
    publish_custody_bundle,
)


def _render(value) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _write_public_audit(path: Path, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    publish_bytes(path.parent, path.name, payload)


def _published_audit(bundle) -> dict:
    audit = dict(bundle.public_audit)
    audit["status"] = "published_private_bundle_verified"
    return audit


def _summary(mode: str, payload: bytes, instances: int) -> str:
    return json.dumps(
        {
            "audit_sha256": hashlib.sha256(payload).hexdigest(),
            "instances": instances,
            "mode": mode,
            "status": "passed",
        },
        sort_keys=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--schema-census", action="store_true")
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--dataset-tree", required=True)
    parser.add_argument("--public-audit", type=Path, required=True)
    arguments = parser.parse_args()

    try:
        source = SourceIdentity(
            commit=arguments.source_commit, dataset_tree=arguments.dataset_tree
        )
        if arguments.schema_census:
            census = build_schema_census(arguments.raw_root, source)
            payload = _render(census)
            _write_public_audit(arguments.public_audit, payload)
            print(_summary("schema-census", payload, census["counts"]["instances"]))
            return 0

        bundle = build_custody_bundle(arguments.raw_root, source)
        audit = _published_audit(bundle)
        payload = _render(audit)
        if arguments.write:
            publish_custody_bundle(arguments.custody_root, bundle)
            check_custody_bundle(arguments.custody_root, bundle)
            _write_public_audit(arguments.public_audit, payload)
            print(_summary("write", payload, audit["counts"]["instances"]))
            return 0

        check_custody_bundle(arguments.custody_root, bundle)
        try:
            observed = arguments.public_audit.read_bytes()
        except (FileNotFoundError, OSError) as exc:
            raise CustodyError("public_audit_missing_or_unsafe") from exc
        if observed != payload:
            raise CustodyError("public_audit_drift")
        print(_summary("check", payload, audit["counts"]["instances"]))
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
