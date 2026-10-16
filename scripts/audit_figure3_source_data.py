#!/usr/bin/env python3
"""Verify Figure 3 aggregate Source Data against public RetailOpt projections."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "experiments" / "retailopt190_short_full_evaluation_projection_v1_20261017.json"
BLIND = ROOT / "experiments" / "retailopt190_label_blind_evaluation_projection_v1_20261017.json"
DIAGNOSTICS = ROOT / "experiments" / "retailopt190_decision_diagnostics_20261017.json"
SUMMARY = ROOT / "manuscript" / "source_data" / "figure3_retailopt_summary.csv"
DIAGNOSTIC_TABLE = ROOT / "manuscript" / "source_data" / "figure3_retailopt_diagnostics.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expected_summary(projection: dict[str, Any], role: str) -> list[dict[str, str]]:
    study = str(projection["study"])
    output: list[dict[str, str]] = []
    for unit, source_key in (("instance", "instances"), ("archetype", "archetypes")):
        base = projection[source_key]["base_short"]
        knowledge = projection[source_key]["knowledge_short"]
        denominator = int(base["total"])
        base_correct = int(base["correct"] if unit == "instance" else base["fully_correct"])
        knowledge_correct = int(knowledge["correct"] if unit == "instance" else knowledge["fully_correct"])
        paired = projection["paired_instances" if unit == "instance" else "paired_archetypes"]
        corrections = int(paired["corrections"])
        regressions = int(paired["regressions"])
        both_correct = base_correct - regressions
        both_wrong = denominator - both_correct - corrections - regressions
        output.append({
            "study": study,
            "study_role": role,
            "unit": unit,
            "denominator": str(denominator),
            "base_correct": str(base_correct),
            "knowledge_correct": str(knowledge_correct),
            "both_correct": str(both_correct),
            "corrections": str(corrections),
            "regressions": str(regressions),
            "both_wrong": str(both_wrong),
            "one_sided_exact_mcnemar_p": (
                repr(float(paired["one_sided_exact_mcnemar_p"])) if unit == "archetype" else ""
            ),
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    primary = json.loads(PRIMARY.read_text(encoding="utf-8"))
    blind = json.loads(BLIND.read_text(encoding="utf-8"))
    diagnostics = json.loads(DIAGNOSTICS.read_text(encoding="utf-8"))
    expected = expected_summary(primary, "prospective independent confirmation")
    expected += expected_summary(blind, "post hoc same-benchmark robustness")
    summary_matches = rows(SUMMARY) == expected

    selected = []
    primary_cards = diagnostics["studies"]["prospective_primary"]["card_fully_correct_over_routed_archetypes"]
    for label, key in (("Core flow card", "retail.core.flow.v1"), ("Substitution card", "retail.substitution.v1")):
        base = primary_cards["base_short"][key]
        knowledge = primary_cards["knowledge_short"][key]
        selected.append({
            "study": "prospective_primary",
            "diagnostic": label,
            "denominator": str(base["total"]),
            "base_correct": str(base["correct"]),
            "knowledge_correct": str(knowledge["correct"]),
            "analysis_role": "post hoc aggregate localization",
        })
    diagnostic_matches = rows(DIAGNOSTIC_TABLE) == selected
    report = {
        "schema": "llm4or-figure3-source-data-audit-v1",
        "status": "passed" if summary_matches and diagnostic_matches else "failed",
        "checks": {
            "summary_exactly_reconstructed": summary_matches,
            "diagnostics_exactly_reconstructed": diagnostic_matches,
            "summary_rows": len(expected),
            "diagnostic_rows": len(selected),
            "primary_instances": int(primary["instances"]["base_short"]["total"]),
            "primary_archetypes": int(primary["archetypes"]["base_short"]["total"]),
        },
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in (PRIMARY, BLIND, DIAGNOSTICS)},
        "outputs": {str(path.relative_to(ROOT)): sha256(path) for path in (SUMMARY, DIAGNOSTIC_TABLE)},
        "privacy": {
            "contains_problem_bodies": False,
            "contains_request_or_response_bodies": False,
            "contains_evaluator_only_answers": False,
            "contains_credentials": False,
        },
        "claim_boundary": "The audit reconstructs aggregate plotted counts only. It adds no model, API, solver or evaluator call and does not turn the post hoc robustness or error localization into independent confirmation or causal decomposition.",
    }
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        path = Path(args.out)
        if not path.is_absolute():
            path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "passed" or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
