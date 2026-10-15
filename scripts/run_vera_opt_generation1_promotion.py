#!/usr/bin/env python3
"""Run the frozen Base/VERA-Opt generation-one promotion matrix."""

from __future__ import annotations

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
from llm4or.declarative_selection_compiler import VERSION as COMPILER_VERSION
from llm4or.gateway import Stopped
from llm4or.pipeline import write_json
from llm4or.run_interruption import RunInterrupted
from llm4or.schema import digest
from llm4or.vera_opt_promotion_evaluation import VERSION as EVALUATION_VERSION
from llm4or.vera_opt_promotion_runtime import VERSION, run_promotion_probe
from llm4or.verified_skill_library import validate_skill_package
from scripts.evaluate_vera_opt_generation1_promotion import evaluate


PLAN_PATH = ROOT / "experiments/vera_opt_generation1_promotion_plan.json"
AUTH_PATH = ROOT / "experiments/vera_opt_generation1_promotion_authorization.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_index(plan: dict) -> dict[str, dict]:
    path = ROOT / plan["public_projection"]
    if sha(path) != plan["public_projection_sha256"]:
        raise Stopped("promotion_public_projection_changed")
    value = json.loads(path.read_text())
    index = {row["problem_id"]: row["public"] for row in value["records"]}
    if set(index) != set(plan["public_inputs"]) or any(
        payload_sha256(index[problem_id]) != expected
        for problem_id, expected in plan["public_inputs"].items()
    ):
        raise Stopped("promotion_public_inputs_changed")
    return index


def candidate_skill(plan: dict) -> dict:
    path = ROOT / plan["candidate_file"]
    if sha(path) != plan["candidate_sha256"]:
        raise Stopped("promotion_candidate_changed")
    value = json.loads(path.read_text()); skill = validate_skill_package(value["skill"], {
        plan["trusted_implementation"]["id"]: plan["trusted_implementation"]["sha256"],
    })
    if digest(skill) != plan["skill_sha256"]:
        raise Stopped("promotion_skill_changed")
    return skill


def preflight(plan: dict, execute_run: bool) -> dict:
    import shutil
    if plan["gateway_version"] != GATEWAY_VERSION or plan["runtime_version"] != VERSION \
            or plan["evaluation_version"] != EVALUATION_VERSION \
            or plan["compiler_version"] != COMPILER_VERSION:
        raise Stopped("promotion_runtime_changed")
    if plan["resilience"]["max_concurrent_requests"] != 5:
        raise Stopped("promotion_concurrency_changed")
    actual = {"python": platform.python_version(), "machine": platform.machine(),
              "packages": {name: importlib.metadata.version(name)
                           for name in plan["runtime"]["packages"]}}
    if actual != plan["runtime"]:
        raise Stopped("promotion_environment_changed")
    if subprocess.run([plan["codex_cli"], "--version"], capture_output=True, text=True,
                      check=True, timeout=15).stdout.strip() != plan["codex_cli_version"]:
        raise Stopped("promotion_cli_changed")
    validate_codex_cli_interface(plan, ROOT)
    if shutil.disk_usage(ROOT).free < plan["limits"]["minimum_free_disk_bytes"]:
        raise Stopped("promotion_disk_guard")
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    public_index(plan); candidate_skill(plan)
    auth = json.loads(AUTH_PATH.read_text())
    if auth["plan_sha256"] != digest(plan) or execute_run and auth["status"] != "approved":
        raise Stopped("promotion_authorization_required")
    return {"status": "passed", "plan_sha256": digest(plan),
            "authorization": auth["status"], "api_requests": 0}


class Driver:
    def __init__(self, plan: dict, gateway: CodexCliGateway):
        self.plan = plan; self.gateway = gateway; self.directory = gateway.directory
        self.public = public_index(plan); self.skill = candidate_skill(plan)

    def one(self, item: dict) -> dict:
        problem_id = item["problem_id"]; replicate = self.plan["replicates"][0]
        scope = f"verag1promotion:BaseVERA:{replicate}:{problem_id}"
        path = self.directory / "inference" / (digest(scope) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        binding = {"scope": scope, "input_sha256": item["input_sha256"],
                   "runtime_version": VERSION, "skill_sha256": self.plan["skill_sha256"]}
        self.gateway.work_started(scope)
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["binding"] != binding or saved["record_sha256"] != digest(saved["record"]):
                raise Stopped("promotion_checkpoint_changed")
            record = saved["record"]
        else:
            record = run_promotion_probe(
                self.public[problem_id], self.gateway, scope, replicate,
                self.plan["token_cap"], skill=self.skill,
                implementation_sha256=self.plan["trusted_implementation"]["sha256"],
            )
            write_json(path, {"binding": binding, "record_sha256": digest(record),
                              "record": record})
        status = "unavailable" if record["status"] == "infrastructure_unavailable" else "complete"
        error = record.get("errors", [{}])[-1].get("reason") if record.get("errors") else None
        self.gateway.work_finished(scope, status, error)
        return {"problem_id": problem_id, "category": item["category"],
                "record_path": str(path), "record_sha256": digest(record)}

    def execute(self) -> dict:
        records = list(self.plan["selection"]["records"]); cells = []
        canary = self.plan.get("serial_canary_records", 0)
        if canary:
            cells.append(self.one(records[0])); records = records[1:]
        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="vera-promotion") as pool:
            cells.extend(pool.map(self.one, records))
        complete = {"plan_sha256": digest(self.plan), "cells": cells,
                    "usage": self.gateway.summary(),
                    "completed_at": datetime.now(timezone.utc).isoformat()}
        write_json(self.directory / "inference_complete.json", complete)
        return complete


def close_authorization(status: str, gateway: CodexCliGateway) -> None:
    auth = json.loads(AUTH_PATH.read_text())
    auth.update(status=status, closed_usage=gateway.summary(),
                closed_at=datetime.now(timezone.utc).isoformat(),
                further_api_calls_authorized=False)
    write_json(AUTH_PATH, auth)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--execute-approved", action="store_true")
    args = parser.parse_args(); plan = json.loads(PLAN_PATH.read_text())
    print(json.dumps(preflight(plan, args.execute_approved), sort_keys=True))
    if not args.execute_approved:
        return
    gateway = CodexCliGateway(ROOT, plan, str(AUTH_PATH.relative_to(ROOT)))
    directory = gateway.directory
    with (directory / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stopped("controller_already_running") from None
        write_json(directory / "controller.json", {"pid": os.getpid(), "state": "running",
                                                     "plan_sha256": digest(plan)})
        try:
            Driver(plan, gateway).execute(); report = evaluate(plan, directory)
            status = "completed_promotion_passed" \
                if report["promotion_gate"]["promoted"] else "completed_promotion_failed"
            close_authorization(status, gateway)
            write_json(directory / "completed.json", {
                "plan_sha256": digest(plan), "state": status, "usage": gateway.summary(),
                "promotion_gate": report["promotion_gate"],
            })
            write_json(directory / "controller.json", {"pid": os.getpid(), "state": status,
                                                         "plan_sha256": digest(plan)})
        except BaseException as exc:
            write_json(directory / "interrupted.json", {
                "reason": str(exc) if isinstance(exc, (Stopped, RunInterrupted)) else type(exc).__name__,
                "usage": gateway.summary(), "automatic_resume": not gateway.halt_reason(),
            })
            write_json(directory / "controller.json", {
                "pid": os.getpid(),
                "state": "resumable_interruption" if not gateway.halt_reason() else "halted",
                "reason": str(exc), "plan_sha256": digest(plan),
            })
            raise


if __name__ == "__main__":
    main()
