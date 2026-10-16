"""Evaluate aggregate development outcomes for the frozen v7 source-ledger pilot."""
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.pipeline import write_json
from llm4or.schema import digest


METHODS = ("Base", "V6", "DualLedger", "FullV7")


def _classify(before, after):
    if before not in {True, False} or after not in {True, False}:
        return "unknown"
    if after and not before:
        return "correction"
    if before and not after:
        return "regression"
    return "both_match" if before else "neither_match"


def evaluate_batch(plan, directory, batch_names):
    public = {row["id"]: row["public"] for row in load_public_registry(ROOT)}
    references = {
        row["problem_id"]: row
        for row in json.loads((ROOT / "data/evaluation/bound_reference_audit_v1.json").read_text())["records"]
    }
    selected = [row for row in plan["selection"]["records"] if row["batch"] in set(batch_names)]
    counts = Counter()
    families = defaultdict(Counter)
    private_rows = []
    for item in selected:
        pid = item["problem_id"]
        path = directory / "inference" / (digest(f"v7dev:LedgerProbe:17:{pid}") + ".json")
        saved = json.loads(path.read_text())
        if saved["record_sha256"] != digest(saved["record"]):
            raise ValueError("v7_probe_record_changed")
        probe = saved["record"]
        source = json.loads(Path(item["source_record_path"]).read_text())
        if digest(source) != item["source_record_sha256"]:
            raise ValueError("v7_source_record_changed")
        scores = {}
        for method in METHODS:
            unavailable = probe.get("status") == "infrastructure_unavailable" and method in {"DualLedger", "FullV7"}
            if unavailable:
                scores[method] = None
                counts[method + ":infrastructure_unavailable"] += 1
                continue
            record = {
                **deepcopy(source),
                "final_model": probe["models"].get(method),
                "status": "completed",
                "errors": [],
                "trace": [],
            }
            score = grade(record, public[pid], references[pid], independent=False).get("published_proxy_match")
            scores[method] = score
            counts[method + ":matched" if score is True else method + ":not_matched" if score is False
                   else method + ":unresolved"] += 1
        for method in ("V6", "DualLedger", "FullV7"):
            outcome = _classify(scores["Base"], scores[method])
            counts[method + "_vs_Base:" + outcome] += 1
            families[item["family_id"]][method + ":" + outcome] += 1
        incremental = _classify(scores["V6"], scores["FullV7"])
        counts["FullV7_vs_V6:" + incremental] += 1
        families[item["family_id"]]["FullV7_vs_V6:" + incremental] += 1
        counts["dual_consensus_accepted"] += probe.get("reports", {}).get("dual_ledger", {}).get("accepted") is True
        counts["base_missing_model"] += probe["models"].get("Base") is None
        counts["dual_recovered_missing_base"] += probe["models"].get("Base") is None and probe["models"].get("DualLedger") is not None
        private_rows.append({
            "problem_id": pid,
            "family_id": item["family_id"],
            "benchmark": item["benchmark"],
            "batch": item["batch"],
            "scores": scores,
            "dual_status": probe.get("reports", {}).get("dual_ledger", {}).get("status"),
            "probe_status": probe.get("status"),
        })
    family_counts = {
        "full_v7_correcting_families": sum(value["FullV7:correction"] > 0 for value in families.values()),
        "full_v7_regressing_families": sum(value["FullV7:regression"] > 0 for value in families.values()),
        "incremental_correcting_families_vs_v6": sum(
            value["FullV7_vs_V6:correction"] > 0 for value in families.values()
        ),
        "incremental_regressing_families_vs_v6": sum(
            value["FullV7_vs_V6:regression"] > 0 for value in families.values()
        ),
    }
    return {"counts": dict(counts), "family_counts": family_counts, "records": private_rows}


def stage1_pass(report):
    counts = report["counts"]
    corrections = counts.get("FullV7_vs_Base:correction", 0)
    regressions = counts.get("FullV7_vs_Base:regression", 0)
    return (
        counts.get("FullV7:infrastructure_unavailable", 0) == 0
        and counts.get("dual_consensus_accepted", 0) >= 5
        and corrections >= 3
        and regressions <= 1
        and corrections - regressions >= 2
        and report["family_counts"]["full_v7_correcting_families"] >= 2
    )


def final_pass(report):
    counts = report["counts"]
    corrections = counts.get("FullV7_vs_Base:correction", 0)
    regressions = counts.get("FullV7_vs_Base:regression", 0)
    inc_corrections = counts.get("FullV7_vs_V6:correction", 0)
    inc_regressions = counts.get("FullV7_vs_V6:regression", 0)
    return (
        corrections >= 10
        and regressions <= 2
        and corrections >= 4 * max(1, regressions)
        and report["family_counts"]["full_v7_correcting_families"] >= 5
        and inc_corrections >= 5
        and inc_regressions <= 2
    )


def write_report(plan, directory, batch_names, name):
    report = evaluate_batch(plan, directory, batch_names)
    report.update({
        "schema": "v7-source-ledger-development-evaluation-v1",
        "plan_sha256": digest(plan),
        "batches": list(batch_names),
        "development_only": True,
        "stage1_gate_passed": stage1_pass(report) if list(batch_names) == ["stage1"] else None,
        "final_development_gate_passed": final_pass(report) if "stage2" in batch_names else None,
        "claim_guard": "Development evidence only; no confirmatory accuracy claim is allowed.",
    })
    write_json(directory / name, report)
    public_summary = {key: value for key, value in report.items() if key != "records"}
    write_json(ROOT / "results" / name, public_summary)
    return report


if __name__ == "__main__":
    plan = json.loads((ROOT / "experiments/v7_source_ledger_pilot_plan.json").read_text())
    directory = ROOT / plan["run_directory"]
    batches = ["stage1", "stage2"] if (directory / "stage2.completed").exists() else ["stage1"]
    report = write_report(plan, directory, batches, "v7_source_ledger_pilot_evaluation.json")
    print(json.dumps({key: report[key] for key in ("counts", "family_counts", "stage1_gate_passed", "final_development_gate_passed")}, sort_keys=True))
