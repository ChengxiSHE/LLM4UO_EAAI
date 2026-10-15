"""Approved live pilot. --probe is the first initial-model call, reused by --run.

No gold/reference files are opened. Evaluation is a separate post-inference step.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.gateway import Stopped
from llm4or.live import LiveGateway, LiveRequest, RUN_DIR
from llm4or.pipeline import PROMPTS, make_payload, run_problem, write_json
from llm4or.schema import digest, loads, model, validate_public


def prepare():
    public_path = ROOT / "data/pilot/public/problems.jsonl"
    raw = public_path.read_bytes()
    problems = [validate_public(loads(line)) for line in raw.decode().splitlines()]
    import scipy, numpy
    files = sorted((ROOT / "llm4or").glob("*.py")) + [Path(__file__).resolve()]
    manifest = {"public_sha256": hashlib.sha256(raw).hexdigest(),
                "problem_ids": [p["id"] for p in problems], "python": platform.python_version(),
                "scipy": scipy.__version__, "numpy": numpy.__version__,
                "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    gateway = LiveGateway(manifest=manifest)
    write_json(RUN_DIR / "manifest.json", manifest)
    # Snapshot trusted implementation, not data labels or private config.
    for p in files:
        target = RUN_DIR / "source_snapshot" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != p.read_bytes():
            raise Stopped("source_snapshot_mismatch")
        if not target.exists():
            target.write_bytes(p.read_bytes())
            target.chmod(0o400)
    return problems, gateway


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("probe", "run", "status"))
    args = parser.parse_args()
    problems, gateway = prepare()
    if args.action == "status":
        print(json.dumps(gateway.summary()))
        return
    if args.action == "probe":
        problem = problems[0]
        response = gateway.request(problem["id"] + ":initial", problem["id"], "initial",
                                   make_payload(problem, "initial"), LiveRequest())
        initial = model(response["text"])
        check = {"status": "passed", "problem_id": problem["id"], "response_hash": digest(response),
                 "model_hash": digest(initial), "reported_model": response["reported_model"],
                 "usage_source": response["usage_source"], "finish_reason": response["finish_reason"],
                 "prompt_tokens": response["prompt_tokens"], "completion_tokens": response["completion_tokens"],
                 "note": "This same initial response is cached and reused, not a separate greeting request."}
        write_json(RUN_DIR / "preflight.json", check)
        print(json.dumps(check))
        return
    if not (RUN_DIR / "preflight.json").exists():
        raise Stopped("first_real_request_has_not_passed_preflight")
    replies = {phase: LiveRequest() for phase in PROMPTS}
    for problem in problems:
        path = RUN_DIR / (problem["id"] + ".inference.json")
        if path.exists():
            result = loads(path.read_text())
            if result["problem_hash"] != digest(problem):
                raise Stopped("saved_problem_hash_mismatch")
        else:
            print("Starting " + problem["id"], flush=True)
            result = run_problem(problem, gateway, replies)
        print(json.dumps({"problem": problem["id"], "status": result["status"],
                          "errors": result["errors"], "gate": result.get("repair_gate", {}).get("status"),
                          "requests": gateway.summary()}), flush=True)
        write_json(RUN_DIR / "usage_summary.json", gateway.summary())
        with gateway._connect() as con:
            recent = list(con.execute("SELECT error FROM attempts ORDER BY created DESC LIMIT 3"))
        if any(r["error"] and (r["error"].startswith(("http_401", "http_402", "http_403", "http_429", "provider_usage"))
                              or r["error"] == "completion_token_limit") for r in recent):
            raise Stopped("provider_guard_failed_batch_paused")
        if len(recent) == 3 and all(r["error"] for r in recent):
            raise Stopped("three_consecutive_transport_failures_batch_paused")
    write_json(RUN_DIR / "inference_complete.json", {"problem_count": len(problems), "usage": gateway.summary(),
                                                    "scope": "fixed_policy_development_pilot_not_evolution"})


if __name__ == "__main__":
    try:
        main()
    except (Stopped, ValueError) as exc:
        print("Pilot stopped: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
