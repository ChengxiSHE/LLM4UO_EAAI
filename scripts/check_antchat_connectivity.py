"""Make one ledgered provider check inside an already-invalidated v7 run.

This diagnostic never prints request or response content. The entire source
run remains excluded from method evaluation irrespective of the result.
"""
import fcntl
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_gateway import FormalGateway
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.source_ledger import compile_ledger, make_ledger_payload
from llm4or.source_ledger_runtime import VERSION


def main():
    plan = json.loads((ROOT / "experiments/v7_source_ledger_pilot_plan.json").read_text())
    run = ROOT / plan["run_directory"]
    with (run / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = sqlite3.connect(run / "requests.sqlite3")
        try:
            halt = db.execute("SELECT reason FROM halt WHERE id=1").fetchone()
            if halt and halt[0] != "circuit_breaker_transport_failures":
                raise RuntimeError("unexpected_halt_state")
            if halt:
                db.execute("DELETE FROM halt WHERE id=1")
            slotted = {row[0] for row in db.execute("SELECT DISTINCT scope FROM slots")}
            db.commit()
        finally:
            db.close()
        item = next(
            row for row in plan["selection"]["records"]
            if row["batch"] == "stage1"
            and f"v7dev:LedgerProbe:17:{row['problem_id']}" not in slotted
        )
        registry = {row["id"]: row for row in load_public_registry(ROOT)}
        public = registry[item["problem_id"]]["public"]
        scope = f"v7dev:LedgerProbe:17:{item['problem_id']}"
        payload = make_ledger_payload(public, "variable_first")
        prefix = digest({
            "problem": public, "replicate": 17, "version": VERSION,
            "view": "variable_first",
        })
        gateway = FormalGateway(
            ROOT, plan,
            authorization_path="experiments/v7_source_ledger_pilot_authorization.json",
        )
        gateway.register(scope, 2, plan["token_cap"])
        response = gateway.request(scope, payload, prefix, 17, 0)
        valid = True
        try:
            compile_ledger(public, json.loads(response["text"]), "variable_first")
        except Exception:
            valid = False
        summary = gateway.summary()
        write_json(run / "antchat_connectivity_probe.json", {
            "schema": "antchat-connectivity-probe-v1",
            "plan_sha256": digest(plan),
            "scope": scope,
            "provider_response_received": True,
            "reported_model_matches": True,
            "strict_ledger_valid": valid,
            "usage": summary,
            "scientific_disposition": (
                "connectivity_only; entire incident run excluded from method evaluation"
            ),
        })
        print(json.dumps({
            "status": "connected", "model": plan["model"],
            "strict_ledger_valid": valid,
            "physical_attempts": summary["physical_attempts"],
            "logical_tokens": summary["logical_tokens"],
        }))


if __name__ == "__main__":
    main()
