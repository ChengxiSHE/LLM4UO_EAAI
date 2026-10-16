#!/usr/bin/env python3
"""Owner-custody paired scoring for frozen TSP confirmation candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.schema import digest
from llm4or.tsp_paired_evaluation import pair_tsp_evaluations
from llm4or.tsp_static_evaluation import evaluate_tsp_static
from scripts.evaluate_tsp_constraint_promotion import bind_role_references


PLAN = ROOT / "experiments/tsp_constraint_confirmation_evaluation_plan_20261014.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _encoded(value) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _write_new(path: Path, value) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_encoded(value))


def evaluate_plan(plan: dict, root=ROOT) -> tuple[dict, dict]:
    root = Path(root).resolve()
    if (
        plan.get("schema") != "tsp-constraint-confirmation-evaluation-plan-v1"
        or plan.get("candidate_inference_complete") is not True
        or plan.get("confirmation_reference_access_authorized") is not True
        or plan.get("parser_tuning_after_candidate_freeze") is not False
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
        "reference_binder_script": "reference_binder_script_sha256",
        "upstream_evaluator": "upstream_evaluator_sha256",
        "candidate_plan": "candidate_plan_sha256",
    }
    for path_key, hash_key in pinned.items():
        if _sha(root / plan[path_key]) != plan[hash_key]:
            raise ValueError(path_key + "_pin")

    split = json.loads((root / plan["split_file"]).read_text())
    candidates = json.loads((root / plan["candidate_file"]).read_text())
    static_candidates = candidates.get("static_rows")
    skill_candidates = candidates.get("skill_rows")
    if (
        type(static_candidates) is not list
        or type(skill_candidates) is not list
        or len(static_candidates) != 140
        or len(skill_candidates) != 140
    ):
        raise ValueError("candidate_schema")
    source_text = (root / plan["source_file"]).read_text()
    references = bind_role_references(
        split, static_candidates, source_text, "confirmation"
    )
    static_public, static_rows = evaluate_tsp_static(
        static_candidates, references
    )
    skill_public, skill_rows = evaluate_tsp_static(skill_candidates, references)
    paired_public, paired_rows = pair_tsp_evaluations(static_rows, skill_rows)
    candidate_report = json.loads((root / plan["candidate_report"]).read_text())
    public = {
        "schema": "tsp-constraint-confirmation-evaluation-v1",
        "version": "tsp-constraint-confirmation-evaluation-v1",
        "role": "sealed_within_source_size_confirmation",
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
        "static_route_counts": candidate_report["static_route_counts"],
        "skill_route_counts": candidate_report["skill_route_counts"],
        "static_adopted": static_public["adopted"],
        "skill_adopted": skill_public["adopted"],
        "static_rows_sha256": digest(static_rows),
        "skill_rows_sha256": digest(skill_rows),
        "paired_rows_sha256": digest(paired_rows),
        "confirmation_reference_answer_accessed": True,
        "model_requests": 0,
        "api_requests": 0,
        "new_candidate_solver_calls": 0,
        "claim_guard": (
            "This is sealed size-13--19 confirmation within the same pinned "
            "OPT-Engine source and constraint-augmentation family. It confirms "
            "prospective size transfer but is not independent cross-source evidence."
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
