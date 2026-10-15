#!/usr/bin/env python3
"""Freeze the six-family common-input CoE development pilot."""

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

from llm4or.benchmark_inputs import payload_sha256, validate_public_input
from llm4or.coe_runtime import VERSION
from llm4or.codex_cli_gateway import VERSION as GATEWAY_VERSION
from llm4or.gurobi_cli_solver import VERSION as GUROBI_VERSION
from llm4or.pipeline import write_json
from llm4or.schema import digest


SOURCE = ROOT / "data/prepared_benchmarks/text2opt_bind_development_pilot_v1.json"
PREPARED = ROOT / "data/prepared_benchmarks/coe_common_development_pilot_v1.json"
PLAN = ROOT / "experiments/coe_common_development_pilot_plan.json"
AUTH = ROOT / "experiments/coe_common_development_pilot_authorization.json"
SKELETON = '''def solve_problem():
    """Solve the exact numeric optimization instance in the description.

    Returns:
        objective_value: the optimal objective value as a single int or float
    """
    objective_value = 0
    return objective_value
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = json.loads(SOURCE.read_text())
    records = []
    for snapshot in ("paper", "current"):
        for row in source["records"]:
            suffix = row["problem_id"].removeprefix("text2opt_")
            public_id = f"coec_{snapshot}_{suffix}"
            public = dict(row["public"])
            public["id"] = public_id
            public = validate_public_input(public)
            records.append({
                "problem_id": public_id,
                "source_problem_id": row["problem_id"],
                "family": row["family"],
                "snapshot": snapshot,
                "public": public,
                "public_input_sha256": payload_sha256(public),
                "source_file": row["source_file"],
                "source_file_sha256": row["source_file_sha256"],
                "code_example": SKELETON,
                "code_example_sha256": hashlib.sha256(SKELETON.encode()).hexdigest(),
            })
    prepared = {
        "schema": "coe-common-development-pilot-data-v1",
        "role": "development_common_input_adapter",
        "selection_rule": "same frozen one-per-family records as the BIND adapter pilot",
        "selection_used_outcomes": False,
        "code_example_policy": "one generic no-answer zero-argument scalar-objective skeleton",
        "records": records,
    }
    write_json(PREPARED, prepared)

    codex = "/Applications/ChatGPT.app/Contents/Resources/codex"
    cli_version = subprocess.run([codex, "--version"], capture_output=True, text=True,
                                 timeout=15, check=True).stdout.strip()
    binary = "/usr/local/bin/gurobi_cl"
    solver_version = subprocess.run([binary, "--version"], capture_output=True, text=True,
                                    timeout=15, check=True).stdout.splitlines()[0].strip()
    frozen = {
        str(PREPARED.relative_to(ROOT)): sha(PREPARED),
        "llm4or/coe_official_adapter.py": sha(ROOT / "llm4or/coe_official_adapter.py"),
        "llm4or/coe_runtime.py": sha(ROOT / "llm4or/coe_runtime.py"),
        "llm4or/codex_cli_gateway.py": sha(ROOT / "llm4or/codex_cli_gateway.py"),
        "llm4or/external_code_adapter.py": sha(ROOT / "llm4or/external_code_adapter.py"),
        "llm4or/restricted_gurobi.py": sha(ROOT / "llm4or/restricted_gurobi.py"),
        "llm4or/gurobi_cli_solver.py": sha(ROOT / "llm4or/gurobi_cli_solver.py"),
        "scripts/run_coe_common_development_pilot.py": sha(ROOT / "scripts/run_coe_common_development_pilot.py"),
    }
    for row in records:
        frozen[row["source_file"]] = sha(ROOT / row["source_file"])
    limits = {
        "max_requests": 396, "max_total_reserved_or_reported_tokens": 20_000_000,
        "max_completion_tokens": 8192, "max_input_bytes": 1048576,
        "max_output_bytes": 1048576, "token_overhead_reserve": 16384,
        "request_seconds": 600, "max_run_seconds": 172800,
        "minimum_free_disk_bytes": 2 * 1024**3,
    }
    plan = {
        "schema": "coe-common-development-pilot-plan-v1",
        "authorization_schema": "codex-cli-development-authorization-v1",
        "role": "development_only_no_independent_claim",
        "claim_guard": "Six outcome-exposed adapter records; no confirmatory superiority claim.",
        "provider_mode": "existing_codex_login_chatgpt_quota_no_api_key_copy",
        "codex_cli": codex, "codex_cli_version": cli_version,
        "model": "gpt-6-luna", "reasoning_effort": "high",
        "temperature_deviation": "Codex CLI has no exposed temperature-zero flag",
        "replicates": [43], "token_cap": 1048576, "trajectory_token_caps": [1048576],
        "run_directory": "results/private/coe_common_development_pilot_20261004",
        "prepared_data": str(PREPARED.relative_to(ROOT)), "prepared_data_sha256": sha(PREPARED),
        "public_inputs": {row["problem_id"]: row["public_input_sha256"] for row in records},
        "selection": {"records": [
            {key: row[key] for key in ("problem_id", "source_problem_id", "family", "snapshot", "source_file")}
            for row in records
        ]},
        "scope_contract": {"prefix": "coecdev", "method": "CoE", "calls_per_scope": 11},
        "settings": {"max_collaborations": 5, "reflection": False, "rng_seed": 0,
                     "paper_hash_seed": "0"},
        "transport": {"prompt_envelope": "official_text_wrapper"},
        "generated_code_policy": "never_execute_bounded_ast_plus_trusted_milp_solver",
        "information_regime": {
            "inference": "full public prose including numeric annex plus generic code skeleton",
            "reference": "official Text2Opt objective loaded after durable reducer response",
            "structured_instance_data": False,
        },
        "upstream": {"repository": "https://github.com/xzymustbexzy/Chain-of-Experts",
                     "paper_commit": "9d96bcc2f067177eb0e122b1aae8227748dc6830",
                     "current_commit": "afb89bf602690ea621f13a23c42722f20f653a43",
                     "license": "not_found"},
        "solver_backend": {"name": "gurobi_cli", "binary": binary, "version": solver_version,
                           "adapter_version": GUROBI_VERSION, "threads": 1, "time_limit": 100},
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "packages": {name: importlib.metadata.version(name) for name in
                                 ("jsonschema", "numpy", "psutil", "scipy")}},
        "runtime_version": VERSION, "gateway_version": GATEWAY_VERSION,
        "limits": limits,
        "resilience": {"max_attempts_per_request": 3, "backoff_seconds": [5, 20],
                       "retryable_local_errors": ["invalid_json_response"],
                       "circuit_breaker_consecutive_failures": 8,
                       "max_concurrent_requests": 1, "per_item_exhaustion_continues": True,
                       "same_fingerprint_cache": True},
        "matrix": {"records": len(records), "unique_request_ceiling": 132,
                   "physical_attempt_ceiling_with_retries": 396},
        "frozen_files": dict(sorted(frozen.items())),
    }
    write_json(PLAN, plan)
    write_json(AUTH, {
        "schema": plan["authorization_schema"], "status": "approved",
        "authorization_basis": "后续不需要我批准，你自行执行即可；请你使用codex自己的额度进行api实验即可",
        "user_confirmation": "User authorized autonomous subsequent execution and Codex quota use.",
        "historical_authorizations_reused": False, "api_key_used": False,
        "codex_login_credentials_copied": False, "plan_sha256": digest(plan),
        "model": plan["model"], "run_directory": str(ROOT / plan["run_directory"]),
        "limits": limits, "further_api_calls_authorized": True,
    })
    print(json.dumps({"plan_sha256": digest(plan), "records": len(records),
                      "unique_requests": 132}, sort_keys=True))


if __name__ == "__main__":
    main()
