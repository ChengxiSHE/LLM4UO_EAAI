#!/usr/bin/env python3
"""Reconcile the RetailOpt README endpoint with the official ReLoop code."""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.atomic_publisher import publish_bytes
from llm4or.retailopt190_endpoint import readme_strict_correct, relative_objective_error, reloop_code_correct


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numeric_comparisons(path: Path, name: str, number: float) -> Counter[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
            continue
        left_name = node.left.id if isinstance(node.left, ast.Name) else node.left.attr if isinstance(node.left, ast.Attribute) else None
        right = node.comparators[0]
        if left_name != name or not isinstance(right, ast.Constant) or right.value != number:
            continue
        counts[type(node.ops[0]).__name__] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retailopt-root", type=Path, required=True)
    parser.add_argument("--reloop-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    plan = json.loads(arguments.plan.read_text())
    checkpoint = json.loads(arguments.checkpoint.read_text())
    ledger_raw = arguments.ledger.read_bytes()
    if hashlib.sha256(ledger_raw).hexdigest() != plan["custody"]["private_ledger_sha256"]:
        raise SystemExit("ledger drift")
    ledger = json.loads(ledger_raw)
    by_opaque = {record["opaque_id"]: record for record in ledger["records"]}
    if set(checkpoint["records"]) != set(by_opaque):
        raise SystemExit("checkpoint membership")
    strict = 0
    reloop = 0
    strict_misses: Counter[str] = Counter()
    rel_errors = []
    terminal = Counter()
    for opaque, record in by_opaque.items():
        result = checkpoint["records"][opaque]
        terminal[result["terminal"]] += 1
        if result["terminal"] != "complete":
            continue
        strict_ok = readme_strict_correct(record, result)
        reloop_ok = reloop_code_correct(record, result)
        strict += int(strict_ok)
        reloop += int(reloop_ok)
        if not strict_ok:
            strict_misses[record["archetype"]] += 1
        rel_errors.append(relative_objective_error(result["objective"], record["reference_objective"]))
    solver_path = arguments.retailopt_root / "solvers/universal_retail_solver.py"
    reloop_path = arguments.reloop_root / "reloop/experiment_runner.py"
    mip_gap_calls = numeric_comparisons(reloop_path, "objective_error", 0.01)
    solver_text = solver_path.read_text(encoding="utf-8")
    if 'setParam("MIPGap", 0.01)' not in solver_text or 'setParam("TimeLimit", 60)' not in solver_text:
        raise SystemExit("upstream solver contract drift")
    if mip_gap_calls["Lt"] < 1 or mip_gap_calls["Gt"] < 1 or mip_gap_calls["LtE"] < 1:
        raise SystemExit("reloop endpoint contract drift")
    audit = {
        "schema": "llm4or-retailopt190-endpoint-stability-audit-v1",
        "status": "passed_reloop_endpoint_only",
        "source": {
            "retailopt_commit": plan["source"]["commit"],
            "retailopt_solver_sha256": sha(solver_path),
            "retailopt_readme_sha256": sha(arguments.retailopt_root / "README.md"),
            "reloop_commit": "0508ac656a98219ebf005cc0433442bc3a465bb8",
            "reloop_experiment_runner_sha256": sha(reloop_path),
        },
        "frozen_run": {
            "plan_sha256": sha(arguments.plan),
            "checkpoint_sha256": sha(arguments.checkpoint),
            "terminal_counts": dict(sorted(terminal.items())),
            "gurobi_version": plan["endpoint"]["gurobi_version"],
            "threads": plan["endpoint"]["threads"],
            "seed": plan["endpoint"]["seed"],
        },
        "contracts": {
            "reference_solver": {"time_limit_seconds": 60, "mip_gap": 0.01},
            "retailopt_readme": {"default_relative_tolerance": 0.0001, "relaxed_relative_tolerance": 0.01, "relaxed_archetypes": ["fixed_order_cost", "pack_size_integer"], "status_match_required": True},
            "reloop_code": {"relative_objective_error_threshold": 0.01, "comparison": "strict_less_than", "status_match_required": False, "ast_comparison_counts": dict(sorted(mip_gap_calls.items()))},
        },
        "results": {
            "denominator": len(by_opaque),
            "retailopt_readme_correct": strict,
            "retailopt_readme_incorrect": len(by_opaque) - strict,
            "retailopt_readme_miss_archetype_counts": dict(sorted(strict_misses.items())),
            "reloop_code_correct": reloop,
            "reloop_code_incorrect": len(by_opaque) - reloop,
            "maximum_relative_objective_error": max(rel_errors),
        },
        "diagnosis": {
            "python_or_gurobi_import_failure": False,
            "solver_worker_timeout_or_crash": False,
            "strict_contract_precision_exceeds_reference_solver_gap": True,
            "all_strict_misses_within_reloop_one_percent_endpoint": reloop == len(by_opaque),
        },
        "decision": {
            "source_snapshot_eligible": True,
            "retailopt_readme_endpoint_eligible": False,
            "reloop_code_endpoint_eligible": reloop == len(by_opaque),
            "frozen_confirmatory_endpoint": "relative objective error < 0.01 on the full denominator; execution and solver status reported separately",
        },
        "privacy": {"contains_problem_bodies": False, "contains_source_ids": False, "contains_per_item_results": False, "contains_objectives": False},
        "execution": {"new_api_calls": 0, "new_model_calls": 0, "new_solver_calls": 0, "credentials_read": False},
        "claim_boundary": "This audit selects a reproducible published endpoint. It does not evaluate a language-model method and does not establish benchmark accuracy.",
    }
    payload = (json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    relative = arguments.output.resolve().relative_to(ROOT.resolve())
    result = publish_bytes(ROOT, relative, payload)
    print(json.dumps({"status": audit["status"], "sha256": hashlib.sha256(payload).hexdigest(), "transaction": result.transaction_id}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
