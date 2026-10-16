#!/usr/bin/env python3
"""Run the frozen second-family VERA-Opt proposal trajectory."""

from datetime import datetime, timezone
import argparse
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
from llm4or.declarative_packing_compiler import (
    optimal_bin_count, parse_packing_text, solve_declarative_packing,
    validate_configuration, VERSION as COMPILER_VERSION,
)
from llm4or.formal_gateway import RequestUnavailable
from llm4or.gateway import Stopped
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.vera_opt_binpacking_proposal import (
    IMPLEMENTATION_ID, PROPOSAL_SCHEMA, VERSION, instruction, package_from_proposal,
    proposal_public_problem_from_questions,
)
from llm4or.verified_skill_library import apply_skill_library, recognizer_matches, validate_skill_package


PLAN_PATH = ROOT / "experiments/vera_opt_binpacking_proposal_plan.json"
AUTH_PATH = ROOT / "experiments/vera_opt_binpacking_proposal_authorization.json"
REPORT_PATH = ROOT / "results/vera_opt_binpacking_development.json"
CANDIDATE_PATH = ROOT / "experiments/vera_opt_binpacking_candidate.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_public_projection(plan: dict) -> tuple[dict, dict[str, str]]:
    path = ROOT / plan["public_projection"]
    if sha(path) != plan["public_projection_sha256"]:
        raise Stopped("public_projection_changed")
    value = json.loads(path.read_text()); split = json.loads((ROOT / plan["split_manifest"]).read_text())
    records = {record["problem_id"]: record for record in split["records"]}
    questions = {}
    for row in value["records"]:
        meta = records.get(row["problem_id"])
        if meta is None or hashlib.sha256(row["question"].encode()).hexdigest() != meta["question_sha256"]:
            raise Stopped("public_question_changed")
        questions[row["problem_id"]] = row["question"]
    if set(questions) != set(records):
        raise Stopped("public_projection_incomplete")
    return split, questions


def preflight(plan: dict, execute_run: bool) -> dict:
    if plan["gateway_version"] != GATEWAY_VERSION or plan["proposal_controller_version"] != VERSION \
            or plan["compiler_version"] != COMPILER_VERSION:
        raise Stopped("runtime_version_changed")
    actual = {"python": platform.python_version(), "machine": platform.machine(),
              "packages": {name: importlib.metadata.version(name) for name in plan["runtime"]["packages"]}}
    if actual != plan["runtime"]:
        raise Stopped("runtime_changed")
    if subprocess.run([plan["codex_cli"], "--version"], capture_output=True, text=True,
                      check=True, timeout=15).stdout.strip() != plan["codex_cli_version"]:
        raise Stopped("cli_changed")
    validate_codex_cli_interface(plan, ROOT)
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise Stopped("frozen_file_changed:" + name)
    split, questions = load_public_projection(plan)
    public = proposal_public_problem_from_questions(questions, split)
    if payload_sha256(public) != plan["public_inputs"][public["id"]]:
        raise Stopped("proposal_input_changed")
    auth = json.loads(AUTH_PATH.read_text())
    if auth["plan_sha256"] != digest(plan) or execute_run and auth["status"] != "approved":
        raise Stopped("authorization_required")
    return {"status": "passed", "plan_sha256": digest(plan), "authorization": auth["status"]}


def static_candidate(proposal: dict, plan: dict, stage: int, questions: dict[str, str],
                     split: dict) -> tuple[dict | None, list[str]]:
    try:
        package = package_from_proposal(
            proposal, implementation_sha256=plan["trusted_implementation"]["sha256"],
            development_manifest_sha256=plan["split_manifest_sha256"],
            proposer=f"{plan['model']}:{plan['reasoning_effort']}:stage{stage + 1}",
        )
        config = validate_configuration(package["implementation"]["configuration"])
        registry = {plan["trusted_implementation"]["id"]: plan["trusted_implementation"]["sha256"]}
        validate_skill_package(package, registry)
        failures = {}
        for record in split["records"]:
            if record["role"] != "development":
                continue
            text = questions[record["problem_id"]]
            try:
                if not recognizer_matches(package, text, registry):
                    raise ValueError("recognizer_miss")
                parse_packing_text(text, config)
            except Exception as exc:
                reason = type(exc).__name__ + ":" + str(exc)
                failures[reason] = failures.get(reason, 0) + 1
        if failures:
            return None, ["answer-free public coverage failures: " + json.dumps(failures, sort_keys=True)]
        return package, []
    except Exception as exc:
        return None, [type(exc).__name__ + ":" + str(exc)]


def load_development_answers(plan: dict, split: dict, questions: dict[str, str]) -> dict[str, float]:
    by_row = {record["source_row"]: record for record in split["records"]
              if record["role"] == "development"}
    answers = {}
    for line_number, line in enumerate((ROOT / plan["source_file"]).read_text().splitlines(), 1):
        if line_number not in by_row:
            continue
        row = json.loads(line); meta = by_row[line_number]
        if row["question"] != questions[meta["problem_id"]] or digest(row["answer"]) != meta["answer_sha256"]:
            raise Stopped("development_source_changed")
        answers[meta["problem_id"]] = float(row["answer"])
    if len(answers) != len(by_row):
        raise Stopped("development_answers_missing")
    return answers


def reverse_item_lines(text: str, prefixes: list[str]) -> str:
    lines = text.splitlines()
    indices = [index for index, line in enumerate(lines)
               if any(line.strip().casefold().startswith(prefix.casefold()) for prefix in prefixes)]
    values = [lines[index] for index in indices][::-1]
    for index, value in zip(indices, values):
        lines[index] = value
    return "\n".join(lines)


def evaluate_candidate(package: dict, plan: dict, split: dict, questions: dict[str, str],
                       answers: dict[str, float]) -> dict:
    registry = {plan["trusted_implementation"]["id"]: plan["trusted_implementation"]["sha256"]}
    rows = [record for record in split["records"] if record["role"] == "development"]
    exact = adopted = 0; failures = {}; private_rows = []
    for meta in rows:
        problem_id = meta["problem_id"]
        report = apply_skill_library(
            flat_input(problem_id, {"question": questions[problem_id]}, "question"),
            {"status": "backend_placeholder", "objective": None}, [package],
            trusted_implementation_digests=registry,
            trusted_implementation_functions={IMPLEMENTATION_ID: solve_declarative_packing},
        )
        objective = report["result"].get("objective") if report["adopted"] else None
        correct = type(objective) in (int, float) and math.isclose(
            float(objective), answers[problem_id], rel_tol=1e-7, abs_tol=1e-6,
        )
        adopted += int(report["adopted"]); exact += int(correct)
        if not report["adopted"]:
            reason = report.get("reason", report.get("compiler_status", "unknown"))
            failures[reason] = failures.get(reason, 0) + 1
        private_rows.append({"problem_id": problem_id, "adopted": report["adopted"],
                             "correct": correct, "result_sha256": report["result_sha256"]})

    config = package["implementation"]["configuration"]
    metamorphic_total = metamorphic_passed = 0
    for meta in rows[:10]:
        text = questions[meta["problem_id"]]
        base = solve_declarative_packing(flat_input(meta["problem_id"], {"question": text}, "question"),
                                         package["limits"], config)
        permuted = solve_declarative_packing(
            flat_input(meta["problem_id"] + "_p", {"question": reverse_item_lines(
                text, config["record_rule"]["line_prefixes"])}, "question"), package["limits"], config,
        )
        metamorphic_total += 1
        metamorphic_passed += int(base.get("status") == permuted.get("status") == "optimal"
                                  and math.isclose(base["objective"], permuted["objective"], abs_tol=1e-7))
        parsed = parse_packing_text(text, config)
        scaled_objective = optimal_bin_count(
            [2 * record["fields"][config["item_weight_field"]] for record in parsed["records"]],
            2 * parsed["capacity"], wall_seconds=20,
        )
        metamorphic_total += 1
        metamorphic_passed += int(base.get("status") == "optimal"
                                  and math.isclose(base["objective"], scaled_objective, abs_tol=1e-7))
    return {"records": len(rows), "adopted": adopted, "exact": exact,
            "accuracy": exact / len(rows), "failure_reasons": dict(sorted(failures.items())),
            "metamorphic_passed": metamorphic_passed, "metamorphic_total": metamorphic_total,
            "records_private_sha256": digest(private_rows)}


def close(status: str, gateway: CodexCliGateway) -> None:
    auth = json.loads(AUTH_PATH.read_text())
    auth.update(status=status, closed_usage=gateway.summary(),
                closed_at=datetime.now(timezone.utc).isoformat(), further_api_calls_authorized=False)
    write_json(AUTH_PATH, auth)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--execute-approved", action="store_true")
    args = parser.parse_args(); plan = json.loads(PLAN_PATH.read_text())
    print(json.dumps(preflight(plan, args.execute_approved), sort_keys=True))
    if not args.execute_approved:
        return
    split, questions = load_public_projection(plan)
    public = proposal_public_problem_from_questions(questions, split)
    gateway = CodexCliGateway(ROOT, plan, str(AUTH_PATH.relative_to(ROOT)))
    directory = gateway.directory; scope = f"verabp:SkillProposer:{plan['replicates'][0]}:{public['id']}"
    with (directory / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stopped("controller_already_running") from None
        write_json(directory / "controller.json", {"pid": os.getpid(), "state": "running",
                                                     "plan_sha256": digest(plan)})
        try:
            gateway.register(scope, 3, plan["token_cap"]); gateway.work_started(scope)
            proposals = []; packages = []; stage_summaries = []; feedback = []
            for stage in range(3):
                payload = {"version": VERSION, "instruction": instruction(stage, proposals, feedback),
                           "problem": public, "context": {"stage": stage + 1, "answer_access": False},
                           "output_contract": "inert declarative skill proposal only",
                           "response_schema": PROPOSAL_SCHEMA}
                try:
                    response = gateway.request(scope, payload, digest({"stage": stage + 1}),
                                               plan["replicates"][0], stage)
                    proposal = json.loads(response["text"])
                    package, errors = static_candidate(proposal, plan, stage, questions, split)
                    proposals.append(proposal)
                    if package is not None:
                        packages.append((stage, package))
                    feedback = errors or ["static validation and answer-free public coverage passed"]
                    stage_summaries.append({"stage": stage + 1, "response_sha256": digest(proposal),
                                            "static_valid": package is not None, "feedback": feedback})
                except RequestUnavailable as exc:
                    feedback = [str(exc)]
                    stage_summaries.append({"stage": stage + 1, "infrastructure_unavailable": True,
                                            "feedback": feedback})
            gateway.work_finished(scope, "complete" if packages else "method_failure",
                                  None if packages else "no_static_valid_candidate")
            answers = load_development_answers(plan, split, questions)
            evaluations = [(stage, package, evaluate_candidate(package, plan, split, questions, answers))
                           for stage, package in packages]
            eligible = [item for item in evaluations if item[2]["exact"] == item[2]["records"]
                        and item[2]["metamorphic_passed"] == item[2]["metamorphic_total"]]
            selected = sorted(eligible, key=lambda item: (-item[2]["exact"], -item[2]["adopted"], item[0]))[0] \
                if eligible else None
            report = {"schema": "vera-opt-binpacking-development-v1",
                      "role": "outcome_exposed_development_skill_induction",
                      "plan_sha256": digest(plan),
                      "api_then_answers_boundary": "all proposal calls completed before answers loaded",
                      "stages": stage_summaries,
                      "candidates": [{"stage": stage + 1, "skill_sha256": digest(package), **evaluation}
                                     for stage, package, evaluation in evaluations],
                      "selected_stage": selected[0] + 1 if selected else None,
                      "selected_skill_sha256": digest(selected[1]) if selected else None,
                      "development_gate_passed": selected is not None, "usage": gateway.summary(),
                      "claim_guard": "development only; promotion and confirmation outcomes remain unopened"}
            if selected:
                write_json(CANDIDATE_PATH, {"schema": "vera-opt-binpacking-candidate-v1",
                    "role": "automatically_proposed_development_selected_not_yet_promoted",
                    "plan_sha256": digest(plan), "skill": selected[1],
                    "skill_sha256": digest(selected[1]), "development_evaluation": selected[2]})
            write_json(REPORT_PATH, report)
            status = "completed_candidate_selected" if selected else "completed_no_candidate"
            close(status, gateway)
            write_json(directory / "completed.json", {"state": status, "plan_sha256": digest(plan),
                                                        "usage": gateway.summary(), "report": report})
            write_json(directory / "controller.json", {"pid": os.getpid(), "state": status,
                                                         "plan_sha256": digest(plan)})
        except BaseException as exc:
            write_json(directory / "interrupted.json", {"reason": str(exc), "usage": gateway.summary(),
                                                         "automatic_resume": not gateway.halt_reason()})
            write_json(directory / "controller.json", {"pid": os.getpid(),
                "state": "halted" if gateway.halt_reason() else "resumable_interruption",
                "reason": str(exc), "plan_sha256": digest(plan)})
            raise


if __name__ == "__main__":
    main()
