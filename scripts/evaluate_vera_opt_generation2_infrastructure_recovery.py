#!/usr/bin/env python3
"""Combine objective infrastructure recovery with the frozen primary records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.vera_opt_confirmation_evaluation import evaluate_confirmation


OUTPUT = ROOT / "results/vera_opt_generation2_confirmation_recovery.json"


def evaluate(plan: dict, directory: Path) -> dict:
    complete = json.loads((directory / "inference_complete.json").read_text())
    if complete["plan_sha256"] != digest(plan) or len(complete["cells"]) != 3:
        raise ValueError("recovery_inference_incomplete")
    recovered = {}
    for cell in complete["cells"]:
        saved = json.loads(Path(cell["record_path"]).read_text())
        if digest(saved["record"]) != cell["record_sha256"]:
            raise ValueError("recovery_checkpoint_changed")
        recovered[cell["problem_id"]] = saved["record"]
    original_plan = json.loads((ROOT / plan["original_plan"]).read_text())
    old_complete = json.loads((ROOT / plan["original_run_directory"] /
                               "inference_complete.json").read_text())
    cells = {cell["problem_id"]: cell for cell in old_complete["cells"]}
    entries = []
    for item in original_plan["selection"]["records"]:
        problem_id = item["problem_id"]
        if problem_id in recovered:
            probe = recovered[problem_id]
        else:
            saved = json.loads(Path(cells[problem_id]["record_path"]).read_text())
            probe = saved["record"]
        entries.append({"problem_id": problem_id, "category": item["category"], "probe": probe})
    split = json.loads((ROOT / plan["split_manifest"]).read_text())
    metadata = {row["source_row"]: row for row in split["records"]
                if row["role"] == "confirmation"}; references = {}
    for line_number, line in enumerate((ROOT / plan["source_file"]).read_text().splitlines(), 1):
        meta = metadata.get(line_number)
        if meta is None:
            continue
        source = json.loads(line)
        if hashlib.sha256(source["question"].encode()).hexdigest() != meta["question_sha256"] \
                or digest(source["answer"]) != meta["answer_sha256"]:
            raise ValueError("recovery_reference_changed")
        references[meta["problem_id"]] = float(source["answer"])
    public, private = evaluate_confirmation(entries, references, alpha=plan["alpha_spend"])
    public["schema"] = "vera-opt-generation2-confirmation-recovery-sensitivity-v1"
    public["plan_sha256"] = digest(plan); public["primary_plan_sha256"] = plan["original_plan_sha256"]
    public["primary_report_sha256"] = plan["original_report_sha256"]
    public["recovered_problem_count"] = 3; public["private_rows_sha256"] = digest(private)
    public["claim_guard"] = (
        "Post-lock infrastructure-only sensitivity; not the preregistered primary result. "
        "Selection used only the Base infrastructure flag and no correctness label."
    )
    write_json(directory / "recovery_private_rows.json", private); write_json(OUTPUT, public)
    return public


if __name__ == "__main__":
    plan = json.loads((ROOT / "experiments/vera_opt_generation2_infrastructure_recovery_plan.json").read_text())
    print(json.dumps(evaluate(plan, ROOT / plan["run_directory"]), sort_keys=True))
