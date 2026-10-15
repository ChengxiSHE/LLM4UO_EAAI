#!/usr/bin/env python3
"""Publish the independent body-free audit of fresh common-38 CoE-safe."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.fresh_common38_coe import AUDIT_PATH
from llm4or.fresh_common38_coe_audit import build_audit, publish


def main() -> None:
    audit = build_audit(ROOT)
    output = ROOT / AUDIT_PATH
    publish(output, audit)
    print(json.dumps({
        "state": "published", "status": audit["status"],
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "correct": audit["checks"]["aggregate"]["correct"],
        "planned": audit["checks"]["aggregate"]["planned"],
        "new_api_calls": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
