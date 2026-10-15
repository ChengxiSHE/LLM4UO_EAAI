"""Freeze the paid Base/V6 Text2Opt confirmation run."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_inputs import payload_sha256
from llm4or.formal_provider import BASE_URL, MODEL, PROFILE
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.text2opt_v6_runtime import VERSION

PLAN = ROOT / "experiments/text2opt_v6_confirmation_run_plan.json"
AUTH = ROOT / "experiments/text2opt_v6_confirmation_run_authorization.json"
PROTOCOL = ROOT / "experiments/text2opt_v6_confirmation_protocol.json"
RESOURCE = ROOT / "data/prepared_benchmarks/text2opt_resource_allocation_v1.json"
TEMPLATE = ROOT / "data/prepared_benchmarks/text2opt_template_confirmation_v1.json"
FILES = [
    "experiments/text2opt_v6_confirmation_protocol.json",
    "data/manifests/text2opt_resource_allocation_v1.json",
    "data/manifests/text2opt_template_confirmation_v1.json",
    "llm4or/benchmark_inputs.py",
    "llm4or/confirmatory_statistics.py",
    "llm4or/formal_gateway.py",
    "llm4or/formal_provider.py",
    "llm4or/formal_runtime.py",
    "llm4or/milp_contracts.py",
    "llm4or/milp_pipeline.py",
    "llm4or/milp_schema.py",
    "llm4or/milp_solver.py",
    "llm4or/run_interruption.py",
    "llm4or/schema.py",
    "llm4or/semantic_contracts.py",
    "llm4or/semantic_contracts_v2.py",
    "llm4or/text2opt_v6_evaluation.py",
    "llm4or/text2opt_v6_runtime.py",
    "scripts/approve_text2opt_v6_confirmation.py",
    "scripts/evaluate_text2opt_v6_confirmation.py",
    "scripts/freeze_text2opt_v6_confirmation_protocol.py",
    "scripts/freeze_text2opt_v6_confirmation_run.py",
    "scripts/run_text2opt_v6_confirmation.py",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_selection():
    resource = json.loads(RESOURCE.read_text())
    template = json.loads(TEMPLATE.read_text())
    rows = []
    for row in resource["confirmation"]:
        rows.append({
            "problem_id": row["id"], "category": "resource_allocation",
            "input_sha256": payload_sha256(row["public"]),
            "source_file": row["source_file"], "source_file_sha256": row["source_file_sha256"],
        })
    for row in template["confirmation"]:
        rows.append({
            "problem_id": row["id"], "category": row["family"],
            "input_sha256": payload_sha256(row["public"]),
            "source_file": row["source_file"], "source_file_sha256": row["source_file_sha256"],
        })
    rows.sort(key=lambda row: (row["category"], row["problem_id"]))
    categories = sorted({row["category"] for row in rows})
    if len(rows) != 431 or len({row["problem_id"] for row in rows}) != 431 or len(categories) != 7:
        raise ValueError("text2opt_v6_selection_changed")
    return rows, categories


def freeze():
    if PLAN.exists() or AUTH.exists():
        raise ValueError("text2opt_v6_run_already_frozen")
    protocol = json.loads(PROTOCOL.read_text())
    if protocol.get("status") != "input_statistics_and_v6_method_frozen":
        raise ValueError("text2opt_v6_protocol_not_frozen")
    for name, expected in protocol["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("text2opt_v6_protocol_file_changed:" + name)
    rows, categories = build_selection()
    unique = len(rows)
    plan = {
        "schema": "text2opt-v6-confirmation-run-plan-v1",
        "kind": "text2opt_v6_confirmation",
        "status": "pending_user_authorization",
        "authorization_schema": "text2opt-v6-confirmation-run-authorization-v1",
        "runtime_version": VERSION,
        "run_directory": "results/private/text2opt_v6_confirmation_20261003",
        "endpoint": BASE_URL,
        "model": MODEL,
        "credential_profile": str(PROFILE),
        "selection": {"records": rows, "problem_count": len(rows), "categories": categories},
        "public_inputs": {row["problem_id"]: row["input_sha256"] for row in rows},
        "methods": {"Probe": {"max_calls": 1}},
        "reported_ablations": ["Base", "V6"],
        "replicates": [17],
        "token_cap": 131072,
        "trajectory_token_caps": [131072],
        "progress_stage": "text2optv6",
        "limits": {
            "max_requests": unique * 3,
            "max_total_reserved_or_reported_tokens": 100000000,
            "max_completion_tokens": 16384,
            "max_input_bytes": 262144,
            "max_output_bytes": 262144,
            "token_overhead_reserve": 4096,
            "request_seconds": 90,
            "max_run_seconds": 604800,
            "minimum_free_disk_bytes": 4294967296,
        },
        "resilience": {
            "max_attempts_per_request": 3,
            "backoff_seconds": [5, 20],
            "circuit_breaker_consecutive_failures": 8,
            "max_concurrent_requests": 5,
        },
        "matrix": {
            "inference_cells": len(rows),
            "unique_request_ceiling_without_retries": unique,
            "physical_attempt_ceiling_with_retries": unique * 3,
        },
        "evaluation": {
            "protocol_sha256": digest(protocol),
            "v7_stage1_result_sha256": protocol["method_selection"]["v7_stage1_result_sha256"],
            "text2opt_outcomes_read_while_freezing": False,
            "scoring_after_all_inference_checkpoints": True,
        },
        "prepared_snapshots": {
            str(RESOURCE.relative_to(ROOT)): sha(RESOURCE),
            str(TEMPLATE.relative_to(ROOT)): sha(TEMPLATE),
        },
        "frozen_files": {name: sha(ROOT / name) for name in FILES},
        "runtime": {
            "python": platform.python_version(), "machine": platform.machine(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "jsonschema", "psutil")
            },
        },
        "claim_guard": (
            "Untouched external V6 confirmation. No method, prompt, endpoint, scoring, category, denominator, "
            "or success-rule change is permitted after this freeze."
        ),
        "cost_note": (
            "Hard ceilings: 431 unique requests, 1,293 physical attempts including retries, and "
            "100,000,000 reserved-or-reported tokens. Provider fiat pricing is unknown."
        ),
    }
    write_json(PLAN, plan)
    write_json(AUTH, {
        "schema": plan["authorization_schema"], "status": "pending",
        "plan_sha256": digest(plan), "endpoint": plan["endpoint"], "model": plan["model"],
        "run_directory": str(ROOT / plan["run_directory"]), "limits": plan["limits"],
        "user_confirmation": None, "historical_authorizations_reused": False,
    })
    return {
        "status": "frozen_pending_user_authorization", "plan_sha256": digest(plan),
        "records": len(rows), "categories": len(categories), "unique_requests": unique,
        "physical_attempt_ceiling": unique * 3,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection-preflight", action="store_true")
    args = parser.parse_args()
    if args.selection_preflight:
        rows, categories = build_selection()
        print(json.dumps({"records": len(rows), "categories": categories,
                          "outcomes_read": False, "api_requests": 0}, sort_keys=True))
        return
    print(json.dumps(freeze(), sort_keys=True))


if __name__ == "__main__":
    main()
