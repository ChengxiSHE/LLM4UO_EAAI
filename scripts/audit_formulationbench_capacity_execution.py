#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import (  # noqa: E402
    PLAN_PATH, RESULT_PATH, ledger_summary, publish_new,
)
from llm4or.schema import digest  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


plan = json.loads((ROOT / PLAN_PATH).read_text())
result = json.loads((ROOT / RESULT_PATH).read_text())
ledger = ledger_summary(ROOT / plan["run_directory"])
checks = {
    "plan_binding": result["plan_sha256"] == digest(plan),
    "capacity_gate_passed": result["capacity_gate"]["passed"] is True,
    "all_eight_terminal": result["capacity_gate"]["terminal_cells"] == 8,
    "all_eight_typed": result["capacity_gate"]["valid_typed_responses"] == 8,
    "zero_infrastructure_unavailable": result["capacity_gate"]["infrastructure_unavailable"] == 0,
    "zero_method_failure": result["capacity_gate"]["method_failures"] == 0,
    "zero_retry": ledger["max_attempt_ordinal"] == 1,
    "zero_halt": ledger["halt"] is None,
    "restart_zero_new": result["capacity_gate"]["restart_new_items"] == 0,
    "frozen_files_match": all(sha(ROOT / path) == expected for path, expected in plan["frozen_files"].items()),
}
audit = {
    "schema": "formulationbench-same-knowledge-v1-capacity-execution-audit",
    "status": "passed" if all(checks.values()) else "failed",
    "plan_file_sha256": sha(ROOT / PLAN_PATH),
    "plan_sha256": digest(plan),
    "result_file_sha256": sha(ROOT / RESULT_PATH),
    "checks": checks,
    "observed": {
        "logical_requests": ledger["logical_slots"],
        "physical_attempts": ledger["physical_attempts"],
        "maximum_completion_tokens": ledger["maximum_completion_tokens"],
        "retry_attempts": 0,
        "model": plan["model"],
        "max_concurrent_requests": plan["resilience"]["max_concurrent_requests"],
    },
    "privacy": {
        "request_bodies_read": False,
        "response_bodies_read": False,
        "benchmark_bodies_used": False,
        "benchmark_labels_used": False,
        "credentials_read_by_auditor": False,
    },
    "claim_boundary": "The synthetic short-output transport gate passed; no benchmark accuracy was estimated.",
}
if audit["status"] != "passed":
    raise SystemExit("capacity_execution_audit_failed")
publish_new(ROOT / "experiments/formulationbench_capacity_canary_execution_audit_20261016.json", audit)
print(audit["status"])
