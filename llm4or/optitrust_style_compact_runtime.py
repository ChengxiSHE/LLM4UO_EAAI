"""Bounded paper-based OptiTrust-style trajectory with compact reviews.

This is a disclosed sensitivity adapter, not an official OptiTrust
implementation. One strict ``milp-v1`` candidate is generated, then five
language-conditioned reviewers may accept, reject, or submit bounded typed
edits. Generated Python is never executed.
"""

from __future__ import annotations

from copy import deepcopy
import json
import math
import re
from typing import Any, Callable

from .benchmark_inputs import payload_sha256, validate_public_input
from .milp_contracts import MODEL_SCHEMA, validate_output
from .optitrust_style_runtime import LANGUAGES, strict_majority
from .schema import canonical, digest


VERSION = "optitrust-style-compact-sidecar-v2"
ANALYSIS_BYTE_CAP = 8_192
REVIEW_BYTE_CAP = 65_536
MAX_EDITS = 16
STAGES = (
    "decomposition",
    "decomposition_reflection",
    "formulation_outline",
    "formulation_reflection",
    "canonical_candidate",
    *("review_" + language for language in LANGUAGES),
)
TEXT_SCHEMA = {
    "type": "object",
    "properties": {"components": {"type": "string", "minLength": 1, "maxLength": ANALYSIS_BYTE_CAP}},
    "required": ["components"],
    "additionalProperties": False,
}
FORMULATION_SCHEMA = {
    "type": "object",
    "properties": {"formulation": {"type": "string", "minLength": 1, "maxLength": ANALYSIS_BYTE_CAP}},
    "required": ["formulation"],
    "additionalProperties": False,
}
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "schema": {"const": "optitrust-review-v1"},
        "candidate_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "verdict": {"enum": ["accept", "repair", "reject"]},
        "edits": {"type": "array", "maxItems": MAX_EDITS, "items": {"type": "object"}},
    },
    "required": ["schema", "candidate_sha256", "verdict", "edits"],
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
        or len(value[key].strip().encode("utf-8")) > ANALYSIS_BYTE_CAP
    ):
        raise ValueError(failure)
    return value[key].strip()


def _instruction(stage: str, language: str | None = None) -> str:
    shared = (
        "Use only the supplied public optimization problem. Do not assume an "
        "answer, hidden reference, or unstated data. Return only the requested "
        "JSON object."
    )
    if stage == "decomposition":
        return shared + " Give a concise bounded component decomposition in `components`."
    if stage == "decomposition_reflection":
        return shared + " Correct the supplied decomposition and return only final `components`."
    if stage == "formulation_outline":
        return shared + " Give a concise indexed mathematical formulation in `formulation`."
    if stage == "formulation_reflection":
        return shared + " Correct the supplied formulation outline in `formulation`."
    if stage == "canonical_candidate":
        return shared + (
            " Produce one complete strict sparse `milp-v1` model. Use explicit "
            "finite coefficients, bounds and domains. Do not emit code."
        )
    _require(language in LANGUAGES, "review_language")
    return shared + (
        f" Review the immutable candidate as a {language} modeling expert. "
        "Return `optitrust-review-v1`: accept it, reject it, or repair it with "
        "at most 16 typed edits. Never emit code or a complete replacement model."
    )


def stage_payload(public: dict[str, Any], slot: int, state: dict[str, Any]) -> dict[str, Any]:
    """Build one exact request in the compact ten-slot trajectory."""
    public = validate_public_input(public)
    _require(type(slot) is int and 0 <= slot < len(STAGES), "optitrust_compact_slot")
    stage = STAGES[slot]
    context: dict[str, Any] = {
        "method": "OptiTrust-style-compact-sidecar",
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
    elif slot == 4:
        context["analysis_hashes"] = deepcopy(state.get("analysis_hashes", {}))
        context["safe_execution_adapter"] = "single_strict_milp_v1_sidecar"
    elif slot >= 5:
        language = LANGUAGES[slot - 5]
        context.update({
            "modeling_language": language,
            "candidate": deepcopy(state.get("candidate")),
            "candidate_sha256": state.get("candidate_sha256"),
            "safe_execution_adapter": "bounded_typed_review_v1",
        })
    if slot in (0, 1):
        schema, contract = TEXT_SCHEMA, {"components": "Bounded corrected component analysis."}
    elif slot in (2, 3):
        schema, contract = FORMULATION_SCHEMA, {"formulation": "Bounded indexed formulation outline."}
    elif slot == 4:
        schema, contract = MODEL_SCHEMA, {"schema": "One strict milp-v1 object; code is forbidden."}
    else:
        schema, contract = REVIEW_SCHEMA, {"schema": "One hash-bound optitrust-review-v1 object."}
    return {
        "version": VERSION,
        "instruction": _instruction(stage, language),
        "problem": public,
        "context": context,
        "output_contract": contract,
        "response_schema": deepcopy(schema),
    }


def _invalid(language: str, reason: str) -> dict[str, Any]:
    return {"language": language, "status": "invalid", "reason": reason, "model": None}


def _resource_ok(model: dict[str, Any], limits: dict[str, int]) -> bool:
    if set(limits) != {"variables", "constraints", "nonzeros", "serialized_bytes"}:
        return False
    if any(type(value) is not int or value < 0 for value in limits.values()):
        return False
    nonzeros = len(model["objective"]["coefficients"]) + sum(
        len(row["coefficients"]) for row in model["constraints"]
    )
    return (
        len(model["variables"]) <= limits["variables"]
        and len(model["constraints"]) <= limits["constraints"]
        and nonzeros <= limits["nonzeros"]
        and len(canonical(model).encode("utf-8")) <= limits["serialized_bytes"]
    )


def _validate_review_shape(review: Any) -> None:
    _require(type(review) is dict, "invalid_review")
    _require(set(review) == {"schema", "candidate_sha256", "verdict", "edits"}, "invalid_review")
    _require(review["schema"] == "optitrust-review-v1", "invalid_review")
    _require(type(review["candidate_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", review["candidate_sha256"]) is not None, "invalid_review")
    _require(review["verdict"] in {"accept", "repair", "reject"}, "invalid_review")
    _require(type(review["edits"]) is list and len(review["edits"]) <= MAX_EDITS, "invalid_review")
    _require(len(canonical(review).encode("utf-8")) <= REVIEW_BYTE_CAP, "review_size_limit")


def apply_review(
    candidate: dict[str, Any], review: Any, *, language: str,
    resource_limits: dict[str, int],
) -> dict[str, Any]:
    """Apply one bounded hash-bound review with a fail-closed typed composer."""
    try:
        _require(language in LANGUAGES, "review_language")
        candidate = validate_output(deepcopy(candidate))
        _validate_review_shape(review)
        _require(review["candidate_sha256"] == digest(candidate), "stale_candidate_hash")
        verdict, edits = review["verdict"], review["edits"]
        if verdict in {"accept", "reject"}:
            _require(edits == [], "verdict_edit_mismatch")
        if verdict == "reject":
            return {"language": language, "status": "rejected", "reason": "review_rejected", "model": None}
        if verdict == "accept":
            _require(_resource_ok(candidate, resource_limits), "resource_limit")
            return {"language": language, "status": "valid", "reason": None, "model": candidate}
        _require(1 <= len(edits) <= MAX_EDITS, "repair_edit_count")
        updated = deepcopy(candidate)
        variables = {row["id"]: row for row in updated["variables"]}
        constraints = {row["id"]: row for row in updated["constraints"]}
        seen: set[tuple[str, str]] = set()
        for edit in edits:
            _require(type(edit) is dict and type(edit.get("op")) is str, "invalid_edit")
            op = edit["op"]
            if op == "replace_variable":
                _require(set(edit) == {"op", "id", "value"} and type(edit["id"]) is str, "invalid_edit")
                target = ("variable", edit["id"]); _require(target not in seen, "duplicate_edit_target"); seen.add(target)
                _require(edit["id"] in variables, "unknown_variable")
                _require(type(edit["value"]) is dict and edit["value"].get("id") == edit["id"], "variable_identity")
                variables[edit["id"]] = deepcopy(edit["value"])
            elif op == "upsert_constraint":
                _require(set(edit) == {"op", "id", "value"} and type(edit["id"]) is str, "invalid_edit")
                target = ("constraint", edit["id"]); _require(target not in seen, "duplicate_edit_target"); seen.add(target)
                _require(type(edit["value"]) is dict and edit["value"].get("id") == edit["id"], "constraint_identity")
                constraints[edit["id"]] = deepcopy(edit["value"])
            elif op == "delete_constraint":
                _require(set(edit) == {"op", "id"} and type(edit["id"]) is str, "invalid_edit")
                target = ("constraint", edit["id"]); _require(target not in seen, "duplicate_edit_target"); seen.add(target)
                _require(edit["id"] in constraints, "unknown_constraint")
                del constraints[edit["id"]]
            elif op == "replace_objective":
                _require(set(edit) == {"op", "value"}, "invalid_edit")
                target = ("objective", "objective"); _require(target not in seen, "duplicate_edit_target"); seen.add(target)
                _require(type(edit["value"]) is dict, "invalid_edit")
                updated["objective"] = deepcopy(edit["value"])
            else:
                raise ValueError("unknown_edit_operation")
        updated["variables"] = list(variables.values())
        updated["constraints"] = list(constraints.values())
        updated = validate_output(updated)
        _require(_resource_ok(updated, resource_limits), "resource_limit")
        return {"language": language, "status": "valid", "reason": None, "model": updated}
    except (TypeError, ValueError, RecursionError) as exc:
        return _invalid(language, str(exc) or "invalid_review")


def _solve_view(
    applied: dict[str, Any], solver: Callable[..., dict[str, Any]],
    solver_config: dict[str, Any],
) -> dict[str, Any]:
    if applied["status"] != "valid":
        return {
            "language": applied["language"], "status": applied["status"],
            "reason": applied["reason"], "model_sha256": None, "objective": None,
        }
    model = applied["model"]
    try:
        solved = solver(
            {"op": "solve", "model": deepcopy(model)},
            time_limit=solver_config["solve_seconds"],
            threads=solver_config["threads"],
            wall_seconds=solver_config["wall_seconds"],
        )
    except Exception as exc:
        return {
            "language": applied["language"], "status": "solver_error",
            "reason": type(exc).__name__, "model_sha256": digest(model), "objective": None,
        }
    objective = solved.get("objective")
    if solved.get("status") != "optimal" or type(objective) not in (int, float) or not math.isfinite(float(objective)):
        return {
            "language": applied["language"], "status": "nonoptimal",
            "reason": str(solved.get("status")), "model_sha256": digest(model), "objective": None,
        }
    return {
        "language": applied["language"], "status": "optimal", "reason": None,
        "model_sha256": digest(model), "objective": float(objective),
    }


def _method_failure(public: dict[str, Any], reason: str, views: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": VERSION + "-private-result",
        "method": "OptiTrust-style-compact-sidecar",
        "problem_id": public["id"],
        "public_input_sha256": payload_sha256(public),
        "status": "method_failure", "reason": reason,
        "author_accept": False, "consensus": None, "views": views,
    }


def run_optitrust_style_compact(
    public: dict[str, Any], gateway: Any, scope: str, replicate: int,
    token_cap: int, *, solver: Callable[..., dict[str, Any]],
    solver_config: dict[str, Any], resource_limits: dict[str, int],
    reference_loader: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Execute ten fixed slots and load evaluator-only reference data last."""
    public = validate_public_input(public)
    gateway.register(scope, len(STAGES), token_cap)
    state: dict[str, Any] = {"analysis_hashes": {}}
    views: list[dict[str, Any]] = []
    for slot in range(len(STAGES)):
        payload = stage_payload(public, slot, state)
        prefix = digest({
            "problem": public, "replicate": replicate, "version": VERSION,
            "slot": slot, "payload": payload,
        })
        raw = gateway.request(scope, payload, prefix, replicate, slot)["text"]
        try:
            if slot <= 1:
                value = _text_output(raw, "components", "decomposition_output_invalid")
                state["components"] = value
                state["analysis_hashes"][f"slot_{slot}_components"] = digest({"components": value})
            elif slot <= 3:
                value = _text_output(raw, "formulation", "formulation_output_invalid")
                state["formulation"] = value
                state["analysis_hashes"][f"slot_{slot}_formulation"] = digest({"formulation": value})
            elif slot == 4:
                candidate = validate_output(json.loads(raw))
                _require(_resource_ok(candidate, resource_limits), "canonical_resource_limit")
                state["candidate"] = candidate
                state["candidate_sha256"] = digest(candidate)
            else:
                language = LANGUAGES[slot - 5]
                try:
                    parsed = json.loads(raw)
                except (TypeError, ValueError, RecursionError):
                    parsed = None
                applied = apply_review(
                    state["candidate"], parsed, language=language,
                    resource_limits=resource_limits,
                )
                views.append(_solve_view(applied, solver, solver_config))
        except (TypeError, ValueError, RecursionError) as exc:
            reason = str(exc) or (
                "canonical_candidate_invalid" if slot == 4 else "compact_output_invalid"
            )
            if slot == 4 and reason not in {"canonical_resource_limit"}:
                reason = "canonical_candidate_invalid"
            return _method_failure(public, reason, views)
    consensus = strict_majority(views, rtol=1e-5, atol=1e-6)
    reference = reference_loader()
    optimum = reference.get("optimum")
    accepted = (
        consensus["status"] == "selected"
        and reference.get("solver_status") == 2
        and type(optimum) in (int, float)
        and math.isfinite(float(optimum))
        and math.isclose(float(consensus["objective"]), float(optimum), rel_tol=1e-5, abs_tol=1e-6)
    )
    return {
        "schema": VERSION + "-private-result",
        "method": "OptiTrust-style-compact-sidecar",
        "problem_id": public["id"],
        "public_input_sha256": payload_sha256(public),
        "status": "complete",
        "reason": None if consensus["status"] == "selected" else "no_strict_majority",
        "author_accept": bool(accepted),
        "canonical_model_sha256": state["candidate_sha256"],
        "consensus": consensus,
        "views": views,
    }


__all__ = [
    "ANALYSIS_BYTE_CAP", "LANGUAGES", "MAX_EDITS", "REVIEW_SCHEMA",
    "STAGES", "VERSION", "apply_review", "run_optitrust_style_compact",
    "stage_payload",
]
