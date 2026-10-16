#!/usr/bin/env python3
"""Run and aggregate the frozen six-family BIND development pilot."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
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
from llm4or.bind_official_adapter import BindPromptSource
from llm4or.bind_runtime import (
    VERSION, bind_reference_projection, run_bind_instance_data,
)
from llm4or.codex_cli_gateway import (
    CodexCliGateway, LocalRequestFailure, VERSION as GATEWAY_VERSION,
    validate_codex_cli_interface,
)
from llm4or.formal_gateway import RequestUnavailable
from llm4or.gateway import Stopped
from llm4or.gurobi_cli_solver import VERSION as GUROBI_SOLVER_VERSION, execute as gurobi_execute
from llm4or.pipeline import write_json
from llm4or.run_interruption import RunInterrupted
from llm4or.schema import digest


PLAN_PATH = ROOT / "experiments/text2opt_bind_development_pilot_plan.json"
AUTH_PATH = ROOT / "experiments/text2opt_bind_development_pilot_authorization.json"
PUBLIC_REPORT = ROOT / "results/text2opt_bind_development_pilot_evaluation.json"
UPSTREAM = ROOT / "data/raw/text2opt_bench_20261003"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_prepared(plan):
    path = ROOT / plan["prepared_data"]
    if sha(path) != plan["prepared_data_sha256"]:
        raise Stopped("bind_prepared_data_changed")
    value = json.loads(path.read_text())
    index = {row["problem_id"]: row for row in value["records"]}
    if set(index) != set(plan["public_inputs"]):
        raise Stopped("bind_prepared_selection_changed")
    for problem_id, expected in plan["public_inputs"].items():
        if payload_sha256(index[problem_id]["public"]) != expected:
            raise Stopped("bind_public_input_changed:" + problem_id)
    return index


def preflight(plan, auth_path, execute):
    import shutil
    actual = {
        "python": platform.python_version(), "machine": platform.machine(),
        "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]},
    }
    if actual != plan["runtime"] or plan["runtime_version"] != VERSION or plan["gateway_version"] != GATEWAY_VERSION:
        raise Stopped("bind_runtime_changed")
    if plan["resilience"]["max_concurrent_requests"] != 1:
        raise Stopped("bind_pilot_concurrency_changed")
    version = subprocess.run(
        [plan["codex_cli"], "--version"], capture_output=True, text=True, timeout=15, check=True,
    ).stdout.strip()
    if version != plan["codex_cli_version"]:
        raise Stopped("bind_codex_cli_version_changed")
    validate_codex_cli_interface(plan, ROOT)
    if shutil.disk_usage(ROOT).free < plan["limits"]["minimum_free_disk_bytes"]:
        raise Stopped("bind_free_disk_guard")
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    BindPromptSource.load(UPSTREAM)
    solver = plan.get("solver_backend", {"name": "highs"})
    if solver["name"] == "gurobi_cli":
        actual_solver_version = subprocess.run(
            [solver["binary"], "--version"], capture_output=True, text=True, timeout=15, check=True,
        ).stdout.splitlines()[0].strip()
        if solver["adapter_version"] != GUROBI_SOLVER_VERSION or actual_solver_version != solver["version"]:
            raise Stopped("bind_gurobi_solver_changed")
    elif solver["name"] != "highs":
        raise Stopped("bind_unknown_solver_backend")
    load_prepared(plan)
    authorization = json.loads(auth_path.read_text())
    if authorization["plan_sha256"] != digest(plan) or execute and authorization["status"] != "approved":
        raise Stopped("bind_development_authorization_required")
    return {"status": "passed", "plan_sha256": digest(plan),
            "authorization": authorization["status"], "api_requests": 0}


class Driver:
    def __init__(self, plan, gateway):
        self.plan = plan
        self.gateway = gateway
        self.directory = gateway.directory
        self.index = load_prepared(plan)
        self.prompts = BindPromptSource.load(UPSTREAM)
        self.solver = gurobi_execute if plan.get("solver_backend", {}).get("name") == "gurobi_cli" else None

    def one(self, item):
        problem_id = item["problem_id"]
        row = self.index[problem_id]
        replicate = self.plan["replicates"][0]
        scope = f"binddev:BIND:{replicate}:{problem_id}"
        path = self.directory / "inference" / (digest(scope) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.gateway.work_started(scope)

        def reference_loader():
            source = ROOT / row["source_file"]
            if sha(source) != row["source_file_sha256"]:
                raise Stopped("bind_source_record_changed:" + problem_id)
            return bind_reference_projection(json.loads(source.read_text()))

        try:
            record = run_bind_instance_data(
                row["public"], row["bind_public"], self.gateway, scope, replicate,
                self.plan["token_cap"], self.prompts, reference_loader,
                max_rounds=self.plan["upstream"]["maximum_rounds"], checkpoint_path=path,
                **({"solver": self.solver} if self.solver is not None else {}),
            )
            self.gateway.work_finished(scope, "complete")
            return {"problem_id": problem_id, "category": item["category"],
                    "record_path": str(path.relative_to(ROOT)), "record_sha256": digest(record),
                    "status": record["status"]}
        except RequestUnavailable as exc:
            self.gateway.work_finished(scope, "unavailable", str(exc))
            return {"problem_id": problem_id, "category": item["category"],
                    "record_path": None, "record_sha256": None,
                    "status": "infrastructure_unavailable", "reason": str(exc)}
        except RunInterrupted:
            raise
        except LocalRequestFailure as exc:
            reason = str(exc)
            self.gateway.work_finished(scope, "method_failure", reason)
            return {"problem_id": problem_id, "category": item["category"],
                    "record_path": None, "record_sha256": None,
                    "status": "method_failure", "reason": reason}
        except Stopped as exc:
            # A local response/translation failure is a method outcome for this
            # record.  It must remain in the denominator and must not abort
            # independent records in the matrix.
            reason = str(exc)
            if reason not in {"invalid_json_response"}:
                raise
            self.gateway.work_finished(scope, "method_failure", reason)
            return {"problem_id": problem_id, "category": item["category"],
                    "record_path": None, "record_sha256": None,
                    "status": "method_failure", "reason": reason}

    def execute(self):
        cells = [self.one(item) for item in self.plan["selection"]["records"]]
        complete = {
            "plan_sha256": digest(self.plan), "cells": cells,
            "usage": self.gateway.summary(), "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(self.directory / "inference_complete.json", complete)
        return complete


def evaluate(plan, directory, complete):
    rounds = Counter()
    reasons = Counter()
    by_family = defaultdict(lambda: {"records": 0, "round1_correct": 0, "final_correct": 0})
    evaluated = 0
    round1_correct = 0
    final_correct = 0
    unavailable = 0
    for cell in complete["cells"]:
        family = cell["category"]
        by_family[family]["records"] += 1
        if cell["status"] == "infrastructure_unavailable":
            unavailable += 1
            reasons[cell.get("reason", "request_unavailable")] += 1
            continue
        if cell["status"] == "method_failure":
            evaluated += 1
            reasons[cell.get("reason", "method_failure")] += 1
            continue
        record = json.loads((ROOT / cell["record_path"]).read_text())
        if digest(record) != cell["record_sha256"]:
            raise Stopped("bind_result_integrity:" + cell["problem_id"])
        evaluated += 1
        first = record["rounds"][0]["objective_matches"] and record["rounds"][0]["status_matches"]
        success = bool(record["success"])
        round1_correct += int(first)
        final_correct += int(success)
        by_family[family]["round1_correct"] += int(first)
        by_family[family]["final_correct"] += int(success)
        rounds[record["rounds_used"]] += 1
        if not success:
            last = record["rounds"][-1]
            reasons[last.get("translation_reason") or last.get("solver_status") or "objective_mismatch"] += 1
    report = {
        "schema": "text2opt-bind-development-pilot-evaluation-v1",
        "role": "development_only_outcomes_previously_exposed_no_confirmation_claim",
        "plan_sha256": digest(plan), "planned_records": len(complete["cells"]),
        "evaluated_records": evaluated, "infrastructure_unavailable": unavailable,
        "round1_correct": round1_correct,
        "round1_accuracy": round1_correct / evaluated if evaluated else None,
        "final_correct": final_correct,
        "final_accuracy": final_correct / evaluated if evaluated else None,
        "oracle_repair_corrections": final_correct - round1_correct,
        "rounds_used": {str(key): value for key, value in sorted(rounds.items())},
        "by_family": {key: value for key, value in sorted(by_family.items())},
        "failure_reasons": dict(sorted(reasons.items())),
        "method_label": "official-prompt BIND common-backbone compatibility adapter",
        "deviations": [
            "Codex CLI stateless transport flattens the official message transcript",
            "generated Python is translated by a whitelist interpreter and never executed",
            (
                "trusted Gurobi CLI consumes controller-written LP instead of importing generated Python"
                if plan.get("solver_backend", {}).get("name") == "gurobi_cli"
                else "trusted HiGHS replaces Gurobi after translation"
            ),
        ],
        "claim_guard": "development adapter evidence only; not an independent external-baseline comparison",
        "usage": complete["usage"],
    }
    write_json(directory / "evaluation.json", report)
    public_report = ROOT / plan.get("public_report", str(PUBLIC_REPORT.relative_to(ROOT)))
    write_json(public_report, report)
    return report


def close_authorization(status, gateway, auth_path):
    authorization = json.loads(auth_path.read_text())
    authorization.update(
        status=status, closed_usage=gateway.summary(),
        closed_at=datetime.now(timezone.utc).isoformat(), further_api_calls_authorized=False,
    )
    write_json(auth_path, authorization)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-approved", action="store_true")
    parser.add_argument("--plan-path", default=str(PLAN_PATH.relative_to(ROOT)))
    parser.add_argument("--authorization-path", default=str(AUTH_PATH.relative_to(ROOT)))
    args = parser.parse_args()
    plan_path = (ROOT / args.plan_path).resolve()
    auth_path = (ROOT / args.authorization_path).resolve()
    if ROOT not in plan_path.parents or ROOT not in auth_path.parents:
        raise Stopped("bind_control_path_outside_repository")
    plan = json.loads(plan_path.read_text())
    print(json.dumps(preflight(plan, auth_path, args.execute_approved), sort_keys=True))
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
            "pid": os.getpid(), "state": "running", "plan_sha256": digest(plan),
        })
        try:
            complete = Driver(plan, gateway).execute()
            report = evaluate(plan, directory, complete)
            status = "completed_development_pilot"
            close_authorization(status, gateway, auth_path)
            write_json(directory / "completed.json", {
                "plan_sha256": digest(plan), "state": status,
                "usage": gateway.summary(), "evaluation": report,
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
                "pid": os.getpid(),
                "state": "resumable_interruption" if not gateway.halt_reason() else "halted",
                "reason": str(exc), "plan_sha256": digest(plan),
            })
            raise


if __name__ == "__main__":
    main()
