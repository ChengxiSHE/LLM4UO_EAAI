"""Score the frozen current-method run and publish a body-free result."""

import hashlib
import json
from pathlib import Path

from llm4or.fresh_common38_native import (
    load_cells, load_references, publish_result, score_cells,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/fresh_common38_current_native_plan_20261015.json"


def main():
    plan = json.loads(PLAN.read_text())
    cells = load_cells(plan, ROOT / plan["output"]["private_run_directory"])
    result = score_cells(plan, cells, load_references(ROOT, plan))
    output = ROOT / plan["output"]["public_result"]
    publish_result(output, result)
    print(json.dumps({"state": "published", "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                      "planned": result["aggregate"]["planned"],
                      "correct": result["aggregate"].get("correct", 0),
                      "solver_unavailable": result["aggregate"].get("solver_unavailable", 0),
                      "api_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
