#!/usr/bin/env python3
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import FULL_PLAN_PATH, publish_new  # noqa: E402


plan = json.loads((ROOT / FULL_PLAN_PATH).read_text())
run = ROOT / plan["run_directory"] / "cells"
custody = Path(sys.argv[1]).resolve()
labels = {
    row["opaque_id"]: row["equivalent"]
    for row in json.loads((custody / "private" / "ledger.json").read_text())["records"]
}
arms = {
    arm: {"statuses": Counter(), "errors": Counter(), "valid_correct": 0,
          "valid_n": 0, "predictions": Counter(), "completion": []}
    for arm in ("flat-k", "pck-k")
}
for cell_id, descriptor in plan["cells"].items():
    cell = json.loads((run / f"{cell_id}.json").read_text())
    row = arms[descriptor["representation"]]
    row["statuses"][cell["status"]] += 1
    row["errors"][cell.get("error") or "none"] += 1
    record = cell.get("record") or {}
    judgment = record.get("judgment")
    if isinstance(judgment, dict):
        prediction = judgment["equivalent"]
        row["valid_n"] += 1
        row["valid_correct"] += int(prediction == labels[descriptor["opaque_id"]])
        row["predictions"][str(prediction).lower()] += 1
        row["completion"].append(record["completion_tokens"])
out = {
    "schema": "formulationbench-same-knowledge-v1-posthoc-diagnostic",
    "status": "complete_exploratory_only",
    "arms": {
        arm: {
            "terminal_status_counts": dict(sorted(row["statuses"].items())),
            "error_counts": dict(sorted(row["errors"].items())),
            "valid_only_correct": row["valid_correct"],
            "valid_only_total": row["valid_n"],
            "valid_only_accuracy": row["valid_correct"] / row["valid_n"],
            "valid_prediction_counts": dict(sorted(row["predictions"].items())),
            "completion_tokens_mean": statistics.mean(row["completion"]),
            "completion_tokens_max": max(row["completion"]),
        }
        for arm, row in arms.items()
    },
    "interpretation": {
        "primary_gate_failed": True,
        "pck_more_method_failures": arms["pck-k"]["statuses"]["method_failure"] > arms["flat-k"]["statuses"]["method_failure"],
        "valid_only_pck_minus_flat": arms["pck-k"]["valid_correct"] / arms["pck-k"]["valid_n"] - arms["flat-k"]["valid_correct"] / arms["flat-k"]["valid_n"],
        "next_hypothesis": "separate bounded decision output from optional evidence emission and route only relevant fact subsets per obligation",
    },
    "privacy": {"bodies_published": False, "per_pair_predictions_published": False, "per_pair_labels_published": False},
    "claim_boundary": "Post-hoc diagnostic on a fully scored development endpoint; it cannot support a confirmatory improvement claim.",
}
publish_new(ROOT / "experiments/formulationbench_same_knowledge_diagnostic_20261016.json", out)
print(json.dumps({"status": out["status"], "next_hypothesis": out["interpretation"]["next_hypothesis"]}, sort_keys=True))
