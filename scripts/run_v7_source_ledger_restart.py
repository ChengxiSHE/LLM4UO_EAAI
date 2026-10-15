"""Run the clean-room restart of the authorized v7 source-ledger pilot."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_gateway import FormalGateway
from llm4or.formal_provider import BASE_URL, MODEL, PROFILE, check_profile_metadata
from llm4or.gateway import Stopped
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.source_ledger_runtime import VERSION
from scripts.evaluate_v7_source_ledger_pilot import write_report
from scripts.run_v7_source_ledger_pilot import Driver

PLAN_PATH = ROOT / "experiments/v7_source_ledger_restart_plan.json"
AUTH_PATH = ROOT / "experiments/v7_source_ledger_restart_authorization.json"


def preflight(plan, require_approval=True):
    """Validate the restart without making a provider request."""
    import shutil
    actual = {
        "python": platform.python_version(),
        "machine": platform.machine(),
        "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]},
    }
    if actual != plan["runtime"]:
        raise Stopped("runtime_version_changed")
    if plan["runtime_version"] != VERSION or plan["resilience"]["max_concurrent_requests"] != 5:
        raise Stopped("v7_restart_runtime_changed")
    if shutil.disk_usage(ROOT).free < plan["limits"]["minimum_free_disk_bytes"]:
        raise Stopped("free_disk_below_guard")
    for path, expected in plan["frozen_files"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise Stopped("frozen_file_changed:" + path)
    registry = {row["id"]: row for row in load_public_registry(ROOT)}
    if any(pid not in registry or registry[pid]["input_sha256"] != value
           for pid, value in plan["public_inputs"].items()):
        raise Stopped("public_input_changed")
    if (plan["endpoint"], plan["model"], plan["credential_profile"]) != (BASE_URL, MODEL, str(PROFILE)):
        raise Stopped("formal_provider_changed")
    check_profile_metadata()
    auth = json.loads(AUTH_PATH.read_text())
    if auth["plan_sha256"] != digest(plan) or require_approval and auth["status"] != "approved":
        raise Stopped("v7_restart_approval_required")
    parent = plan["incident_recovery"]
    original_auth = json.loads((ROOT / parent["authorization_path"]).read_text())
    if (original_auth.get("status") != "closed_invalid_environment_incident"
            or original_auth.get("further_api_calls_authorized") is not False):
        raise Stopped("original_incident_authorization_not_closed")
    return {"status": "passed", "plan_sha256": digest(plan),
            "authorization": auth["status"], "api_requests": 0}


def close_authorization(status, gateway):
    auth = json.loads(AUTH_PATH.read_text())
    auth.update(status=status, closed_usage=gateway.summary(),
                closed_at=datetime.now(timezone.utc).isoformat(),
                further_api_calls_authorized=False)
    write_json(AUTH_PATH, auth)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-approved", action="store_true")
    args = parser.parse_args()
    plan = json.loads(PLAN_PATH.read_text())
    print(json.dumps(preflight(plan, require_approval=args.execute_approved)))
    if not args.execute_approved:
        return
    gateway = FormalGateway(
        ROOT, plan,
        authorization_path=str(AUTH_PATH.relative_to(ROOT)),
    )
    with (gateway.directory / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stopped("controller_already_running") from None
        write_json(gateway.directory / "controller.json", {
            "pid": os.getpid(), "state": "running", "plan_sha256": digest(plan),
        })
        try:
            driver = Driver(plan, gateway)
            if not (gateway.directory / "stage1.completed").exists():
                driver.execute_batch("stage1")
            stage1 = write_report(
                plan, gateway.directory, ["stage1"],
                "v7_source_ledger_stage1_evaluation.json",
            )
            if not stage1["stage1_gate_passed"]:
                close_authorization("completed_stage1_gate_failed", gateway)
                write_json(gateway.directory / "controller.json", {
                    "pid": os.getpid(), "state": "completed_stage1_gate_failed",
                    "plan_sha256": digest(plan),
                })
                return
            if not (gateway.directory / "stage2.completed").exists():
                driver.execute_batch("stage2")
            final = write_report(
                plan, gateway.directory, ["stage1", "stage2"],
                "v7_source_ledger_pilot_evaluation.json",
            )
            close_authorization("completed", gateway)
            write_json(gateway.directory / "completed.json", {
                "plan_sha256": digest(plan), "usage": gateway.summary(),
                "development_gate_passed": final["final_development_gate_passed"],
            })
            write_json(gateway.directory / "controller.json", {
                "pid": os.getpid(), "state": "completed", "plan_sha256": digest(plan),
            })
        except BaseException as exc:
            write_json(gateway.directory / "interrupted.json", {
                "reason": str(exc) if isinstance(exc, Stopped) else type(exc).__name__,
                "usage": gateway.summary(), "automatic_resume": not gateway.halt_reason(),
            })
            write_json(gateway.directory / "controller.json", {
                "pid": os.getpid(),
                "state": "resumable_interruption" if not gateway.halt_reason() else "halted",
                "reason": str(exc), "plan_sha256": digest(plan),
            })
            raise


if __name__ == "__main__":
    main()
