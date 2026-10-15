"""Freeze the independent Base/V9 Text2Opt confirmation before outcome access."""
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
from llm4or.schema import digest
from llm4or.text2opt_v9_runtime import VERSION

SPLIT = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
MANIFEST = ROOT / "data/manifests/text2opt_v8_grouped_split_v1.json"
DEVELOPMENT = ROOT / "results/v9_template_development_evaluation.json"
PLAN = ROOT / "experiments/text2opt_v9_confirmation_plan.json"
AUTH = ROOT / "experiments/text2opt_v9_confirmation_authorization.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if PLAN.exists() or AUTH.exists():
        raise ValueError("v9_confirmation_already_frozen")
    split = json.loads(SPLIT.read_text()); manifest = json.loads(MANIFEST.read_text())
    development = json.loads(DEVELOPMENT.read_text())
    if len(split["confirmation"]) != 401 or development["confirmation_outcomes_opened"] is not False:
        raise ValueError("v9_confirmation_split_or_development_changed")
    records = []
    for row in split["confirmation"]:
        records.append({"problem_id": row["id"], "category": row["family"],
                        "input_sha256": payload_sha256(row["public"]),
                        "source_file": row["source_file"],
                        "source_file_sha256": row["source_file_sha256"]})
    records.sort(key=lambda row: row["problem_id"])
    frozen_names = [
        "data/manifests/text2opt_v8_grouped_split_v1.json",
        "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json",
        "results/v9_template_development_evaluation.json",
        "llm4or/benchmark_inputs.py", "llm4or/codex_cli_gateway.py",
        "llm4or/confirmatory_statistics.py", "llm4or/formal_gateway.py",
        "llm4or/formal_runtime.py", "llm4or/gateway.py", "llm4or/milp_pipeline.py",
        "llm4or/milp_schema.py", "llm4or/milp_solver.py", "llm4or/pipeline.py",
        "llm4or/run_interruption.py", "llm4or/schema.py",
        "llm4or/text2opt_template_compiler.py", "llm4or/text2opt_v6_runtime.py",
        "llm4or/text2opt_v9_evaluation.py", "llm4or/text2opt_v9_runtime.py",
        "scripts/evaluate_text2opt_v9_confirmation.py", "scripts/run_text2opt_v9_confirmation.py",
    ]
    codex_cli = "/Applications/ChatGPT.app/Contents/Resources/codex"
    codex_version = subprocess.run([codex_cli, "--version"], capture_output=True, text=True,
                                   check=True).stdout.strip()
    plan = {
        "schema": "text2opt-v9-confirmation-plan-v1", "kind": "text2opt_v9_confirmation",
        "authorization_schema": "codex-cli-confirmation-authorization-v1",
        "run_directory": "results/private/text2opt_v9_confirmation_20261003",
        "claim_guard": (
            "Independent confirmation. No method, parser, solver, prompt, endpoint, scoring, category, "
            "denominator, or success-rule change is permitted after this freeze."
        ),
        "confirmation_outcomes_opened": False,
        "prepared_split": str(SPLIT.relative_to(ROOT)), "prepared_split_sha256": sha(SPLIT),
        "split_manifest_sha256": sha(MANIFEST), "development_evidence_sha256": sha(DEVELOPMENT),
        "provider_mode": "existing_codex_login_chatgpt_quota_no_api_key_copy",
        "codex_cli": codex_cli, "codex_cli_version": codex_version,
        "model": "gpt-6-luna", "reasoning_effort": "high",
        "gateway_version": GATEWAY_VERSION, "runtime_version": VERSION,
        "scope_contract": {"prefix": "v9confirm", "method": "BaseV9", "calls_per_scope": 1},
        "replicates": [29], "token_cap": 524288, "serial_canary_records": 1,
        "methods": {"Base": {"max_calls": 1},
                    "V9": {"max_calls": 1, "trusted_compiler_else_unchanged_base": True}},
        "matrix": {"records": 401, "unique_request_ceiling": 401,
                   "physical_attempt_ceiling_with_retries": 1203},
        "selection": {"records": records},
        "public_inputs": {row["id"]: payload_sha256(row["public"]) for row in split["confirmation"]},
        "endpoint": {"name": "benchmark formulation accuracy",
                     "definition": "optimal status and objective agreement with the published solver outcome",
                     "relative_tolerance": 1e-5, "absolute_tolerance": 1e-6},
        "success_rule": {
            "all_conditions_required": True, "paired_completion_rate": ">=0.99",
            "accuracy_delta": ">=0.05", "corrections": ">=10",
            "correction_regression_ratio": ">=4", "one_sided_exact_mcnemar_p": "<=0.05",
            "positive_categories": ">=4", "negative_categories": "<=1",
        },
        "resilience": {"max_concurrent_requests": 5, "max_attempts_per_request": 3,
                       "backoff_seconds": [5, 20], "circuit_breaker_consecutive_failures": 8,
                       "same_fingerprint_cache": True, "per_item_exhaustion_continues": True},
        "limits": {"max_completion_tokens": 32768, "max_input_bytes": 524288,
                   "max_output_bytes": 4194304, "max_requests": 1203,
                   "max_total_reserved_or_reported_tokens": 200000000,
                   "minimum_free_disk_bytes": 4294967296, "request_seconds": 600,
                   "max_run_seconds": 604800, "token_overhead_reserve": 131072},
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "packages": {name: importlib.metadata.version(name)
                                 for name in ("jsonschema", "numpy", "psutil", "scipy")}},
        "frozen_files": {name: sha(ROOT / name) for name in frozen_names},
        "cli_limit_note": (
            "The Codex CLI has no per-turn output-token hard stop. Every attempt is durably reserved; "
            "reported usage replaces the reservation and any overrun globally halts later dispatch."
        ),
        "outcome_access": {"references_model_visible": False, "gold_programs_executed": False,
                           "scoring_only_after_inference_complete": True},
    }
    PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    auth = {"schema": plan["authorization_schema"], "status": "pending",
            "plan_sha256": digest(plan), "model": plan["model"],
            "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
            "user_confirmation": None, "historical_authorizations_reused": False,
            "api_key_used": False, "codex_login_credentials_copied": False,
            "authorization_basis": "User authorized autonomous subsequent execution on 2026-10-03."}
    AUTH.write_text(json.dumps(auth, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"plan": str(PLAN.relative_to(ROOT)), "plan_sha256": digest(plan),
                      "authorization": str(AUTH.relative_to(ROOT)), "records": len(records),
                      "unique_requests": 401, "physical_attempt_ceiling": 1203}, sort_keys=True))


if __name__ == "__main__":
    main()
