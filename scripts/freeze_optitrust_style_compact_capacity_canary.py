#!/usr/bin/env python3
"""Freeze the four-item compact-sidecar capacity gate."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.optitrust_style_compact_canary import AUTH_PATH, PLAN_PATH, authorization, build_plan, publish_new
from llm4or.schema import digest


def main() -> None:
    plan = build_plan(ROOT)
    publish_new(ROOT / PLAN_PATH, plan)
    publish_new(ROOT / AUTH_PATH, authorization(ROOT, plan))
    print(json.dumps({
        "state": "frozen", "plan_sha256": digest(plan),
        "synthetic_cells": plan["matrix"]["inference_cells"],
        "maximum_logical_requests": plan["matrix"]["logical_requests"],
        "maximum_physical_attempts": plan["limits"]["max_requests"],
        "concurrency": plan["resilience"]["max_concurrent_requests"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
