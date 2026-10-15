"""Outcome-aware development replay of v7 Stage 1 without new model calls."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.milp_schema import model
from llm4or.milp_solver import execute
from llm4or.semantic_contracts import apply_contracts_transactionally
from llm4or.semantic_contracts_v2 import derive_contracts
from llm4or.source_ledger import SOURCE_LEDGER_SCHEMA

PLAN = ROOT / "experiments/v7_source_ledger_restart_plan.json"
RUN = ROOT / "results/private/v7_source_ledger_restart_20261003"


def structural_model(raw):
    """Compile model fields while treating quote evidence as diagnostic."""
    value = deepcopy(raw)
    quotes = (
        [item.get("quote") for item in value.get("variables", [])]
        + [item.get("quote") for item in value.get("constraints", [])]
        + [value.get("objective", {}).get("quote")]
    )
    for quote in quotes:
        if isinstance(quote, dict) and isinstance(quote.get("text"), str) and quote["text"]:
            start = quote.get("start") if isinstance(quote.get("start"), int) else 0
            end = quote.get("end") if isinstance(quote.get("end"), int) else 0
            quote["start"] = max(0, start)
            quote["end"] = max(quote["start"] + 1, end)
    errors = list(Draft202012Validator(SOURCE_LEDGER_SCHEMA).iter_errors(value))
    if errors:
        raise ValueError("structural_schema_invalid")
    return model({
        "schema": "milp-v1",
        "variables": [
            {key: item[key] for key in ("id", "meaning", "unit", "domain", "lower", "upper")}
            for item in value["variables"]
        ],
        "constraints": [
            {key: item[key] for key in ("id", "coefficients", "sense", "rhs")}
            for item in value["constraints"]
        ],
        "objective": {
            "coefficients": {
                item["id"]: item["objective_coefficient"]
                for item in value["variables"] if item["objective_coefficient"] != 0
            },
            "sense": value["objective"]["sense"],
            "unit": value["objective"]["unit"],
            "offset": value["objective"]["offset"],
        },
    })


def canonical_model(value):
    value = deepcopy(model(value))
    value["variables"] = sorted(value["variables"], key=lambda item: item["id"])
    value["constraints"] = sorted(value["constraints"], key=lambda item: item["id"])
    for row in value["constraints"]:
        row["coefficients"] = dict(sorted(row["coefficients"].items()))
    value["objective"]["coefficients"] = dict(sorted(value["objective"]["coefficients"].items()))
    return value


def transition(before, after):
    if before not in {True, False} or after not in {True, False}:
        return "unknown"
    if after and not before:
        return "correction"
    if before and not after:
        return "regression"
    return "both_match" if before else "neither_match"


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

    counts = Counter()
    accepted = []
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
        candidate = None
        try:
            left = structural_model(raw[(problem_id, 0)])
            right = structural_model(raw[(problem_id, 1)])
            if canonical_model(left) == canonical_model(right):
                if execute({"op": "solve", "model": left}).get("status") == "optimal":
                    candidate = left
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
        dual = candidate if candidate is not None else base
        if candidate is None:
            full = v6
        else:
            full, _ = apply_contracts_transactionally(
                public, candidate, execute, derive_contracts(public, candidate)
            )
            accepted.append(problem_id)
        scores = {
            "Base": score(source, problem_id, base),
            "V6": score(source, problem_id, v6),
            "DualLedger": score(source, problem_id, dual),
            "FullV7": score(source, problem_id, full),
        }
        counts["DualLedger_vs_Base:" + transition(scores["Base"], scores["DualLedger"])] += 1
        counts["FullV7_vs_Base:" + transition(scores["Base"], scores["FullV7"])] += 1
        counts["FullV7_vs_V6:" + transition(scores["V6"], scores["FullV7"])] += 1
        records.append({"problem_id": problem_id, "accepted": candidate is not None, "scores": scores})
    print(json.dumps({
        "schema": "v7-stage1-offline-variant-replay-v1",
        "variant": "diagnostic_quotes_exact_dual_model_consensus_fail_closed_v6",
        "new_api_calls": 0,
        "accepted": len(accepted),
        "accepted_problem_ids": accepted,
        "counts": dict(counts),
        "records": records,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
