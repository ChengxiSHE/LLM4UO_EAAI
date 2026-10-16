"""Safe paper-based OptiTrust-style trajectory for the common endpoint.

This is a disclosed structural sensitivity, not an official-code reproduction.
Generated Python is never executed: each language-conditioned coding view emits
the same validated ``milp-v1`` sidecar for a trusted solver.
"""

from __future__ import annotations

from copy import deepcopy
import json
import math
from statistics import median
from typing import Any, Callable

from .benchmark_inputs import payload_sha256, validate_public_input
from .milp_contracts import MODEL_SCHEMA, validate_output
from .schema import digest


VERSION = "optitrust-style-safe-sidecar-v1"
LANGUAGES = ("Pyomo", "Gurobipy", "DOcplex", "CVXPY", "PySCIPOpt")
STAGES = (
    "decomposition",
    "decomposition_reflection",
    "formulation",
    "formulation_reflection",
    *("candidate_" + language for language in LANGUAGES),
)
TEXT_SCHEMA = {
    "type": "object",
    "properties": {"components": {"type": "string", "minLength": 1}},
    "required": ["components"],
    "additionalProperties": False,
}
FORMULATION_SCHEMA = {
    "type": "object",
    "properties": {"formulation": {"type": "string", "minLength": 1}},
    "required": ["formulation"],
    "additionalProperties": False,
}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def _text_output(raw: str, key: str, failure: str) -> str:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, RecursionError):
        raise ValueError(failure) from None
    if (
        type(value) is not dict
        or set(value) != {key}
        or type(value[key]) is not str
        or not value[key].strip()
        or len(value[key].encode("utf-8")) > 256_000
    ):
        raise ValueError(failure)
    return value[key].strip()


def _instruction(stage: str, language: str | None = None) -> str:
    shared = (
        "Use the supplied public optimization problem exactly. Do not assume an "
        "answer, hidden reference, or unstated data. Return only the requested "
        "JSON object."
    )
    if stage == "decomposition":
        return shared + (
            " Identify the decision variables and their domains, the objective, "
            "all explicit and implicit constraints, and every numeric parameter. "
            "Place the concise component analysis in `components`."
        )
    if stage == "decomposition_reflection":
        return shared + (
            " Audit the prior component analysis for omissions, wrong domains, "
            "unused values and duplicated constraints. Return the corrected final "
            "analysis in `components`."
        )
    if stage == "formulation":
        return shared + (
            " Convert the reflected components into a complete mathematical "
            "formulation with indexed variables, domains, objective and constraints. "
            "Place it in `formulation`."
        )
    if stage == "formulation_reflection":
        return shared + (
            " Independently check the prior formulation against the original "
            "problem and reflected components, then return a corrected complete "
            "formulation in `formulation`."
        )
    _require(language in LANGUAGES, "candidate_language")
    return shared + (
        f" Reason as an expert who would implement the model with {language}. "
        "For safe evaluation, do not emit or execute code. Instead return the exact "
        "equivalent sparse `milp-v1` JSON sidecar described by the response schema. "
        "Use explicit finite coefficients, bounds and variable domains."
    )


def stage_payload(public: dict[str, Any], slot: int, state: dict[str, str]) -> dict[str, Any]:
    """Build one of the nine fixed paper-structure requests."""
    public = validate_public_input(public)
    _require(type(slot) is int and 0 <= slot < 9, "optitrust_slot")
    stage = STAGES[slot]
    context: dict[str, Any] = {
        "method": "OptiTrust-style-safe-sidecar",
        "stage": stage,
        "step": slot,
    }
    language = None
    if slot == 1:
        context["previous_components"] = state.get("components", "")
    elif slot == 2:
        context["components"] = state.get("components", "")
    elif slot == 3:
        context["components"] = state.get("components", "")
        context["previous_formulation"] = state.get("formulation", "")
    elif slot >= 4:
        language = LANGUAGES[slot - 4]
        context.update({
            "modeling_language": language,
            "components": state.get("components", ""),
            "formulation": state.get("formulation", ""),
            "safe_execution_adapter": "strict_milp_v1_sidecar",
        })
    if slot in (0, 1):
        schema = TEXT_SCHEMA
        contract = {"components": "Corrected natural-language model components."}
    elif slot in (2, 3):
        schema = FORMULATION_SCHEMA
        contract = {"formulation": "Complete mathematical formulation."}
    else:
        schema = MODEL_SCHEMA
        contract = {
            "schema": "Return one strict milp-v1 object; generated code is forbidden."
        }
    return {
        "version": VERSION,
        "instruction": _instruction(stage, language),
        "problem": public,
        "context": context,
        "output_contract": contract,
        "response_schema": deepcopy(schema),
    }


def strict_majority(
    candidates: list[dict[str, Any]], *, rtol: float, atol: float,
) -> dict[str, Any]:
    """Select a unique strict objective majority among five candidates."""
    _require(len(candidates) == 5, "five_candidates_required")
    _require(rtol >= 0 and atol >= 0, "majority_tolerance")
    valid = []
    for candidate in candidates:
        objective = candidate.get("objective")
        if (
            candidate.get("status") == "optimal"
            and type(objective) in (int, float)
            and math.isfinite(float(objective))
            and candidate.get("language") in LANGUAGES
        ):
            valid.append(candidate)
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for pivot in valid:
        members = [
            candidate for candidate in valid
            if math.isclose(
                float(candidate["objective"]), float(pivot["objective"]),
                rel_tol=rtol, abs_tol=atol,
            )
        ]
        key = tuple(sorted(candidate["language"] for candidate in members))
        groups[key] = members
    majorities = [(key, members) for key, members in groups.items() if len(members) >= 3]
    if len(majorities) != 1:
        best = max((len(members) for members in groups.values()), default=0)
        return {
            "status": "no_majority", "votes": best, "objective": None,
            "languages": [],
        }
    languages, members = majorities[0]
    objective = float(median(float(candidate["objective"]) for candidate in members))
    return {
        "status": "selected", "votes": len(members),
        "objective": objective, "languages": list(languages),
    }


def _candidate(
    language: str, raw: str, solver: Callable[..., dict[str, Any]],
    solver_config: dict[str, Any],
) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        model = validate_output(parsed)
    except (TypeError, ValueError, RecursionError):
        return {
            "language": language, "status": "invalid", "reason": "invalid_milp_v1",
            "model_sha256": None, "objective": None,
        }
    try:
        solved = solver(
            {"op": "solve", "model": deepcopy(model)},
            time_limit=solver_config["solve_seconds"],
            threads=solver_config["threads"],
            wall_seconds=solver_config["wall_seconds"],
        )
    except Exception as exc:
        return {
            "language": language, "status": "solver_error",
            "reason": type(exc).__name__, "model_sha256": digest(model),
            "objective": None,
        }
    status = solved.get("status")
    objective = solved.get("objective")
    if status != "optimal" or type(objective) not in (int, float) or not math.isfinite(float(objective)):
        return {
            "language": language, "status": "nonoptimal", "reason": str(status),
            "model_sha256": digest(model), "objective": None,
        }
    return {
        "language": language, "status": "optimal", "reason": None,
        "model_sha256": digest(model), "objective": float(objective),
    }


def run_optitrust_style(
    public: dict[str, Any], gateway: Any, scope: str, replicate: int,
    token_cap: int, *, solver: Callable[..., dict[str, Any]],
    solver_config: dict[str, Any], reference_loader: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Execute the fixed nine-slot trajectory and load the reference last."""
    public = validate_public_input(public)
    gateway.register(scope, 9, token_cap)
    state: dict[str, str] = {}
    candidates: list[dict[str, Any]] = []
    for slot in range(9):
        payload = stage_payload(public, slot, state)
        prefix = digest({
            "problem": public, "replicate": replicate, "version": VERSION,
            "slot": slot, "payload": payload,
        })
        raw = gateway.request(scope, payload, prefix, replicate, slot)["text"]
        try:
            if slot <= 1:
                state["components"] = _text_output(
                    raw, "components", "decomposition_output_invalid",
                )
            elif slot <= 3:
                state["formulation"] = _text_output(
                    raw, "formulation", "formulation_output_invalid",
                )
            else:
                candidates.append(_candidate(
                    LANGUAGES[slot - 4], raw, solver, solver_config,
                ))
        except ValueError as exc:
            return {
                "schema": VERSION + "-private-result",
                "method": "OptiTrust-style-safe-sidecar",
                "problem_id": public["id"],
                "public_input_sha256": payload_sha256(public),
                "status": "method_failure", "reason": str(exc),
                "author_accept": False, "consensus": None, "candidates": candidates,
            }
    consensus = strict_majority(candidates, rtol=1e-5, atol=1e-6)
    reference = reference_loader()
    optimum = reference.get("optimum")
    accepted = (
        consensus["status"] == "selected"
        and reference.get("solver_status") == 2
        and type(optimum) in (int, float)
        and math.isfinite(float(optimum))
        and math.isclose(
            float(consensus["objective"]), float(optimum),
            rel_tol=1e-5, abs_tol=1e-6,
        )
    )
    return {
        "schema": VERSION + "-private-result",
        "method": "OptiTrust-style-safe-sidecar",
        "problem_id": public["id"],
        "public_input_sha256": payload_sha256(public),
        "status": "complete",
        "reason": None if consensus["status"] == "selected" else "no_strict_majority",
        "author_accept": bool(accepted),
        "consensus": consensus,
        "candidates": candidates,
    }


__all__ = [
    "LANGUAGES", "STAGES", "VERSION", "run_optitrust_style",
    "stage_payload", "strict_majority",
]
