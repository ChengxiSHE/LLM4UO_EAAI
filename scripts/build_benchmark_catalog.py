"""Create one public-input support audit record per planned source problem."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.benchmark_registry import load_public_registry, triage
from llm4or.pipeline import write_json
from llm4or.schema import digest


def main():
    reviews = json.loads((ROOT / "data/revisions/complexor_public_review_v1.json").read_text())
    reviewed = {r["id"]: r for r in reviews["rows"]}
    rows = []
    for record in load_public_registry(ROOT):
        item = {k: v for k, v in record.items() if k != "public"}
        item.update(triage(record["public"]))
        if item["id"] in reviewed:
            review = reviewed[item["id"]]
            if review["input_sha256"] != item["input_sha256"]:
                raise ValueError("stale public semantic review")
            item["public_manual_review"] = review
        item.update(denominator_included=True, reference_status="requires_separate_evaluator_audit")
        rows.append(item)
    report = {"schema": "benchmark-support-catalog-v1", "status": "complete_inventory_conservative_triage_not_type_certification",
              "input_selection": "pinned_sources_plus_complexor_parameter_metadata_v1", "records": rows,
              "source_records": len(rows), "independent_test_denominator": None,
              "counts": {name: dict(Counter(r["type_triage"] for r in rows if r["benchmark"] == name)) for name in sorted({r["benchmark"] for r in rows})},
              "input_ambiguities": [r["id"] for r in rows if r["input_status"] != "ready"],
              "registry_hash": digest([{k: r[k] for k in ("id", "input_sha256", "input_revision")} for r in rows]),
              "rules_use_only_public_input": True, "reference_answers_used": False, "actual_model_api_calls": 0}
    write_json(ROOT / "data/manifests/benchmark_support_catalog.json", report)
    print(json.dumps({k: report[k] for k in ("source_records", "counts", "input_ambiguities")}, ensure_ascii=False))


if __name__ == "__main__": main()
