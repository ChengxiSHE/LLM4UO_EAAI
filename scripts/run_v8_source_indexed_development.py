"""Run the frozen two-stage V8 source-indexed development experiment."""
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
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_inputs import payload_sha256
from llm4or.codex_cli_gateway import (
    CodexCliGateway, VERSION as GATEWAY_VERSION, validate_codex_cli_interface,
)
from llm4or.gateway import Stopped
from llm4or.pipeline import write_json
from llm4or.run_interruption import RunInterrupted
from llm4or.schema import digest
from llm4or.source_indexed_evaluation import (
    evaluate_source_indexed_development, final_development_gate, stage1_gate,
)
from llm4or.source_indexed_runtime import VERSION, run_source_indexed_probe


DEFAULT_PLAN_PATH = ROOT / "experiments/v8_source_indexed_development_plan.json"
DEFAULT_AUTH_PATH = ROOT / "experiments/v8_source_indexed_development_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def public_index(plan):
    path = ROOT / plan["prepared_split"]
    if sha(path) != plan["prepared_split_sha256"]:
        raise Stopped("v8_prepared_split_changed")
    value = json.loads(path.read_text())
    index = {row["id"]: row["public"] for row in value["development"]}
    if set(index) != set(plan["public_inputs"]) or any(
        payload_sha256(index[problem_id]) != expected
        for problem_id, expected in plan["public_inputs"].items()
    ):
        raise Stopped("v8_public_inputs_changed")
    return index


def preflight(plan, auth_path, require_approval=True):
    actual_runtime = {
        "python": platform.python_version(), "machine": platform.machine(),
        "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]},
    }
    if actual_runtime != plan["runtime"]:
        raise Stopped("v8_runtime_changed")
    if plan["runtime_version"] != VERSION or plan["gateway_version"] != GATEWAY_VERSION:
        raise Stopped("v8_code_version_changed")
    if plan["resilience"]["max_concurrent_requests"] != 5:
        raise Stopped("v8_concurrency_changed")
    version = subprocess.run(
        [plan["codex_cli"], "--version"], capture_output=True, text=True, timeout=15, check=True,
    ).stdout.strip()
    if version != plan["codex_cli_version"]:
        raise Stopped("codex_cli_version_changed")
    validate_codex_cli_interface(plan, ROOT)
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    public_index(plan)
    auth = json.loads(auth_path.read_text())
    if auth["plan_sha256"] != digest(plan) or require_approval and auth["status"] != "approved":
        raise Stopped("v8_source_indexed_approval_required")
    return {"status": "passed", "plan_sha256": digest(plan),
            "authorization": auth["status"], "api_requests": 0}


class Driver:
    def __init__(self, plan, gateway):
        self.plan = plan
        self.gateway = gateway
        self.directory = gateway.directory
        self.public = public_index(plan)

    def one(self, item):
        problem_id = item["problem_id"]
        replicate = self.plan["replicates"][0]
        scope = f"v8dev:IndexedProbe:{replicate}:{problem_id}"
        path = self.directory / "inference" / (digest(scope) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        binding = {"scope": scope, "input_sha256": item["input_sha256"], "runtime_version": VERSION}
        self.gateway.work_started(scope)
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["binding"] != binding or saved["record_sha256"] != digest(saved["record"]):
                raise Stopped("v8_checkpoint_changed")
            record = saved["record"]
        else:
            record = run_source_indexed_probe(
                self.public[problem_id], self.gateway, scope, replicate, self.plan["token_cap"]
            )
            write_json(path, {"binding": binding, "record_sha256": digest(record), "record": record})
        status = "unavailable" if record["status"] == "infrastructure_unavailable" else "complete"
        error = record.get("errors", [{}])[-1].get("reason") if record.get("errors") else None
        self.gateway.work_finished(scope, status, error)
        return {
            "problem_id": problem_id, "category": item["category"], "batch": item["batch"],
            "record_path": str(path), "record_sha256": digest(record), "probe": record,
        }

    def run_batch(self, batch):
        records = [row for row in self.plan["selection"]["records"] if row["batch"] == batch]
        completed = []
        if batch == "stage1":
            canary_count = self.plan.get("stage1_serial_canary_records", 0)
            if canary_count not in (0, 1):
                raise Stopped("v8_invalid_canary_count")
            if canary_count:
                completed.append(self.one(records[0]))
                records = records[1:]
        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="v8-indexed") as pool:
            return completed + list(pool.map(self.one, records))


def references(plan):
    path = ROOT / plan["development_evaluator"]
    if sha(path) != plan["development_evaluator_sha256"]:
        raise Stopped("v8_development_evaluator_changed")
    value = json.loads(path.read_text())
    expected = {row["problem_id"] for row in plan["selection"]["records"]}
    if set(value["references"]) != expected:
        raise Stopped("v8_development_reference_set_changed")
    return value["references"]


def evaluate(entries, plan, directory, stage):
    public, private = evaluate_source_indexed_development(entries, references(plan))
    public["stage"] = stage
    public["gate"] = stage1_gate(public) if stage == "stage1" else final_development_gate(public)
    write_json(directory / f"v8_{stage}_evaluation.json", public)
    write_json(directory / f"v8_{stage}_evaluation_private.json", private)
    return public


def close_authorization(status, gateway, auth_path):
    auth = json.loads(auth_path.read_text())
    auth.update(status=status, closed_usage=gateway.summary(),
                closed_at=datetime.now(timezone.utc).isoformat(), further_api_calls_authorized=False)
    write_json(auth_path, auth)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-approved", action="store_true")
    parser.add_argument("--plan-path", default=str(DEFAULT_PLAN_PATH.relative_to(ROOT)))
    parser.add_argument("--authorization-path", default=str(DEFAULT_AUTH_PATH.relative_to(ROOT)))
    args = parser.parse_args()
    plan_path = (ROOT / args.plan_path).resolve()
    auth_path = (ROOT / args.authorization_path).resolve()
    if ROOT not in plan_path.parents or ROOT not in auth_path.parents:
        raise Stopped("v8_control_path_outside_repository")
    plan = json.loads(plan_path.read_text())
    print(json.dumps(preflight(plan, auth_path, require_approval=args.execute_approved)))
    if not args.execute_approved:
        return
    gateway = CodexCliGateway(ROOT, plan, str(auth_path.relative_to(ROOT)))
    directory = gateway.directory
    with (directory / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stopped("controller_already_running") from None
        write_json(directory / "controller.json", {
            "pid": os.getpid(), "state": "running_stage1", "plan_sha256": digest(plan),
        })
        try:
            driver = Driver(plan, gateway)
            stage1 = driver.run_batch("stage1")
            write_json(directory / "stage1_inference_complete.json", {
                "plan_sha256": digest(plan), "cells": [{k: v for k, v in row.items() if k != "probe"} for row in stage1],
                "usage": gateway.summary(),
            })
            report1 = evaluate(stage1, plan, directory, "stage1")
            if not report1["gate"]["passed"]:
                close_authorization("completed_stage1_gate_failed", gateway, auth_path)
                write_json(directory / "completed.json", {
                    "plan_sha256": digest(plan), "state": "completed_stage1_gate_failed",
                    "usage": gateway.summary(), "stage1_gate": report1["gate"],
                })
                write_json(directory / "controller.json", {
                    "pid": os.getpid(), "state": "completed_stage1_gate_failed", "plan_sha256": digest(plan),
                })
                return
            write_json(directory / "controller.json", {
                "pid": os.getpid(), "state": "running_stage2", "plan_sha256": digest(plan),
            })
            stage2 = driver.run_batch("stage2")
            all_entries = stage1 + stage2
            write_json(directory / "inference_complete.json", {
                "plan_sha256": digest(plan), "cells": [{k: v for k, v in row.items() if k != "probe"} for row in all_entries],
                "usage": gateway.summary(), "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            final = evaluate(all_entries, plan, directory, "final")
            status = "completed_development_gate_passed" if final["gate"]["passed"] else "completed_development_gate_failed"
            close_authorization(status, gateway, auth_path)
            write_json(directory / "completed.json", {
                "plan_sha256": digest(plan), "state": status, "usage": gateway.summary(),
                "development_gate": final["gate"],
            })
            write_json(directory / "controller.json", {
                "pid": os.getpid(), "state": status, "plan_sha256": digest(plan),
            })
        except BaseException as exc:
            write_json(directory / "interrupted.json", {
                "reason": str(exc) if isinstance(exc, (Stopped, RunInterrupted)) else type(exc).__name__,
                "usage": gateway.summary(), "automatic_resume": not gateway.halt_reason(),
            })
            write_json(directory / "controller.json", {
                "pid": os.getpid(), "state": "resumable_interruption" if not gateway.halt_reason() else "halted",
                "reason": str(exc), "plan_sha256": digest(plan),
            })
            raise


if __name__ == "__main__":
    main()
