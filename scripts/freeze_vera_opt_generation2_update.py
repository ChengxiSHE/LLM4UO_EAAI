#!/usr/bin/env python3
"""Freeze the bounded generation-two VERA-Opt failure-driven update."""

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
from llm4or.vera_opt_evolution import (
    IMPLEMENTATION_ID, PROBLEM_ID, VERSION, public_failure_problem,
)
from llm4or.verified_skill_library import validate_skill_package


SOURCE = ROOT / "data/raw/optengine_20261004/test_data/canonical/canonical.jsonl"
SPLIT = ROOT / "experiments/vera_opt_generation1_split.json"
PARENT = ROOT / "experiments/vera_opt_generation1_candidate.json"
PROMOTION_PLAN = ROOT / "experiments/vera_opt_generation1_promotion_plan.json"
PROMOTION_REPORT = ROOT / "results/vera_opt_generation1_promotion.json"
PRIVATE = ROOT / "results/private/vera_opt_generation2_update_20261004"
PUBLIC = PRIVATE / "public_failure.json"
PLAN = ROOT / "experiments/vera_opt_generation2_update_plan.json"
AUTH = ROOT / "experiments/vera_opt_generation2_update_authorization.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if PLAN.exists() or AUTH.exists():
        raise ValueError("generation2_update_already_frozen")
    parent_value = json.loads(PARENT.read_text()); promotion = json.loads(PROMOTION_REPORT.read_text())
    promotion_plan = json.loads(PROMOTION_PLAN.read_text())
    compiler_sha = sha(ROOT / "llm4or/declarative_selection_compiler.py")
    parent = validate_skill_package(parent_value["skill"], {IMPLEMENTATION_ID: compiler_sha})
    if promotion["promotion_gate"]["promoted"] \
            or promotion["skill"]["abstained"] != 1 or promotion["comparison"]["regressions"] != 0:
        raise ValueError("unexpected_generation1_promotion_state")
    private_rows = json.loads((ROOT / promotion_plan["run_directory"] /
                               "promotion_private_rows.json").read_text())
    failures = [row for row in private_rows if not row["skill_adopted"]]
    if len(failures) != 1:
        raise ValueError("unexpected_structural_failure_count")
    failure_id = failures[0]["problem_id"]
    projection = json.loads((ROOT / promotion_plan["public_projection"]).read_text())
    public = next(row["public"] for row in projection["records"] if row["problem_id"] == failure_id)
    proposal_problem = public_failure_problem(public, parent, "trusted compiler failed closed")
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(PUBLIC, {
        "schema": "vera-opt-generation2-public-failure-v1",
        "contains_reference_answer": False, "source_problem_id": failure_id,
        "problem": proposal_problem,
    })
    frozen_names = [
        str(SOURCE.relative_to(ROOT)), str(SPLIT.relative_to(ROOT)), str(PARENT.relative_to(ROOT)),
        str(PROMOTION_PLAN.relative_to(ROOT)), str(PROMOTION_REPORT.relative_to(ROOT)),
        str(PUBLIC.relative_to(ROOT)), "llm4or/benchmark_inputs.py",
        "llm4or/codex_cli_gateway.py", "llm4or/declarative_selection_compiler.py",
        "llm4or/gateway.py", "llm4or/milp_schema.py", "llm4or/milp_solver.py",
        "llm4or/pipeline.py", "llm4or/run_interruption.py", "llm4or/schema.py",
        "llm4or/vera_opt_evolution.py", "llm4or/verified_skill_library.py",
        "scripts/run_vera_opt_generation2_update.py",
    ]
    codex = "/Applications/ChatGPT.app/Contents/Resources/codex"
    cli_version = subprocess.run([codex, "--version"], capture_output=True, text=True,
                                 check=True, timeout=15).stdout.strip()
    limits = {
        "max_completion_tokens": 4096, "max_input_bytes": 262144,
        "max_output_bytes": 1048576, "max_requests": 3,
        "max_total_reserved_or_reported_tokens": 2_000_000,
        "minimum_free_disk_bytes": 2 * 1024**3, "request_seconds": 600,
        "max_run_seconds": 7200, "token_overhead_reserve": 16384,
    }
    plan = {
        "schema": "vera-opt-generation2-update-plan-v1",
        "authorization_schema": "codex-cli-development-authorization-v1",
        "role": "failure_driven_typed_skill_update",
        "claim_guard": "Generation-two development only; final confirmation outcomes remain unopened.",
        "provider_mode": "existing_codex_login_chatgpt_quota_no_api_key_copy",
        "codex_cli": codex, "codex_cli_version": cli_version,
        "model": "gpt-6-luna", "reasoning_effort": "high",
        "gateway_version": GATEWAY_VERSION, "controller_version": VERSION,
        "compiler_version": COMPILER_VERSION,
        "scope_contract": {"prefix": "verag2", "method": "TypedPatch", "calls_per_scope": 1},
        "replicates": [79], "token_cap": 262144,
        "run_directory": str(PRIVATE.relative_to(ROOT)),
        "public_failure": str(PUBLIC.relative_to(ROOT)), "public_failure_sha256": sha(PUBLIC),
        "public_inputs": {PROBLEM_ID: payload_sha256(proposal_problem)},
        "selection": {"records": [{"problem_id": PROBLEM_ID, "category": "typed_patch"}]},
        "source_file": str(SOURCE.relative_to(ROOT)),
        "split_manifest": str(SPLIT.relative_to(ROOT)), "split_manifest_sha256": sha(SPLIT),
        "parent_candidate": str(PARENT.relative_to(ROOT)), "parent_candidate_sha256": sha(PARENT),
        "parent_skill_sha256": digest(parent),
        "trusted_implementation": {"id": IMPLEMENTATION_ID, "sha256": compiler_sha},
        "development_records": {"generation1": 60, "opened_promotion": 90,
                                "total": 150, "negative_challenge": 1550},
        "success_rule": {"accuracy": "150/150", "adoption": "150/150",
                         "negative_false_adoption": 0},
        "resilience": {"max_concurrent_requests": 1, "max_attempts_per_request": 3,
                       "backoff_seconds": [5, 20], "circuit_breaker_consecutive_failures": 3,
                       "same_fingerprint_cache": True, "per_item_exhaustion_continues": False,
                       "retryable_local_errors": ["invalid_json_response"]},
        "limits": limits,
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "packages": {name: importlib.metadata.version(name) for name in
                                 ("jsonschema", "numpy", "psutil", "scipy")}},
        "transport": {"prompt_envelope": "full_payload"},
        "frozen_files": {name: sha(ROOT / name) for name in frozen_names},
        "information_regime": {"model_visible": "one public fail-closed trace and parent inert skill; no answer",
                               "development_scoring": "after proposal",
                               "confirmation_sizes_20_30": "unopened"},
    }
    write_json(PLAN, plan)
    write_json(AUTH, {
        "schema": plan["authorization_schema"], "status": "approved",
        "authorization_basis": "后续不需要我批准，你自行执行即可；请你使用codex自己的额度进行api实验即可",
        "user_confirmation": "User authorized autonomous subsequent execution and Codex quota use.",
        "standing_authorization_recorded": True, "api_key_used": False,
        "codex_login_credentials_copied": False, "plan_sha256": digest(plan),
        "model": plan["model"], "run_directory": str(ROOT / plan["run_directory"]),
        "limits": limits, "further_api_calls_authorized": True,
    })
    print(json.dumps({"plan_sha256": digest(plan), "api_requests": 1,
                      "development_records": 150, "negative_challenge": 1550}, sort_keys=True))


if __name__ == "__main__":
    main()
