"""Evaluate the reference-free V9 template compiler on development data only."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.text2opt_template_compiler import VERSION, solve_template_problem


SPLIT = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
EVALUATOR = ROOT / "data/next_development/text2opt_v8/evaluator.json"
BASE_ROWS = ROOT / "results/private/v8_source_indexed_restart3_20261003/v8_stage1_evaluation_private.json"
PUBLIC_OUTPUT = ROOT / "results/v9_template_development_evaluation.json"
PRIVATE_OUTPUT = ROOT / "results/private/v9_template_development_20261003/rows.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    split = json.loads(SPLIT.read_text())
    evaluator = json.loads(EVALUATOR.read_text())
    references = evaluator["references"]
    structured = [row for row in split["development"] if row["family"] != "resource_allocation"]
    rows = []
    for row in structured:
        solved = solve_template_problem(row["public"])
        reference = references[row["id"]]["theoretical_optimum"]
        matched = solved.get("status") == "optimal" and math.isclose(
            solved["objective"], reference, rel_tol=1e-5, abs_tol=1e-6,
        )
        rows.append({"problem_id": row["id"], "family": row["family"],
                     "status": solved.get("status"), "matched": matched})
    base_rows = json.loads(BASE_ROWS.read_text())
    by_id = {row["problem_id"]: row for row in rows}
    paired = []
    for old in base_rows:
        if old["category"] == "resource_allocation":
            v9 = old["base"]  # explicit fail-closed Base fallback
        else:
            v9 = by_id[old["problem_id"]]["matched"]
        paired.append({"problem_id": old["problem_id"], "family": old["category"],
                       "base": old["base"], "v9": v9})
    corrections = sum(row["v9"] and not row["base"] for row in paired)
    regressions = sum(row["base"] and not row["v9"] for row in paired)
    family = Counter((row["family"], row["matched"]) for row in rows)
    public = {
        "schema": "v9-template-development-evaluation-v1",
        "method_version": VERSION,
        "role": "development_only_not_independent_confirmation",
        "confirmation_outcomes_opened": False,
        "structured_development": {
            "records": len(rows), "correct": sum(row["matched"] for row in rows),
            "accuracy": sum(row["matched"] for row in rows) / len(rows),
            "by_family": {name: {"records": family[name, True] + family[name, False],
                                  "correct": family[name, True]}
                          for name in sorted({row["family"] for row in rows})},
        },
        "frozen_v8_stage1_replay": {
            "records": len(paired), "base_correct": sum(row["base"] for row in paired),
            "v9_correct": sum(row["v9"] for row in paired), "corrections": corrections,
            "regressions": regressions, "net_corrections": corrections-regressions,
            "method_rule": "trusted compiler for recognized structured public text; otherwise unchanged Base",
        },
        "evidence_hashes": {str(path.relative_to(ROOT)): sha(path)
                            for path in (SPLIT, EVALUATOR, BASE_ROWS)},
    }
    write_json(PUBLIC_OUTPUT, public)
    write_json(PRIVATE_OUTPUT, {"schema": "v9-template-development-private-v1",
                                "structured_rows": rows, "paired_rows": paired})
    print(json.dumps(public, sort_keys=True))


if __name__ == "__main__":
    main()
