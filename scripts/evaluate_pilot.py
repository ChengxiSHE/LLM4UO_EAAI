"""Post-inference evaluation with explicit semantic/unit mappings reviewed offline.

Mappings name decisions by their meaning, never by which permutation earns a
higher score. No API calls, no corrections to inference artifacts, no feedback
into the running harness.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.evaluator import evaluate
from llm4or.pipeline import write_json
from llm4or.schema import digest, model

RUN = ROOT / "results/private/pilot_s1_20260831"
BRANCHES = ("initial", "teacher_model", "baseline_final", "semantic_final")


def align(candidate, reference, review):
    """Rename IDs/meaning strings and verified unit synonyms; no coefficient edits."""
    original = model(candidate)
    reference = model(reference)
    if (review["candidate_hash"] != digest(original)
            or review["reference_hash"] != digest(reference)
            or review["status"] != "semantic_mapping_reviewed"
            or not review["rationale"]):
        raise ValueError("mapping provenance missing")
    mapping = review["variable_mapping"]
    source = {v["id"]: v for v in original["variables"]}
    target = {v["id"]: v for v in reference["variables"]}
    if set(mapping) != set(source) or set(mapping.values()) != set(target) or len(mapping) != len(target):
        raise ValueError("mapping is not a bijection")
    if review["unit_scale"] != 1 or review["objective_scale"] != 1:
        raise ValueError("unit scaling is not implemented; only reviewed synonyms")
    for old, new in mapping.items():
        if source[old]["domain"] != target[new]["domain"]:
            raise ValueError("domain mismatch cannot be normalized away")
    result = deepcopy(original)
    for v in result["variables"]:
        r = target[mapping[v["id"]]]
        # Bounds are ALWAYS retained from the candidate, never from the reference.
        v.update(id=r["id"], meaning=r["meaning"], unit=r["unit"])
    for row in result["constraints"]:
        row["coefficients"] = {mapping[k]: v for k, v in row["coefficients"].items()}
    obj = result["objective"]
    obj["coefficients"] = {mapping[k]: v for k, v in obj["coefficients"].items()}
    obj["unit"] = reference["objective"]["unit"]
    return model(result)


def main():
    if not (RUN / "inference_complete.json").exists():
        raise SystemExit("Complete all inference before opening evaluator references")
    reviews = json.loads((RUN / "mapping_review.json").read_text())
    public = [json.loads(line) for line in (ROOT / "data/pilot/public/problems.jsonl").read_text().splitlines()]
    records = []
    for problem in public:
        pid = problem["id"]
        inference = json.loads((RUN / (pid + ".inference.json")).read_text())
        audit = json.loads((ROOT / "data/pilot/evaluator" / (pid + ".json")).read_text())
        reference = audit["reference"]
        scores = {}
        evaluated = {}
        for branch in BRANCHES:
            candidate = inference.get(branch)
            if candidate is None:
                scores[branch] = {"formulation_check": "no_valid_model", "objective_match_proxy": None}
                continue
            key = pid + ":" + digest(candidate)
            if key not in reviews:
                scores[branch] = {"formulation_check": "mapping_unresolved", "objective_match_proxy": None}
                continue
            mapped = align(candidate, reference, reviews[key])
            if key not in evaluated:
                evaluated[key] = evaluate(mapped, reference)
            score = deepcopy(evaluated[key])
            score.update(raw_candidate_hash=digest(candidate), mapping_review_hash=digest(reviews[key]))
            scores[branch] = score
        record = {"problem": pid, "status": inference["status"], "errors": inference["errors"],
                  "evidence_status": inference.get("evidence", {}).get("status"),
                  "feasibility_witness": any(inference.get("evidence", {}).get(k, {}).get("status") == "witness"
                                             for k in ("left_to_right", "right_to_left")),
                  "gate": inference.get("repair_gate", {}), "scores": scores}
        write_json(RUN / (pid + ".evaluation.json"), record)
        records.append(record)
    totals = {}
    for branch in BRANCHES:
        checks = [r["scores"][branch] for r in records]
        totals[branch] = {"denominator": len(public),
                          "objective_match": sum(c["objective_match_proxy"] is True for c in checks),
                          "objective_unresolved": sum(c["objective_match_proxy"] is None for c in checks),
                          "formulation_match": sum(c["formulation_check"] == "same_within_tolerance_exact_objective" for c in checks),
                          "formulation_different": sum(c["formulation_check"] == "different" for c in checks),
                          "formulation_unresolved": sum(c["formulation_check"] not in {"same_within_tolerance_exact_objective", "different"} for c in checks)}
    with sqlite3.connect(RUN / "requests.sqlite3") as con:
        con.row_factory = sqlite3.Row
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        attempts = list(con.execute("SELECT * FROM attempts ORDER BY created"))
    assert integrity == "ok"
    assert len(attempts) <= 60
    assert all(sum(a["problem"] == p["id"] for a in attempts) <= 6 for p in public)
    assert all(sum(a["problem"] == p["id"] and a["key"].endswith(":retry1") for a in attempts) <= 1 for p in public)
    assert all(set(json.loads(a["request"])["problem"]) == {"id", "text"} for a in attempts)
    actual_usage = []
    for a in attempts:
        if a["response"]:
            response = json.loads(a["response"])
            assert digest(response) == a["response_hash"]
            if response.get("usage_source") == "provider_reported":
                assert response["completion_tokens"] <= 2048
                assert response["request_utf8_bytes"] <= 24000
                actual_usage.append(response)
    report = {"kind": "ten_question_development_feasibility_pilot_not_superiority_test",
              "problem_count": len(public), "reference_status": "assistant_reviewed_not_independent_expert_gold",
              "totals": totals, "records": records,
              "request_count": len(attempts), "attempts_with_usage": len(actual_usage),
              "prompt_tokens": sum(r["prompt_tokens"] for r in actual_usage),
              "completion_tokens": sum(r["completion_tokens"] for r in actual_usage),
              "total_tokens": sum(r["total_tokens"] for r in actual_usage),
              "api_errors": [{"key": a["key"], "status": a["status"], "error": a["error"]} for a in attempts if a["status"] != "complete"],
              "database_integrity": integrity, "inference_gold_fields_absent": True,
              "evaluated_after_all_inference": True, "cross_task_evolution": False,
              "monetary_cost": None, "equal_token_comparison": False,
              "run_wall_seconds": max(a["finished"] or a["created"] for a in attempts) - min(a["created"] for a in attempts)}
    write_json(RUN / "evaluation_summary.json", report)
    # Public summary omits raw provider responses and private runtime records.
    write_json(ROOT / "results/pilot_s1_summary.json", {k: v for k, v in report.items() if k != "records"})
    print(json.dumps({k: report[k] for k in ("totals", "request_count", "total_tokens", "api_errors")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
