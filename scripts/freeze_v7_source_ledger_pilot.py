"""Freeze the two-stage development-only v7 source-ledger pilot."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_provider import BASE_URL, MODEL, PROFILE
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.source_ledger_runtime import VERSION


PLAN_PATH = ROOT / "experiments/v7_source_ledger_pilot_plan.json"
AUTH_PATH = ROOT / "experiments/v7_source_ledger_pilot_authorization.json"
SOURCE = ROOT / "results/private/formal_v3_20260912/inference_complete.json"
FILES = [
    "experiments/family_split_v1.json",
    "data/evaluation/bound_reference_audit_v1.json",
    "llm4or/benchmark_inputs.py",
    "llm4or/benchmark_registry.py",
    "llm4or/formal_evaluation.py",
    "llm4or/formal_gateway.py",
    "llm4or/formal_provider.py",
    "llm4or/milp_contracts.py",
    "llm4or/milp_schema.py",
    "llm4or/milp_solver.py",
    "llm4or/run_interruption.py",
    "llm4or/schema.py",
    "llm4or/semantic_contracts.py",
    "llm4or/semantic_contracts_v2.py",
    "llm4or/source_ledger.py",
    "llm4or/source_ledger_runtime.py",
    "scripts/approve_v7_source_ledger_pilot.py",
    "scripts/evaluate_v7_source_ledger_pilot.py",
    "scripts/freeze_v7_source_ledger_pilot.py",
    "scripts/run_v7_source_ledger_pilot.py",
    "results/private/formal_v3_20260912/inference_complete.json",
]
QUOTAS = {
    "ComplexOR": 2,
    "IndustryOR": 5,
    "MAMO ComplexLP": 5,
    "NL4Opt": 5,
    "OptMATH-Bench": 5,
    "OptiBench": 8,
}


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def selection():
    registry = {row["id"]: row for row in load_public_registry(ROOT)}
    split = json.loads((ROOT / "experiments/family_split_v1.json").read_text())
    role = {pid: family["role"] for family in split["families"] for pid in family["members"]}
    family_id = {pid: family["id"] for family in split["families"] for pid in family["members"]}
    complete = json.loads(SOURCE.read_text())
    rows = []
    for cell in complete["cells"]:
        pid = cell["id"]
        if not (
            cell["method"] == "Base"
            and cell["replicate"] == 17
            and cell["token_cap"] == 65536
            and role.get(pid) in {"development_propose", "development_select"}
        ):
            continue
        source = json.loads(Path(cell["record_path"]).read_text())
        if digest(source) != cell["record_sha256"]:
            raise ValueError("source_record_changed")
        if source.get("status") == "infrastructure_unavailable":
            continue
        rows.append({
            "problem_id": pid,
            "benchmark": registry[pid]["benchmark"],
            "family_id": family_id[pid],
            "role": role[pid],
            "input_sha256": registry[pid]["input_sha256"],
            "source_record_path": cell["record_path"],
            "source_record_sha256": cell["record_sha256"],
        })
    rows.sort(key=lambda item: (item["benchmark"], item["family_id"], item["problem_id"]))
    stage1_ids = set()
    for benchmark, quota in QUOTAS.items():
        seen = set()
        choices = []
        for row in rows:
            if row["benchmark"] != benchmark or row["family_id"] in seen:
                continue
            seen.add(row["family_id"])
            choices.append(row["problem_id"])
        if len(choices) < quota:
            raise ValueError("insufficient_stage1_families:" + benchmark)
        stage1_ids.update(choices[:quota])
    if len(rows) != 146 or len(stage1_ids) != 30:
        raise ValueError("unexpected_v7_selection_size")
    for row in rows:
        row["batch"] = "stage1" if row["problem_id"] in stage1_ids else "stage2"
    return {
        "schema": "v7-source-ledger-development-selection-v1",
        "records": rows,
        "problem_count": len(rows),
        "stage1_records": 30,
        "stage2_records": len(rows) - 30,
        "family_count": len({row["family_id"] for row in rows}),
        "locked_or_update_gate_records": 0,
        "labels_or_references_read_for_selection": False,
        "source_status_filter": "exclude only four Base transport interruptions; retain model-format failures",
        "selection_rule": (
            "All development_propose/development_select Base records at replicate 17 and 65536 tokens, except "
            "transport interruptions. Stage 1 takes fixed benchmark quotas and the lexicographically first "
            "record from distinct operational families; Stage 2 contains every remainder."
        ),
    }


def main():
    if PLAN_PATH.exists() or AUTH_PATH.exists():
        raise ValueError("v7_pilot_already_frozen")
    chosen = selection()
    unique_requests = chosen["problem_count"] * 2
    plan = {
        "schema": "v7-source-ledger-pilot-plan-v1",
        "kind": "v7_source_ledger_pilot",
        "status": "pending_user_authorization",
        "authorization_schema": "v7-source-ledger-pilot-authorization-v1",
        "runtime_version": VERSION,
        "run_directory": "results/private/v7_source_ledger_pilot_20261003",
        "endpoint": BASE_URL,
        "model": MODEL,
        "credential_profile": str(PROFILE),
        "selection": chosen,
        "public_inputs": {row["problem_id"]: row["input_sha256"] for row in chosen["records"]},
        "methods": {"LedgerProbe": {"max_calls": 2}},
        "reported_ablations": ["Base", "V6", "DualLedger", "FullV7"],
        "replicates": [17],
        "token_cap": 131072,
        "trajectory_token_caps": [131072],
        "progress_stage": "v7dev",
        "limits": {
            "max_requests": unique_requests * 3,
            "max_total_reserved_or_reported_tokens": 220000000,
            "max_completion_tokens": 16384,
            "max_input_bytes": 262144,
            "max_output_bytes": 262144,
            "token_overhead_reserve": 4096,
            "request_seconds": 90,
            "max_run_seconds": 259200,
            "minimum_free_disk_bytes": 4294967296,
        },
        "resilience": {
            "max_attempts_per_request": 3,
            "backoff_seconds": [5, 20],
            "circuit_breaker_consecutive_failures": 8,
            "max_concurrent_requests": 5,
        },
        "matrix": {
            "inference_cells": chosen["problem_count"],
            "stage1_cells": chosen["stage1_records"],
            "stage2_cells": chosen["stage2_records"],
            "unique_request_ceiling_without_retries": unique_requests,
            "physical_attempt_ceiling_with_retries": unique_requests * 3,
        },
        "stage_rules": {
            "stage1": (
                "Continue only with zero infrastructure-unavailable FullV7 cases, at least 5 accepted dual-view "
                "consensus models, at least 3 corrections and at most 1 regression versus Base, net at least 2, "
                "and at least 2 correcting operational families."
            ),
            "final_development": (
                "Promising only with at least 10 corrections and at most 2 regressions versus Base, corrections "
                "at least four times regressions, at least 5 correcting operational families, and at least 5/at "
                "most 2 incremental corrections/regressions versus V6."
            ),
        },
        "evaluation": {
            "development_only": True,
            "primary": "published objective/status benchmark accuracy and paired transitions",
            "confirmatory_claim_allowed": False,
            "locked_test_access_during_inference": False,
            "stage2_is_pre_authorized_only_if_stage1_rule_passes_without_method_change": True,
        },
        "runtime": {
            "python": platform.python_version(),
            "machine": platform.machine(),
            "packages": {name: importlib.metadata.version(name) for name in ["numpy", "scipy", "jsonschema", "psutil"]},
        },
        "frozen_files": {path: sha(path) for path in FILES},
        "cost_note": (
            "Private-provider fiat pricing is unknown. The hard ceilings cover at most 292 unique requests, "
            "876 physical attempts including retries, and 220,000,000 reserved-or-reported tokens. Stage 1 "
            "uses only 60 unique requests and stops the authorization automatically if its gate fails."
        ),
    }
    write_json(PLAN_PATH, plan)
    authorization = {
        "schema": plan["authorization_schema"],
        "status": "pending",
        "plan_sha256": digest(plan),
        "endpoint": BASE_URL,
        "model": MODEL,
        "run_directory": str(ROOT / plan["run_directory"]),
        "limits": plan["limits"],
        "user_confirmation": None,
        "historical_authorizations_reused": False,
    }
    write_json(AUTH_PATH, authorization)
    print(json.dumps({
        "status": "frozen_pending_user_authorization",
        "plan_sha256": digest(plan),
        "selection": {key: chosen[key] for key in ("problem_count", "family_count", "stage1_records", "stage2_records")},
        "matrix": plan["matrix"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
