#!/usr/bin/env python3
"""Run and verify the frozen VERA-Opt generation-two typed update."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_inputs import flat_input, payload_sha256
from llm4or.codex_cli_gateway import CodexCliGateway, VERSION as GATEWAY_VERSION, validate_codex_cli_interface
from llm4or.declarative_selection_compiler import (
    VERSION as COMPILER_VERSION, solve_declarative_selection,
)
from llm4or.gateway import Stopped
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.vera_opt_evolution import (
    IMPLEMENTATION_ID, PATCH_SCHEMA, VERSION, apply_prefix_patch, instruction,
)
from llm4or.verified_skill_library import apply_skill_library, validate_skill_package


PLAN_PATH = ROOT / "experiments/vera_opt_generation2_update_plan.json"
AUTH_PATH = ROOT / "experiments/vera_opt_generation2_update_authorization.json"
REPORT_PATH = ROOT / "results/vera_opt_generation2_development.json"
CANDIDATE_PATH = ROOT / "experiments/vera_opt_generation2_candidate.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_public_failure(plan: dict) -> dict:
    path = ROOT / plan["public_failure"]
    if sha(path) != plan["public_failure_sha256"]:
        raise Stopped("generation2_public_failure_changed")
    value = json.loads(path.read_text()); problem = value["problem"]
    if payload_sha256(problem) != plan["public_inputs"][problem["id"]]:
        raise Stopped("generation2_public_payload_changed")
    return value


def load_parent(plan: dict) -> dict:
    path = ROOT / plan["parent_candidate"]
    if sha(path) != plan["parent_candidate_sha256"]:
        raise Stopped("generation2_parent_changed")
    value = json.loads(path.read_text())
    skill = validate_skill_package(value["skill"], {
        plan["trusted_implementation"]["id"]: plan["trusted_implementation"]["sha256"],
    })
    if digest(skill) != plan["parent_skill_sha256"]:
        raise Stopped("generation2_parent_skill_changed")
    return skill


def preflight(plan: dict, execute_run: bool) -> dict:
    actual = {"python": platform.python_version(), "machine": platform.machine(),
              "packages": {name: importlib.metadata.version(name)
                           for name in plan["runtime"]["packages"]}}
    if actual != plan["runtime"] or plan["gateway_version"] != GATEWAY_VERSION \
            or plan["controller_version"] != VERSION \
            or plan["compiler_version"] != COMPILER_VERSION:
        raise Stopped("generation2_runtime_changed")
    if subprocess.run([plan["codex_cli"], "--version"], capture_output=True, text=True,
                      check=True, timeout=15).stdout.strip() != plan["codex_cli_version"]:
        raise Stopped("generation2_cli_changed")
    validate_codex_cli_interface(plan, ROOT)
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    load_public_failure(plan); load_parent(plan)
    auth = json.loads(AUTH_PATH.read_text())
    if auth["plan_sha256"] != digest(plan) or execute_run and auth["status"] != "approved":
        raise Stopped("generation2_authorization_required")
    return {"status": "passed", "plan_sha256": digest(plan),
            "authorization": auth["status"], "api_requests": 0}


def development_rows(plan: dict) -> tuple[list[dict], dict[str, str], dict[str, float]]:
    split = json.loads((ROOT / plan["split_manifest"]).read_text())
    rows = [row for row in split["records"] if row["role"] in {"development", "promotion"}]
    by_row = {row["source_row"]: row for row in rows}; questions = {}; answers = {}
    for line_number, line in enumerate((ROOT / plan["source_file"]).read_text().splitlines(), 1):
        meta = by_row.get(line_number)
        if meta is None:
            continue
        value = json.loads(line)
        if hashlib.sha256(value["question"].encode()).hexdigest() != meta["question_sha256"] \
                or digest(value["answer"]) != meta["answer_sha256"]:
            raise Stopped("generation2_development_source_changed")
        questions[meta["problem_id"]] = value["question"]
        answers[meta["problem_id"]] = float(value["answer"])
    if len(questions) != 150:
        raise Stopped("generation2_development_missing")
    return rows, questions, answers


def evaluate_candidate(skill: dict, plan: dict) -> dict:
    rows, questions, answers = development_rows(plan)
    registry = {IMPLEMENTATION_ID: plan["trusted_implementation"]["sha256"]}
    functions = {IMPLEMENTATION_ID: solve_declarative_selection}
    exact = adopted = 0; private = []
    for meta in rows:
        problem_id = meta["problem_id"]
        report = apply_skill_library(
            flat_input(problem_id, {"question": questions[problem_id]}, "question"),
            {"status": "backend_placeholder", "objective": None}, [skill],
            trusted_implementation_digests=registry,
            trusted_implementation_functions=functions,
        )
        objective = report["result"].get("objective") if report["adopted"] else None
        correct = type(objective) in (int, float) and math.isclose(
            objective, answers[problem_id], rel_tol=1e-7, abs_tol=1e-6,
        )
        adopted += report["adopted"]; exact += correct
        private.append({"problem_id": problem_id, "adopted": report["adopted"],
                        "correct": correct, "result_sha256": report["result_sha256"]})
    false_adopted = 0; negative_by_family = {}
    selected_rows = {row["source_row"] for row in rows}
    for line_number, line in enumerate((ROOT / plan["source_file"]).read_text().splitlines(), 1):
        if line_number in selected_rows:
            continue
        value = json.loads(line)
        if value["problem_class"] == "Knapsack":
            continue
        family = value["problem_class"]
        report = apply_skill_library(
            flat_input(f"negative_{line_number}", {"question": value["question"]}, "question"),
            {"status": "backend_placeholder", "objective": None}, [skill],
            trusted_implementation_digests=registry,
            trusted_implementation_functions=functions,
        )
        negative_by_family.setdefault(family, {"records": 0, "false_adopted": 0})
        negative_by_family[family]["records"] += 1
        negative_by_family[family]["false_adopted"] += report["adopted"]
        false_adopted += report["adopted"]
    return {"records": len(rows), "exact": exact, "adopted": adopted,
            "accuracy": exact / len(rows), "false_adopted": false_adopted,
            "negative_challenge": negative_by_family,
            "private_rows_sha256": digest(private),
            "gate_passed": exact == adopted == len(rows) and false_adopted == 0}


def close(status: str, gateway: CodexCliGateway) -> None:
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
    public_value = load_public_failure(plan); public = public_value["problem"]
    parent = load_parent(plan); gateway = CodexCliGateway(ROOT, plan, str(AUTH_PATH.relative_to(ROOT)))
    directory = gateway.directory; replicate = plan["replicates"][0]
    scope = f"verag2:TypedPatch:{replicate}:{public['id']}"
    with (directory / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stopped("controller_already_running") from None
        write_json(directory / "controller.json", {"pid": os.getpid(), "state": "running",
                                                     "plan_sha256": digest(plan)})
        try:
            gateway.register(scope, 1, plan["token_cap"]); gateway.work_started(scope)
            payload = {"version": VERSION, "instruction": instruction(), "problem": public,
                       "context": {"generation": 2, "answer_access": False},
                       "output_contract": "typed prefix patch only", "response_schema": PATCH_SCHEMA}
            response = gateway.request(scope, payload, digest({"generation": 2}), replicate, 0)
            proposal = json.loads(response["text"])
            child = apply_prefix_patch(
                parent, proposal,
                public_failure_text=public_value["problem"]["text"],
                implementation_sha256=plan["trusted_implementation"]["sha256"],
                proposer=f"{plan['model']}:{plan['reasoning_effort']}:generation2",
            )
            gateway.work_finished(scope, "complete", None)
            evaluation = evaluate_candidate(child, plan)
            report = {
                "schema": "vera-opt-generation2-development-v1",
                "plan_sha256": digest(plan), "parent_skill_sha256": digest(parent),
                "proposal_sha256": digest(proposal), "child_skill_sha256": digest(child),
                "evaluation": evaluation, "development_gate_passed": evaluation["gate_passed"],
                "usage": gateway.summary(),
                "claim_guard": "Development plus opened promotion only; final confirmation remains unopened.",
            }
            write_json(REPORT_PATH, report)
            if evaluation["gate_passed"]:
                write_json(CANDIDATE_PATH, {
                    "schema": "vera-opt-generation2-candidate-v1",
                    "role": "failure_driven_candidate_not_yet_confirmed",
                    "plan_sha256": digest(plan), "skill": child,
                    "skill_sha256": digest(child), "development_evaluation": evaluation,
                })
            status = "completed_candidate_selected" if evaluation["gate_passed"] \
                else "completed_no_candidate"
            close(status, gateway)
            write_json(directory / "completed.json", {"state": status,
                "plan_sha256": digest(plan), "usage": gateway.summary(), "report": report})
            write_json(directory / "controller.json", {"pid": os.getpid(), "state": status,
                                                         "plan_sha256": digest(plan)})
        except BaseException as exc:
            write_json(directory / "interrupted.json", {"reason": type(exc).__name__,
                                                         "usage": gateway.summary()})
            write_json(directory / "controller.json", {"pid": os.getpid(), "state": "interrupted",
                                                         "reason": str(exc),
                                                         "plan_sha256": digest(plan)})
            raise


if __name__ == "__main__":
    main()
