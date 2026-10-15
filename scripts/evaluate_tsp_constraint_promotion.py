#!/usr/bin/env python3
"""Owner-custody paired scoring for frozen TSP constraint promotion candidates."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.schema import digest
from llm4or.tsp_paired_evaluation import pair_tsp_evaluations
from llm4or.tsp_static_evaluation import evaluate_tsp_static


PLAN = ROOT / "experiments/tsp_constraint_promotion_evaluation_plan_20261014.json"
SOURCE_FIELDS = {
    "answer",
    "constraint_type",
    "experimental_type",
    "problem_class",
    "question",
    "size",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _encoded(value) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def _write_new(path: Path, value) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_encoded(value))


def bind_role_references(
    split: dict, candidates: list[dict], source_text: str, role: str
) -> dict[str, float]:
    if role not in {"development", "promotion", "confirmation"}:
        raise ValueError("role")
    if type(split) is not dict or type(split.get("public_records")) is not list:
        raise ValueError("split_schema")
    selected_rows = [row for row in split["public_records"] if row.get("role") == role]
    selected = {row["problem_id"]: row for row in selected_rows}
    candidate_by_id = {
        row.get("problem_id"): row
        for row in candidates
        if type(row) is dict and type(row.get("problem_id")) is str
    }
    if (
        not selected
        or len(selected) != len(selected_rows)
        or set(candidate_by_id) != set(selected)
        or len(candidate_by_id) != len(candidates)
    ):
        raise ValueError("candidate_inventory")
    for problem_id, candidate in candidate_by_id.items():
        expected = selected[problem_id]
        if (
            candidate.get("size") != expected.get("size")
            or candidate.get("question_sha256") != expected.get("question_sha256")
        ):
            raise ValueError("candidate_binding")

    within_size = defaultdict(int)
    references = {}
    for line in source_text.splitlines():
        source = json.loads(line)
        if type(source) is not dict or set(source) != SOURCE_FIELDS:
            raise ValueError("source_fields")
        if source["experimental_type"] != "constraint_augmentation":
            raise ValueError("source_tag")
        if source["problem_class"] != "TSP":
            continue
        size = source["size"]
        if type(size) is not int or not 4 <= size <= 19:
            raise ValueError("source_size")
        index = within_size[size]
        within_size[size] += 1
        problem_id = (
            f"optengine_tsp_constraint_augmentation_s{size:02d}_i{index:02d}"
        )
        expected = selected.get(problem_id)
        if expected is None:
            continue
        question = source["question"]
        if (
            expected.get("within_size_index") != index
            or type(question) is not str
            or hashlib.sha256(question.encode()).hexdigest()
            != expected.get("question_sha256")
        ):
            raise ValueError("question_binding")
        answer = source["answer"]
        if type(answer) not in (int, float) or not math.isfinite(answer):
            raise ValueError("reference_value")
        references[problem_id] = float(answer)
    if set(references) != set(selected):
        raise ValueError("reference_inventory")
    return references


def evaluate_plan(plan: dict, root=ROOT) -> tuple[dict, dict]:
    root = Path(root).resolve()
    if (
        plan.get("schema") != "tsp-constraint-promotion-evaluation-plan-v1"
        or plan.get("candidate_inference_complete") is not True
        or plan.get("promotion_reference_access_authorized") is not True
        or plan.get("confirmation_reference_access_authorized") is not False
    ):
        raise ValueError("plan_schema")
    pinned = {
        "split_file": "split_sha256",
        "source_file": "source_sha256",
        "candidate_file": "candidate_sha256",
        "candidate_report": "candidate_report_sha256",
        "evaluation_module": "evaluation_module_sha256",
        "paired_module": "paired_module_sha256",
        "evaluation_script": "evaluation_script_sha256",
        "upstream_evaluator": "upstream_evaluator_sha256",
    }
    for path_key, hash_key in pinned.items():
        if _sha(root / plan[path_key]) != plan[hash_key]:
            raise ValueError(path_key + "_pin")
    split = json.loads((root / plan["split_file"]).read_text())
    candidates = json.loads((root / plan["candidate_file"]).read_text())
    static_candidates = candidates.get("static_rows")
    skill_candidates = candidates.get("skill_rows")
    if type(static_candidates) is not list or type(skill_candidates) is not list:
        raise ValueError("candidate_schema")
    source_text = (root / plan["source_file"]).read_text()
    references = bind_role_references(split, static_candidates, source_text, "promotion")
    static_public, static_rows = evaluate_tsp_static(static_candidates, references)
    skill_public, skill_rows = evaluate_tsp_static(skill_candidates, references)
    paired_public, paired_rows = pair_tsp_evaluations(static_rows, skill_rows)
    candidate_report = json.loads((root / plan["candidate_report"]).read_text())
    public = {
        "schema": "tsp-constraint-promotion-evaluation-v1",
        "version": "tsp-constraint-promotion-evaluation-v1",
        "role": "prospective_within_source_size_transfer_promotion",
        "plan_sha256": digest(plan),
        "split_sha256": plan["split_sha256"],
        "candidate_sha256": plan["candidate_sha256"],
        "records": paired_public["records"],
        "static_correct": paired_public["control_correct"],
        "static_accuracy": paired_public["control_accuracy"],
        "skill_correct": paired_public["skill_correct"],
        "skill_accuracy": paired_public["skill_accuracy"],
        "accuracy_delta": paired_public["accuracy_delta"],
        "corrections": paired_public["corrections"],
        "regressions": paired_public["regressions"],
        "paired_one_sided_exact_p": paired_public["paired_one_sided_exact_p"],
        "zero_regression_one_sided_95_upper": paired_public[
            "zero_regression_one_sided_95_upper"
        ],
        "by_size": paired_public["by_size"],
        "skill_route_counts": candidate_report["skill_route_counts"],
        "static_adopted": static_public["adopted"],
        "skill_adopted": skill_public["adopted"],
        "static_rows_sha256": digest(static_rows),
        "skill_rows_sha256": digest(skill_rows),
        "paired_rows_sha256": digest(paired_rows),
        "promotion_reference_answer_accessed": True,
        "confirmation_reference_answer_accessed": False,
        "model_requests": 0,
        "api_requests": 0,
        "new_candidate_solver_calls": 0,
        "claim_guard": (
            "This is prospective size transfer within the same pinned OPT-Engine "
            "constraint-augmentation source and perturbation family. It is stronger than "
            "development evidence but is not independent cross-source confirmation."
        ),
    }
    private = {
        "static_rows": static_rows,
        "skill_rows": skill_rows,
        "paired_rows": paired_rows,
    }
    return public, private


def main() -> None:
    plan = json.loads(PLAN.read_text())
    public, private = evaluate_plan(plan, ROOT)
    _write_new(ROOT / plan["private_output"], private)
    _write_new(ROOT / plan["public_output"], public)
    print(
        json.dumps(
            {
                key: public[key]
                for key in (
                    "records",
                    "static_correct",
                    "static_accuracy",
                    "skill_correct",
                    "skill_accuracy",
                    "accuracy_delta",
                    "corrections",
                    "regressions",
                    "paired_one_sided_exact_p",
                )
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
