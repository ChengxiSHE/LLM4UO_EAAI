#!/usr/bin/env python3
"""Open BinPacking promotion answers only after inference is complete."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.vera_opt_promotion_evaluation import evaluate_promotion
from llm4or.verified_skill_library import make_promotion_event

PUBLIC_REPORT = ROOT / "results/vera_opt_binpacking_promotion.json"
EVENT = ROOT / "experiments/vera_opt_binpacking_promotion_event.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_references(plan: dict, inference: dict) -> dict[str, float]:
    selected = {row["problem_id"]: row for row in plan["selection"]["records"]}
    if len(inference.get("cells", [])) != len(selected) \
            or {cell["problem_id"] for cell in inference["cells"]} != set(selected):
        raise ValueError("promotion_inference_incomplete")
    split = json.loads((ROOT / plan["split_manifest"]).read_text())
    metadata = {row["problem_id"]: row for row in split["records"] if row["role"] == "promotion"}
    if set(metadata) != set(selected):
        raise ValueError("promotion_split_binding")
    by_row = {row["source_row"]: row for row in metadata.values()}; references = {}
    for line_number, line in enumerate((ROOT / plan["source_file"]).read_text().splitlines(), 1):
        meta = by_row.get(line_number)
        if meta is None:
            continue
        source = json.loads(line)
        if hashlib.sha256(source["question"].encode()).hexdigest() != meta["question_sha256"] \
                or digest(source["answer"]) != meta["answer_sha256"]:
            raise ValueError("promotion_reference_changed")
        references[meta["problem_id"]] = float(source["answer"])
    if set(references) != set(selected):
        raise ValueError("promotion_references_missing")
    return references


def evaluate(plan: dict, directory: Path) -> dict:
    inference_path = directory / "inference_complete.json"
    if not inference_path.exists():
        raise ValueError("promotion_inference_not_complete")
    inference = json.loads(inference_path.read_text())
    if inference.get("plan_sha256") != digest(plan):
        raise ValueError("promotion_inference_plan_binding")
    references = load_references(plan, inference); entries = []
    for cell in inference["cells"]:
        saved = json.loads(Path(cell["record_path"]).read_text())
        if saved["record_sha256"] != cell["record_sha256"] \
                or digest(saved["record"]) != cell["record_sha256"]:
            raise ValueError("promotion_checkpoint_changed")
        entries.append({"problem_id": cell["problem_id"], "category": cell["category"],
                        "probe": saved["record"]})
    public, private = evaluate_promotion(entries, references, alpha=plan["alpha_spend"])
    public["plan_sha256"] = digest(plan); public["skill_sha256"] = plan["skill_sha256"]
    public["private_rows_sha256"] = digest(private)
    public["claim_guard"] = "Second-family hidden promotion; not final confirmation."
    write_json(directory / "promotion_private_rows.json", private); write_json(PUBLIC_REPORT, public)
    candidate = json.loads((ROOT / plan["candidate_file"]).read_text())
    event = make_promotion_event(
        generation=1, previous_event_sha256=None, skill=candidate["skill"],
        trusted_implementations={plan["trusted_implementation"]["id"]:
                                 plan["trusted_implementation"]["sha256"]},
        static_evidence_sha256=sha(ROOT / plan["candidate_file"]),
        replay_evidence_sha256=sha(ROOT / "results/vera_opt_binpacking_development.json"),
        promotion_evidence_sha256=digest(public),
        decision="accepted" if public["promotion_gate"]["promoted"] else "rejected",
    )
    write_json(EVENT, event); return public


if __name__ == "__main__":
    plan = json.loads((ROOT / "experiments/vera_opt_binpacking_promotion_plan.json").read_text())
    print(json.dumps(evaluate(plan, ROOT / plan["run_directory"]), sort_keys=True))
