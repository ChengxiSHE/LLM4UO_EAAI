"""Freeze an outcome-blind external confirmation protocol for Base versus V6."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest

OUTPUT = ROOT / "experiments/text2opt_v6_confirmation_protocol.json"
FILES = [
    "data/manifests/text2opt_resource_allocation_v1.json",
    "data/manifests/text2opt_template_confirmation_v1.json",
    "llm4or/confirmatory_statistics.py",
    "scripts/prepare_text2opt_external.py",
    "scripts/prepare_text2opt_template_external.py",
]


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise ValueError("text2opt_v6_protocol_already_frozen")
    v7 = json.loads((ROOT / "results/v7_source_ledger_stage1_evaluation.json").read_text())
    auth = json.loads((ROOT / "experiments/v7_source_ledger_restart_authorization.json").read_text())
    if v7.get("stage1_gate_passed") is not False:
        raise ValueError("v7_failure_not_finalized")
    if auth.get("status") != "completed_stage1_gate_failed" or auth.get("further_api_calls_authorized") is not False:
        raise ValueError("v7_authorization_not_closed")
    protocol = {
        "schema": "text2opt-v6-confirmation-protocol-v1",
        "status": "input_statistics_and_v6_method_frozen",
        "api_requests": 0,
        "upstream": {
            "repository": "https://github.com/SprocketLab/Text2Opt-Bench",
            "revision": "1dac06be656c41d827ef20987cf8af0b48d382a2",
            "license": "MIT",
        },
        "cohorts": {
            "resource_allocation_official_eval": {"records": 248, "categories": 1},
            "family_diverse_capacity_compatible": {"records": 183, "categories": 6},
            "combined": {"records": 431, "categories": 7},
        },
        "comparison": "V6 versus Base",
        "method_selection": {
            "reason": (
                "V7 failed its development gate. V6 remains the strongest non-regressing development method: "
                "the v7 Stage 1 replay observed 2 corrections and 0 regressions versus Base, consistent with "
                "earlier positive V6 development and frozen-secondary evidence."
            ),
            "v7_stage1_result_sha256": digest(v7),
            "v7_stage1_gate_passed": False,
            "v7_not_carried_into_confirmation": True,
            "method_changes_after_external_outcomes": False,
        },
        "endpoint": {
            "name": "benchmark formulation accuracy",
            "definition": "candidate solver status is optimal and objective matches the published solver outcome",
            "model_parse_contract_or_solver_failure": "incorrect",
            "upstream_evaluator_code_relative_tolerance": 1e-5,
            "upstream_evaluator_code_absolute_tolerance": 1e-6,
            "documentation_discrepancy": (
                "Pinned README prose says relative tolerance 1e-4, while pinned executable evaluator uses "
                "rel_tol=1e-5 and abs_tol=1e-6; executable code wins."
            ),
        },
        "success_rule": {
            "paired_completion_rate": ">=0.99",
            "accuracy_delta": ">=0.01",
            "corrections": ">=5",
            "correction_regression_ratio": "corrections >= 4 * max(1, regressions)",
            "one_sided_exact_mcnemar_p": "<=0.05",
            "category_spread": "positive delta in >=2 of 7 categories and negative delta in <=1 category",
            "all_conditions_required": True,
        },
        "multiplicity": "One pre-registered primary paired comparison; no multiplicity adjustment.",
        "outcome_access": {
            "evaluation_fields_model_visible": False,
            "gold_programs_executed": False,
            "references_read_during_method_development": False,
            "text2opt_outcomes_read_while_freezing": False,
            "scoring_allowed_only_after_all_inference_checkpoints": True,
        },
        "required_reporting": [
            "all selected denominators and infrastructure availability",
            "Base and V6 accuracy with Wilson 95% intervals",
            "paired corrections, regressions, exact one-sided p-value, and conditional exact delta interval",
            "all seven category results and category-macro accuracy delta",
            "resource-allocation and six-category cohorts separately",
            "logical and physical requests, retries, tokens, and failures",
        ],
        "claim_boundary": (
            "Passing supports a pre-registered external benchmark V6 formulation-accuracy improvement over Base. "
            "It does not prove semantic equivalence for every formulation or eliminate public-data contamination."
        ),
        "frozen_files": {path: sha(path) for path in FILES},
    }
    write_json(OUTPUT, protocol)
    print(json.dumps({
        "status": protocol["status"], "protocol_sha256": digest(protocol),
        "records": 431, "categories": 7, "api_requests": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
