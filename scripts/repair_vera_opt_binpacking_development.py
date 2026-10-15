#!/usr/bin/env python3
"""Apply the existing outcome-blind recognizer pruning to BinPacking proposals."""

import json
import hashlib
from copy import deepcopy
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.declarative_packing_compiler import validate_configuration
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.vera_opt_binpacking_proposal import package_from_proposal
from llm4or.vera_opt_repair import prune_recognizer_for_public_coverage, VERSION as REPAIR_VERSION
from llm4or.verified_skill_library import validate_skill_package
from scripts.run_vera_opt_binpacking_proposal import (
    AUTH_PATH, CANDIDATE_PATH, PLAN_PATH, REPORT_PATH, evaluate_candidate,
    load_development_answers, load_public_projection,
)


REVALIDATION_PLAN = ROOT / "experiments/vera_opt_binpacking_development_revalidation_plan.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text()); revalidation = json.loads(REVALIDATION_PLAN.read_text())
    if revalidation != {
        "schema": "vera-opt-binpacking-development-revalidation-plan-v1",
        "role": "zero_api_call_rebind_to_exact_trusted_solver_and_public_only_recognizer_repair",
        "proposal_plan_sha256": digest(plan),
        "compiler_sha256": sha(ROOT / "llm4or/declarative_packing_compiler.py"),
        "evaluation_runner_sha256": sha(ROOT / "scripts/run_vera_opt_binpacking_proposal.py"),
        "repair_version": REPAIR_VERSION,
        "repair_script_sha256": sha(Path(__file__)),
        "allowed_api_calls": 0,
        "answer_boundary": "development answers only; promotion and confirmation remain unopened",
    }:
        raise ValueError("revalidation_plan_changed")
    split, questions = load_public_projection(plan)
    development_questions = [questions[record["problem_id"]] for record in split["records"]
                             if record["role"] == "development"]
    directory = ROOT / plan["run_directory"]
    scope = f"verabp:SkillProposer:{plan['replicates'][0]}:vera_opt_binpacking_generation1"
    with sqlite3.connect("file:" + str(directory / "requests.sqlite3") + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT s.slot,r.response,r.response_hash FROM slots s JOIN requests r ON r.key=s.key "
            "WHERE s.scope=? AND r.status='complete' ORDER BY s.slot", (scope,),
        ).fetchall()
    candidates = []
    compiler_sha256 = revalidation["compiler_sha256"]
    registry = {plan["trusted_implementation"]["id"]: compiler_sha256}
    for row in rows:
        response = json.loads(row["response"])
        if digest(response) != row["response_hash"]:
            raise ValueError("response_hash_mismatch")
        proposal = json.loads(response["text"])
        package = package_from_proposal(
            proposal, implementation_sha256=compiler_sha256,
            development_manifest_sha256=plan["split_manifest_sha256"],
            proposer=f"{plan['model']}:{plan['reasoning_effort']}:stage{row['slot'] + 1}",
        )
        validate_configuration(package["implementation"]["configuration"])
        before = digest(package)
        recognizer, repair = prune_recognizer_for_public_coverage(
            package["recognizer"], development_questions,
        )
        package["recognizer"] = recognizer
        validate_skill_package(package, registry)
        from llm4or.declarative_packing_compiler import parse_packing_text
        from llm4or.verified_skill_library import recognizer_matches
        failures = []
        for record in split["records"]:
            if record["role"] != "development":
                continue
            text = questions[record["problem_id"]]
            if not recognizer_matches(package, text, registry):
                failures.append("recognizer_miss")
            else:
                try:
                    parse_packing_text(text, package["implementation"]["configuration"])
                except Exception as exc:
                    failures.append(type(exc).__name__ + ":" + str(exc))
        if failures:
            continue
        candidates.append((row["slot"], package, {"version": REPAIR_VERSION,
            "answer_access": False, "before_sha256": before, "after_sha256": digest(package),
            "recognizer": repair}))
    answers = load_development_answers(plan, split, questions)
    evaluation_plan = deepcopy(plan)
    evaluation_plan["trusted_implementation"] = {
        **plan["trusted_implementation"], "sha256": compiler_sha256,
    }
    evaluations = [(stage, package, repair,
                    evaluate_candidate(package, evaluation_plan, split, questions, answers))
                   for stage, package, repair in candidates]
    eligible = [item for item in evaluations if item[3]["exact"] == item[3]["records"]
                and item[3]["metamorphic_passed"] == item[3]["metamorphic_total"]]
    selected = sorted(eligible, key=lambda item: (-item[3]["exact"], -item[3]["adopted"], item[0]))[0] \
        if eligible else None
    original = json.loads(REPORT_PATH.read_text())
    original["outcome_blind_development_repair"] = [
        {"stage": stage + 1, "skill_sha256": digest(package), "repair": repair, **evaluation}
        for stage, package, repair, evaluation in evaluations
    ]
    original["selected_stage"] = selected[0] + 1 if selected else None
    original["selected_skill_sha256"] = digest(selected[1]) if selected else None
    original["development_gate_passed"] = selected is not None
    original["claim_guard"] = "development only; repair used public text only; promotion and confirmation unopened"
    original["revalidation_plan_sha256"] = digest(revalidation)
    if selected:
        write_json(CANDIDATE_PATH, {"schema": "vera-opt-binpacking-candidate-v1",
            "role": "automatically_proposed_outcome_blind_repaired_development_selected_not_yet_promoted",
            "proposal_plan_sha256": digest(plan), "revalidation_plan_sha256": digest(revalidation),
            "skill": selected[1], "skill_sha256": digest(selected[1]),
            "repair": selected[2], "development_evaluation": selected[3]})
    write_json(REPORT_PATH, original)
    print(json.dumps({"development_gate_passed": selected is not None,
                      "selected_skill_sha256": original["selected_skill_sha256"],
                      "candidate_count": len(evaluations)}, sort_keys=True))


if __name__ == "__main__":
    main()
