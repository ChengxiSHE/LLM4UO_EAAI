#!/usr/bin/env python3
"""Run the frozen six-family common-input CoE development pilot."""

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
from llm4or.bind_runtime import bind_reference_projection
from llm4or.coe_official_adapter import CoEPromptSource
from llm4or.coe_runtime import VERSION, run_coe_forward
from llm4or.codex_cli_gateway import CodexCliGateway, LocalRequestFailure, VERSION as GATEWAY_VERSION, validate_codex_cli_interface
from llm4or.formal_gateway import RequestUnavailable
from llm4or.gateway import Stopped
from llm4or.gurobi_cli_solver import VERSION as GUROBI_VERSION, execute as gurobi_execute
from llm4or.pipeline import write_json
from llm4or.run_interruption import RunInterrupted
from llm4or.schema import digest


PLAN_PATH = ROOT / "experiments/coe_common_development_pilot_plan.json"
AUTH_PATH = ROOT / "experiments/coe_common_development_pilot_authorization.json"
REPORT_PATH = ROOT / "results/coe_common_development_pilot_evaluation.json"
UPSTREAM = ROOT / "data/raw/xzymustbexzy__Chain-of-Experts_20261003"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_prepared(plan):
    path = ROOT / plan["prepared_data"]
    if sha(path) != plan["prepared_data_sha256"]:
        raise Stopped("coe_common_prepared_changed")
    value = json.loads(path.read_text())
    index = {row["problem_id"]: row for row in value["records"]}
    if set(index) != set(plan["public_inputs"]):
        raise Stopped("coe_common_selection_changed")
    for problem_id, expected in plan["public_inputs"].items():
        if payload_sha256(index[problem_id]["public"]) != expected:
            raise Stopped("coe_common_public_changed:" + problem_id)
    return index


def preflight(plan, execute):
    actual = {"python": platform.python_version(), "machine": platform.machine(),
              "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]}}
    if actual != plan["runtime"] or plan["runtime_version"] != VERSION or plan["gateway_version"] != GATEWAY_VERSION:
        raise Stopped("coe_common_runtime_changed")
    if os.environ.get("PYTHONHASHSEED") != plan["settings"]["paper_hash_seed"]:
        raise Stopped("coe_common_hash_seed_required")
    if plan["resilience"]["max_concurrent_requests"] != 1:
        raise Stopped("coe_common_concurrency_changed")
    if subprocess.run([plan["codex_cli"], "--version"], capture_output=True, text=True,
                      timeout=15, check=True).stdout.strip() != plan["codex_cli_version"]:
        raise Stopped("coe_common_cli_changed")
    solver = plan["solver_backend"]
    actual_solver = subprocess.run([solver["binary"], "--version"], capture_output=True,
                                   text=True, timeout=15, check=True).stdout.splitlines()[0].strip()
    if solver["adapter_version"] != GUROBI_VERSION or actual_solver != solver["version"]:
        raise Stopped("coe_common_solver_changed")
    validate_codex_cli_interface(plan, ROOT)
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    CoEPromptSource.load(UPSTREAM, "paper"); CoEPromptSource.load(UPSTREAM, "current")
    load_prepared(plan)
    auth = json.loads(AUTH_PATH.read_text())
    if auth["plan_sha256"] != digest(plan) or execute and auth["status"] != "approved":
        raise Stopped("coe_common_authorization_required")
    return {"status": "passed", "plan_sha256": digest(plan), "authorization": auth["status"],
            "api_requests": 0}


class Driver:
    def __init__(self, plan, gateway):
        self.plan, self.gateway, self.directory = plan, gateway, gateway.directory
        self.index = load_prepared(plan)
        self.prompts = {name: CoEPromptSource.load(UPSTREAM, name) for name in ("paper", "current")}

    def one(self, item):
        row = self.index[item["problem_id"]]; problem_id = row["problem_id"]
        replicate = self.plan["replicates"][0]; scope = f"coecdev:CoE:{replicate}:{problem_id}"
        path = self.directory / "inference" / (digest(scope) + ".json"); path.parent.mkdir(parents=True, exist_ok=True)
        self.gateway.work_started(scope)
        source_path = ROOT / row["source_file"]
        if sha(source_path) != row["source_file_sha256"]:
            raise Stopped("coe_common_source_changed:" + problem_id)
        native = {"description": row["public"]["text"], "code_example": row["code_example"]}
        def reference():
            if sha(source_path) != row["source_file_sha256"]:
                raise Stopped("coe_common_reference_changed:" + problem_id)
            ref = bind_reference_projection(json.loads(source_path.read_text()))
            return [{"input": {}, "output": [ref["optimum"]]}]
        try:
            record = run_coe_forward(
                row["public"], native, "solve_problem", self.gateway, scope, replicate,
                self.plan["token_cap"], self.prompts[row["snapshot"]], reference,
                max_collaborations=self.plan["settings"]["max_collaborations"],
                rng_seed=self.plan["settings"]["rng_seed"], solver=gurobi_execute,
                checkpoint_path=path,
            )
            self.gateway.work_finished(scope, "complete")
            return {"problem_id": problem_id, "source_problem_id": row["source_problem_id"],
                    "family": row["family"], "snapshot": row["snapshot"], "status": "complete",
                    "record_path": str(path.relative_to(ROOT)), "record_sha256": digest(record)}
        except RequestUnavailable as exc:
            self.gateway.work_finished(scope, "unavailable", str(exc))
            return {"problem_id": problem_id, "source_problem_id": row["source_problem_id"],
                    "family": row["family"], "snapshot": row["snapshot"],
                    "status": "infrastructure_unavailable", "reason": str(exc)}
        except RunInterrupted:
            raise
        except (LocalRequestFailure, ValueError, json.JSONDecodeError) as exc:
            reason = "method_failure:" + type(exc).__name__
            self.gateway.work_finished(scope, "method_failure", reason)
            return {"problem_id": problem_id, "source_problem_id": row["source_problem_id"],
                    "family": row["family"], "snapshot": row["snapshot"],
                    "status": "method_failure", "reason": reason}

    def execute(self):
        cells = [self.one(item) for item in self.plan["selection"]["records"]]
        complete = {"plan_sha256": digest(self.plan), "cells": cells,
                    "usage": self.gateway.summary(), "completed_at": datetime.now(timezone.utc).isoformat()}
        write_json(self.directory / "inference_complete.json", complete)
        return complete


def evaluate(plan, complete):
    by_snapshot = defaultdict(lambda: {"planned": 0, "evaluated": 0, "author_exact": 0,
                                       "tolerance": 0, "adapter_supported": 0,
                                       "infrastructure_unavailable": 0, "method_failure": 0})
    by_family = defaultdict(lambda: {"paper": None, "current": None})
    reasons = Counter(); cells = []
    for cell in complete["cells"]:
        agg = by_snapshot[cell["snapshot"]]; agg["planned"] += 1
        if cell["status"] != "complete":
            agg[cell["status"]] += 1; reasons[cell.get("reason", cell["status"])] += 1; cells.append(cell); continue
        record = json.loads((ROOT / cell["record_path"]).read_text())
        if digest(record) != cell["record_sha256"]: raise Stopped("coe_common_result_integrity")
        agg["evaluated"] += 1; agg["author_exact"] += int(record["author_accept"])
        agg["tolerance"] += int(record["tolerance_accept"]); agg["adapter_supported"] += int(record["adapter_supported"])
        by_family[cell["family"]][cell["snapshot"]] = record["author_accept"]
        cells.append({**cell, "author_accept": record["author_accept"],
                      "tolerance_accept": record["tolerance_accept"],
                      "adapter_supported": record["adapter_supported"],
                      "selected_experts": [step["expert_key"] for step in record["steps"]],
                      "final_output_sha256": record["final_output_sha256"]})
    for value in by_snapshot.values():
        value["author_exact_accuracy"] = value["author_exact"] / value["evaluated"] if value["evaluated"] else None
        value["tolerance_accuracy"] = value["tolerance"] / value["evaluated"] if value["evaluated"] else None
    report = {"schema": "coe-common-development-pilot-evaluation-v1",
              "role": "development_common_input_adapter_not_confirmatory",
              "plan_sha256": digest(plan), "by_snapshot": dict(sorted(by_snapshot.items())),
              "by_family": dict(sorted(by_family.items())), "failure_reasons": dict(sorted(reasons.items())),
              "cells": cells,
              "comparison_context": {"V9_on_same_records": "6/6", "BIND_round1_on_same_records": "6/6",
                                     "BIND_final_on_same_records": "6/6"},
              "deviations": ["generic no-answer code skeleton replaces native benchmark-specific skeleton",
                             "Codex CLI common backbone has no temperature-zero flag",
                             "minimal structured transport wrapper follows official prompts",
                             "reflection disabled", "generated Python never executed"],
              "claim_guard": "six outcome-exposed development records; no superiority claim",
              "usage": complete["usage"]}
    write_json(REPORT_PATH, report); return report


def close(status, gateway):
    auth = json.loads(AUTH_PATH.read_text()); auth.update(status=status, closed_usage=gateway.summary(),
        closed_at=datetime.now(timezone.utc).isoformat(), further_api_calls_authorized=False); write_json(AUTH_PATH, auth)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--execute-approved", action="store_true"); args = parser.parse_args()
    plan = json.loads(PLAN_PATH.read_text()); print(json.dumps(preflight(plan, args.execute_approved), sort_keys=True))
    if not args.execute_approved: return
    gateway = CodexCliGateway(ROOT, plan, str(AUTH_PATH.relative_to(ROOT))); directory = gateway.directory
    with (directory / "controller.lock").open("a") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise Stopped("controller_already_running") from None
        write_json(directory / "controller.json", {"pid": os.getpid(), "state": "running", "plan_sha256": digest(plan)})
        try:
            complete = Driver(plan, gateway).execute(); report = evaluate(plan, complete)
            status = "completed_development_pilot"; close(status, gateway)
            write_json(directory / "completed.json", {"state": status, "plan_sha256": digest(plan),
                                                        "usage": gateway.summary(), "evaluation": report})
            write_json(directory / "controller.json", {"pid": os.getpid(), "state": status, "plan_sha256": digest(plan)})
        except BaseException as exc:
            write_json(directory / "interrupted.json", {"reason": str(exc), "usage": gateway.summary(),
                                                         "automatic_resume": not gateway.halt_reason()})
            write_json(directory / "controller.json", {"pid": os.getpid(), "state": "halted" if gateway.halt_reason() else "resumable_interruption",
                                                         "reason": str(exc), "plan_sha256": digest(plan)})
            raise


if __name__ == "__main__": main()
