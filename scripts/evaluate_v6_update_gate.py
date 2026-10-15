"""Freeze and run a fresh-to-v6 aggregate evaluation on update-gate records.

V6 was designed only from development-role outcomes and label-free locked
actionability.  This script binds the unchanged method before opening any
update-gate published-reference outcomes.  It reports only aggregates.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_inputs import payload_sha256
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.milp_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.semantic_contracts import apply_contracts_transactionally, derive_contracts as derive_v1
from llm4or.semantic_contracts_v2 import derive_contracts as derive_v2


PLAN = ROOT / "experiments/v6_update_gate_evaluation_plan.json"
RESULT = ROOT / "results/v6_update_gate_evaluation.json"
SOURCE = ROOT / "results/private/formal_v3_20260912"
ROLE = "update_gate"
FILES = [
    "experiments/family_split_v1.json",
    "experiments/full_run_plan.json",
    "data/evaluation/bound_reference_audit_v1.json",
    "llm4or/benchmark_inputs.py",
    "llm4or/benchmark_registry.py",
    "llm4or/formal_evaluation.py",
    "llm4or/milp_schema.py",
    "llm4or/milp_solver.py",
    "llm4or/semantic_contracts.py",
    "llm4or/semantic_contracts_v2.py",
    "scripts/evaluate_v6_update_gate.py",
    "results/private/formal_v3_20260912/inference_complete.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    registry = {row["id"]: row for row in load_public_registry(ROOT)}
    split = json.loads((ROOT / "experiments/family_split_v1.json").read_text())
    roles = {pid: family["role"] for family in split["families"] for pid in family["members"]}
    families = {pid: family["id"] for family in split["families"] for pid in family["members"]}
    complete = json.loads((SOURCE / "inference_complete.json").read_text())
    cells = {
        cell["id"]: cell
        for cell in complete["cells"]
        if cell["method"] == "Base"
        and cell["replicate"] == 17
        and cell["token_cap"] == 65536
        and roles.get(cell["id"]) == ROLE
    }
    return registry, families, cells


def actionable_binding(registry, families, cells):
    changed = []
    changed_families = set()
    for pid, cell in sorted(cells.items()):
        record = json.loads(Path(cell["record_path"]).read_text())
        initial = record.get("final_model")
        if initial is None:
            continue
        bundle = derive_v2(registry[pid]["public"], initial)
        repaired, _ = apply_contracts_transactionally(registry[pid]["public"], initial, execute, bundle)
        if digest(repaired) != digest(initial):
            changed.append(pid)
            changed_families.add(families[pid])
    return {
        "records": len(cells),
        "changed_records": len(changed),
        "changed_operational_families": len(changed_families),
        "changed_problem_ids_sha256": digest(changed),
    }


def exact_one_sided_sign_probability(corrections, regressions):
    discordant = corrections + regressions
    if discordant == 0:
        return 1.0
    return sum(math.comb(discordant, k) for k in range(corrections, discordant + 1)) / (2 ** discordant)


def freeze():
    if PLAN.exists() or RESULT.exists():
        raise ValueError("v6_update_gate_evaluation_already_frozen")
    registry, families, cells = inputs()
    actionable = actionable_binding(registry, families, cells)
    if actionable["records"] != 176:
        raise ValueError("unexpected_update_gate_size")
    if actionable["changed_records"] < 5 or actionable["changed_operational_families"] < 3:
        raise ValueError("insufficient_actionability_before_label_access")
    plan = {
        "schema": "v6-update-gate-evaluation-plan-v1",
        "status": "frozen_waiting_for_evaluation",
        "method": "Base+SemanticContracts-v2",
        "comparators": ["Base", "Base+SemanticContracts-v1"],
        "source_method": "Base",
        "source_role": ROLE,
        "replicate": 17,
        "token_cap": 65536,
        "locked_scoring": "aggregate_only_no_problem_or_family_identifiers",
        "preflight_without_labels": actionable,
        "new_api_requests": 0,
        "primary_endpoint": "published objective/status agreement (formulation accuracy proxy)",
        "success_rule": {
            "versus_base": (
                "positive accuracy difference, zero regressions, at least 5 corrections, "
                "at least 3 correcting operational families, and one-sided exact paired sign p <= 0.05"
            ),
            "incremental_versus_v5": "at least 1 correction and zero regressions",
            "all_conditions_required": True,
        },
        "claim_guard": (
            "Fresh-to-v6 evaluation on the previously unopened update-gate block. V6 was selected from "
            "development-role outcomes and label-free actionability only. Published objective/status "
            "agreement is reported as benchmark formulation accuracy; operational families are not "
            "expert-certified IID, so family-level counts remain a required sensitivity analysis."
        ),
        "frozen_files": {name: sha(ROOT / name) for name in FILES},
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(PLAN, plan)
    print(json.dumps({
        "status": "frozen",
        "plan_sha256": digest(plan),
        "preflight_without_labels": actionable,
        "api_requests": 0,
    }, sort_keys=True))


def preflight(plan):
    for name, expected in plan["frozen_files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("frozen_file_changed:" + name)
    registry, families, cells = inputs()
    full = json.loads((ROOT / "experiments/full_run_plan.json").read_text())
    if any(
        pid not in registry or registry[pid]["input_sha256"] != value
        for pid, value in full["public_inputs"].items()
    ):
        raise ValueError("public_input_changed")
    if actionable_binding(registry, families, cells) != plan["preflight_without_labels"]:
        raise ValueError("actionable_cohort_changed")
    return registry, families, cells


def classify(before, after):
    if before not in {True, False} or after not in {True, False}:
        return "unknown"
    if after and not before:
        return "correction"
    if before and not after:
        return "regression"
    return "both_match" if before else "neither_match"


def evaluate():
    if RESULT.exists():
        raise ValueError("v6_update_gate_evaluation_already_exists")
    plan = json.loads(PLAN.read_text())
    registry, families, cells = preflight(plan)
    references = {
        row["problem_id"]: row
        for row in json.loads((ROOT / "data/evaluation/bound_reference_audit_v1.json").read_text())["records"]
    }
    counts = Counter()
    effects = defaultdict(Counter)
    for pid, cell in sorted(cells.items()):
        counts["records"] += 1
        record = json.loads(Path(cell["record_path"]).read_text())
        if digest(record) != cell["record_sha256"]:
            raise ValueError("source_record_changed")
        if record.get("input_sha256") != payload_sha256(registry[pid]["public"]):
            raise ValueError("record_input_changed")
        initial = record.get("final_model")
        if initial is None:
            counts["no_model"] += 1
            continue
        bundle_v6 = derive_v2(registry[pid]["public"], initial)
        if not bundle_v6["contracts"]:
            continue
        counts["contract_triggered"] += 1
        for contract in bundle_v6["contracts"]:
            counts["contract:" + contract["source"]] += 1
        v6, report = apply_contracts_transactionally(registry[pid]["public"], initial, execute, bundle_v6)
        counts["status:" + report["status"]] += 1
        if digest(v6) == digest(initial):
            continue
        counts["v6_model_change_vs_base"] += 1
        bundle_v5 = derive_v1(registry[pid]["public"], initial)
        v5, _ = apply_contracts_transactionally(registry[pid]["public"], initial, execute, bundle_v5)
        base_score = grade(record, registry[pid]["public"], references[pid], independent=False).get(
            "published_proxy_match"
        )
        v6_record = {
            **deepcopy(record),
            "final_model": v6,
            "final_solve": execute({"op": "solve", "model": v6}),
            "status": "completed",
        }
        v6_score = grade(v6_record, registry[pid]["public"], references[pid], independent=False).get(
            "published_proxy_match"
        )
        outcome = classify(base_score, v6_score)
        counts["versus_base:" + outcome] += 1
        effects[families[pid]]["base:" + outcome] += 1
        if digest(v6) != digest(v5):
            counts["v6_incremental_model_change_vs_v5"] += 1
            v5_record = {
                **deepcopy(record),
                "final_model": v5,
                "final_solve": execute({"op": "solve", "model": v5}),
                "status": "completed",
            }
            v5_score = grade(v5_record, registry[pid]["public"], references[pid], independent=False).get(
                "published_proxy_match"
            )
            incremental = classify(v5_score, v6_score)
            counts["versus_v5:" + incremental] += 1
            effects[families[pid]]["v5:" + incremental] += 1
    corrections = counts["versus_base:correction"]
    regressions = counts["versus_base:regression"]
    family_counts = {
        "changed_operational_families_vs_base": sum(
            any(key.startswith("base:") for key in value) for value in effects.values()
        ),
        "correcting_operational_families_vs_base": sum(
            value["base:correction"] > 0 for value in effects.values()
        ),
        "regressing_operational_families_vs_base": sum(
            value["base:regression"] > 0 for value in effects.values()
        ),
        "incremental_correcting_operational_families_vs_v5": sum(
            value["v5:correction"] > 0 for value in effects.values()
        ),
        "incremental_regressing_operational_families_vs_v5": sum(
            value["v5:regression"] > 0 for value in effects.values()
        ),
    }
    p_value = exact_one_sided_sign_probability(corrections, regressions)
    accuracy_delta = (corrections - regressions) / counts["records"]
    passed = (
        accuracy_delta > 0
        and corrections >= 5
        and regressions == 0
        and family_counts["correcting_operational_families_vs_base"] >= 3
        and p_value <= 0.05
        and counts["versus_v5:correction"] >= 1
        and counts["versus_v5:regression"] == 0
    )
    report = {
        "schema": "v6-update-gate-evaluation-v1",
        "plan_sha256": digest(plan),
        "method": plan["method"],
        "counts": dict(counts),
        "family_counts": family_counts,
        "statistics": {
            "accuracy_delta_over_all_records": accuracy_delta,
            "paired_one_sided_exact_sign_p": p_value,
            "discordant_records": corrections + regressions,
        },
        "success": passed,
        "success_rule": plan["success_rule"],
        "claim_guard": plan["claim_guard"],
        "new_api_requests": 0,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(RESULT, report)
    print(json.dumps(report, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()
    if args.freeze == args.evaluate:
        raise ValueError("choose_exactly_one_mode")
    freeze() if args.freeze else evaluate()


if __name__ == "__main__":
    main()
