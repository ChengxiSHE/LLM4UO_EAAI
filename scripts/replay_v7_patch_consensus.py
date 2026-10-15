"""Replay fact-level dual-view consensus variants on v7 development outputs."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.milp_schema import model
from llm4or.milp_solver import execute
from llm4or.semantic_contracts import apply_contracts_transactionally
from llm4or.semantic_contracts_v2 import derive_contracts
from scripts.replay_v7_stage1_variants import structural_model

PLAN = ROOT / "experiments/v7_source_ledger_restart_plan.json"
RUN = ROOT / "results/private/v7_source_ledger_restart_20261003"


def transition(before, after):
    if before not in {True, False} or after not in {True, False}:
        return "unknown"
    if after and not before:
        return "correction"
    if before and not after:
        return "regression"
    return "both_match" if before else "neither_match"


def fact_patch(base, left, right, include_rows):
    """Patch only facts on which two complete structural views agree."""
    if base is None:
        return None, []
    candidate = deepcopy(model(base))
    base_vars = {item["id"]: item for item in candidate["variables"]}
    left_vars = {item["id"]: item for item in left["variables"]}
    right_vars = {item["id"]: item for item in right["variables"]}
    if set(base_vars) != set(left_vars) or set(base_vars) != set(right_vars):
        return model(base), []
    changes = []
    for variable_id, target in base_vars.items():
        for field in ("domain", "lower", "upper"):
            value = left_vars[variable_id][field]
            if value == right_vars[variable_id][field] and target[field] != value:
                target[field] = deepcopy(value)
                changes.append("variable:" + field)
    all_ids = set(base_vars)
    for variable_id in sorted(all_ids):
        left_value = left["objective"]["coefficients"].get(variable_id, 0)
        right_value = right["objective"]["coefficients"].get(variable_id, 0)
        base_value = candidate["objective"]["coefficients"].get(variable_id, 0)
        if left_value == right_value and base_value != left_value:
            if left_value == 0:
                candidate["objective"]["coefficients"].pop(variable_id, None)
            else:
                candidate["objective"]["coefficients"][variable_id] = left_value
            changes.append("objective:coefficient")
    for field in ("sense", "offset"):
        value = left["objective"][field]
        if value == right["objective"][field] and candidate["objective"][field] != value:
            candidate["objective"][field] = deepcopy(value)
            changes.append("objective:" + field)
    if include_rows:
        base_rows = {item["id"]: item for item in candidate["constraints"]}
        left_rows = {item["id"]: item for item in left["constraints"]}
        right_rows = {item["id"]: item for item in right["constraints"]}
        for row_id in sorted(set(base_rows) & set(left_rows) & set(right_rows)):
            left_row = {key: left_rows[row_id][key] for key in ("coefficients", "sense", "rhs")}
            right_row = {key: right_rows[row_id][key] for key in ("coefficients", "sense", "rhs")}
            base_row = {key: base_rows[row_id][key] for key in ("coefficients", "sense", "rhs")}
            if left_row == right_row and base_row != left_row:
                base_rows[row_id].update(deepcopy(left_row))
                changes.append("constraint:row")
    try:
        candidate = model(candidate)
    except (ValueError, TypeError, KeyError):
        return model(base), []
    if not changes or execute({"op": "solve", "model": candidate}).get("status") != "optimal":
        return model(base), []
    return candidate, changes


def main():
    plan = json.loads(PLAN.read_text())
    registry = {row["id"]: row for row in load_public_registry(ROOT)}
    references = {
        row["problem_id"]: row
        for row in json.loads((ROOT / "data/evaluation/bound_reference_audit_v1.json").read_text())["records"]
    }
    raw = {}
    db = sqlite3.connect(RUN / "requests.sqlite3")
    try:
        rows = db.execute(
            "SELECT s.scope,s.slot,a.response,a.status FROM slots s JOIN attempts a ON a.key=s.key"
        )
        for scope, slot, response, status in rows:
            if status == "complete":
                raw[(scope.split(":")[-1], slot)] = json.loads(json.loads(response)["text"])
    finally:
        db.close()

    def score(source, problem_id, candidate):
        record = {
            **deepcopy(source), "final_model": candidate, "status": "completed",
            "errors": [], "trace": [],
        }
        return grade(
            record, registry[problem_id]["public"], references[problem_id], independent=False
        ).get("published_proxy_match")

    variants = {}
    for include_rows in (False, True):
        name = "scalar_fact_consensus" if not include_rows else "scalar_and_row_fact_consensus"
        counts = Counter()
        change_counts = Counter()
        records = []
        selected = [row for row in plan["selection"]["records"] if row["batch"] == "stage1"]
        for item in selected:
            problem_id = item["problem_id"]
            public = registry[problem_id]["public"]
            source = json.loads(Path(item["source_record_path"]).read_text())
            base = model(source["final_model"]) if source.get("final_model") is not None else None
            if base is None:
                v6 = None
            else:
                v6, _ = apply_contracts_transactionally(
                    public, base, execute, derive_contracts(public, base)
                )
            patched, changes = base, []
            try:
                left = structural_model(raw[(problem_id, 0)])
                right = structural_model(raw[(problem_id, 1)])
                patched, changes = fact_patch(base, left, right, include_rows)
            except (KeyError, TypeError, ValueError, RuntimeError):
                pass
            if patched is None:
                full = v6
            else:
                full, _ = apply_contracts_transactionally(
                    public, patched, execute, derive_contracts(public, patched)
                )
            before = score(source, problem_id, base)
            after = score(source, problem_id, full)
            v6_score = score(source, problem_id, v6)
            counts["Full_vs_Base:" + transition(before, after)] += 1
            counts["Full_vs_V6:" + transition(v6_score, after)] += 1
            change_counts.update(changes)
            records.append({
                "problem_id": problem_id, "changes": changes,
                "scores": {"Base": before, "V6": v6_score, "Full": after},
            })
        variants[name] = {
            "counts": dict(counts), "change_counts": dict(change_counts), "records": records,
        }
    print(json.dumps({
        "schema": "v7-stage1-patch-consensus-replay-v1",
        "new_api_calls": 0,
        "variants": variants,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
