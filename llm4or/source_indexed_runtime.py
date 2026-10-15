"""Reference-free Base/source-indexed development runtime."""
from copy import deepcopy

from .benchmark_inputs import payload_sha256, validate_public_input
from .formal_runtime import parse_model
from .gateway import Stopped
from .milp_schema import loads
from .milp_solver import execute
from .run_interruption import RunInterrupted, interrupts_run
from .schema import digest
from .source_indexed_model import compile_source_indexed, make_source_indexed_payload
from .text2opt_v6_runtime import initial_payload


VERSION = "source-indexed-runtime-v1"


def run_source_indexed_probe(problem, gateway, scope, replicate, token_cap, solver=execute):
    public = validate_public_input(problem)
    gateway.register(scope, 2, token_cap)
    out = {
        "schema": "source-indexed-probe-v1",
        "version": VERSION,
        "problem_id": public["id"],
        "input_sha256": payload_sha256(public),
        "models": {"Base": None, "SourceIndexed": None, "FullV8": None},
        "solve": {"Base": None, "SourceIndexed": None, "FullV8": None},
        "reports": {},
        "errors": [],
        "method_infrastructure_unavailable": {"Base": False, "SourceIndexed": False, "FullV8": False},
        "status": "unresolved",
    }

    def request(payload, channel, slot):
        prefix = digest({
            "problem": public, "replicate": replicate, "version": VERSION, "channel": channel,
        })
        return gateway.request(scope, payload, prefix, replicate, slot)["text"]

    try:
        base = parse_model(request(initial_payload(public), "base", 0))
        if base.get("schema") == "milp-v1":
            out["models"]["Base"] = base
    except (ValueError, RuntimeError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, Stopped) else type(exc).__name__
        if isinstance(exc, RunInterrupted) or isinstance(exc, Stopped) and interrupts_run(reason):
            raise RunInterrupted(reason) from None
        out["errors"].append({"phase": "base", "reason": reason})
        if reason.startswith("request_unavailable:"):
            out["method_infrastructure_unavailable"]["Base"] = True

    indexed = None
    try:
        raw = loads(request(make_source_indexed_payload(public), "source_indexed", 1))
        indexed, report = compile_source_indexed(public, raw)
        state = solver({"op": "solve", "model": indexed})
        report = {**report, "solve_status": state.get("status")}
        if state.get("status") != "optimal":
            indexed = None
            report.update(status="rejected", reason="source_indexed_not_optimal")
        else:
            report.update(status="accepted", accepted=True)
        out["reports"]["source_indexed"] = report
    except (ValueError, RuntimeError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, Stopped) else type(exc).__name__
        if isinstance(exc, RunInterrupted) or isinstance(exc, Stopped) and interrupts_run(reason):
            raise RunInterrupted(reason) from None
        out["errors"].append({"phase": "source_indexed", "reason": reason})
        out["reports"]["source_indexed"] = {"status": "rejected", "accepted": False, "reason": reason}
        if reason.startswith("request_unavailable:"):
            out["method_infrastructure_unavailable"]["SourceIndexed"] = True

    base = out["models"]["Base"]
    out["models"]["SourceIndexed"] = indexed
    # The executable gate is fail closed.  It adopts only a source-bound model
    # that compiles and solves; otherwise it preserves the independently
    # generated Base model, including when the auxiliary request is unavailable.
    out["models"]["FullV8"] = indexed if indexed is not None else base
    out["reports"]["full_gate"] = {
        "status": "accepted_source_indexed" if indexed is not None else "fallback_base",
        "accepted": indexed is not None,
    }
    if out["method_infrastructure_unavailable"]["SourceIndexed"]:
        out["method_infrastructure_unavailable"]["FullV8"] = False if base is not None else True
    for method, candidate in out["models"].items():
        out["solve"][method] = (
            solver({"op": "solve", "model": deepcopy(candidate)}) if candidate is not None else None
        )
    out["model_sha256"] = {
        method: digest(candidate) if candidate is not None else None
        for method, candidate in out["models"].items()
    }
    out["usage"] = gateway.scope_usage(scope)
    out["status"] = (
        "infrastructure_unavailable" if out["models"]["FullV8"] is None
        and any(out["method_infrastructure_unavailable"].values())
        else "completed_with_fallback" if indexed is None and base is not None
        else "completed_with_errors" if out["errors"]
        else "completed"
    )
    return out


__all__ = ["VERSION", "run_source_indexed_probe"]
