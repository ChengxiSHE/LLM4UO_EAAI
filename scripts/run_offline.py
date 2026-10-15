"""Run deterministic synthetic fixtures through the real process-limited kernel."""
import argparse
import hashlib
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.evaluator import evaluate
from llm4or.fixtures import scenario
from llm4or.gateway import Gateway, Limits
from llm4or.pipeline import run_problem, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/offline_s0")
    args = parser.parse_args()
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((ROOT / "llm4or").glob("*.py"))}
    import numpy, scipy
    manifest = {"source_hashes": source_hashes, "python": platform.python_version(),
                "numpy": numpy.__version__, "scipy": scipy.__version__,
                "platform": platform.platform()}
    gateway = Gateway(args.output, Limits(requests=20, per_problem=6), manifest=manifest)
    reports = []
    for name in ("correction", "overconstraint", "unresolved", "malformed"):
        problem, replies, reference = scenario(name)
        result = run_problem(problem, gateway, replies)
        scores = {}
        # Evaluation occurs only after inference and is stored separately.
        for branch in ("baseline_final", "semantic_final"):
            if branch in result:
                scores[branch] = evaluate(result[branch], reference)
        write_json(args.output / (name + ".evaluation.json"), scores)
        reports.append({"scenario": name, "status": result["status"],
                        "gate": result.get("repair_gate", {}).get("status"),
                        "gate_reason": result.get("repair_gate", {}).get("reason"),
                        "scores": {k: {s: v[s] for s in ("objective_match_proxy", "formulation_check")}
                                   for k, v in scores.items()}})
    # Explicit expected outcomes; do not report success solely because the script exits.
    assert reports[0]["gate"] == "accepted_relative_to_evidence", reports[0]
    assert reports[0]["scores"]["semantic_final"]["formulation_check"] == "same_within_tolerance_exact_objective"
    assert reports[1]["gate_reason"] == "protected_example_regression", reports[1]
    assert reports[2]["gate_reason"] == "teacher_unresolved", reports[2]
    assert reports[3]["status"] == "initial_failed", reports[3]
    assert gateway.summary()["attempts_including_failures"] == 15, gateway.summary()
    summary = {"kind": "synthetic_offline_integration_not_benchmark", "passed": True,
               "manifest": manifest, "requests": gateway.summary(), "cases": reports,
               "limitations": ["Fixed replies do not test model competence or provider compatibility.",
                               "No cross-task evolution has been run.",
                               "Repair acceptance is relative to teacher claims; correlated errors remain possible."]}
    write_json(args.output / "summary.json", summary)
    print(f"Offline integration passed: {len(reports)} cases, 15 simulated attempts, 0 API requests. Report: {args.output / 'summary.json'}")


if __name__ == "__main__":
    main()
