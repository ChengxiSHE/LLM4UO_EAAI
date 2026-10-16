#!/usr/bin/env python3
"""Freeze a post-lock, infrastructure-only completion sensitivity run."""

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
from llm4or.vera_opt_confirmation_evaluation import VERSION as EVALUATION_VERSION
from llm4or.vera_opt_promotion_runtime import VERSION as RUNTIME_VERSION


ORIGINAL_PLAN = ROOT / "experiments/vera_opt_generation2_confirmation_plan.json"
ORIGINAL_REPORT = ROOT / "results/vera_opt_generation2_confirmation.json"
PLAN = ROOT / "experiments/vera_opt_generation2_infrastructure_recovery_plan.json"
AUTH = ROOT / "experiments/vera_opt_generation2_infrastructure_recovery_authorization.json"
PRIVATE = ROOT / "results/private/vera_opt_generation2_infrastructure_recovery_20261004"
PUBLIC = PRIVATE / "public_projection.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if PLAN.exists() or AUTH.exists():
        raise ValueError("recovery_already_frozen")
    original = json.loads(ORIGINAL_PLAN.read_text()); report = json.loads(ORIGINAL_REPORT.read_text())
    old_directory = ROOT / original["run_directory"]
    private_rows = json.loads((old_directory / "confirmation_private_rows.json").read_text())
    selected_ids = sorted(row["problem_id"] for row in private_rows
                          if row["infrastructure"]["Base"] is True)
    if len(selected_ids) != 3 or report["comparison"]["paired_infrastructure_unavailable"] != 3:
        raise ValueError("unexpected_infrastructure_selection")
    old_public = json.loads((ROOT / original["public_projection"]).read_text())
    records = [row for row in old_public["records"] if row["problem_id"] in selected_ids]
    if len(records) != 3:
        raise ValueError("recovery_public_missing")
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(PUBLIC, {"schema": "vera-opt-infrastructure-recovery-public-v1",
                        "contains_answers": False, "records": records})
    selection_index = {row["problem_id"]: row for row in original["selection"]["records"]}
    frozen_names = [
        str(ORIGINAL_PLAN.relative_to(ROOT)), str(ORIGINAL_REPORT.relative_to(ROOT)),
        str(PUBLIC.relative_to(ROOT)), original["candidate_file"], original["split_manifest"],
        original["source_file"], "llm4or/benchmark_inputs.py", "llm4or/codex_cli_gateway.py",
        "llm4or/declarative_selection_compiler.py", "llm4or/formal_runtime.py",
        "llm4or/gateway.py", "llm4or/milp_schema.py", "llm4or/milp_solver.py",
        "llm4or/pipeline.py", "llm4or/run_interruption.py", "llm4or/schema.py",
        "llm4or/text2opt_v6_runtime.py", "llm4or/text2opt_v9_runtime.py",
        "llm4or/vera_opt_confirmation_evaluation.py", "llm4or/vera_opt_promotion_evaluation.py",
        "llm4or/vera_opt_promotion_runtime.py", "llm4or/verified_skill_library.py",
        "scripts/evaluate_vera_opt_generation2_infrastructure_recovery.py",
        "scripts/run_vera_opt_generation2_infrastructure_recovery.py",
    ]
    codex = original["codex_cli"]
    cli_version = subprocess.run([codex, "--version"], capture_output=True, text=True,
                                 check=True, timeout=15).stdout.strip()
    limits = {"max_completion_tokens": 32768, "max_input_bytes": 524288,
              "max_output_bytes": 4194304, "max_requests": 9,
              "max_total_reserved_or_reported_tokens": 8_000_000,
              "minimum_free_disk_bytes": 2 * 1024**3, "request_seconds": 600,
              "max_run_seconds": 21600, "token_overhead_reserve": 131072}
    plan = {
        "schema": "vera-opt-generation2-infrastructure-recovery-plan-v1",
        "authorization_schema": "codex-cli-sensitivity-authorization-v1",
        "role": "post_lock_infrastructure_only_sensitivity",
        "claim_guard": "Not the preregistered primary confirmation; selection uses infrastructure flag only.",
        "provider_mode": original["provider_mode"], "codex_cli": codex,
        "codex_cli_version": cli_version, "model": original["model"],
        "reasoning_effort": original["reasoning_effort"], "gateway_version": GATEWAY_VERSION,
        "runtime_version": RUNTIME_VERSION, "evaluation_version": EVALUATION_VERSION,
        "compiler_version": COMPILER_VERSION,
        "scope_contract": {"prefix": "verag2recovery", "method": "BaseVERA",
                           "calls_per_scope": 1},
        "replicates": original["replicates"], "token_cap": original["token_cap"],
        "serial_canary_records": 0, "run_directory": str(PRIVATE.relative_to(ROOT)),
        "public_projection": str(PUBLIC.relative_to(ROOT)),
        "public_projection_sha256": sha(PUBLIC),
        "source_file": original["source_file"], "split_manifest": original["split_manifest"],
        "split_manifest_sha256": original["split_manifest_sha256"],
        "candidate_file": original["candidate_file"], "candidate_sha256": original["candidate_sha256"],
        "skill_sha256": original["skill_sha256"],
        "trusted_implementation": original["trusted_implementation"],
        "original_plan": str(ORIGINAL_PLAN.relative_to(ROOT)),
        "original_plan_sha256": digest(original),
        "original_report": str(ORIGINAL_REPORT.relative_to(ROOT)),
        "original_report_sha256": sha(ORIGINAL_REPORT),
        "original_run_directory": original["run_directory"],
        "selection_rule": "Base infrastructure_unavailable is true; correctness was not used",
        "selection": {"records": [selection_index[problem_id] for problem_id in selected_ids]},
        "public_inputs": {row["problem_id"]: payload_sha256(row["public"]) for row in records},
        "alpha_spend": original["alpha_spend"], "success_rule": original["success_rule"],
        "resilience": {"max_concurrent_requests": 3, "max_attempts_per_request": 3,
                       "backoff_seconds": [5, 20], "circuit_breaker_consecutive_failures": 8,
                       "same_fingerprint_cache": True, "per_item_exhaustion_continues": True,
                       "retryable_local_errors": ["invalid_json_response"]},
        "limits": limits,
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "packages": {name: importlib.metadata.version(name) for name in
                                 ("jsonschema", "numpy", "psutil", "scipy")}},
        "transport": {"prompt_envelope": "full_payload"},
        "frozen_files": {name: sha(ROOT / name) for name in frozen_names},
        "outcome_access": {"primary_outcomes_already_open": True,
                           "references_model_visible": False,
                           "selection_uses_correctness": False},
    }
    write_json(PLAN, plan)
    write_json(AUTH, {"schema": plan["authorization_schema"], "status": "approved",
        "authorization_basis": "后续不需要我批准，你自行执行即可；请你使用codex自己的额度进行api实验即可",
        "user_confirmation": "User authorized autonomous subsequent execution and Codex quota use.",
        "standing_authorization_recorded": True, "api_key_used": False,
        "codex_login_credentials_copied": False, "plan_sha256": digest(plan),
        "model": plan["model"], "run_directory": str(ROOT / plan["run_directory"]),
        "limits": limits, "further_api_calls_authorized": True})
    print(json.dumps({"plan_sha256": digest(plan), "records": 3,
                      "selection_rule": plan["selection_rule"]}, sort_keys=True))


if __name__ == "__main__":
    main()
