#!/usr/bin/env python3
"""Freeze the 30-record official-BIND common-backbone development matrix."""

from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
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
from llm4or.gurobi_cli_solver import DEFAULT_BINARY, VERSION as SOLVER_VERSION
from llm4or.schema import digest


SPLIT = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
UPSTREAM = ROOT / "data/raw/text2opt_bench_20261003"
SOURCE_PLAN = ROOT / "experiments/text2opt_bind_development_pilot_gurobi_plan.json"
SOURCE_AUTH = ROOT / "experiments/text2opt_bind_development_pilot_gurobi_authorization.json"
PREPARED = ROOT / "data/prepared_benchmarks/text2opt_bind_development_matrix_v1.json"
PLAN = ROOT / "experiments/text2opt_bind_development_matrix_plan.json"
AUTH = ROOT / "experiments/text2opt_bind_development_matrix_authorization.json"
FAMILIES = (
    "disaster_response", "jssp", "modified_facility_location",
    "rcpsp", "transportation", "vrptw",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cache_binding(source_plan):
    source_db = ROOT / source_plan["run_directory"] / "requests.sqlite3"
    database = sqlite3.connect(source_db)
    database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            "SELECT key,charged,response_hash FROM requests WHERE status='complete' ORDER BY key"
        ).fetchall()
        physical = database.execute("SELECT count(*) FROM physical").fetchone()[0]
    finally:
        database.close()
    if len(rows) != 19 or physical != 0:
        raise ValueError("bind_development_matrix_cache_set_changed")
    return {
        "source_database": str(source_db.relative_to(ROOT)),
        "source_db_sha256": sha(source_db),
        "source_plan_sha256": digest(source_plan),
        "request_count": len(rows),
        "charged": sum(row["charged"] for row in rows),
        "entries": [dict(row) for row in rows],
    }


def main():
    if any(path.exists() for path in (PREPARED, PLAN, AUTH)):
        raise ValueError("bind_development_matrix_already_frozen")
    BindPromptSource.load(UPSTREAM)
    split = json.loads(SPLIT.read_text())
    selected = [row for row in split["development"] if row["family"] in FAMILIES]
    counts = Counter(row["family"] for row in selected)
    if len(selected) != 30 or counts != Counter({family: 5 for family in FAMILIES}):
        raise ValueError("bind_development_matrix_selection_changed")

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
    records.sort(key=lambda row: row["problem_id"])
    prepared = {
        "schema": "text2opt-bind-development-matrix-public-v1",
        "role": "development_only_outcomes_previously_exposed_no_confirmation_claim",
        "selection_used_outcomes": False,
        "selection_rule": "all 30 structured records in the frozen v8 development split",
        "upstream_commit": UPSTREAM_COMMIT,
        "records": records,
    }
    PREPARED.write_text(json.dumps(prepared, sort_keys=True, separators=(",", ":")) + "\n")

    source_plan = json.loads(SOURCE_PLAN.read_text())
    source_auth = json.loads(SOURCE_AUTH.read_text())
    if source_auth["status"] != "completed_development_pilot" or source_auth["plan_sha256"] != digest(source_plan):
        raise ValueError("bind_development_matrix_source_not_complete")
    cache = cache_binding(source_plan)
    codex_cli = "/Applications/ChatGPT.app/Contents/Resources/codex"
    codex_version = subprocess.run(
        [codex_cli, "--version"], capture_output=True, text=True, timeout=15, check=True,
    ).stdout.strip()
    solver_version = subprocess.run(
        [DEFAULT_BINARY, "--version"], capture_output=True, text=True, timeout=15, check=True,
    ).stdout.splitlines()[0].strip()
    frozen_names = [
        str(SPLIT.relative_to(ROOT)), str(PREPARED.relative_to(ROOT)),
        "llm4or/bind_official_adapter.py", "llm4or/bind_runtime.py",
        "llm4or/restricted_gurobi.py", "llm4or/external_code_adapter.py",
        "llm4or/codex_cli_gateway.py", "llm4or/milp_solver.py",
        "llm4or/gurobi_cli_solver.py", "scripts/run_bind_development_pilot.py",
        "scripts/audit_bind_prompt_adapter.py", "scripts/freeze_bind_development_matrix.py",
        "data/raw/text2opt_bench_20261003/main/evaluation/agentic_offload.py",
        "data/raw/text2opt_bench_20261003/main/evaluation/run_eval.py",
    ] + [row["source_file"] for row in records]
    plan = {
        "schema": "text2opt-bind-development-matrix-plan-v1",
        "authorization_schema": "codex-cli-development-authorization-v1",
        "run_directory": "results/private/text2opt_bind_development_matrix_20261003",
        "role": "development_only_no_independent_claim",
        "claim_guard": "Expanded official-prompt reproduction on the outcome-exposed development split only.",
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
        "replicates": [37], "token_cap": 2359296,
        "selection": {"records": [
            {"problem_id": row["problem_id"], "category": row["family"],
             "input_sha256": row["public_input_sha256"], "source_file": row["source_file"]}
            for row in records
        ]},
        "public_inputs": {row["problem_id"]: row["public_input_sha256"] for row in records},
        "matrix": {"records": 30, "unique_request_ceiling": 90,
                   "physical_attempt_ceiling_with_retries": 270},
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
                   "max_output_bytes": 4194304, "max_requests": 270,
                   "max_total_reserved_or_reported_tokens": 60000000,
                   "minimum_free_disk_bytes": 2147483648, "request_seconds": 600,
                   "max_run_seconds": 345600, "token_overhead_reserve": 131072},
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "packages": {name: importlib.metadata.version(name)
                                 for name in ("jsonschema", "numpy", "psutil", "scipy")}},
        "solver_backend": {
            "name": "gurobi_cli", "binary": DEFAULT_BINARY, "version": solver_version,
            "adapter_version": SOLVER_VERSION, "time_limit_seconds": 100,
            "threads": 1, "mip_gap": 0, "independent_primal_recheck": True,
        },
        "cache_import": cache,
        "expected_new_logical_request_ceiling": 72,
        "expected_new_physical_request_ceiling_with_retries": 216,
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
        "existing_academic_solver_license_only": True,
    }
    AUTH.write_text(json.dumps(authorization, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "plan_sha256": digest(plan), "records": len(records), "families": dict(sorted(counts.items())),
        "cache_import_requests": cache["request_count"],
        "expected_new_logical_request_ceiling": 72,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
