"""Explicit, pre-evaluation format recovery using the existing authorized ledger.

One retry per affected problem, same model and limits. Original failures and
responses are preserved. No gold reference or evaluator is read.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_pilot import prepare
from llm4or.live import LiveRequest, RUN_DIR
from llm4or.pipeline import PROMPTS, run_problem, write_json
from llm4or.schema import digest, loads

SELECTION = {"dev_007": "initial", "dev_012": "initial", "dev_014": "initial",
             "dev_021": "initial", "dev_034": "initial", "dev_037": "initial",
             "dev_018": "baseline_repair"}

FORMAT_GUIDE = """SERIALIZATION REQUIREMENT: Return only the mathematical LP JSON object, with EXACTLY FOUR TOP-LEVEL KEYS: schema, variables, constraints, objective. Never include output_contract, rules, context, problem, version, explanations, or markdown in your output. schema must be the literal string lp-v1. variables and constraints are arrays, objective is an object. Every variable has exactly id/meaning/unit/domain/lower/upper; every constraint exactly id/coefficients/sense/rhs; objective exactly coefficients/sense/unit/offset. Put constraints and objective directly at the root. Do not copy the request envelope into the response. Emit one valid JSON object and stop."""


class FormattingRecovery:
    def __init__(self, gateway):
        self.gateway = gateway
        self.directory = gateway.directory
        self.mode = gateway.mode

    def request(self, key, problem, phase, payload, reply):
        retry = SELECTION.get(problem) == phase
        with self.gateway._connect() as con:
            original = con.execute("SELECT * FROM attempts WHERE key=?", (key,)).fetchone()
        if retry:
            assert original is not None and original["status"] == "complete"
            # The diagnosis is structural only, before any reference scoring.
            payload = loads(original["request"])
            payload["instruction"] += "\n" + FORMAT_GUIDE + "\nThis is the one permitted format retry. Preserve your mathematical interpretation; repair only JSON structure. Do not solve a different problem."
            payload["context"]["previous_unparseable_response"] = loads(original["response"])["text"]
            payload["context"]["retry_reason"] = "JSON syntax or lp-v1 structural contract violation"
            payload["version"] += ":explicit-format-retry1"
            return self.gateway.request(key + ":retry1", problem, phase, payload, reply)
        if original is not None:
            # Exact replay: do not rewrite old requests or remove old failures.
            return self.gateway.request(key, problem, phase, loads(original["request"]), reply)
        if phase != "teacher_feedback":
            payload["instruction"] += "\n" + FORMAT_GUIDE
            payload["version"] += ":serialization-clarification"
        return self.gateway.request(key, problem, phase, payload, reply)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    problems, gateway = prepare()
    if (RUN_DIR / "evaluation_summary.json").exists() or (RUN_DIR / "mapping_review.json").exists():
        raise SystemExit("No post-evaluation tuning in this pilot")
    policy = {"status": "explicit_recovery_before_evaluation", "selection": SELECTION,
              "reason": "Six initial schemas invalid; first failing phase for dev_018 is baseline JSON. One retry each; later failures cannot get another retry.",
              "format_guide": FORMAT_GUIDE, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "same_ledger": str(gateway.db), "mathematical_hypothesis_changed": False,
              "mixed_serialization_versions_must_be_reported": True}
    auditpath = RUN_DIR / "format_recovery_policy.json"
    if auditpath.exists() and digest(loads(auditpath.read_text())) != digest(policy):
        raise SystemExit("Recovery policy is frozen")
    write_json(auditpath, policy)
    snapshot = RUN_DIR / "source_snapshot/scripts/retry_pilot_format.py"
    if not snapshot.exists():
        snapshot.write_bytes(Path(__file__).read_bytes()); snapshot.chmod(0o400)
    marker = RUN_DIR / "inference_complete.json"
    if marker.exists():
        original_marker = RUN_DIR / "inference_first_pass_complete.json"
        if not original_marker.exists(): marker.rename(original_marker)
        else: marker.unlink()
    for problem in problems:
        pid = problem["id"]
        if pid not in SELECTION:
            continue
        original_path = RUN_DIR / (pid + ".inference.first_pass.json")
        path = RUN_DIR / (pid + ".inference.json")
        if not original_path.exists():
            original_path.write_bytes(path.read_bytes())
        print("Explicit format recovery " + pid, flush=True)
        result = run_problem(problem, FormattingRecovery(gateway), {phase: LiveRequest() for phase in PROMPTS})
        result["format_recovery"] = {"phase": SELECTION[pid], "original_inference": original_path.name,
                                     "policy_hash": digest(policy)}
        write_json(path, result)
        print(json.dumps({"problem": pid, "status": result["status"], "errors": result["errors"],
                          "gate": result.get("repair_gate", {}).get("status"), "usage": gateway.summary()}), flush=True)
        write_json(RUN_DIR / "usage_summary.json", gateway.summary())
        with gateway._connect() as con:
            failed = list(con.execute("SELECT error FROM attempts WHERE status!='complete'"))
        if failed:
            raise SystemExit("Transport safety failure; inspect ledger before any further requests")
    write_json(marker, {"problem_count": len(problems), "usage": gateway.summary(),
                        "format_recovery_policy": digest(policy), "scope": "fixed_policy_development_pilot_not_evolution"})


if __name__ == "__main__": main()
