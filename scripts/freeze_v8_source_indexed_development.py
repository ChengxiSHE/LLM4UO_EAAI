"""Freeze the two-stage Codex-quota V8 development experiment."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.codex_cli_gateway import VERSION as GATEWAY_VERSION
from llm4or.schema import digest
from llm4or.source_indexed_runtime import VERSION


SPLIT = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
MANIFEST = ROOT / "data/manifests/text2opt_v8_grouped_split_v1.json"
EVALUATOR = ROOT / "data/next_development/text2opt_v8/evaluator.json"
PLAN = ROOT / "experiments/v8_source_indexed_development_plan.json"
AUTH = ROOT / "experiments/v8_source_indexed_development_authorization.json"
CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank(prefix, row):
    return hashlib.sha256((prefix + row["id"] + ":" + row["public_text_sha256"]).encode()).hexdigest()


def main():
    split = json.loads(SPLIT.read_text())
    manifest = json.loads(MANIFEST.read_text())
    if sha(SPLIT) != manifest["bindings"]["prepared_split_sha256"]:
        raise ValueError("v8_split_manifest_mismatch")
    development = split["development"]
    stage1_ids = set()
    resource = [row for row in development if row["family"] == "resource_allocation"]
    for stratum in sorted({row["stratum"] for row in resource}):
        stage1_ids.add(min(
            (row for row in resource if row["stratum"] == stratum),
            key=lambda row: rank("v8-stage1-resource:", row),
        )["id"])
    for family in sorted({row["family"] for row in development if row["family"] != "resource_allocation"}):
        stage1_ids.add(min(
            (row for row in development if row["family"] == family),
            key=lambda row: rank("v8-stage1-template:", row),
        )["id"])
    if len(stage1_ids) != 10:
        raise ValueError("v8_stage1_size")
    records = [{
        "problem_id": row["id"], "category": row["family"],
        "input_sha256": __import__("llm4or.benchmark_inputs", fromlist=["payload_sha256"]).payload_sha256(row["public"]),
        "public_text_sha256": row["public_text_sha256"],
        "source_file": row["source_file"], "source_file_sha256": row["source_file_sha256"],
        "batch": "stage1" if row["id"] in stage1_ids else "stage2",
    } for row in development]
    records.sort(key=lambda row: (row["batch"], row["category"], row["problem_id"]))
    frozen = [
        "data/manifests/text2opt_v8_grouped_split_v1.json",
        "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json",
        "data/next_development/text2opt_v8/evaluator.json",
        "llm4or/benchmark_inputs.py", "llm4or/codex_cli_gateway.py",
        "llm4or/confirmatory_statistics.py", "llm4or/contracts.py",
        "llm4or/formal_runtime.py", "llm4or/gateway.py", "llm4or/milp_contracts.py",
        "llm4or/milp_pipeline.py", "llm4or/milp_schema.py", "llm4or/milp_solver.py",
        "llm4or/run_interruption.py", "llm4or/schema.py", "llm4or/source_indexed_evaluation.py",
        "llm4or/source_indexed_model.py", "llm4or/source_indexed_runtime.py",
        "llm4or/text2opt_v6_runtime.py", "scripts/run_v8_source_indexed_development.py",
    ]
    limits = {
        "max_completion_tokens": 32768, "max_input_bytes": 524288, "max_output_bytes": 4194304,
        "token_overhead_reserve": 8192, "request_seconds": 600, "max_run_seconds": 604800,
        "minimum_free_disk_bytes": 4294967296, "max_requests": 420,
        "max_total_reserved_or_reported_tokens": 150000000,
    }
    plan = {
        "schema": "v8-source-indexed-development-plan-v1",
        "kind": "v8_source_indexed_development",
        "authorization_schema": "codex-cli-development-authorization-v1",
        "claim_guard": "Development only. Passing cannot be reported as independent confirmation.",
        "codex_cli": CODEX,
        "codex_cli_version": subprocess.run([CODEX, "--version"], capture_output=True, text=True, check=True).stdout.strip(),
        "model": "gpt-6-luna", "reasoning_effort": "high",
        "provider_mode": "existing_codex_login_chatgpt_quota_no_api_key_copy",
        "run_directory": "results/private/v8_source_indexed_development_20261003",
        "prepared_split": str(SPLIT.relative_to(ROOT)), "prepared_split_sha256": sha(SPLIT),
        "split_manifest_sha256": sha(MANIFEST),
        "development_evaluator": str(EVALUATOR.relative_to(ROOT)),
        "development_evaluator_sha256": sha(EVALUATOR),
        "development_outcomes_opened_only_after_split_freeze": True,
        "confirmation_outcomes_opened": False,
        "runtime_version": VERSION, "gateway_version": GATEWAY_VERSION,
        "runtime": {
            "python": platform.python_version(), "machine": platform.machine(),
            "packages": {name: importlib.metadata.version(name) for name in ("jsonschema", "numpy", "psutil", "scipy")},
        },
        "methods": {"IndexedProbe": {"max_calls": 2}},
        "replicates": [17], "token_cap": 524288, "trajectory_token_caps": [524288],
        "selection": {
            "problem_count": len(records), "stage1_count": len(stage1_ids),
            "stage2_count": len(records)-len(stage1_ids), "family_count": len({row["category"] for row in records}),
            "labels_used_for_selection": False, "records": records,
        },
        "public_inputs": {row["problem_id"]: row["input_sha256"] for row in records},
        "stage1_gate": {
            "paired_completion_rate": ">=0.90", "source_indexed_accepted": ">=5",
            "corrections": ">=2", "regressions": "<=1", "net_corrections": ">=1",
            "correcting_categories": ">=1", "stage2_if_and_only_if_all_pass": True,
        },
        "final_development_gate": {
            "paired_completion_rate": ">=0.95", "source_indexed_acceptance_rate": ">=0.50",
            "accuracy_delta": ">=0.03", "corrections": ">=5", "regressions": "<=2",
            "correction_regression_ratio": ">=2", "one_sided_exact_p": "<=0.10",
            "positive_categories": ">=2", "negative_categories": "<=1",
        },
        "matrix": {
            "inference_cells": len(records), "unique_request_ceiling": len(records)*2,
            "physical_attempt_ceiling_with_retries": len(records)*2*3,
        },
        "limits": limits,
        "resilience": {
            "max_attempts_per_request": 3, "backoff_seconds": [5, 20],
            "circuit_breaker_consecutive_failures": 8, "max_concurrent_requests": 5,
            "same_fingerprint_cache": True, "per_item_exhaustion_continues": True,
        },
        "cli_limit_note": (
            "The Codex CLI does not expose a per-turn output-token hard stop. The ledger reserves the frozen "
            "completion allowance before each call, records reported usage when available, and stops before later "
            "calls at the global ceiling; a single provider turn could exceed its reservation."
        ),
        "frozen_files": {name: sha(ROOT / name) for name in frozen},
    }
    PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"], "status": "pending",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": limits,
        "user_confirmation": None, "historical_authorizations_reused": False,
        "api_key_used": False, "codex_login_credentials_copied": False,
    }
    AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "plan": str(PLAN.relative_to(ROOT)), "plan_sha256": digest(plan),
        "authorization": str(AUTH.relative_to(ROOT)), "stage1_calls": len(stage1_ids)*2,
        "conditional_total_unique_calls": len(records)*2,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
