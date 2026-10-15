#!/usr/bin/env python3
"""Audit comparison membership and public-input bindings, without scoring.

Only frozen plans, the public split manifest, and the public-only CoE prepared
manifest are decoded. No response, ledger, solver output or reference is read.
This report is not an execution authorization or a new experimental result.
"""
from collections import Counter
from itertools import combinations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.benchmark_inputs import payload_sha256
from llm4or.schema import digest

PLAN_FILES = {
    "V9": "experiments/text2opt_v9_confirmation_restart2_plan.json",
    "BIND": "experiments/text2opt_bind_common_reproduction_restart_plan.json",
    "CoE": "experiments/coe_common_reproduction_restart_plan.json",
    "SkillOpt": "experiments/skillopt_text2opt_test_recovery_plan.json",
    "AlphaOPT": "experiments/alphaopt_common_reproduction_plan.json",
}
PUBLIC_MANIFEST = "data/manifests/skillopt_text2opt_family_split_v1.json"
OUTPUT = "results/external_comparison_cohort_audit.json"
SOURCE_PREFIX = "data/raw/text2opt_bench_20261003/"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique(rows, key):
    out = {r[key]: dict(r) for r in rows}
    if len(out) != len(rows):
        raise ValueError("cohort_duplicate_identity")
    return out


def audit(root=ROOT):
    plans = {name: read(root / path) for name, path in PLAN_FILES.items()}
    public = read(root / PUBLIC_MANIFEST)
    manifest_sha = sha(root / PUBLIC_MANIFEST)
    if public["selection"]["outcome_used_for_selection"] is not False:
        raise ValueError("cohort_selection_uses_outcomes")
    test = unique(public["roles"]["test"], "id")
    for name in ("SkillOpt", "AlphaOPT"):
        plan = plans[name]
        if plan["public_manifest"] != PUBLIC_MANIFEST or plan["public_manifest_sha256"] != manifest_sha:
            raise ValueError("cohort_manifest_binding_changed")
        for problem_id, row in test.items():
            h = payload_sha256(row["public"])
            if h != row["public_input_sha256"] or h != plan["public_inputs"][problem_id]:
                raise ValueError("cohort_public_input_changed")
    if set(plans["AlphaOPT"]["public_inputs"]) != set(test):
        raise ValueError("alphaopt_test_cohort_not_exact")

    rows = {name: unique(plans[name]["selection"]["records"], "problem_id") for name in ("V9", "BIND")}
    for name in ("V9", "BIND"):
        if set(rows[name]) != set(plans[name]["public_inputs"]):
            raise ValueError("cohort_selection_public_scope_mismatch")
        for problem_id, row in rows[name].items():
            if row["input_sha256"] != plans[name]["public_inputs"][problem_id]:
                raise ValueError("cohort_selection_hash_mismatch")

    coe_plan = plans["CoE"]
    coe_path = root / coe_plan["prepared_data"]
    if sha(coe_path) != coe_plan["prepared_data_sha256"]:
        raise ValueError("coe_public_manifest_changed")
    coe = read(coe_path)
    if coe["selection_used_outcomes"] is not False:
        raise ValueError("coe_selection_uses_outcomes")
    coe_by_id = unique(coe["records"], "problem_id")
    selected_coe = unique(coe_plan["selection"]["records"], "problem_id")
    if set(coe_by_id) != set(selected_coe) or set(coe_by_id) != set(coe_plan["public_inputs"]):
        raise ValueError("coe_public_scope_mismatch")
    by_snapshot = {}
    for problem_id, row in coe_by_id.items():
        if any(row[k] != v for k, v in selected_coe[problem_id].items()):
            raise ValueError("coe_source_binding_changed")
        if payload_sha256(row["public"]) != row["public_input_sha256"] or row["public_input_sha256"] != coe_plan["public_inputs"][problem_id]:
            raise ValueError("coe_public_input_changed")
        canonical_public = dict(row["public"], id=row["source_problem_id"])
        entry = {"input_sha256": payload_sha256(canonical_public), "category": row["family"],
                 "source_file": row["source_file"], "source_file_sha256": row["source_file_sha256"]}
        snapshot = by_snapshot.setdefault(row["snapshot"], {})
        if row["source_problem_id"] in snapshot:
            raise ValueError("coe_snapshot_duplicate")
        snapshot[row["source_problem_id"]] = entry
    if set(by_snapshot) != {"paper", "current"} or by_snapshot["paper"] != by_snapshot["current"]:
        raise ValueError("coe_snapshots_not_same_public_cohort")
    rows["CoE"] = by_snapshot["paper"]
    for name in ("SkillOpt", "AlphaOPT"):
        rows[name] = {i: {"category": r["family"], "input_sha256": r["public_input_sha256"],
                          "source_file": r["source_file"], "source_file_sha256": r["source_file_sha256"]}
                      for i, r in test.items()}

    # Source identity and exact public payload (after CoE ID normalization) must
    # agree across EVERY shared record, not only the five-way intersection.
    for name, records in rows.items():
        for row in records.values():
            row["source_file"] = row["source_file"].removeprefix(SOURCE_PREFIX)
            if "source_file_sha256" not in row:
                row["source_file_sha256"] = plans[name]["frozen_files"][SOURCE_PREFIX + row["source_file"]]
    pairwise = []
    for a, b in combinations(PLAN_FILES, 2):
        shared = sorted(set(rows[a]) & set(rows[b]))
        keys = ("category", "input_sha256", "source_file", "source_file_sha256")
        if any(any(rows[a][i][k] != rows[b][i][k] for k in keys) for i in shared):
            raise ValueError("cross_method_public_or_source_binding_mismatch:" + a + ":" + b)
        pairwise.append({"methods": [a, b], "shared_records": len(shared),
                         "exact_public_and_source_bindings_match": True, "problem_ids": shared})

    sets = {name: set(values) for name, values in rows.items()}
    shared_all = sorted(set.intersection(*sets.values()))
    target = set(test)
    missing = {name: sorted(target - sets[name]) for name in ("BIND", "CoE", "V9")}
    cohorts = {}
    for name, records in rows.items():
        plan = plans[name]
        cohorts[name] = {"unique_planned_source_records": len(records),
                         "families": dict(sorted(Counter(r["category"] for r in records.values()).items())),
                         "problem_ids": sorted(records), "model": plan["model"],
                         "reasoning_effort": plan["reasoning_effort"], "replicate_namespaces": plan["replicates"],
                         "plan_path": PLAN_FILES[name], "plan_sha256": digest(plan),
                         "plan_file_sha256": sha(root / PLAN_FILES[name]),
                         "information_regime": plan.get("information_regime", {"target": "single-call public problem; static public-text compiler"}),
                         "limits": plan["limits"], "same_backbone_is_not_equal_cost_or_equal_information": True}
    return {
        "schema": "external-comparison-cohort-audit-v1", "audit_script_sha256": sha(Path(__file__)),
        "purpose": "membership and public/source binding audit only; no outcome or cost recomputation",
        "inputs": {PUBLIC_MANIFEST: manifest_sha, coe_plan["prepared_data"]: sha(coe_path)},
        "cohorts": cohorts, "pairwise_intersections": pairwise,
        "all_method_intersection": {"records": len(shared_all), "problem_ids": shared_all},
        "fixed_40_completion_options": {
            "status": "design_only_not_executable_or_authorized_dispatch", "target_manifest": PUBLIC_MANIFEST,
            "target_role": "test", "target_records": len(target),
            "reuse_existing_without_score_selection": {name: sorted(target & sets[name]) for name in ("BIND", "CoE")},
            "missing_problem_ids": missing,
            "missing_bind_records": len(missing["BIND"]),
            "missing_coe_records_per_snapshot": len(missing["CoE"]),
            "missing_coe_cells_both_snapshots": 2 * len(missing["CoE"]),
            "missing_v9_confirmation_records": len(missing["V9"]),
            "rule": "Only fill missing identities with unchanged method settings; retain all existing outcomes including failures. Freeze a separate complete plan before dispatch; do not reopen old authorizations.",
            "priority": "after running AlphaOPT and already-approved relational-method study; no additional baseline calls now",
            "base_caveat": "SkillOpt empty-skill and AlphaOPT no-library are method-specific controls, not interchangeable with V9 one-call Base; static compiler checkpoints do not fill missing Base responses",
        },
        "new_model_requests": 0, "new_solver_calls": 0, "references_or_responses_opened": False,
        "claim_guard": "Planned cohort sizes are not completed evaluation denominators. Do not rank scores from different cohorts, interpret five shared records as a main result, pool official snapshots, or confuse BIND oracle repair with answer-blind inference. All cohorts are previously exposed Text2Opt records.",
    }


if __name__ == "__main__":
    report = audit()
    path = ROOT / OUTPUT
    content = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path.exists() and path.read_text() != content:
        raise ValueError("cohort_audit_output_changed_use_new_version")
    path.write_text(content)
    print(json.dumps({"output": OUTPUT, "all_method_shared": report["all_method_intersection"]["records"],
                      "pairwise": [{k: r[k] for k in ("methods", "shared_records")} for r in report["pairwise_intersections"]],
                      "new_model_or_solver_calls": 0}, ensure_ascii=False))
