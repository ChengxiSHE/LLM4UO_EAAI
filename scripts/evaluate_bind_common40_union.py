#!/usr/bin/env python3
"""Aggregate exactly the fixed 40 identities, without reruns or solver calls."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.pipeline import write_json
from llm4or.schema import digest
from scripts.audit_external_comparison_cohorts import PUBLIC_MANIFEST, sha


def read(path):
    return json.loads(path.read_text())


def evaluate():
    extension_path = ROOT / "experiments/bind_common40_completion_plan.json"
    extension = read(extension_path)
    binding = extension["completion"]
    parent_path = ROOT / binding["parent_plan"]
    parent = read(parent_path)
    if digest(parent) != binding["parent_plan_sha256"] or sha(ROOT / PUBLIC_MANIFEST) != binding["target_manifest_sha256"]:
        raise ValueError("union_source_binding_changed")
    target = {r["id"]: r for r in read(ROOT / PUBLIC_MANIFEST)["roles"]["test"]}
    if len(target) != 40:
        raise ValueError("union_target_not_40")
    common = set(target) & set(parent["public_inputs"])
    if (sorted(common) != binding["reuse_without_rerun"] or len(common) != 10
            or set(extension["public_inputs"]) != set(target) - common):
        raise ValueError("union_not_exact_missing_only")
    cells, source_receipts = {}, []
    by_family = defaultdict(lambda: Counter(planned=0, evaluated=0, round1_correct=0, final_correct=0,
                                           infrastructure_unavailable=0, method_failure=0))
    for name, plan, path, selected in (("parent", parent, parent_path, common),
                                     ("completion", extension, extension_path, set(target) - common)):
        directory = ROOT / plan["run_directory"]
        completed_path = directory / "completed.json"
        inference_path = directory / "inference_complete.json"
        if name == "parent" and (sha(completed_path) != binding["old_completed_sha256"]
                                  or sha(inference_path) != binding["old_inference_complete_sha256"]):
            raise ValueError("historical_results_changed_after_freeze")
        completed, inference = read(completed_path), read(inference_path)
        if completed["plan_sha256"] != digest(plan) or inference["plan_sha256"] != digest(plan):
            raise ValueError("union_run_plan_mismatch")
        if completed["state"] != "completed_retrospective_reproduction":
            raise ValueError("union_run_not_closed_complete")
        index = {c["problem_id"]: c for c in inference["cells"]}
        if len(index) != len(inference["cells"]) or set(index) != set(plan["public_inputs"]):
            raise ValueError("union_source_cells_mismatch")
        source_receipts.append({"name": name, "plan": str(path.relative_to(ROOT)), "plan_sha256": digest(plan),
                                "inference_complete_sha256": sha(inference_path), "completed_sha256": sha(completed_path),
                                "included_identities": len(selected),
                                "whole_source_run_usage_not_target_subset_cost": inference["usage"]})
        for problem_id in sorted(selected):
            row, cell = target[problem_id], index[problem_id]
            if plan["public_inputs"][problem_id] != row["public_input_sha256"] or cell["category"] != row["family"]:
                raise ValueError("union_public_or_family_mismatch")
            counts = by_family[row["family"]]
            counts["planned"] += 1
            status, first, final = cell["status"], False, False
            if status == "infrastructure_unavailable":
                counts["infrastructure_unavailable"] += 1
            elif status == "method_failure":
                counts["evaluated"] += 1
                counts["method_failure"] += 1
            else:
                record_path = ROOT / cell["record_path"]
                record = read(record_path)
                if (digest(record) != cell["record_sha256"] or record["problem_id"] != problem_id
                        or record["public_input_sha256"] != row["public_input_sha256"]):
                    raise ValueError("union_record_integrity")
                first = bool(record["rounds"][0]["objective_matches"] and record["rounds"][0]["status_matches"])
                final = bool(record["success"])
                counts["evaluated"] += 1
                counts["round1_correct"] += int(first)
                counts["final_correct"] += int(final)
            cells[problem_id] = {"family": row["family"], "source": name, "status": status,
                                 "round1_correct": first, "final_correct": final,
                                 "public_input_sha256": row["public_input_sha256"]}
    if set(cells) != set(target):
        raise ValueError("union_incomplete_or_duplicate")
    totals = sum(by_family.values(), Counter())
    report = {"schema": "bind-fixed-common40-union-v1", "role": "retrospective_two_family_comparison",
              "target_manifest": PUBLIC_MANIFEST, "target_manifest_sha256": sha(ROOT / PUBLIC_MANIFEST),
              "source_runs": source_receipts, "counts": dict(totals),
              "round1_accuracy_evaluated": totals["round1_correct"] / totals["evaluated"] if totals["evaluated"] else None,
              "oracle_final_accuracy_evaluated": totals["final_correct"] / totals["evaluated"] if totals["evaluated"] else None,
              "round1_success_fraction_all_planned": totals["round1_correct"] / 40,
              "oracle_final_success_fraction_all_planned": totals["final_correct"] / 40,
              "by_family": {k: dict(v) for k, v in sorted(by_family.items())}, "cells": cells,
              "claim_guard": "All old overlapping outcomes retained without rerun. BIND receives structured instance data and oracle feedback in rounds 2/3; final is not answer-blind. Safe-adapter reproduction, not unrestricted native code. No fresh confirmation or cross-cohort ranking.",
              "new_model_calls": 0, "new_solver_calls": 0}
    write_json(ROOT / "results/bind_fixed_common40.json", report)
    print(json.dumps({"counts": report["counts"], "new_model_calls": 0, "new_solver_calls": 0}))
    return report


if __name__ == "__main__":
    evaluate()
