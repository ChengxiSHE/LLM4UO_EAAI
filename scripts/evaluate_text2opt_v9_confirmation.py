"""Score a completed frozen Base/V9 run after every inference checkpoint exists."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.text2opt_v9_evaluation import evaluate_v9_confirmation


RAW = ROOT / "data/raw/text2opt_bench_20261003"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_references(plan):
    references = {}
    for item in plan["selection"]["records"]:
        path = RAW / item["source_file"]
        if sha(path) != item["source_file_sha256"]:
            raise ValueError("v9_reference_source_changed")
        source = json.loads(path.read_text()); result = source.get("gurobi_result", {})
        references[item["problem_id"]] = {
            "solver_status": result.get("solver_status"),
            "theoretical_optimum": result.get("theoretical_optimum"),
        }
    return references


def evaluate(plan, directory):
    completed = json.loads((directory / "inference_complete.json").read_text())
    if completed.get("plan_sha256") != digest(plan):
        raise ValueError("v9_completion_plan_mismatch")
    selected = {row["problem_id"]: row for row in plan["selection"]["records"]}
    if len(completed.get("cells", [])) != len(selected):
        raise ValueError("v9_completion_size_mismatch")
    entries = []
    for cell in completed["cells"]:
        problem_id = cell["problem_id"]
        if problem_id not in selected:
            raise ValueError("v9_unselected_problem")
        saved = json.loads(Path(cell["record_path"]).read_text()); record_hash = digest(saved["record"])
        if saved["record_sha256"] != record_hash or cell["record_sha256"] != record_hash:
            raise ValueError("v9_probe_changed")
        entries.append({"problem_id": problem_id, "category": selected[problem_id]["category"],
                        "probe": saved["record"]})
    public, private = evaluate_v9_confirmation(entries, load_references(plan))
    public.update({"plan_sha256": digest(plan), "gold_programs_executed": False,
                   "outcomes_opened_only_after_inference_complete": True})
    write_json(directory / "evaluation_private.json", {
        "schema": "text2opt-v9-confirmation-private-evaluation-v1",
        "rows": private, "public_summary_sha256": digest(public),
    })
    write_json(ROOT / "results/text2opt_v9_confirmation_evaluation.json", public)
    return public


if __name__ == "__main__":
    plan = json.loads((ROOT / "experiments/text2opt_v9_confirmation_plan.json").read_text())
    report = evaluate(plan, ROOT / plan["run_directory"])
    print(json.dumps({"records": report["records"],
                      "confirmed": report["confirmation_gate"]["confirmed"],
                      "accuracy_delta": report["comparison"]["accuracy_delta"],
                      "paired_one_sided_exact_p": report["comparison"]["paired_one_sided_exact_p"]},
                     sort_keys=True))
