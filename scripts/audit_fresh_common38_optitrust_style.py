#!/usr/bin/env python3
"""Publish or check the independent OptiTrust-style common-38 audit."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.fresh_common38_optitrust_style import AUDIT_PATH
from llm4or.fresh_common38_optitrust_style_audit import (
    build_audit, publish_or_check,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    audit = build_audit(ROOT)
    output = ROOT / AUDIT_PATH
    publish_or_check(output, audit, check=args.check)
    print(json.dumps({
        "state": "checked" if args.check else "published",
        "status": audit["status"],
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "correct": audit["checks"]["aggregate"]["correct"],
        "planned": audit["checks"]["aggregate"]["planned"],
        "new_api_calls": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
