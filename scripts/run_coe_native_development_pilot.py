#!/usr/bin/env python3
"""Run the frozen native CoE paper/current development pilot."""

from __future__ import annotations

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
from llm4or.coe_official_adapter import CoEPromptSource
from llm4or.coe_runtime import VERSION, run_coe_forward
from llm4or.codex_cli_gateway import (
    CodexCliGateway, LocalRequestFailure, VERSION as GATEWAY_VERSION,
    validate_codex_cli_interface,
)
from llm4or.formal_gateway import RequestUnavailable
from llm4or.gateway import Stopped
from llm4or.gurobi_cli_solver import VERSION as GUROBI_VERSION, execute as gurobi_execute
from llm4or.pipeline import write_json
from llm4or.run_interruption import RunInterrupted
from llm4or.schema import digest


PLAN_PATH = ROOT / "experiments/coe_native_development_pilot_plan.json"
AUTH_PATH = ROOT / "experiments/coe_native_development_pilot_authorization.json"
REPORT_PATH = ROOT / "results/coe_native_development_pilot_evaluation.json"
UPSTREAM = ROOT / "data/raw/xzymustbexzy__Chain-of-Experts_20261003"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_prepared(plan):
    path = ROOT / plan["prepared_data"]
    if sha(path) != plan["prepared_data_sha256"]:
        raise Stopped("coe_prepared_data_changed")
    value = json.loads(path.read_text())
    index = {row["problem_id"]: row for row in value["records"]}
    if set(index) != set(plan["public_inputs"]):
        raise Stopped("coe_prepared_selection_changed")
    for problem_id, expected in plan["public_inputs"].items():
        if payload_sha256(index[problem_id]["public"]) != expected:
            raise Stopped("coe_public_input_changed:" + problem_id)
    return index


def preflight(plan, auth_path, execute):
    actual = {
        "python": platform.python_version(), "machine": platform.machine(),
        "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]},
    }
    if actual != plan["runtime"] or plan["runtime_version"] != VERSION \
            or plan["gateway_version"] != GATEWAY_VERSION:
        raise Stopped("coe_runtime_changed")
    if plan["resilience"]["max_concurrent_requests"] != 1:
        raise Stopped("coe_concurrency_changed")
    if os.environ.get("PYTHONHASHSEED") != plan["settings"]["paper_hash_seed"]:
        raise Stopped("coe_paper_hash_seed_required")
    cli = subprocess.run([plan["codex_cli"], "--version"], capture_output=True, text=True,
                         timeout=15, check=True).stdout.strip()
    if cli != plan["codex_cli_version"]:
        raise Stopped("coe_codex_cli_version_changed")
    solver = plan["solver_backend"]
    solver_version = subprocess.run([solver["binary"], "--version"], capture_output=True,
                                    text=True, timeout=15, check=True).stdout.splitlines()[0].strip()
    if solver["adapter_version"] != GUROBI_VERSION or solver_version != solver["version"]:
        raise Stopped("coe_solver_changed")
    validate_codex_cli_interface(plan, ROOT)
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    CoEPromptSource.load(UPSTREAM, "paper")
    CoEPromptSource.load(UPSTREAM, "current")
    load_prepared(plan)
    authorization = json.loads(auth_path.read_text())
    if authorization["plan_sha256"] != digest(plan) or execute and authorization["status"] != "approved":
        raise Stopped("coe_development_authorization_required")
    return {"status": "passed", "plan_sha256": digest(plan),
            "authorization": authorization["status"], "api_requests": 0}


class Driver:
    def __init__(self, plan, gateway):
        self.plan = plan
        self.gateway = gateway
        self.directory = gateway.directory
        self.index = load_prepared(plan)
        self.prompts = {name: CoEPromptSource.load(UPSTREAM, name) for name in ("paper", "current")}

    def one(self, item):
        problem_id = item["problem_id"]
        row = self.index[problem_id]
        replicate = self.plan["replicates"][0]
        scope = f"coedev:CoE:{replicate}:{problem_id}"
        path = self.directory / "inference" / (digest(scope) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.gateway.work_started(scope)
        for key, hash_key in (("description_file", "description_sha256"),
                              ("code_example_file", "code_example_sha256")):
            if sha(ROOT / row[key]) != row[hash_key]:
                raise Stopped("coe_native_source_changed:" + problem_id)
        native = {
            "description": (ROOT / row["description_file"]).read_text(),
            "code_example": (ROOT / row["code_example_file"]).read_text(),
        }
        def references():
            sample = ROOT / row["sample_file"]
            if sha(sample) != row["sample_sha256"]:
                raise Stopped("coe_sample_changed:" + problem_id)
            return json.loads(sample.read_text())
        try:
            record = run_coe_forward(
                row["public"], native, row["native_problem_id"], self.gateway, scope,
                replicate, self.plan["token_cap"], self.prompts[row["snapshot"]], references,
                max_collaborations=self.plan["settings"]["max_collaborations"],
                rng_seed=self.plan["settings"]["rng_seed"], solver=gurobi_execute,
                checkpoint_path=path,
            )
            self.gateway.work_finished(scope, "complete")
            return {"problem_id": problem_id, "native_problem_id": row["native_problem_id"],
                    "snapshot": row["snapshot"], "record_path": str(path.relative_to(ROOT)),
                    "record_sha256": digest(record), "status": "complete"}
        except RequestUnavailable as exc:
            self.gateway.work_finished(scope, "unavailable", str(exc))
            return {"problem_id": problem_id, "native_problem_id": row["native_problem_id"],
                    "snapshot": row["snapshot"], "status": "infrastructure_unavailable",
                    "reason": str(exc), "record_path": None, "record_sha256": None}
        except RunInterrupted:
            raise
        except LocalRequestFailure as exc:
            self.gateway.work_finished(scope, "method_failure", str(exc))
            return {"problem_id": problem_id, "native_problem_id": row["native_problem_id"],
                    "snapshot": row["snapshot"], "status": "method_failure", "reason": str(exc),
                    "record_path": None, "record_sha256": None}
        except (ValueError, json.JSONDecodeError) as exc:
            reason = "method_failure:" + type(exc).__name__
            self.gateway.work_finished(scope, "method_failure", reason)
            return {"problem_id": problem_id, "native_problem_id": row["native_problem_id"],
                    "snapshot": row["snapshot"], "status": "method_failure", "reason": reason,
                    "record_path": None, "record_sha256": None}

    def execute(self):
        cells = [self.one(item) for item in self.plan["selection"]["records"]]
        complete = {"plan_sha256": digest(self.plan), "cells": cells,
                    "usage": self.gateway.summary(),
                    "completed_at": datetime.now(timezone.utc).isoformat()}
        write_json(self.directory / "inference_complete.json", complete)
        return complete


def evaluate(plan, complete):
    by_snapshot = defaultdict(lambda: {"planned": 0, "evaluated": 0, "author_exact": 0,
                                       "tolerance": 0, "adapter_supported": 0,
                                       "infrastructure_unavailable": 0, "method_failure": 0})
    reasons = Counter()
    cells = []
    for cell in complete["cells"]:
        summary = by_snapshot[cell["snapshot"]]
        summary["planned"] += 1
        if cell["status"] != "complete":
            summary[cell["status"]] += 1
            reasons[cell.get("reason", cell["status"])] += 1
            cells.append(cell)
            continue
        record = json.loads((ROOT / cell["record_path"]).read_text())
        if digest(record) != cell["record_sha256"]:
            raise Stopped("coe_result_integrity:" + cell["problem_id"])
        summary["evaluated"] += 1
        summary["author_exact"] += int(record["author_accept"])
        summary["tolerance"] += int(record["tolerance_accept"])
        summary["adapter_supported"] += int(record["adapter_supported"])
        cells.append({**cell, "author_accept": record["author_accept"],
                      "tolerance_accept": record["tolerance_accept"],
                      "adapter_supported": record["adapter_supported"],
                      "selected_experts": [step["expert_key"] for step in record["steps"]],
                      "final_output_sha256": record["final_output_sha256"]})
    for values in by_snapshot.values():
        values["author_exact_accuracy"] = values["author_exact"] / values["evaluated"] if values["evaluated"] else None
        values["tolerance_accuracy"] = values["tolerance"] / values["evaluated"] if values["evaluated"] else None
    report = {
        "schema": "coe-native-development-pilot-evaluation-v1",
        "role": "development_adapter_reproduction_not_confirmatory_comparison",
        "plan_sha256": digest(plan),
        "method_label": "official-prompt CoE forward-only safe native adapter",
        "by_snapshot": dict(sorted(by_snapshot.items())),
        "failure_reasons": dict(sorted(reasons.items())),
        "cells": cells,
        "deviations": [
            "Codex CLI common backbone replaces the paper model and has no temperature-zero flag",
            "minimal structured transport wrapper is appended after each byte-exact official prompt",
            "generated Python is translated by a whitelist interpreter and never executed",
            "trusted Gurobi CLI consumes the validated symbolic model",
            "reflection is disabled because the released reflection evaluator executes generated Python",
        ],
        "claim_guard": "small outcome-exposed development pilot; no superiority or confirmation claim",
        "usage": complete["usage"],
    }
    write_json(REPORT_PATH, report)
    return report


def close_authorization(status, gateway, auth_path):
    authorization = json.loads(auth_path.read_text())
    authorization.update(status=status, closed_usage=gateway.summary(),
                         closed_at=datetime.now(timezone.utc).isoformat(),
                         further_api_calls_authorized=False)
    write_json(auth_path, authorization)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-approved", action="store_true")
    args = parser.parse_args()
    plan = json.loads(PLAN_PATH.read_text())
    print(json.dumps(preflight(plan, AUTH_PATH, args.execute_approved), sort_keys=True))
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
            complete = Driver(plan, gateway).execute()
            report = evaluate(plan, complete)
            status = "completed_development_pilot"
            close_authorization(status, gateway, AUTH_PATH)
            write_json(directory / "completed.json", {"plan_sha256": digest(plan), "state": status,
                                                        "usage": gateway.summary(), "evaluation": report})
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
