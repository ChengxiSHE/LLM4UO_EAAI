"""Freeze external input bindings and statistics without reading outcomes."""
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest


OUTPUT = ROOT / "experiments/text2opt_confirmation_protocol.json"
FILES = [
    "data/manifests/text2opt_resource_allocation_v1.json",
    "data/manifests/text2opt_template_confirmation_v1.json",
    "llm4or/confirmatory_statistics.py",
    "scripts/prepare_text2opt_external.py",
    "scripts/prepare_text2opt_template_external.py",
    "scripts/freeze_text2opt_confirmation_protocol.py",
]


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise ValueError("text2opt_confirmation_protocol_already_frozen")
    resource = json.loads((ROOT / FILES[0]).read_text())
    template = json.loads((ROOT / FILES[1]).read_text())
    if resource["counts"]["confirmation"] != 248 or template["selection"]["records"] != 183:
        raise ValueError("external_confirmation_size_changed")
    if resource["leakage_checks"] != {
        "evaluator_fields_copied_to_public_snapshot": False,
        "exact_normalized_text_overlap": 0,
        "gold_solution_executed": False,
    } or template["leakage_checks"] != {
        "duplicate_normalized_public_texts": 0,
        "evaluator_fields_copied_to_public_snapshot": False,
        "gold_solution_executed": False,
        "used_for_method_development": False,
    }:
        raise ValueError("external_leakage_guard_changed")
    protocol = {
        "schema": "text2opt-confirmation-protocol-v1",
        "status": "input_and_statistics_frozen_waiting_for_v7_development_gate",
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
        "outcome_access": {
            "references_read_during_method_development": False,
            "gold_programs_executed": False,
            "evaluation_fields_model_visible": False,
            "scoring_allowed_only_after_method_and_run_plan_are_hash_frozen": True,
        },
        "endpoint": {
            "name": "benchmark formulation accuracy",
            "definition": "candidate solver status is optimal and objective matches the published solver outcome",
            "model_parse_contract_or_solver_failure": "incorrect",
            "upstream_evaluator_code_relative_tolerance": 1e-5,
            "upstream_evaluator_code_absolute_tolerance": 1e-6,
            "documentation_discrepancy": (
                "Pinned README prose says relative tolerance 1e-4, while pinned main/evaluation/"
                "problem_evaluator.py uses rel_tol=1e-5 and abs_tol=1e-6. The executable evaluator code wins."
            ),
        },
        "comparisons": ["FullV7 versus Base", "FullV7 versus V6"],
        "multiplicity": "Holm family-wise adjustment across the two one-sided paired primary tests at alpha 0.05",
        "joint_success_rule": {
            "all_conditions_for_both_comparisons": True,
            "paired_completion_rate": ">=0.99",
            "accuracy_delta": ">=0.02",
            "correction_regression_ratio": "corrections >= 2 * max(1, regressions)",
            "holm_adjusted_one_sided_exact_mcnemar_p": "<=0.05",
            "category_spread": "positive delta in >=4 of 7 categories and negative delta in <=1 category",
        },
        "required_reporting": [
            "all selected denominators and infrastructure availability",
            "pooled accuracy with Wilson 95% intervals",
            "paired corrections regressions and exact one-sided p-values",
            "Holm-adjusted p-values and conditional exact paired-delta intervals",
            "all seven category results and category-macro accuracy delta",
            "resource-allocation and six-category cohorts separately",
            "logical and physical requests tokens latency and abstention",
        ],
        "claim_boundary": (
            "Passing supports a pre-registered external benchmark formulation-accuracy improvement. "
            "It does not prove semantic equivalence for every formulation or eliminate public-data contamination."
        ),
        "future_run_freeze": (
            "Only after the unchanged v7 development gate passes: bind the exact method, prompts, provider, "
            "public snapshots, runner, evaluator, request budgets, and a new explicit authorization."
        ),
        "frozen_files": {path: sha(path) for path in FILES},
        "outcomes_read_while_freezing": False,
        "api_requests": 0,
    }
    write_json(OUTPUT, protocol)
    print(json.dumps({
        "status": protocol["status"],
        "protocol_sha256": digest(protocol),
        "records": 431,
        "api_requests": 0,
        "outcomes_read": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
