#!/usr/bin/env python3
"""Run or resume the frozen OptiTrust-style common-38 row."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formal_gateway import FormalGateway
from llm4or.formal_provider import check_profile_metadata
from llm4or.fresh_common38_optitrust_style_compact import PLAN_PATH, run_plan


def main() -> None:
    plan = json.loads((ROOT / PLAN_PATH).read_text())
    check_profile_metadata()
    gateway = FormalGateway(
        ROOT, plan, authorization_path=plan["authorization_path"],
    )
    output = run_plan(
        ROOT, plan, ROOT / plan["run_directory"], gateway,
        workers=plan["resilience"]["max_concurrent_requests"],
    )
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
