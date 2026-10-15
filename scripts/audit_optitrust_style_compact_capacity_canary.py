#!/usr/bin/env python3
"""Publish or verify the no-new-call compact capacity audit."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.optitrust_style_compact_canary import AUDIT_PATH, PLAN_PATH, build_audit_from, publish_new
from llm4or.schema import canonical


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan_path = ROOT / PLAN_PATH
    plan = json.loads(plan_path.read_text())
    audit = build_audit_from(
        ROOT, plan, plan_path, ROOT / plan["run_directory"],
        ROOT / plan["output"]["public_result"], expected_offline=False,
    )
    output = ROOT / AUDIT_PATH
    if args.check:
        if not output.is_file() or canonical(json.loads(output.read_text())) != canonical(audit):
            raise ValueError("audit_byte_identity")
    else:
        publish_new(output, audit)
    print(json.dumps({"state": "checked" if args.check else "published", "status": audit["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
