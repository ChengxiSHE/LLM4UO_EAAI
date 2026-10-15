#!/usr/bin/env python3
"""Freeze a six-family official-BIND common-backbone development pilot."""

from collections import defaultdict
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
from llm4or.bind_official_adapter import (
    BindPromptSource, UPSTREAM_AGENTIC_SHA256, UPSTREAM_COMMIT, UPSTREAM_RUNNER_SHA256,
)
from llm4or.bind_runtime import VERSION, public_bind_projection
from llm4or.codex_cli_gateway import VERSION as GATEWAY_VERSION
from llm4or.schema import digest


SPLIT = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
UPSTREAM = ROOT / "data/raw/text2opt_bench_20261003"
PREPARED = ROOT / "data/prepared_benchmarks/text2opt_bind_development_pilot_v1.json"
PLAN = ROOT / "experiments/text2opt_bind_development_pilot_plan.json"
AUTH = ROOT / "experiments/text2opt_bind_development_pilot_authorization.json"
FAMILIES = (
    "disaster_response", "jssp", "modified_facility_location",
    "rcpsp", "transportation", "vrptw",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank(row):
    return hashlib.sha256(("bind-development-pilot-v1:" + row["id"] + ":" +
                           row["public_text_sha256"]).encode()).hexdigest()


def main():
    if any(path.exists() for path in (PREPARED, PLAN, AUTH)):
        raise ValueError("bind_development_pilot_already_frozen")
    BindPromptSource.load(UPSTREAM)
    split = json.loads(SPLIT.read_text())
    groups = defaultdict(list)
    for row in split["development"]:
        if row["family"] in FAMILIES:
            groups[row["family"]].append(row)
    selected = [min(groups[family], key=rank) for family in FAMILIES]
    records = []
    for row in selected:
        source = UPSTREAM / row["source_file"]
        if sha(source) != row["source_file_sha256"]:
            raise ValueError("bind_source_record_changed:" + row["id"])
        upstream_problem = json.loads(source.read_text())
        records.append({
            "problem_id": row["id"], "family": row["family"],
            "public": row["public"], "public_input_sha256": payload_sha256(row["public"]),
            "bind_public": public_bind_projection(upstream_problem),
            "source_file": str(source.relative_to(ROOT)),
            "source_file_sha256": row["source_file_sha256"],
        })
    prepared = {
        "schema": "text2opt-bind-development-pilot-public-v1",
        "role": "development_only_outcomes_previously_exposed_no_confirmation_claim",
        "selection_used_outcomes": False,
        "selection_rule": "one existing development record per retained template family by salted public hash",
        "upstream_commit": UPSTREAM_COMMIT,
        "records": sorted(records, key=lambda row: row["problem_id"]),
    }
    PREPARED.write_text(json.dumps(prepared, sort_keys=True, separators=(",", ":")) + "\n")
    codex_cli = "/Applications/ChatGPT.app/Contents/Resources/codex"
    codex_version = subprocess.run(
        [codex_cli, "--version"], capture_output=True, text=True, timeout=15, check=True,
    ).stdout.strip()
    frozen_names = [
        str(SPLIT.relative_to(ROOT)), str(PREPARED.relative_to(ROOT)),
        "llm4or/bind_official_adapter.py", "llm4or/bind_runtime.py",
        "llm4or/restricted_gurobi.py", "llm4or/external_code_adapter.py",
        "llm4or/codex_cli_gateway.py", "llm4or/milp_solver.py",
        "scripts/run_bind_development_pilot.py", "scripts/audit_bind_prompt_adapter.py",
        "data/raw/text2opt_bench_20261003/main/evaluation/agentic_offload.py",
        "data/raw/text2opt_bench_20261003/main/evaluation/run_eval.py",
    ] + [row["source_file"] for row in records]
    plan = {
        "schema": "text2opt-bind-development-pilot-plan-v1",
        "authorization_schema": "codex-cli-development-authorization-v1",
        "run_directory": "results/private/text2opt_bind_development_pilot_20261003",
        "role": "development_only_no_independent_claim",
        "claim_guard": "Adapter and failure-mode pilot only; no confirmatory superiority claim.",
        "prepared_data": str(PREPARED.relative_to(ROOT)),
        "prepared_data_sha256": sha(PREPARED),
        "upstream": {
            "repository": "https://github.com/SprocketLab/text2opt-bench",
            "commit": UPSTREAM_COMMIT,
            "agentic_source_sha256": UPSTREAM_AGENTIC_SHA256,
            "runner_source_sha256": UPSTREAM_RUNNER_SHA256,
            "method": "instance_data oracle-guided repair", "maximum_rounds": 3,
        },
        "provider_mode": "existing_codex_login_chatgpt_quota_no_api_key_copy",
        "codex_cli": codex_cli, "codex_cli_version": codex_version,
        "model": "gpt-6-luna", "reasoning_effort": "high",
        "gateway_version": GATEWAY_VERSION, "runtime_version": VERSION,
        "scope_contract": {"prefix": "binddev", "method": "BIND", "calls_per_scope": 3},
        "replicates": [37], "token_cap": 786432,
        "selection": {"records": [
            {"problem_id": row["problem_id"], "category": row["family"],
             "input_sha256": row["public_input_sha256"], "source_file": row["source_file"]}
            for row in records
        ]},
        "public_inputs": {row["problem_id"]: row["public_input_sha256"] for row in records},
        "matrix": {"records": 6, "unique_request_ceiling": 18,
                   "physical_attempt_ceiling_with_retries": 54},
        "endpoint": {"definition": "official optimal-status and objective match",
                     "relative_tolerance": 1e-5, "absolute_tolerance": 1e-6},
        "information_regime": {
            "round_1": "official instance-data prompt; no reference outcome",
            "rounds_2_3": "official oracle feedback including expected objective/status/structure",
            "reference_loader_boundary": "after durable response checkpoint",
        },
        "generated_code_policy": "never_execute_translate_whitelisted_ast_to_milp_v1",
        "resilience": {"max_concurrent_requests": 1, "max_attempts_per_request": 3,
                       "backoff_seconds": [5, 20], "circuit_breaker_consecutive_failures": 8,
                       "same_fingerprint_cache": True, "per_item_exhaustion_continues": True},
        "limits": {"max_completion_tokens": 32768, "max_input_bytes": 1048576,
                   "max_output_bytes": 4194304, "max_requests": 54,
                   "max_total_reserved_or_reported_tokens": 20000000,
                   "minimum_free_disk_bytes": 2147483648, "request_seconds": 600,
                   "max_run_seconds": 172800, "token_overhead_reserve": 131072},
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "packages": {name: importlib.metadata.version(name)
                                 for name in ("jsonschema", "numpy", "psutil", "scipy")}},
        "frozen_files": {name: sha(ROOT / name) for name in frozen_names},
    }
    PLAN.write_text(json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
    authorization = {
        "schema": plan["authorization_schema"], "status": "approved",
        "plan_sha256": digest(plan), "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": "User authorized autonomous subsequent execution on 2026-10-03.",
        "authorization_basis": "后续不需要我批准，你自行执行即可",
        "api_key_used": False, "codex_login_credentials_copied": False,
        "historical_authorizations_reused": False,
    }
    AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "plan_sha256": digest(plan), "records": len(records),
        "families": [row["family"] for row in records],
        "unique_request_ceiling": 18, "physical_attempt_ceiling": 54,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
