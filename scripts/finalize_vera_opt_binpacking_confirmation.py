#!/usr/bin/env python3
"""Zero-call finalizer for the completed BinPacking confirmation evaluation."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest

PLAN = ROOT / "experiments/vera_opt_binpacking_confirmation_plan.json"
AUTH = ROOT / "experiments/vera_opt_binpacking_confirmation_authorization.json"
REPORT = ROOT / "results/vera_opt_binpacking_confirmation.json"


def main() -> None:
    plan = json.loads(PLAN.read_text())
    directory = ROOT / plan["run_directory"]
    inference = json.loads((directory / "inference_complete.json").read_text())
    report = json.loads(REPORT.read_text())
    progress = json.loads((directory / "progress.json").read_text())
    if inference.get("plan_sha256") != digest(plan) or len(inference.get("cells", [])) != 150:
        raise ValueError("confirmation_inference_binding")
    if report.get("plan_sha256") != digest(plan) or report.get("records") != 150:
        raise ValueError("confirmation_report_binding")
    if progress.get("work") != {"complete": 150} or progress.get("halt") is not None:
        raise ValueError("confirmation_work_incomplete")
    gate = report["confirmation_gate"]
    status = "completed_confirmation_passed" if gate["confirmed"] else "completed_confirmation_failed"
    auth = json.loads(AUTH.read_text())
    auth.update(status=status, closed_usage=progress,
                closed_at=datetime.now(timezone.utc).isoformat(),
                further_api_calls_authorized=False)
    write_json(AUTH, auth)
    write_json(directory / "completed.json", {
        "plan_sha256": digest(plan), "state": status,
        "usage": progress, "confirmation_gate": gate,
        "zero_call_finalizer": True,
        "finalizer_reason": "Runner expected promoted instead of confirmed after evaluation completed.",
    })
    write_json(directory / "controller.json", {
        "state": status, "plan_sha256": digest(plan), "zero_call_finalizer": True,
    })
    print(json.dumps({"api_requests": 0, "state": status,
                      "plan_sha256": digest(plan)}, sort_keys=True))


if __name__ == "__main__":
    main()
