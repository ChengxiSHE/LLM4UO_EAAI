#!/usr/bin/env python3
"""Freeze and authorize the bounded generation-one VERA-Opt proposal run."""

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

from llm4or.benchmark_inputs import payload_sha256
from llm4or.codex_cli_gateway import VERSION as GATEWAY_VERSION
from llm4or.declarative_selection_compiler import VERSION as COMPILER_VERSION
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.vera_opt_proposal import (
    IMPLEMENTATION_ID, PROBLEM_ID, VERSION, proposal_public_problem_from_questions,
)
from llm4or.vera_opt_repair import VERSION as REPAIR_VERSION


SPLIT = ROOT / "experiments/vera_opt_generation1_split.json"
SOURCE = ROOT / "data/raw/optengine_20261004/test_data/canonical/canonical.jsonl"
PRIVATE = ROOT / "results/private/vera_opt_generation1_proposal_20261004_v11"
PUBLIC_PROJECTION = PRIVATE / "public_projection.json"
PLAN = ROOT / "experiments/vera_opt_generation1_proposal_plan.json"
AUTH = ROOT / "experiments/vera_opt_generation1_proposal_authorization.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    split = json.loads(SPLIT.read_text())
    by_row = {record["source_row"]: record for record in split["records"]}
    records = []
    for line_number, line in enumerate(SOURCE.read_text().splitlines(), 1):
        meta = by_row.get(line_number)
        if meta is None:
            continue
        row = json.loads(line)
        if hashlib.sha256(row["question"].encode()).hexdigest() != meta["question_sha256"]:
            raise ValueError("question_hash_drift")
        records.append({"problem_id": meta["problem_id"], "question": row["question"]})
    if len(records) != len(by_row):
        raise ValueError("public_projection_incomplete")
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(PUBLIC_PROJECTION, {
        "schema": "vera-opt-public-question-projection-v1",
        "contains_answers": False,
        "records": records,
    })
    questions = {record["problem_id"]: record["question"] for record in records}
    public = proposal_public_problem_from_questions(questions, split)

    codex = "/Applications/ChatGPT.app/Contents/Resources/codex"
    cli_version = subprocess.run([codex, "--version"], capture_output=True, text=True,
                                 timeout=15, check=True).stdout.strip()
    compiler = ROOT / "llm4or/declarative_selection_compiler.py"
    frozen = {
        str(SPLIT.relative_to(ROOT)): sha(SPLIT),
        str(SOURCE.relative_to(ROOT)): sha(SOURCE),
        str(PUBLIC_PROJECTION.relative_to(ROOT)): sha(PUBLIC_PROJECTION),
        "llm4or/verified_skill_library.py": sha(ROOT / "llm4or/verified_skill_library.py"),
        "llm4or/declarative_selection_compiler.py": sha(compiler),
        "llm4or/vera_opt_proposal.py": sha(ROOT / "llm4or/vera_opt_proposal.py"),
        "llm4or/vera_opt_repair.py": sha(ROOT / "llm4or/vera_opt_repair.py"),
        "llm4or/codex_cli_gateway.py": sha(ROOT / "llm4or/codex_cli_gateway.py"),
        "scripts/run_vera_opt_generation1_proposal_v7.py": sha(
            ROOT / "scripts/run_vera_opt_generation1_proposal_v7.py"
        ),
    }
    limits = {
        "max_requests": 9,
        "max_total_reserved_or_reported_tokens": 3_000_000,
        "max_completion_tokens": 8192,
        "max_input_bytes": 1_048_576,
        "max_output_bytes": 1_048_576,
        "token_overhead_reserve": 16_384,
        "request_seconds": 600,
        "max_run_seconds": 10_800,
        "minimum_free_disk_bytes": 2 * 1024**3,
    }
    plan = {
        "schema": "vera-opt-generation1-proposal-plan-v11",
        "authorization_schema": "codex-cli-development-authorization-v1",
        "role": "development_only_automatic_declarative_skill_proposal",
        "claim_guard": "No promotion or confirmation answer is available to the proposer.",
        "provider_mode": "existing_codex_login_chatgpt_quota_no_api_key_copy",
        "codex_cli": codex,
        "codex_cli_version": cli_version,
        "model": "gpt-6-luna",
        "reasoning_effort": "high",
        "replicates": [71],
        "token_cap": 1_200_000,
        "trajectory_token_caps": [1_200_000],
        "run_directory": str(PRIVATE.relative_to(ROOT)),
        "source_file": str(SOURCE.relative_to(ROOT)),
        "split_manifest": str(SPLIT.relative_to(ROOT)),
        "split_manifest_sha256": sha(SPLIT),
        "public_projection": str(PUBLIC_PROJECTION.relative_to(ROOT)),
        "public_projection_sha256": sha(PUBLIC_PROJECTION),
        "public_inputs": {PROBLEM_ID: payload_sha256(public)},
        "selection": {"records": [{"problem_id": PROBLEM_ID, "family": "Knapsack"}]},
        "scope_contract": {"prefix": "verag1", "method": "SkillProposer", "calls_per_scope": 3},
        "transport": {"prompt_envelope": "full_payload"},
        "information_regime": {
            "proposal": "all 60 public development questions across sizes 5-10; no answers",
            "revision": "prior proposals plus static schema feedback; bounded outcome-blind literal repair uses public parse coverage only",
            "development_evaluation": "60 answers loaded only after all proposal requests complete",
            "promotion_and_confirmation": "unopened",
        },
        "trusted_implementation": {"id": IMPLEMENTATION_ID, "sha256": sha(compiler)},
        "proposal_controller_version": VERSION,
        "repair_controller_version": REPAIR_VERSION,
        "compiler_version": COMPILER_VERSION,
        "gateway_version": GATEWAY_VERSION,
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "packages": {name: importlib.metadata.version(name) for name in
                                 ("jsonschema", "numpy", "psutil", "scipy")}},
        "limits": limits,
        "resilience": {
            "max_attempts_per_request": 3,
            "backoff_seconds": [5, 20],
            "retryable_local_errors": ["invalid_json_response"],
            "circuit_breaker_consecutive_failures": 8,
            "max_concurrent_requests": 1,
            "per_item_exhaustion_continues": True,
            "same_fingerprint_cache": True,
        },
        "matrix": {"proposal_stages": 3, "development_records": 60,
                   "promotion_records_reserved": 90, "confirmation_records_reserved": 110,
                   "physical_attempt_ceiling": 9},
        "frozen_files": dict(sorted(frozen.items())),
    }
    write_json(PLAN, plan)
    write_json(AUTH, {
        "schema": plan["authorization_schema"],
        "status": "approved",
        "authorization_basis": "后续不需要我批准，你自行执行即可；请你使用codex自己的额度进行api实验即可",
        "user_confirmation": "User authorized autonomous subsequent execution and Codex quota use.",
        "standing_authorization_recorded": True,
        "api_key_used": False,
        "codex_login_credentials_copied": False,
        "plan_sha256": digest(plan),
        "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]),
        "limits": limits,
        "further_api_calls_authorized": True,
    })
    print(json.dumps({"plan_sha256": digest(plan), "proposal_stages": 3,
                      "development_records": 60}, sort_keys=True))


if __name__ == "__main__":
    main()
