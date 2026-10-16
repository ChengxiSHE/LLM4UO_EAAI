#!/usr/bin/env python3
"""Zero-call finalizer for an exhausted BinPacking proposal stage.

The original runner predated its LocalRequestFailure catch.  This finalizer
uses only the two completed, ledger-bound proposal responses, records the
third exhausted slot, and performs the already-frozen development evaluation.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.codex_cli_gateway import CodexCliGateway
from llm4or.pipeline import write_json
from llm4or.schema import canonical, digest
from scripts.run_vera_opt_binpacking_proposal import (
    AUTH_PATH, CANDIDATE_PATH, PLAN_PATH, REPORT_PATH, evaluate_candidate,
    load_development_answers, load_public_projection, static_candidate,
)


RECOVERY_PLAN = ROOT / "experiments/vera_opt_binpacking_proposal_recovery_plan.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text()); recovery = json.loads(RECOVERY_PLAN.read_text())
    directory = ROOT / plan["run_directory"]; database_path = directory / "requests.sqlite3"
    expected = {
        "schema": "vera-opt-binpacking-proposal-recovery-plan-v1",
        "role": "zero_api_call_finalize_after_local_format_exhaustion",
        "original_plan_sha256": digest(plan), "ledger_sha256": sha(database_path),
        "finalizer_sha256": sha(Path(__file__)), "allowed_api_calls": 0,
        "selection_rule": "evaluate every completed static-valid proposal; record exhausted slots",
    }
    if recovery != expected:
        raise ValueError("recovery_plan_changed")
    gateway = CodexCliGateway(ROOT, plan, str(AUTH_PATH.relative_to(ROOT)))
    split, questions = load_public_projection(plan)
    scope = f"verabp:SkillProposer:{plan['replicates'][0]}:vera_opt_binpacking_generation1"
    with sqlite3.connect("file:" + str(database_path) + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        metadata = db.execute("SELECT config FROM metadata WHERE id=1").fetchone()
        if not metadata or json.loads(metadata["config"])["plan"] != digest(plan):
            raise ValueError("ledger_plan_mismatch")
        slots = db.execute(
            "SELECT s.slot,r.status,r.response,r.response_hash,r.error FROM slots s "
            "JOIN requests r ON r.key=s.key WHERE s.scope=? ORDER BY s.slot", (scope,),
        ).fetchall()
    if [row["slot"] for row in slots] != [0, 1, 2] \
            or [row["status"] for row in slots] != ["complete", "complete", "exhausted"]:
        raise ValueError("unexpected_slot_states")
    proposals = []; packages = []; stage_summaries = []
    for row in slots:
        stage = row["slot"]
        if row["status"] != "complete":
            stage_summaries.append({"stage": stage + 1, "method_failure": row["error"],
                                    "static_valid": False,
                                    "feedback": ["method_failure:" + row["error"]]})
            continue
        response = json.loads(row["response"])
        if digest(response) != row["response_hash"]:
            raise ValueError("response_hash_mismatch")
        proposal = json.loads(response["text"])
        package, errors = static_candidate(proposal, plan, stage, questions, split)
        proposals.append(proposal)
        if package is not None:
            packages.append((stage, package))
        stage_summaries.append({"stage": stage + 1, "response_sha256": digest(proposal),
                                "static_valid": package is not None,
                                "feedback": errors or ["static validation and answer-free public coverage passed"]})
    answers = load_development_answers(plan, split, questions)
    evaluations = [(stage, package, evaluate_candidate(package, plan, split, questions, answers))
                   for stage, package in packages]
    eligible = [item for item in evaluations if item[2]["exact"] == item[2]["records"]
                and item[2]["metamorphic_passed"] == item[2]["metamorphic_total"]]
    selected = sorted(eligible, key=lambda item: (-item[2]["exact"], -item[2]["adopted"], item[0]))[0] \
        if eligible else None
    report = {"schema": "vera-opt-binpacking-development-v1",
              "role": "outcome_exposed_development_skill_induction",
              "plan_sha256": digest(plan), "recovery_plan_sha256": digest(recovery),
              "api_then_answers_boundary": "all three proposal slots completed or exhausted before answers loaded",
              "stages": stage_summaries,
              "candidates": [{"stage": stage + 1, "skill_sha256": digest(package), **evaluation}
                             for stage, package, evaluation in evaluations],
              "selected_stage": selected[0] + 1 if selected else None,
              "selected_skill_sha256": digest(selected[1]) if selected else None,
              "development_gate_passed": selected is not None, "usage": gateway.summary(),
              "claim_guard": "development only; promotion and confirmation outcomes remain unopened"}
    if selected:
        write_json(CANDIDATE_PATH, {"schema": "vera-opt-binpacking-candidate-v1",
            "role": "automatically_proposed_development_selected_not_yet_promoted",
            "plan_sha256": digest(plan), "recovery_plan_sha256": digest(recovery),
            "skill": selected[1], "skill_sha256": digest(selected[1]),
            "development_evaluation": selected[2]})
    write_json(REPORT_PATH, report)
    status = "completed_candidate_selected" if selected else "completed_no_candidate"
    auth = json.loads(AUTH_PATH.read_text())
    auth.update(status=status, closed_usage=gateway.summary(),
                closed_at=datetime.now(timezone.utc).isoformat(), further_api_calls_authorized=False,
                recovery_plan_sha256=digest(recovery))
    write_json(AUTH_PATH, auth)
    write_json(directory / "completed.json", {"state": status, "plan_sha256": digest(plan),
               "recovery_plan_sha256": digest(recovery), "usage": gateway.summary(), "report": report})
    write_json(directory / "controller.json", {"state": status, "plan_sha256": digest(plan),
                                                 "recovery_plan_sha256": digest(recovery)})
    print(canonical({"state": status, "selected_skill_sha256": report["selected_skill_sha256"],
                     "development_gate_passed": report["development_gate_passed"],
                     "usage": report["usage"]}))


if __name__ == "__main__":
    main()
