"""Run the frozen Base/V6 Text2Opt external confirmation."""
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

from llm4or.benchmark_inputs import payload_sha256
from llm4or.formal_gateway import FormalGateway
from llm4or.formal_provider import BASE_URL, MODEL, PROFILE, check_profile_metadata
from llm4or.gateway import Stopped
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.text2opt_v6_runtime import VERSION, run_text2opt_v6_probe
from scripts.evaluate_text2opt_v6_confirmation import evaluate

PLAN_PATH = ROOT / "experiments/text2opt_v6_confirmation_run_plan.json"
AUTH_PATH = ROOT / "experiments/text2opt_v6_confirmation_run_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def public_index(plan):
    index = {}
    for name, expected in plan["prepared_snapshots"].items():
        path = ROOT / name
        if sha(path) != expected:
            raise Stopped("text2opt_public_snapshot_changed")
        value = json.loads(path.read_text())
        for row in value.get("confirmation", []):
            index[row["id"]] = row["public"]
    if set(index) != set(plan["public_inputs"]) or any(
        value != payload_sha256(index[problem_id])
        for problem_id, value in plan["public_inputs"].items()
    ):
        raise Stopped("text2opt_public_inputs_changed")
    return index


def preflight(plan, require_approval=True):
    import shutil
    actual = {
        "python": platform.python_version(), "machine": platform.machine(),
        "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]},
    }
    if actual != plan["runtime"] or plan["runtime_version"] != VERSION:
        raise Stopped("text2opt_v6_runtime_changed")
    if plan["resilience"]["max_concurrent_requests"] != 5:
        raise Stopped("text2opt_concurrency_changed")
    if shutil.disk_usage(ROOT).free < plan["limits"]["minimum_free_disk_bytes"]:
        raise Stopped("free_disk_below_guard")
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    public_index(plan)
    if (plan["endpoint"], plan["model"], plan["credential_profile"]) != (BASE_URL, MODEL, str(PROFILE)):
        raise Stopped("formal_provider_changed")
    check_profile_metadata()
    auth = json.loads(AUTH_PATH.read_text())
    if auth["plan_sha256"] != digest(plan) or require_approval and auth["status"] != "approved":
        raise Stopped("text2opt_v6_confirmation_approval_required")
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
        scope = f"text2optv6:Probe:{replicate}:{problem_id}"
        path = self.directory / "inference" / (digest(scope) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        binding = {
            "scope": scope, "input_sha256": item["input_sha256"],
            "runtime_version": VERSION,
        }
        self.gateway.work_started(scope)
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["binding"] != binding or saved["record_sha256"] != digest(saved["record"]):
                raise Stopped("text2opt_v6_checkpoint_changed")
            record = saved["record"]
        else:
            record = run_text2opt_v6_probe(
                self.public[problem_id], self.gateway, scope, replicate, self.plan["token_cap"]
            )
            write_json(path, {"binding": binding, "record_sha256": digest(record), "record": record})
        status = "unavailable" if record["status"] == "infrastructure_unavailable" else "complete"
        error = record.get("errors", [{}])[-1].get("reason") if record.get("errors") else None
        self.gateway.work_finished(scope, status, error)
        return {"problem_id": problem_id, "record_path": str(path), "record_sha256": digest(record)}

    def execute(self):
        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="text2opt-v6") as pool:
            cells = list(pool.map(self.one, self.plan["selection"]["records"]))
        complete = {
            "plan_sha256": digest(self.plan), "cells": cells,
            "usage": self.gateway.summary(), "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(self.directory / "inference_complete.json", complete)
        return complete


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
    gateway = FormalGateway(ROOT, plan, authorization_path=str(AUTH_PATH.relative_to(ROOT)))
    with (gateway.directory / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stopped("controller_already_running") from None
        write_json(gateway.directory / "controller.json", {
            "pid": os.getpid(), "state": "running", "plan_sha256": digest(plan),
        })
        try:
            Driver(plan, gateway).execute()
            report = evaluate(plan, gateway.directory)
            close_authorization("completed", gateway)
            write_json(gateway.directory / "completed.json", {
                "plan_sha256": digest(plan), "usage": gateway.summary(),
                "confirmed": report["confirmation_gate"]["confirmed"],
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
