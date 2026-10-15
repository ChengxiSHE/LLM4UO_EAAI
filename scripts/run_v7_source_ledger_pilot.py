"""Run the authorized, resumable v7 source-ledger development pilot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
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
from llm4or.source_ledger_runtime import VERSION, run_source_ledger_probe
from scripts.evaluate_v7_source_ledger_pilot import write_report

PLAN_PATH = ROOT / "experiments/v7_source_ledger_pilot_plan.json"
AUTH_PATH = ROOT / "experiments/v7_source_ledger_pilot_authorization.json"


def preflight(plan, require_approval=True):
    import shutil
    actual = {
        "python": platform.python_version(),
        "machine": platform.machine(),
        "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]},
    }
    if actual != plan["runtime"]:
        raise Stopped("runtime_version_changed")
    if plan["runtime_version"] != VERSION or plan["resilience"]["max_concurrent_requests"] != 5:
        raise Stopped("v7_pilot_runtime_changed")
    if shutil.disk_usage(ROOT).free < plan["limits"]["minimum_free_disk_bytes"]:
        raise Stopped("free_disk_below_guard")
    for path, expected in plan["frozen_files"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise Stopped("frozen_file_changed:" + path)
    registry = {row["id"]: row for row in load_public_registry(ROOT)}
    if any(pid not in registry or registry[pid]["input_sha256"] != value for pid, value in plan["public_inputs"].items()):
        raise Stopped("public_input_changed")
    if (plan["endpoint"], plan["model"], plan["credential_profile"]) != (BASE_URL, MODEL, str(PROFILE)):
        raise Stopped("formal_provider_changed")
    check_profile_metadata()
    auth = json.loads(AUTH_PATH.read_text())
    if auth["plan_sha256"] != digest(plan) or require_approval and auth["status"] != "approved":
        raise Stopped("v7_pilot_approval_required")
    return {"status": "passed", "plan_sha256": digest(plan), "authorization": auth["status"], "api_requests": 0}


class Driver:
    def __init__(self, plan, gateway):
        self.plan = plan
        self.gateway = gateway
        self.directory = gateway.directory
        self.public = {row["id"]: row for row in load_public_registry(ROOT)}

    def one(self, item):
        pid = item["problem_id"]
        replicate = self.plan["replicates"][0]
        scope = f"v7dev:LedgerProbe:{replicate}:{pid}"
        path = self.directory / "inference" / (digest(scope) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        binding = {
            "scope": scope,
            "input_sha256": self.public[pid]["input_sha256"],
            "source_record_sha256": item["source_record_sha256"],
            "runtime_version": VERSION,
        }
        self.gateway.work_started(scope)
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["binding"] != binding or saved["record_sha256"] != digest(saved["record"]):
                raise Stopped("v7_pilot_checkpoint_changed")
            record = saved["record"]
        else:
            source = json.loads(Path(item["source_record_path"]).read_text())
            if digest(source) != item["source_record_sha256"]:
                raise Stopped("v7_source_record_changed")
            record = run_source_ledger_probe(
                self.public[pid]["public"], source, self.gateway, scope, replicate,
                self.plan["token_cap"]
            )
            write_json(path, {"binding": binding, "record_sha256": digest(record), "record": record})
        status = "unavailable" if record.get("status") == "infrastructure_unavailable" else "complete"
        error = record.get("errors", [{}])[-1].get("reason") if record.get("errors") else None
        self.gateway.work_finished(scope, status, error)
        return {"problem_id": pid, "batch": item["batch"], "record_path": str(path), "record_sha256": digest(record)}

    def execute_batch(self, batch):
        items = [row for row in self.plan["selection"]["records"] if row["batch"] == batch]
        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="v7-ledger") as pool:
            cells = list(pool.map(self.one, items))
        write_json(self.directory / (batch + ".json"), {
            "plan_sha256": digest(self.plan), "batch": batch, "cells": cells,
            "usage": self.gateway.summary(), "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        (self.directory / (batch + ".completed")).write_text(digest(cells) + "\n")


def close_authorization(status, gateway):
    auth = json.loads(AUTH_PATH.read_text())
    auth.update(status=status, closed_usage=gateway.summary(), closed_at=datetime.now(timezone.utc).isoformat(),
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
    gateway = FormalGateway(ROOT, plan, authorization_path="experiments/v7_source_ledger_pilot_authorization.json")
    with (gateway.directory / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stopped("controller_already_running") from None
        write_json(gateway.directory / "controller.json", {"pid": os.getpid(), "state": "running", "plan_sha256": digest(plan)})
        try:
            driver = Driver(plan, gateway)
            if not (gateway.directory / "stage1.completed").exists():
                driver.execute_batch("stage1")
            stage1 = write_report(plan, gateway.directory, ["stage1"], "v7_source_ledger_stage1_evaluation.json")
            if not stage1["stage1_gate_passed"]:
                close_authorization("completed_stage1_gate_failed", gateway)
                write_json(gateway.directory / "controller.json", {"pid": os.getpid(), "state": "completed_stage1_gate_failed", "plan_sha256": digest(plan)})
                return
            if not (gateway.directory / "stage2.completed").exists():
                driver.execute_batch("stage2")
            final = write_report(plan, gateway.directory, ["stage1", "stage2"], "v7_source_ledger_pilot_evaluation.json")
            close_authorization("completed", gateway)
            write_json(gateway.directory / "completed.json", {"plan_sha256": digest(plan), "usage": gateway.summary(),
                       "development_gate_passed": final["final_development_gate_passed"]})
            write_json(gateway.directory / "controller.json", {"pid": os.getpid(), "state": "completed", "plan_sha256": digest(plan)})
        except BaseException as exc:
            write_json(gateway.directory / "interrupted.json", {"reason": str(exc) if isinstance(exc, Stopped) else type(exc).__name__,
                       "usage": gateway.summary(), "automatic_resume": not gateway.halt_reason()})
            write_json(gateway.directory / "controller.json", {"pid": os.getpid(), "state": "resumable_interruption" if not gateway.halt_reason() else "halted",
                       "reason": str(exc), "plan_sha256": digest(plan)})
            raise


if __name__ == "__main__":
    main()
