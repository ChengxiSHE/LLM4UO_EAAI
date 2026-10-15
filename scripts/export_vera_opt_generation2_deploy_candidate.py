#!/usr/bin/env python3
"""Squash development ancestry into a first deployable promotion candidate."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.verified_skill_library import validate_skill_package


SOURCE = ROOT / "experiments/vera_opt_generation2_candidate.json"
REPORT = ROOT / "results/vera_opt_generation2_development.json"
OUTPUT = ROOT / "experiments/vera_opt_generation2_deploy_candidate.json"
COMPILER = ROOT / "llm4or/declarative_selection_compiler.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source = json.loads(SOURCE.read_text()); report = json.loads(REPORT.read_text())
    if not report.get("development_gate_passed") or source["skill_sha256"] != report["child_skill_sha256"]:
        raise ValueError("generation2_not_deployable")
    compiler_sha = sha(COMPILER)
    child = validate_skill_package(source["skill"], {"declarative.selection.v1": compiler_sha})
    deploy = deepcopy(child); deploy["version"] = 1; deploy["parent_sha256"] = None
    deploy["provenance"] = {
        "proposer": "vera-opt-generation2-squash",
        "development_manifest_sha256": child["provenance"]["development_manifest_sha256"],
        "proposal_sha256": digest({
            "generation1_skill_sha256": report["parent_skill_sha256"],
            "generation2_skill_sha256": report["child_skill_sha256"],
            "generation2_plan_sha256": report["plan_sha256"],
        }),
    }
    deploy = validate_skill_package(deploy, {"declarative.selection.v1": compiler_sha})
    write_json(OUTPUT, {
        "schema": "vera-opt-generation2-deploy-candidate-v1",
        "role": "squashed_first_deployment_candidate_not_yet_confirmed",
        "research_ancestry": {
            "generation1_skill_sha256": report["parent_skill_sha256"],
            "generation2_skill_sha256": report["child_skill_sha256"],
            "generation2_development_report_sha256": sha(REPORT),
        },
        "skill": deploy, "skill_sha256": digest(deploy),
    })
    print(json.dumps({"skill_sha256": digest(deploy),
                      "research_child_sha256": digest(child)}, sort_keys=True))


if __name__ == "__main__":
    main()
