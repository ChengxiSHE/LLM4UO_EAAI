#!/usr/bin/env python3
"""Aggregate non-secret accounting across the BIND 30-record continuations."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/text2opt_bind_development_matrix_lineage.json"
AUTHORIZATIONS = [
    "experiments/text2opt_bind_development_matrix_authorization.json",
    "experiments/text2opt_bind_development_matrix_restart_authorization.json",
    "experiments/text2opt_bind_development_matrix_retry_authorization.json",
]


def main():
    runs = []
    for name in AUTHORIZATIONS:
        value = json.loads((ROOT / name).read_text())
        usage = value["closed_usage"]
        if value["further_api_calls_authorized"] is not False:
            raise ValueError("bind_lineage_authorization_not_closed:" + name)
        runs.append({
            "authorization": name,
            "plan_sha256": value["plan_sha256"],
            "status": value["status"],
            "physical_attempts": usage["physical_attempts"],
            "completed_physical_attempts": usage["completed_physical_attempts"],
            "failed_physical_attempts": usage["physical_attempts"] - usage["completed_physical_attempts"],
            "physical_reserved_or_reported_tokens": usage["physical_reserved_or_reported_tokens"],
            "halt": usage["halt"],
        })
    total_physical = sum(row["physical_attempts"] for row in runs)
    total_complete = sum(row["completed_physical_attempts"] for row in runs)
    total_tokens = sum(row["physical_reserved_or_reported_tokens"] for row in runs)
    final = json.loads((ROOT / "results/text2opt_bind_development_matrix_evaluation.json").read_text())
    if (
        total_physical != 32 or total_complete != 30
        or final["planned_records"] != 30 or final["final_correct"] != 30
        or final["usage"]["logical_requests"] != 36
    ):
        raise ValueError("bind_lineage_expected_counts_changed")
    report = {
        "schema": "text2opt-bind-development-matrix-lineage-v1",
        "role": "development_only_no_confirmatory_claim",
        "runs": runs,
        "totals": {
            "physical_attempts_during_30_record_expansion": total_physical,
            "completed_physical_attempts_during_expansion": total_complete,
            "failed_outer_json_attempts_during_expansion": total_physical - total_complete,
            "physical_reserved_or_reported_tokens_during_expansion": total_tokens,
            "final_logical_responses": final["usage"]["logical_requests"],
            "final_logical_reserved_or_reported_tokens": final["usage"]["logical_reserved_or_reported_tokens"],
            "exact_cache_hits_from_prior_six_record_pilot": final["usage"]["logical_requests"] - total_complete,
        },
        "scientific_result": {
            "round1_correct": final["round1_correct"],
            "final_correct": final["final_correct"],
            "records": final["planned_records"],
            "oracle_repair_corrections": final["oracle_repair_corrections"],
        },
        "accounting_note": (
            "Physical expansion cost includes two failed outer-format attempts. Final logical cost counts the "
            "36 successful responses used by the method, including six exact cache hits from the prior pilot."
        ),
    }
    OUTPUT.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps(report["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
