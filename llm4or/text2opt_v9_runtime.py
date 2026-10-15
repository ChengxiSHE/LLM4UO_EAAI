"""Reference-free Base/V9 runtime for independent Text2Opt confirmation."""
from copy import deepcopy

from .benchmark_inputs import payload_sha256, validate_public_input
from .formal_runtime import parse_model
from .gateway import Stopped
from .milp_solver import execute
from .run_interruption import RunInterrupted, interrupts_run
from .schema import digest
from .text2opt_template_compiler import detect_template_family, solve_template_problem
from .text2opt_v6_runtime import initial_payload as v6_initial_payload


VERSION = "text2opt-v9-confirmation-runtime-v1"


def initial_payload(problem):
    payload = v6_initial_payload(problem)
    payload["version"] = VERSION
    return payload


def run_text2opt_v9_probe(problem, gateway, scope, replicate, token_cap, solver=execute):
    """Generate Base once; replace it only after a trusted public-text solve."""
    public = validate_public_input(problem)
    gateway.register(scope, 1, token_cap)
    output = {
        "schema": "text2opt-v9-confirmation-probe-v1",
        "version": VERSION,
        "problem_id": public["id"],
        "input_sha256": payload_sha256(public),
        "models": {"Base": None},
        "solve": {"Base": None, "V9": None},
        "reports": {},
        "errors": [],
        "method_infrastructure_unavailable": {"Base": False, "V9": False},
        "status": "unresolved",
    }
    try:
        family = detect_template_family(public["text"])
        compiled = solve_template_problem(public)
        output["reports"]["compiler"] = {
            "status": compiled.get("status"), "family": family,
            "certificate": compiled.get("certificate"), "adopted": compiled.get("status") == "optimal",
        }
        if compiled.get("status") == "optimal":
            output["solve"]["V9"] = compiled
    except Stopped as exc:
        output["reports"]["compiler"] = {
            "status": "not_applicable", "reason": str(exc), "adopted": False,
        }

    payload = initial_payload(public)
    prefix = digest({
        "problem": public, "replicate": replicate, "version": VERSION, "channel": "base",
    })
    try:
        parsed = parse_model(gateway.request(scope, payload, prefix, replicate, 0)["text"])
        if parsed.get("schema") == "milp-v1":
            output["models"]["Base"] = parsed
        else:
            output["reports"]["base"] = {
                "status": "unsupported", "reason": parsed.get("reason"), "accepted": False,
            }
    except (ValueError, RuntimeError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, Stopped) else type(exc).__name__
        if isinstance(exc, RunInterrupted) or isinstance(exc, Stopped) and interrupts_run(reason):
            raise RunInterrupted(reason) from None
        output["errors"].append({"phase": "base", "reason": reason})
        if reason.startswith("request_unavailable:"):
            output["method_infrastructure_unavailable"]["Base"] = True
            if output["solve"]["V9"] is None:
                output["method_infrastructure_unavailable"]["V9"] = True
    if output["models"]["Base"] is not None:
        output["solve"]["Base"] = solver({"op": "solve", "model": deepcopy(output["models"]["Base"])})
    if output["solve"]["V9"] is None:
        output["solve"]["V9"] = deepcopy(output["solve"]["Base"])
        output["reports"]["fallback"] = "unchanged_base"
    output["model_sha256"] = {
        "Base": digest(output["models"]["Base"]) if output["models"]["Base"] is not None else None,
        "V9": None,
    }
    output["usage"] = gateway.scope_usage(scope)
    output["status"] = (
        "infrastructure_unavailable"
        if any(output["method_infrastructure_unavailable"].values())
        else "completed_with_errors" if output["errors"]
        else "completed"
    )
    return output


__all__ = ["VERSION", "initial_payload", "run_text2opt_v9_probe"]
