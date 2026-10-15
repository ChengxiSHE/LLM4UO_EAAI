"""Verify pins and export label-free inputs for all six selected source versions.

Outputs are local preparation artifacts, not a locked split or evaluated result.
No source code, generated code, or model API is executed. Reference fields are
parsed only as part of their JSON containers and never projected or printed.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.benchmark_inputs import (BASE_PROFILE, complexor_input, flat_input,
                                     input_shape_issues, payload_sha256)

FIELDS = {"IndustryOR": "en_question", "MAMO ComplexLP": "en_question",
          "OptMATH-Bench": "en_question", "OptiBench": "question", "NL4Opt": "en_question"}
SLUGS = {"IndustryOR": "industryor", "MAMO ComplexLP": "mamo_complexlp",
         "OptMATH-Bench": "optmath", "OptiBench": "optibench", "NL4Opt": "nl4opt", "ComplexOR": "complexor"}


def checked_file(path, sha256):
    data = (ROOT / path).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError("source hash mismatch: " + str(path))
    return data


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def scaffold_metadata(text):
    # ast.parse only constructs a syntax tree. It does not run the scaffold.
    tree = ast.parse(text)
    domains = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "cat":
            domains[ast.unparse(node.value)] += 1
    discrete = any(d in {"'Integer'", '"Integer"', "'Binary'", '"Binary"', "LpInteger", "LpBinary"} for d in domains)
    return {"explicit_cat_annotations": dict(domains), "explicit_discrete_declaration": discrete,
            "has_todo": "TODO" in text,
            "interpretation": "Scaffold metadata only, not independently certified problem type or agent-visible base input"}


def prepare_complexor(benchmark):
    source = benchmark["source"]
    manifest = json.loads((ROOT / source["manifest"]).read_text())
    if (manifest["repo"], manifest["revision"]) != (source["repo"], source["revision"]):
        raise ValueError("bundle pin differs from manifest")
    verified = {r["upstream_path"]: checked_file(r["local_path"], r["sha256"]) for r in manifest["records"]}
    entries = [{"path": r["upstream_path"], "sha256": r["sha256"]}
               for r in manifest["records"] if r["upstream_path"].startswith("dataset/ComplexOR/")]
    bundle_hash = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if source["sha256"] != bundle_hash:
        raise ValueError("bundle digest changed")
    public, audit = [], []
    for name in manifest["problem_ids"]:
        folder = f"dataset/ComplexOR/{name}"
        specification = json.loads(verified[folder + "/input_targets.json"])
        samples = json.loads(verified[folder + "/data.json"])
        payload = complexor_input("complexor_" + name, specification, samples)
        public.append(payload)
        audit.append({"id": payload["id"], "upstream_problem_id": name,
                      "source_folder": source["local_path"] + "/" + name,
                      "payload_sha256": payload_sha256(payload), "instances": len(payload["instances"]),
                      "shape_issues": input_shape_issues(payload),
                      "scaffold_audit": scaffold_metadata(verified[folder + "/code_example.py"].decode()),
                      "reference": {"path": source["local_path"] + "/" + name + "/data.json",
                                    "selector": "each sample.output; evaluator-only, not exported"}})
    return public, {"problem_audit": audit, "verified_source_files": len(verified),
                    "source_fields": ["background", "constraints", "objective", "description", "parameters"],
                    "visible_fields": ["description", "parameters.symbol/definition/shape", "data[].input"],
                    "excluded_fields": ["background", "constraints", "objective", "data[].output", "code_example.py"],
                    "parameter_instances": sum(r["instances"] for r in audit),
                    "problems_with_shape_issues": sum(bool(r["shape_issues"]) for r in audit),
                    "shape_issue_count": sum(len(r["shape_issues"]) for r in audit),
                    "problems_with_explicit_discrete_scaffold_declarations": sum(r["scaffold_audit"]["explicit_discrete_declaration"] for r in audit),
                    "scaffold_execution": "never; static syntax inspection only"}


def prepare_flat(benchmark):
    source = benchmark["source"]
    raw = checked_file(source["local_path"], source["sha256"])
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    field = FIELDS[benchmark["name"]]
    slug = SLUGS[benchmark["name"]]
    public = [flat_input(f"{slug}_{i:04d}", row, field) for i, row in enumerate(rows)]
    fields = Counter(k for row in rows for k in row)
    metadata = {}
    for key in ("difficulty", "type"):
        if key in fields:
            metadata[key] = dict(Counter(str(row.get(key)) for row in rows))
    return public, {"verified_source_files": 1, "source_fields": dict(fields),
                    "visible_fields": [field], "excluded_fields": sorted(set(fields) - {field}),
                    "source_metadata_not_sent_to_agent": metadata,
                    "instance_style": "self-contained problem text, no separate instance payload",
                    "problem_audit": [{"id": p["id"], "source_row_index": i,
                                       "payload_sha256": payload_sha256(p)} for i, p in enumerate(public)]}


def main():
    plan = json.loads((ROOT / "experiments/benchmark_plan.json").read_text())
    if plan["api_enabled"] or plan["request_budget_authorized"] != 0:
        raise ValueError("this preparation stage requires API calls disabled")
    expected = set(SLUGS)
    if {b["name"] for b in plan["benchmarks"]} != expected or len(plan["benchmarks"]) != 6:
        raise ValueError("expected exactly six selected benchmarks")
    pending, audits = [], []
    for benchmark in plan["benchmarks"]:
        public, audit = (prepare_complexor(benchmark) if benchmark["name"] == "ComplexOR" else prepare_flat(benchmark))
        if len(public) != benchmark["source_rows_before_split"]:
            raise ValueError("source count differs from plan")
        path = Path("data/prepared_benchmarks") / (SLUGS[benchmark["name"]] + ".json")
        export = {"schema": "benchmark-public-inputs-v1", "profile": BASE_PROFILE,
                  "status": "all_source_rows_not_a_locked_test_split", "problems": public}
        pending.append((ROOT / path, export))
        audits.append({"name": benchmark["name"], "source": benchmark["source"],
                       "source_problems": len(public), "input_profile": BASE_PROFILE,
                       "export": str(path), "final_test_denominator": None,
                       "reference_labels_used_for_selection": False, "rows_removed": 0,
                       "evaluator_ready": False, "solver_coverage_certified": False, **audit})
    # Validate all six sources before writing exports.
    for path, export in pending:
        write_json(path, export)
    report = {"schema": "benchmark-input-audit-v1", "date": "2026-08-31",
              "status": "input_projection_ready_not_experiment_ready", "benchmarks": audits,
              "source_rows_sum_not_independent_test_size": sum(x["source_problems"] for x in audits),
              "actual_model_api_calls": 0, "source_code_executed": False, "local_source_edits": [],
              "limitations": ["Field projection does not establish natural-language correctness or remove embedded answer leakage.",
                             "Parameter shape conflicts are reported without guessing fixes or removing problems.",
                             "Scaffold-assisted results require a separate equally informed comparison profile.",
                             "lp-v1 remains continuous-only with 16 variables and 64 constraint rows.",
                             "Source problem counts are not independent unseen test counts; family splits remain pending.",
                             "Reference audit, status-aware evaluation, MILP/NLP coverage and fresh-family management remain pending."]}
    write_json(ROOT / "data/manifests/benchmark_input_audit.json", report)
    print(json.dumps({"benchmarks": len(audits), "source_problems": report["source_rows_sum_not_independent_test_size"],
                      "complexor_shape_issues": next(a["shape_issue_count"] for a in audits if a["name"] == "ComplexOR"),
                      "actual_model_api_calls": 0}))


if __name__ == "__main__":
    main()
