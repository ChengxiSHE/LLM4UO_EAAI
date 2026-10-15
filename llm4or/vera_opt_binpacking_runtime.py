"""Reference-free Base/VERA inference for the BinPacking family study."""

from __future__ import annotations

from copy import deepcopy

from .benchmark_inputs import payload_sha256, validate_public_input
from .declarative_packing_compiler import solve_declarative_packing
from .formal_runtime import parse_model
from .gateway import Stopped
from .milp_solver import execute
from .run_interruption import RunInterrupted, interrupts_run
from .schema import digest
from .text2opt_v9_runtime import initial_payload as frozen_base_payload
from .verified_skill_library import apply_skill_library


VERSION = "vera-opt-binpacking-runtime-v1"
IMPLEMENTATION_ID = "declarative.bin_packing.v1"


def run_promotion_probe(problem, gateway, scope, replicate, token_cap, *,
                        skill, implementation_sha256, solver=execute):
    public = validate_public_input(problem)
    gateway.register(scope, 1, token_cap)
    output = {
        "schema": "vera-opt-binpacking-probe-v1", "version": VERSION,
        "problem_id": public["id"], "input_sha256": payload_sha256(public),
        "models": {"Base": None}, "solve": {"Base": None, "VERA": None},
        "reports": {}, "errors": [],
        "method_infrastructure_unavailable": {"Base": False, "VERA": False},
        "status": "unresolved",
    }
    payload = frozen_base_payload(public)
    prefix = digest({"problem": public, "replicate": replicate,
                     "base_payload_version": payload["version"], "channel": "base"})
    try:
        parsed = parse_model(gateway.request(scope, payload, prefix, replicate, 0)["text"])
        if parsed.get("schema") == "milp-v1":
            output["models"]["Base"] = parsed
        else:
            output["reports"]["base"] = {"status": "unsupported",
                "reason": parsed.get("reason"), "accepted": False}
    except (ValueError, RuntimeError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, Stopped) else type(exc).__name__
        if isinstance(exc, RunInterrupted) or isinstance(exc, Stopped) and interrupts_run(reason):
            raise RunInterrupted(reason) from None
        output["errors"].append({"phase": "base", "reason": reason})
        if reason.startswith("request_unavailable:"):
            output["method_infrastructure_unavailable"]["Base"] = True
    if output["models"]["Base"] is not None:
        output["solve"]["Base"] = solver({"op": "solve", "model": deepcopy(output["models"]["Base"])})
    backend = output["solve"]["Base"] or {"status": "backend_unavailable", "objective": None}
    application = apply_skill_library(
        public, backend, [skill],
        trusted_implementation_digests={IMPLEMENTATION_ID: implementation_sha256},
        trusted_implementation_functions={IMPLEMENTATION_ID: solve_declarative_packing},
    )
    output["reports"]["skill"] = {key: deepcopy(application.get(key)) for key in (
        "adopted", "skill_sha256", "implementation_id", "compiler_status", "reason",
        "fallback_identity", "result_sha256",
    ) if key in application}
    output["solve"]["VERA"] = deepcopy(application["result"])
    output["model_sha256"] = {"Base": digest(output["models"]["Base"])
                              if output["models"]["Base"] is not None else None,
                              "VERA": None}
    output["usage"] = gateway.scope_usage(scope)
    output["status"] = ("infrastructure_unavailable"
                        if any(output["method_infrastructure_unavailable"].values())
                        else "completed_with_errors" if output["errors"] else "completed")
    return output


__all__ = ["IMPLEMENTATION_ID", "VERSION", "run_promotion_probe"]
