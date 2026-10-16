#!/usr/bin/env python3
"""Freeze the untouched generation-two VERA-Opt confirmation comparison."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_inputs import flat_input, payload_sha256
from llm4or.codex_cli_gateway import VERSION as GATEWAY_VERSION
from llm4or.declarative_selection_compiler import VERSION as COMPILER_VERSION
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.vera_opt_confirmation_evaluation import VERSION as EVALUATION_VERSION
from llm4or.vera_opt_promotion_runtime import (
    IMPLEMENTATION_ID, VERSION as RUNTIME_VERSION,
)
from llm4or.verified_skill_library import validate_skill_package


SPLIT = ROOT / "experiments/vera_opt_generation1_split.json"
SOURCE = ROOT / "data/raw/optengine_20261004/test_data/canonical/canonical.jsonl"
CANDIDATE = ROOT / "experiments/vera_opt_generation2_deploy_candidate.json"
DEVELOPMENT = ROOT / "results/vera_opt_generation2_development.json"
PRIVATE = ROOT / "results/private/vera_opt_generation2_confirmation_20261004"
PUBLIC = PRIVATE / "public_projection.json"
PLAN = ROOT / "experiments/vera_opt_generation2_confirmation_plan.json"
AUTH = ROOT / "experiments/vera_opt_generation2_confirmation_authorization.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if PLAN.exists() or AUTH.exists():
        raise ValueError("confirmation_already_frozen")
    split = json.loads(SPLIT.read_text()); candidate = json.loads(CANDIDATE.read_text())
    development = json.loads(DEVELOPMENT.read_text())
    if not development.get("development_gate_passed"):
        raise ValueError("generation2_development_not_passed")
    compiler_sha = sha(ROOT / "llm4or/declarative_selection_compiler.py")
    skill = validate_skill_package(candidate["skill"], {IMPLEMENTATION_ID: compiler_sha})
    if digest(skill) != candidate["skill_sha256"]:
        raise ValueError("deploy_candidate_changed")
    rows = sorted((row for row in split["records"] if row["role"] == "confirmation"),
                  key=lambda row: row["problem_id"])
    if len(rows) != 110:
        raise ValueError("confirmation_size_changed")
    by_row = {row["source_row"]: row for row in rows}; records = []
    for line_number, line in enumerate(SOURCE.read_text().splitlines(), 1):
        meta = by_row.get(line_number)
        if meta is None:
            continue
        value = json.loads(line); question = value["question"]
        if hashlib.sha256(question.encode()).hexdigest() != meta["question_sha256"]:
            raise ValueError("confirmation_question_changed")
        public = flat_input(meta["problem_id"], {"question": question}, "question")
        records.append({"problem_id": meta["problem_id"], "size": meta["size"],
                        "within_size_index": meta["within_size_index"],
                        "source_row": meta["source_row"], "public": public,
                        "input_sha256": payload_sha256(public)})
    if len(records) != 110:
        raise ValueError("confirmation_projection_incomplete")
    records.sort(key=lambda row: row["problem_id"])
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(PUBLIC, {"schema": "vera-opt-generation2-confirmation-public-v1",
                        "contains_answers": False, "records": records})
    frozen_names = [
        str(SPLIT.relative_to(ROOT)), str(SOURCE.relative_to(ROOT)),
        str(CANDIDATE.relative_to(ROOT)), str(DEVELOPMENT.relative_to(ROOT)),
        str(PUBLIC.relative_to(ROOT)), "llm4or/benchmark_inputs.py",
        "llm4or/codex_cli_gateway.py", "llm4or/confirmatory_statistics.py",
        "llm4or/declarative_selection_compiler.py", "llm4or/formal_gateway.py",
        "llm4or/formal_runtime.py", "llm4or/gateway.py", "llm4or/milp_pipeline.py",
        "llm4or/milp_schema.py", "llm4or/milp_solver.py", "llm4or/pipeline.py",
        "llm4or/run_interruption.py", "llm4or/schema.py", "llm4or/text2opt_v6_runtime.py",
        "llm4or/text2opt_v9_runtime.py", "llm4or/vera_opt_confirmation_evaluation.py",
        "llm4or/vera_opt_promotion_evaluation.py", "llm4or/vera_opt_promotion_runtime.py",
        "llm4or/verified_skill_library.py",
        "scripts/evaluate_vera_opt_generation2_confirmation.py",
        "scripts/run_vera_opt_generation2_confirmation.py",
    ]
    codex = "/Applications/ChatGPT.app/Contents/Resources/codex"
    cli_version = subprocess.run([codex, "--version"], capture_output=True, text=True,
                                 check=True, timeout=15).stdout.strip()
    limits = {"max_completion_tokens": 32768, "max_input_bytes": 524288,
              "max_output_bytes": 4194304, "max_requests": 330,
              "max_total_reserved_or_reported_tokens": 80_000_000,
              "minimum_free_disk_bytes": 2 * 1024**3, "request_seconds": 600,
              "max_run_seconds": 345600, "token_overhead_reserve": 131072}
    plan = {
        "schema": "vera-opt-generation2-confirmation-plan-v1",
        "authorization_schema": "codex-cli-confirmation-authorization-v1",
        "role": "untouched_size_extrapolation_confirmation",
        "claim_guard": "No method, candidate, prompt, endpoint, scoring, or gate change after freeze.",
        "confirmation_outcomes_opened": False,
        "provider_mode": "existing_codex_login_chatgpt_quota_no_api_key_copy",
        "codex_cli": codex, "codex_cli_version": cli_version,
        "model": "gpt-6-luna", "reasoning_effort": "high",
        "gateway_version": GATEWAY_VERSION, "runtime_version": RUNTIME_VERSION,
        "evaluation_version": EVALUATION_VERSION, "compiler_version": COMPILER_VERSION,
        "scope_contract": {"prefix": "verag2confirm", "method": "BaseVERA",
                           "calls_per_scope": 1},
        "replicates": [83], "token_cap": 524288, "serial_canary_records": 1,
        "run_directory": str(PRIVATE.relative_to(ROOT)),
        "public_projection": str(PUBLIC.relative_to(ROOT)),
        "public_projection_sha256": sha(PUBLIC),
        "source_file": str(SOURCE.relative_to(ROOT)),
        "split_manifest": str(SPLIT.relative_to(ROOT)), "split_manifest_sha256": sha(SPLIT),
        "candidate_file": str(CANDIDATE.relative_to(ROOT)), "candidate_sha256": sha(CANDIDATE),
        "skill_sha256": candidate["skill_sha256"],
        "trusted_implementation": {"id": IMPLEMENTATION_ID, "sha256": compiler_sha},
        "selection": {"records": [{"problem_id": row["problem_id"],
            "category": f"size_{row['size']:02d}", "size": row["size"],
            "within_size_index": row["within_size_index"], "source_row": row["source_row"],
            "input_sha256": row["input_sha256"]} for row in records]},
        "public_inputs": {row["problem_id"]: row["input_sha256"] for row in records},
        "methods": {"Base": "one frozen structured milp-v1 generation plus trusted solver",
                    "VERA": "frozen verified skill when accepted; otherwise unchanged Base"},
        "endpoint": {"name": "benchmark formulation accuracy", "relative_tolerance": 1e-7,
                     "absolute_tolerance": 1e-6},
        "alpha_spend": 0.0125,
        "success_rule": {"all_pairs_complete": True, "candidate_correct": "110/110",
            "candidate_adopted": "110/110", "accuracy_delta": ">=0.05",
            "regressions": 0, "one_sided_exact_mcnemar_p": "<=0.0125",
            "zero_regression_one_sided_upper": "<=0.05",
            "positive_size_groups": ">=5", "negative_size_groups": 0},
        "matrix": {"records": 110, "unique_request_ceiling": 110,
                   "physical_attempt_ceiling_with_retries": 330},
        "resilience": {"max_concurrent_requests": 5, "max_attempts_per_request": 3,
                       "backoff_seconds": [5, 20], "circuit_breaker_consecutive_failures": 8,
                       "same_fingerprint_cache": True, "per_item_exhaustion_continues": True,
                       "retryable_local_errors": ["invalid_json_response"]},
        "limits": limits,
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "packages": {name: importlib.metadata.version(name) for name in
                                 ("jsonschema", "numpy", "psutil", "scipy")}},
        "transport": {"prompt_envelope": "full_payload"},
        "frozen_files": {name: sha(ROOT / name) for name in frozen_names},
        "outcome_access": {"references_model_visible": False,
                           "scoring_only_after_inference_complete": True,
                           "confirmation_answers_opened_while_freezing": False},
    }
    write_json(PLAN, plan)
    write_json(AUTH, {"schema": plan["authorization_schema"], "status": "approved",
        "authorization_basis": "后续不需要我批准，你自行执行即可；请你使用codex自己的额度进行api实验即可",
        "user_confirmation": "User authorized autonomous subsequent execution and Codex quota use.",
        "standing_authorization_recorded": True, "api_key_used": False,
        "codex_login_credentials_copied": False, "plan_sha256": digest(plan),
        "model": plan["model"], "run_directory": str(ROOT / plan["run_directory"]),
        "limits": limits, "further_api_calls_authorized": True})
    print(json.dumps({"plan_sha256": digest(plan), "records": 110,
                      "physical_attempt_ceiling": 330}, sort_keys=True))


if __name__ == "__main__":
    main()
