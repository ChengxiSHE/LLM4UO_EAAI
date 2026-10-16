"""Run the frozen Base/V9 independent Text2Opt confirmation."""
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
from llm4or.codex_cli_gateway import CodexCliGateway, VERSION as GATEWAY_VERSION, validate_codex_cli_interface
from llm4or.gateway import Stopped
from llm4or.pipeline import write_json
from llm4or.run_interruption import RunInterrupted
from llm4or.schema import digest
from llm4or.text2opt_v9_runtime import VERSION, run_text2opt_v9_probe
from scripts.evaluate_text2opt_v9_confirmation import evaluate

PLAN_PATH = ROOT / "experiments/text2opt_v9_confirmation_plan.json"
AUTH_PATH = ROOT / "experiments/text2opt_v9_confirmation_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def public_index(plan):
    path = ROOT / plan["prepared_split"]
    if sha(path) != plan["prepared_split_sha256"]:
        raise Stopped("v9_prepared_split_changed")
    value = json.loads(path.read_text()); index = {row["id"]: row["public"] for row in value["confirmation"]}
    if set(index) != set(plan["public_inputs"]) or any(
            payload_sha256(index[problem_id]) != expected for problem_id, expected in plan["public_inputs"].items()):
        raise Stopped("v9_public_inputs_changed")
    return index


def preflight(plan, auth_path=AUTH_PATH, require_approval=True):
    import shutil
    actual = {"python": platform.python_version(), "machine": platform.machine(),
              "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]}}
    if actual != plan["runtime"] or plan["runtime_version"] != VERSION or plan["gateway_version"] != GATEWAY_VERSION:
        raise Stopped("v9_runtime_changed")
    if plan["resilience"]["max_concurrent_requests"] != 5:
        raise Stopped("v9_concurrency_changed")
    version = subprocess.run([plan["codex_cli"], "--version"], capture_output=True, text=True,
                             timeout=15, check=True).stdout.strip()
    if version != plan["codex_cli_version"]:
        raise Stopped("v9_codex_cli_version_changed")
    validate_codex_cli_interface(plan, ROOT)
    if shutil.disk_usage(ROOT).free < plan["limits"]["minimum_free_disk_bytes"]:
        raise Stopped("v9_free_disk_guard")
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    public_index(plan)
    auth = json.loads(auth_path.read_text())
    if auth["plan_sha256"] != digest(plan) or require_approval and auth["status"] != "approved":
        raise Stopped("v9_confirmation_approval_required")
    return {"status": "passed", "plan_sha256": digest(plan), "authorization": auth["status"],
            "api_requests": 0}


class Driver:
    def __init__(self, plan, gateway):
        self.plan = plan; self.gateway = gateway; self.directory = gateway.directory
        self.public = public_index(plan)
        self.checkpoint_import = plan.get("checkpoint_import", {}).get("records", {})

    def one(self, item):
        problem_id = item["problem_id"]; replicate = self.plan["replicates"][0]
        scope = f"v9confirm:BaseV9:{replicate}:{problem_id}"
        path = self.directory / "inference" / (digest(scope) + ".json"); path.parent.mkdir(parents=True, exist_ok=True)
        binding = {"scope": scope, "input_sha256": item["input_sha256"], "runtime_version": VERSION}
        self.gateway.work_started(scope)
        imported = self.checkpoint_import.get(problem_id)
        if not path.exists() and imported:
            source = (ROOT / imported["record_path"]).resolve()
            if ROOT not in source.parents or sha(source) != imported["file_sha256"]:
                raise Stopped("v9_checkpoint_import_changed")
            saved = json.loads(source.read_text())
            if saved["binding"] != binding or saved["record_sha256"] != digest(saved["record"]):
                raise Stopped("v9_checkpoint_import_binding")
            write_json(path, saved)
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["binding"] != binding or saved["record_sha256"] != digest(saved["record"]):
                raise Stopped("v9_checkpoint_changed")
            record = saved["record"]
        else:
            record = run_text2opt_v9_probe(
                self.public[problem_id], self.gateway, scope, replicate, self.plan["token_cap"]
            )
            write_json(path, {"binding": binding, "record_sha256": digest(record), "record": record})
        status = "unavailable" if record["status"] == "infrastructure_unavailable" else "complete"
        error = record.get("errors", [{}])[-1].get("reason") if record.get("errors") else None
        self.gateway.work_finished(scope, status, error)
        return {"problem_id": problem_id, "category": item["category"],
                "record_path": str(path), "record_sha256": digest(record)}

    def execute(self):
        records = self.plan["selection"]["records"]; cells = []
        canary = self.plan.get("serial_canary_records", 0)
        if canary:
            cells.append(self.one(records[0])); records = records[1:]
        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="v9-confirm") as pool:
            cells.extend(pool.map(self.one, records))
        complete = {"plan_sha256": digest(self.plan), "cells": cells,
                    "usage": self.gateway.summary(), "completed_at": datetime.now(timezone.utc).isoformat()}
        write_json(self.directory / "inference_complete.json", complete)
        return complete


def close_authorization(status, gateway, auth_path):
    auth = json.loads(auth_path.read_text())
    auth.update(status=status, closed_usage=gateway.summary(), closed_at=datetime.now(timezone.utc).isoformat(),
                further_api_calls_authorized=False)
    write_json(auth_path, auth)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--execute-approved", action="store_true")
    parser.add_argument("--plan-path", default=str(PLAN_PATH.relative_to(ROOT)))
    parser.add_argument("--authorization-path", default=str(AUTH_PATH.relative_to(ROOT))); args = parser.parse_args()
    plan_path = (ROOT / args.plan_path).resolve(); auth_path = (ROOT / args.authorization_path).resolve()
    if ROOT not in plan_path.parents or ROOT not in auth_path.parents:
        raise Stopped("v9_control_path_outside_repository")
    plan = json.loads(plan_path.read_text()); print(json.dumps(preflight(plan, auth_path, require_approval=args.execute_approved)))
    if not args.execute_approved:
        return
    gateway = CodexCliGateway(ROOT, plan, str(auth_path.relative_to(ROOT))); directory = gateway.directory
    with (directory / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stopped("controller_already_running") from None
        write_json(directory / "controller.json", {"pid": os.getpid(), "state": "running",
                                                     "plan_sha256": digest(plan)})
        try:
            Driver(plan, gateway).execute(); report = evaluate(plan, directory)
            status = "completed_confirmation_passed" if report["confirmation_gate"]["confirmed"] else "completed_confirmation_failed"
            close_authorization(status, gateway, auth_path)
            write_json(directory / "completed.json", {"plan_sha256": digest(plan), "state": status,
                                                        "usage": gateway.summary(),
                                                        "confirmation_gate": report["confirmation_gate"]})
            write_json(directory / "controller.json", {"pid": os.getpid(), "state": status,
                                                         "plan_sha256": digest(plan)})
        except BaseException as exc:
            write_json(directory / "interrupted.json", {
                "reason": str(exc) if isinstance(exc, (Stopped, RunInterrupted)) else type(exc).__name__,
                "usage": gateway.summary(), "automatic_resume": not gateway.halt_reason(),
            })
            write_json(directory / "controller.json", {"pid": os.getpid(),
                "state": "resumable_interruption" if not gateway.halt_reason() else "halted",
                "reason": str(exc), "plan_sha256": digest(plan)})
            raise


if __name__ == "__main__":
    main()
