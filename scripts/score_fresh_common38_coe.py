#!/usr/bin/env python3
"""Publish the body-free fresh-common current-snapshot CoE-safe result."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.fresh_common38_coe import (
    PLAN_PATH, ledger_summary, load_cells, publish_new, score_cells,
)


def main() -> None:
    plan = json.loads((ROOT / PLAN_PATH).read_text())
    directory = ROOT / plan["run_directory"]
    result = score_cells(plan, load_cells(plan, directory), ledger_summary(directory))
    output = ROOT / plan["output"]["public_result"]
    publish_new(output, result)
    print(json.dumps({
        "state": "published", "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "correct": result["aggregate"]["correct"],
        "planned": result["aggregate"]["planned"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
