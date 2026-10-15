"""Create a separate ComplexOR parameter-metadata revision with an audit trail."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.benchmark_inputs import input_shape_issues, payload_sha256
from llm4or.data_revisions import revise_parameter_shapes
from prepare_benchmark_inputs import prepare_complexor, write_json


def main():
    plan = json.loads((ROOT / "experiments/benchmark_plan.json").read_text())
    benchmark = next(b for b in plan["benchmarks"] if b["name"] == "ComplexOR")
    public, audit = prepare_complexor(benchmark)  # verifies the pinned sources
    by_id = {p["id"]: p for p in public}
    file_manifest = json.loads((ROOT / benchmark["source"]["manifest"]).read_text())
    source_records = {r["upstream_path"]: r for r in file_manifest["records"]}

    def evidence(problem, quote, field):
        path = f"dataset/ComplexOR/{problem}/input_targets.json"
        record = source_records[path]
        # Quote occurrence is evidence provenance, not automatic entailment.
        content = (ROOT / record["local_path"]).read_text()
        if quote not in content:
            raise ValueError("review quote absent from pinned source")
        return {"path": record["local_path"], "sha256": record["sha256"],
                "field": field, "quote": quote}

    edits = {
        "complexor_MediaSelectionProblem": [{
            "parameter": "CostOfMedia", "before": ["TargetAudiences"], "after": ["AdvertisingMedia"],
            "rationale": "Cost is defined per media option; eight media and eight costs agree. Only the declared axis is corrected; values and candidate domains are untouched.",
            "evidence": [evidence("MediaSelectionProblem", "Cost of media parameter", "parameters.CostOfMedia.definition"),
                         evidence("MediaSelectionProblem", "The number of advertising media", "parameters.AdvertisingMedia.definition")] }],
        "complexor_nltrans": [
            {"parameter": "Supply", "before": [], "after": ["Origins"],
             "rationale": "The text and definition index supply by origin i, matching the existing five-element array.",
             "evidence": [evidence("nltrans", "amounts of goods available at origin `i`", "parameters.Supply.definition")]},
            {"parameter": "Demand", "before": [], "after": ["Destinations"],
             "rationale": "The text and definition index demand by destination j, matching the existing five-element array.",
             "evidence": [evidence("nltrans", "amounts of goods required at destination `j`", "parameters.Demand.definition")]}]}
    reviews = [{"problem_id": pid, "before_sha256": payload_sha256(by_id[pid]),
                "status": "reviewed_metadata_only", "edits": changes} for pid, changes in edits.items()]
    review_map = {r["problem_id"]: r for r in reviews}
    revised = [revise_parameter_shapes(p, review_map[p["id"]]) if p["id"] in review_map else p for p in public]
    for old, new in zip(public, revised):
        if old["instances"] != new["instances"] or old["text"] != new["text"]:
            raise ValueError("metadata revision changed actual input/text")
    unresolved = [
        {"problem_id": "complexor_fleet", "status": "unresolved_input_semantics",
         "reason": "NumberOfPassengers is stored [4,3,3,4] but declared [Locations,Periods,Locations,Periods]=[3,4,3,4]. Delta is declared [Periods,Locations,Locations,Periods], while its definition names (i,t,j,h). Both time-first and location-first repairs are possible; equal Planes/Periods sizes cannot resolve axis meaning.",
         "needed": "Author-defined tensor axis order and a consistent flight/demand instance. Do not transpose or relabel axes based only on size."},
        {"problem_id": "complexor_net1", "status": "unresolved_input_semantics",
         "reason": "Text defines costs/capacities for city pairs. Cities=2, Links=3, arrays are 2x3 and declarations are Links x Links. No ordered arc endpoint list exists. Relabeling as Cities x Links would fit dimensions but would not define the network.",
         "needed": "A city-pair matrix or explicit arc endpoints with aligned costs/capacities. Do not truncate the third column."},
        {"problem_id": "complexor_netmcol", "status": "unresolved_input_semantics",
         "reason": "City-pair/product text has Cities=2 and Products=5, cost/capacity tensors are 2x5x5 with Links x Links x Products declarations. JointCapacity is 5x5 although city pairs would be 2x2. No arc endpoint mapping explains the extra columns/rows.",
         "needed": "Author-confirmed topology, tensor axis mapping and joint capacities. Do not reshape, crop, or invent links."}]
    # Public input/interface cross-check only. These pinned CoE files were read
    # inertly from the previously downloaded archive; no output label was used.
    coe_revision = "afb89bf602690ea621f13a23c42722f20f653a43"
    upstream_crosscheck = [
        {"path": "dataset/ComplexOR_backup/net1/code_example.py", "sha256": "78f44c241f8155a256da0cd521480c66b688c100b343bf0a652e7d0e95bed626"},
        {"path": "dataset/ComplexOR_backup/net1/sample.json", "sha256": "e86a25301ea745d9a92d19d346a3842e2099d9a8da825968571ee7e48758437b"},
        {"path": "dataset/ComplexOR/netmcol/code_example.py", "sha256": "875bd07c6e7d77cee62204087bdb3c8dd083bf9e9813faee74d3e4c7f9e556c6"},
        {"path": "dataset/ComplexOR/netmcol/sample.json", "sha256": "9ebfba61ba6dde5613933ec722d7bae6dde84835300c6402cb295ea122e6fd82"}]
    for record in upstream_crosscheck:
        record.update(repo="xzymustbexzy/Chain-of-Experts", revision=coe_revision,
                      url=f"https://raw.githubusercontent.com/xzymustbexzy/Chain-of-Experts/{coe_revision}/{record['path']}")
    out = {"schema": "benchmark-public-inputs-v1", "profile": "description_parameters_v1",
           "input_revision": "complexor-parameter-metadata-v1", "status": "all_37_retained_reference_reaudit_pending",
           "problems": revised}
    destination = ROOT / "data/prepared_benchmarks/complexor_parameters_v1.json"
    write_json(destination, out)
    report = {"schema": "complexor-parameter-revision-v1", "source": benchmark["source"],
              "revision": out["input_revision"], "source_problem_count": 37, "retained_problem_count": len(revised),
              "reviewed_edits": reviews, "edited_problems": len(reviews), "shape_edits": sum(len(r["edits"]) for r in reviews),
              "source_shape_issue_count": audit["shape_issue_count"],
              "remaining_shape_issue_count": sum(len(input_shape_issues(p)) for p in revised),
              "unresolved": unresolved, "rows_removed": 0, "numeric_inputs_changed": False,
              "reference_values_read_or_changed": False, "original_source_modified": False,
              "edited_problem_reference_revalidation_required": list(edits),
              "extra_semantic_conflicts_not_detected_by_shape_only": ["fleet Delta axis meaning", "netmcol JointCapacity city-pair interpretation"],
              "upstream_crosscheck": upstream_crosscheck,
              "upstream_crosscheck_findings": [
                  "CoE net1 supplies explicit arc endpoints and a three-city 3x3 instance. ORMind has two cities and 2x3 arrays; substitution would replace the instance, not repair metadata.",
                  "CoE netmcol supplies explicit links but its single-link example uses compressed 1x1x1 arrays despite a city-pair description. It does not uniquely decode ORMind's 2x5x5 tensors."],
              "export": str(destination.relative_to(ROOT)), "export_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
              "input_hashes": [{"id": p["id"], "before": payload_sha256(by_id[p["id"]]), "after": payload_sha256(p)} for p in revised],
              "scope": "Input metadata review by assistant, not independent expert certification or reference validation",
              "actual_model_api_calls": 0}
    write_json(ROOT / "data/revisions/complexor_parameters_v1.json", report)
    print(json.dumps({"retained": len(revised), "edits": report["shape_edits"],
                      "remaining_shape_conflicts": report["remaining_shape_issue_count"], "unresolved_problems": len(unresolved)}))


if __name__ == "__main__":
    main()
