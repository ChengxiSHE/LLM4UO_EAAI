#!/usr/bin/env python3
"""Fixed-40 CoE strict/scalar-tolerance aggregation; no model/solver calls."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.benchmark_inputs import payload_sha256
from llm4or.pipeline import write_json
from llm4or.schema import digest
from scripts.audit_external_comparison_cohorts import PUBLIC_MANIFEST, sha


def read(path):
    return json.loads(path.read_text())


def blank():
    return Counter(planned=0, complete=0, author_exact=0, scalar_tolerance=0,
                   adapter_supported=0, adapter_unsupported=0, method_failure=0,
                   infrastructure_unavailable=0)


def evaluate():
    path = ROOT / "experiments/coe_common40_completion_plan.json"
    extension = read(path)
    binding = extension["completion"]
    parent_path = ROOT / binding["parent_plan"]
    parent = read(parent_path)
    if digest(parent) != binding["parent_plan_sha256"] or sha(ROOT / PUBLIC_MANIFEST) != binding["target_manifest_sha256"]:
        raise ValueError("coe_union_source_binding_changed")
    target = {r["id"]: r for r in read(ROOT / PUBLIC_MANIFEST)["roles"]["test"]}
    old_ids = set(binding["reuse_source_ids_without_rerun"])
    if len(target) != 40 or len(old_ids) != 5 or not old_ids <= set(target):
        raise ValueError("coe_union_target_partition")
    scores, receipts = {}, []
    aggregates = {s: blank() for s in ("paper", "current")}
    families = defaultdict(lambda: {s: blank() for s in ("paper", "current")})
    for name, plan, plan_path, selected in (("parent", parent, parent_path, old_ids),
                                          ("completion", extension, path, set(target) - old_ids)):
        directory = ROOT / plan["run_directory"]
        complete_path, inference_path = directory / "completed.json", directory / "inference_complete.json"
        if name == "parent" and (sha(complete_path) != binding["old_completed_sha256"]
                                  or sha(inference_path) != binding["old_inference_complete_sha256"]):
            raise ValueError("coe_union_historical_result_changed")
        completed, inference = read(complete_path), read(inference_path)
        if (completed["plan_sha256"] != digest(plan) or inference["plan_sha256"] != digest(plan)
                or completed["state"] != "completed_retrospective_reproduction"):
            raise ValueError("coe_union_run_not_closed_bound")
        prepared_path = ROOT / plan["prepared_data"]
        if sha(prepared_path) != plan["prepared_data_sha256"]:
            raise ValueError("coe_union_prepared_changed")
        rows = read(prepared_path)["records"]
        index = {r["problem_id"]: r for r in rows}
        cells = {c["problem_id"]: c for c in inference["cells"]}
        if (len(index) != len(rows) or len(cells) != len(inference["cells"])
                or set(index) != set(cells) or set(cells) != set(plan["public_inputs"])):
            raise ValueError("coe_union_cells_mismatch")
        if name == "completion" and {r["source_problem_id"] for r in rows} != selected:
            raise ValueError("coe_union_not_missing_only")
        receipts.append({"source": name, "plan": str(plan_path.relative_to(ROOT)), "plan_sha256": digest(plan),
                         "inference_sha256": sha(inference_path), "completed_sha256": sha(complete_path),
                         "included_source_identities": len(selected), "included_cells": 2 * len(selected),
                         "whole_source_run_usage_not_target_subset_cost": inference["usage"]})
        for snapshot in ("paper", "current"):
            for source_id in sorted(selected):
                problem_id = "coec_" + snapshot + "_" + source_id.removeprefix("text2opt_")
                row, cell, public_row = index[problem_id], cells[problem_id], target[source_id]
                if (row["source_problem_id"] != source_id or row["snapshot"] != snapshot
                        or cell["source_problem_id"] != source_id or cell["snapshot"] != snapshot
                        or row["family"] != public_row["family"] or cell["family"] != row["family"]
                        or payload_sha256(row["public"]) != plan["public_inputs"][problem_id]
                        or row["public_input_sha256"] != plan["public_inputs"][problem_id]
                        or payload_sha256(dict(row["public"], id=source_id)) != public_row["public_input_sha256"]
                        or row["source_file_sha256"] != public_row["source_file_sha256"]):
                    raise ValueError("coe_union_identity_mismatch")
                status = cell["status"]
                count = blank(); count["planned"] = 1
                if status in ("method_failure", "infrastructure_unavailable"):
                    count[status] = 1
                elif status == "complete":
                    record = read(ROOT / cell["record_path"])
                    if (digest(record) != cell["record_sha256"] or record["problem_id"] != problem_id
                            or record["public_input_sha256"] != row["public_input_sha256"]):
                        raise ValueError("coe_union_record_integrity")
                    count["complete"] = 1
                    count["author_exact"] = int(record["author_accept"])
                    count["scalar_tolerance"] = int(record["tolerance_accept"])
                    count["adapter_supported"] = int(record["adapter_supported"])
                    count["adapter_unsupported"] = int(not record["adapter_supported"])
                else:
                    raise ValueError("coe_union_unknown_cell_status")
                aggregates[snapshot].update(count)
                families[row["family"]][snapshot].update(count)
                scores[problem_id] = {"source": name, "source_problem_id": source_id, "snapshot": snapshot,
                                      "family": row["family"], "status": status,
                                      "author_exact": bool(count["author_exact"]),
                                      "scalar_tolerance": bool(count["scalar_tolerance"]),
                                      "adapter_supported": bool(count["adapter_supported"]),
                                      "public_input_sha256": row["public_input_sha256"]}
    if len(scores) != 80 or any(v["planned"] != 40 for v in aggregates.values()):
        raise ValueError("coe_union_not_exact_40_per_snapshot")
    by_snapshot = {}
    for snapshot, counts in aggregates.items():
        available = 40 - counts["infrastructure_unavailable"]
        by_snapshot[snapshot] = {**dict(counts), "endpoint_denominator_including_method_failures": available,
                                 "author_exact_accuracy": counts["author_exact"] / available if available else None,
                                 "scalar_tolerance_accuracy": counts["scalar_tolerance"] / available if available else None,
                                 "author_exact_success_fraction_all_planned": counts["author_exact"] / 40,
                                 "scalar_tolerance_success_fraction_all_planned": counts["scalar_tolerance"] / 40}
    report = {"schema": "coe-fixed-common40-union-v1", "role": "retrospective_two_family_common_cohort",
              "target_manifest": PUBLIC_MANIFEST, "target_manifest_sha256": sha(ROOT / PUBLIC_MANIFEST),
              "by_snapshot": by_snapshot, "by_family": {k: {s: dict(v) for s, v in x.items()} for k, x in sorted(families.items())},
              "cells": scores, "source_runs": receipts,
              "secondary_objective_field_projection": "Not computed by this zero-solve aggregation; scalar tolerance is not dictionary-field normalization.",
              "claim_guard": "Five old and 35 new source identities per snapshot, no favorable reruns. Primary is original strict scalar-return endpoint, with method/adapter failures retained. Safe-adapter outcomes are not unrestricted native-method failures; no fresh confirmation.",
              "new_model_calls": 0, "new_solver_calls": 0}
    write_json(ROOT / "results/coe_fixed_common40.json", report)
    print(json.dumps({"by_snapshot": by_snapshot, "new_model_calls": 0, "new_solver_calls": 0}))
    return report


if __name__ == "__main__":
    evaluate()
