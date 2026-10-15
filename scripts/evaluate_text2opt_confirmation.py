"""Score a completed frozen Text2Opt run; never imported by inference code."""
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.text2opt_evaluation import evaluate_confirmation


RAW = ROOT / "data/raw/text2opt_bench_20261003"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_references(plan):
    references = {}
    for item in plan["selection"]["records"]:
        path = RAW / item["source_file"]
        if sha(path) != item["source_file_sha256"]:
            raise ValueError("text2opt_reference_source_changed")
        # The upstream JSON is untrusted data.  Only two scalar evaluator
        # fields are retained; gold_solution is never executed or exported.
        source = json.loads(path.read_text())
        result = source.get("gurobi_result", {})
        references[item["problem_id"]] = {
            "solver_status": result.get("solver_status"),
            "theoretical_optimum": result.get("theoretical_optimum"),
        }
    return references


def evaluate(plan, directory):
    completed = json.loads((directory / "inference_complete.json").read_text())
    if completed.get("plan_sha256") != digest(plan):
        raise ValueError("text2opt_completion_plan_mismatch")
    selected = {row["problem_id"]: row for row in plan["selection"]["records"]}
    if len(completed.get("cells", [])) != len(selected):
        raise ValueError("text2opt_completion_size_mismatch")
    entries = []
    for cell in completed["cells"]:
        pid = cell["problem_id"]
        if pid not in selected:
            raise ValueError("text2opt_completion_unselected_problem")
        path = Path(cell["record_path"])
        saved = json.loads(path.read_text())
        if saved["record_sha256"] != digest(saved["record"]) or cell["record_sha256"] != digest(saved["record"]):
            raise ValueError("text2opt_probe_changed")
        entries.append({
            "problem_id": pid, "category": selected[pid]["category"], "probe": saved["record"],
        })
    public, private_rows = evaluate_confirmation(entries, load_references(plan))
    public.update({
        "plan_sha256": digest(plan),
        "protocol_sha256": plan["evaluation"]["protocol_sha256"],
        "gold_programs_executed": False,
    })
    private = {"schema": "text2opt-confirmation-private-evaluation-v1", "rows": private_rows,
               "public_summary_sha256": digest(public)}
    write_json(directory / "evaluation_private.json", private)
    write_json(ROOT / "results/text2opt_confirmation_evaluation.json", public)
    return public


if __name__ == "__main__":
    plan = json.loads((ROOT / "experiments/text2opt_confirmation_run_plan.json").read_text())
    report = evaluate(plan, ROOT / plan["run_directory"])
    print(json.dumps({
        "records": report["records"],
        "confirmed": report["joint_confirmation_gate"]["confirmed"],
        "holm_adjusted_p": report["joint_confirmation_gate"]["holm_adjusted_p"],
    }, sort_keys=True))
