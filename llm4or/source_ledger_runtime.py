"""Development runtime for the v7 dual-view source-ledger mechanism."""
from copy import deepcopy
import json

from .benchmark_inputs import payload_sha256, validate_public_input
from .gateway import Stopped
from .milp_schema import loads, model
from .milp_solver import execute
from .schema import digest
from .run_interruption import RunInterrupted, interrupts_run
from .semantic_contracts import apply_contracts_transactionally
from .semantic_contracts_v2 import derive_contracts as derive_contracts_v2
from .source_ledger import compile_dual_view_consensus, make_ledger_payload


VERSION = "source-ledger-runtime-v2"


def run_source_ledger_probe(problem, initial_record, gateway, scope, replicate, token_cap, solver=execute):
    public = validate_public_input(problem)
    if initial_record.get("input_sha256") != payload_sha256(public):
        raise Stopped("source_initial_input_mismatch")
    initial_value = initial_record.get("final_model")
    initial = model(initial_value) if initial_value is not None else None
    gateway.register(scope, 2, token_cap)
    out = {
        "schema": "source-ledger-probe-v1",
        "version": VERSION,
        "problem_id": public["id"],
        "input_sha256": payload_sha256(public),
        "initial_model_sha256": digest(initial) if initial is not None else None,
        "models": {"Base": initial},
        "reports": {},
        "errors": [],
        "helper_infrastructure_unavailable": False,
        "status": "unresolved",
    }

    def request(view, slot):
        payload = make_ledger_payload(public, view)
        prefix = digest({"problem": public, "replicate": replicate, "version": VERSION, "view": view})
        response = gateway.request(scope, payload, prefix, replicate, slot)
        return loads(response["text"])

    raw = {}
    for slot, view in enumerate(("variable_first", "constraint_first")):
        try:
            raw[view] = request(view, slot)
        except (ValueError, RuntimeError, KeyError, TypeError) as exc:
            reason = str(exc) if isinstance(exc, Stopped) else type(exc).__name__
            if isinstance(exc, RunInterrupted) or isinstance(exc, Stopped) and interrupts_run(reason):
                raise RunInterrupted(reason) from None
            out["errors"].append({"phase": view, "reason": reason})
    if initial is None:
        v6, v6_report = None, {"status": "no_initial_model", "accepted": False}
    else:
        v6, v6_report = apply_contracts_transactionally(
            public, initial, solver, derive_contracts_v2(public, initial)
        )
    out["models"]["V6"] = v6
    out["reports"]["v6"] = v6_report
    dual = None
    dual_report = {"schema": "dual-view-source-contract-v1", "status": "missing_view", "accepted": False}
    if set(raw) == {"variable_first", "constraint_first"}:
        dual, dual_report = compile_dual_view_consensus(
            public, raw["variable_first"], raw["constraint_first"], solver
        )
    # The source ledger is an auxiliary proposal mechanism. Rejection or
    # transport failure must preserve the prior model rather than turn a
    # scoreable Base/V6 result into an artificial regression.
    out["models"]["DualLedger"] = dual if dual is not None else initial
    out["reports"]["dual_ledger"] = dual_report
    if dual is None:
        full, full_report = v6, {
            "status": "fallback_v6_no_consensus", "accepted": False,
        }
    else:
        full, full_report = apply_contracts_transactionally(
            public, dual, solver, derive_contracts_v2(public, dual)
        )
    out["models"]["FullV7"] = full
    out["reports"]["full_v6_guard"] = full_report
    out["model_sha256"] = {name: digest(value) if value is not None else None for name, value in out["models"].items()}
    out["solve"] = {name: solver({"op": "solve", "model": value}) if value is not None else None
                    for name, value in out["models"].items()}
    out["usage"] = gateway.scope_usage(scope)
    out["helper_infrastructure_unavailable"] = any(
        item["reason"].startswith("request_unavailable:") for item in out["errors"]
    )
    out["status"] = (
        "unresolved" if out["models"]["FullV7"] is None
        else "completed_with_fallback" if dual is None
        else "completed_with_errors" if out["errors"]
        else "completed"
    )
    return out


__all__ = ["VERSION", "run_source_ledger_probe"]
