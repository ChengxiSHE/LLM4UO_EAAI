"""Compact OptiTrust-style trajectory using a bounded indexed MILP IR.

This disclosed sensitivity adapter is not an official reproduction.  A model
proposes one compact IR, a trusted benchmark-agnostic interpreter expands it,
and five language-conditioned reviewers may accept, reject, abstain, or submit
bounded replacement patches.  Generated code is never executed.
"""

from __future__ import annotations

from copy import deepcopy
import json
import math
import re
from typing import Any, Callable

from .benchmark_inputs import payload_sha256, validate_public_input
from .formal_gateway import RequestUnavailable
from .indexed_milp_ir import IRCompileError, compile_ir, validate_ir_surface
from .optitrust_style_runtime import LANGUAGES, strict_majority
from .schema import canonical, digest


VERSION = "optitrust-style-indexed-sidecar-v3"
ANALYSIS_BYTE_CAP = 8_192
REVIEW_BYTE_CAP = 32_768
MAX_PATCHES = 8
MAX_PATCH_DEPTH = 12
STAGES = (
    "decomposition", "decomposition_reflection",
    "formulation_outline", "formulation_reflection",
    "canonical_indexed_ir",
    *("review_" + language for language in LANGUAGES),
)
TEXT_SCHEMA = {
    "type": "object",
    "properties": {"components": {"type": "string", "minLength": 1, "maxLength": ANALYSIS_BYTE_CAP}},
    "required": ["components"], "additionalProperties": False,
}
FORMULATION_SCHEMA = {
    "type": "object",
    "properties": {"formulation": {"type": "string", "minLength": 1, "maxLength": ANALYSIS_BYTE_CAP}},
    "required": ["formulation"], "additionalProperties": False,
}
IR_SCHEMA = {
    "type": "object",
    "properties": {
        "schema": {"const": "indexed-milp-ir-v1"},
        "data_parameter": {"const": "instance_data"},
        "sets": {"type": "array", "items": {"type": "object"}},
        "variables": {"type": "array", "items": {"type": "object"}},
        "constraints": {"type": "array", "items": {"type": "object"}},
        "objective": {"type": "object"},
    },
    "required": ["schema", "data_parameter", "sets", "variables", "constraints", "objective"],
    "additionalProperties": False,
}
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "schema": {"const": "optitrust-ir-review-v1"},
        "candidate_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "verdict": {"enum": ["accept", "repair", "reject"]},
        "patches": {"type": "array", "maxItems": MAX_PATCHES, "items": {"type": "object"}},
    },
    "required": ["schema", "candidate_sha256", "verdict", "patches"],
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
        type(value) is not dict or set(value) != {key}
        or type(value[key]) is not str or not value[key].strip()
        or len(value[key].strip().encode()) > ANALYSIS_BYTE_CAP
    ):
        raise ValueError(failure)
    return value[key].strip()


def _instance_data(public: dict[str, Any]) -> Any:
    public = validate_public_input(public)
    _require(
        len(public.get("parameters", [])) == 1
        and public["parameters"][0].get("symbol") == "instance_data"
        and public["parameters"][0].get("shape") == []
        and len(public.get("instances", [])) == 1
        and type(public["instances"][0].get("input")) is dict
        and set(public["instances"][0]["input"]) == {"instance_data"},
        "public_instance_contract",
    )
    return deepcopy(public["instances"][0]["input"]["instance_data"])


def _ir_language_contract() -> dict[str, Any]:
    return {
        "schema": "indexed-milp-ir-v1",
        "top_level_keys": ["schema", "data_parameter", "sets", "variables", "constraints", "objective"],
        "sets": {
            "range": ["id", "kind", "start", "stop"],
            "records": ["id", "kind", "path", "arity"],
        },
        "bindings": [
            {"name": "index_name", "set": "declared_set_id"},
            {"unpack": ["record", "field", "names"], "set": "declared_record_set_id"},
        ],
        "numeric_expressions": [
            "finite JSON number", {"env": "binding_name"},
            {"data": ["key_or_numeric_index", "..."]},
            {"op": "add|sub|mul|div|neg|sqrt|min|max", "args": ["numeric_expr"]},
            {"if": {"condition": "predicate", "then": "numeric_expr", "else": "numeric_expr"}},
            {"aggregate": "sum|min|max", "over": ["bindings"], "where": "predicate", "value": "numeric_expr"},
        ],
        "predicates": [
            "true_or_false",
            {"compare": "eq|ne|lt|le|gt|ge", "left": "numeric_expr", "right": "numeric_expr"},
            {"logic": "and|or|not", "args": ["predicate"]},
            {"aggregate": "any|all", "over": ["bindings"], "where": "predicate", "predicate": "predicate"},
        ],
        "variable_keys": ["id", "meaning", "unit", "domain", "forall", "where", "lower", "upper"],
        "constraint_keys": ["id", "forall", "where", "terms", "sense", "rhs"],
        "term_keys": ["family", "indices", "coefficient", "sum", "where"],
        "objective_keys": ["terms", "sense", "unit", "offset"],
        "rules": [
            "Use only declared finite sets and public instance_data paths.",
            "A data path may start with instance_data; later binding-name strings are resolved as indices.",
            "Numeric binding references may be a binding-name string, {name:...}, or {env:...}.",
            "Safe defaults: forall=[], where=true, lower=null, upper=null, unit='unit', coefficient=1, sum=[], indices=[], offset=0.",
            "The objective sense may be min/max or minimize/maximize; constraint senses are le/ge/eq.",
            "Every generated family index must be a nonnegative integer.",
            "All coefficients must remain linear in decision variables.",
            "Return the IR JSON only; do not return code or an expanded model.",
        ],
    }


def _instruction(stage: str, language: str | None = None) -> str:
    shared = (
        "Use only the supplied public optimization problem and instance_data. "
        "Do not assume a hidden reference, answer, or unstated fact. Return only "
        "the requested JSON object."
    )
    if stage == "decomposition":
        return shared + " Give a concise component decomposition in `components`."
    if stage == "decomposition_reflection":
        return shared + " Correct the supplied decomposition and return final `components`."
    if stage == "formulation_outline":
        return shared + " Give a concise indexed mathematical formulation in `formulation`."
    if stage == "formulation_reflection":
        return shared + " Correct the supplied indexed formulation in `formulation`."
    if stage == "canonical_indexed_ir":
        return shared + (
            " Encode one complete model in the supplied `indexed-milp-ir-v1` "
            "language. Keep it compact and do not emit Python or expanded milp-v1."
        )
    _require(language in LANGUAGES, "review_language")
    return shared + (
        f" Review the immutable indexed IR as a {language} modeling expert. "
        "Return optitrust-ir-review-v1. Accept, reject, or repair with at most "
        "eight replacement patches; each patch has op='replace', a path array "
        "to an existing value, and a replacement value. Do not emit code."
    )


def stage_payload(public: dict[str, Any], slot: int, state: dict[str, Any]) -> dict[str, Any]:
    public = validate_public_input(public)
    _require(type(slot) is int and 0 <= slot < len(STAGES), "optitrust_indexed_slot")
    stage = STAGES[slot]
    context: dict[str, Any] = {
        "method": "OptiTrust-style-indexed-sidecar", "stage": stage, "step": slot,
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
        context["safe_execution_adapter"] = "indexed_milp_ir_v1"
    elif slot >= 5:
        language = LANGUAGES[slot - 5]
        context.update({
            "modeling_language": language,
            "candidate_ir": deepcopy(state.get("candidate_ir")),
            "candidate_sha256": state.get("candidate_sha256"),
            "candidate_admitted": state.get("canonical_admitted"),
            "candidate_admission_error": state.get("canonical_admission_error"),
            "safe_execution_adapter": "bounded_ir_replacement_patch_v1",
        })
    if slot in (0, 1):
        response_schema, contract = TEXT_SCHEMA, {"components": "Bounded corrected component analysis."}
    elif slot in (2, 3):
        response_schema, contract = FORMULATION_SCHEMA, {"formulation": "Bounded indexed formulation outline."}
    elif slot == 4:
        response_schema, contract = IR_SCHEMA, _ir_language_contract()
    else:
        response_schema, contract = REVIEW_SCHEMA, {
            "schema": "optitrust-ir-review-v1",
            "patch": {"op": "replace", "path": ["existing", "path"], "value": "replacement"},
        }
    return {
        "version": VERSION, "instruction": _instruction(stage, language),
        "problem": public, "context": context, "output_contract": contract,
        "response_schema": deepcopy(response_schema),
    }


def _invalid(language: str, reason: str) -> dict[str, Any]:
    return {"language": language, "status": "invalid", "reason": reason, "model": None}


def _validate_review_shape(review: Any) -> None:
    _require(type(review) is dict, "invalid_review")
    _require(set(review) == {"schema", "candidate_sha256", "verdict", "patches"}, "invalid_review")
    _require(review["schema"] == "optitrust-ir-review-v1", "invalid_review")
    _require(
        type(review["candidate_sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", review["candidate_sha256"]) is not None,
        "invalid_review",
    )
    _require(review["verdict"] in {"accept", "repair", "reject"}, "invalid_review")
    _require(type(review["patches"]) is list and len(review["patches"]) <= MAX_PATCHES, "invalid_review")
    _require(len(canonical(review).encode()) <= REVIEW_BYTE_CAP, "review_size_limit")


def _replace_existing(root: Any, path: Any, value: Any) -> None:
    _require(type(path) is list and 1 <= len(path) <= MAX_PATCH_DEPTH, "invalid_patch_path")
    current = root
    for component in path[:-1]:
        if type(current) is dict:
            _require(type(component) is str and component in current, "unknown_patch_path")
            current = current[component]
        elif type(current) is list:
            _require(type(component) is int and 0 <= component < len(current), "unknown_patch_path")
            current = current[component]
        else:
            raise ValueError("unknown_patch_path")
    final = path[-1]
    if type(current) is dict:
        _require(type(final) is str and final in current, "unknown_patch_path")
    elif type(current) is list:
        _require(type(final) is int and 0 <= final < len(current), "unknown_patch_path")
    else:
        raise ValueError("unknown_patch_path")
    current[final] = deepcopy(value)


def apply_ir_review(
    candidate_ir: dict[str, Any], review: Any, *, data: Any, language: str,
    resource_limits: dict[str, int],
) -> dict[str, Any]:
    """Compile an accepted IR or a bounded, hash-bound replacement-patched IR."""
    try:
        _require(language in LANGUAGES, "review_language")
        _validate_review_shape(review)
        _require(review["candidate_sha256"] == digest(candidate_ir), "stale_candidate_hash")
        verdict, patches = review["verdict"], review["patches"]
        if verdict in {"accept", "reject"}:
            _require(patches == [], "verdict_patch_mismatch")
        if verdict == "reject":
            return {"language": language, "status": "rejected", "reason": "review_rejected", "model": None}
        updated = deepcopy(candidate_ir)
        if verdict == "repair":
            _require(1 <= len(patches) <= MAX_PATCHES, "repair_patch_count")
            seen = set()
            for patch in patches:
                _require(type(patch) is dict and set(patch) == {"op", "path", "value"}, "invalid_patch")
                _require(patch["op"] == "replace", "invalid_patch")
                try:
                    path_key = canonical(patch["path"])
                except (TypeError, ValueError, RecursionError, OverflowError):
                    raise ValueError("invalid_patch_path") from None
                _require(path_key not in seen, "duplicate_patch_path")
                seen.add(path_key)
                _replace_existing(updated, patch["path"], patch["value"])
        admission = compile_ir(data, updated, resource_limits)
        return {
            "language": language, "status": "valid", "reason": None,
            "model": admission["model"], "ir_sha256": admission["ir_sha256"],
            "admission_metrics": admission["metrics"],
        }
    except (IRCompileError, TypeError, ValueError, RecursionError) as exc:
        return _invalid(language, str(exc) or "invalid_review")


def _solve_view(applied, solver, solver_config):
    if applied["status"] != "valid":
        return {
            "language": applied["language"], "status": applied["status"],
            "reason": applied["reason"], "model_sha256": None, "objective": None,
        }
    model = applied["model"]
    try:
        solved = solver(
            {"op": "solve", "model": deepcopy(model)},
            time_limit=solver_config["solve_seconds"], threads=solver_config["threads"],
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


def _method_failure(public, reason, views):
    return {
        "schema": VERSION + "-private-result", "method": "OptiTrust-style-indexed-sidecar",
        "problem_id": public["id"], "public_input_sha256": payload_sha256(public),
        "status": "method_failure", "reason": reason, "author_accept": False,
        "consensus": None, "views": views, "review_abstentions": 0,
    }


def run_optitrust_style_indexed(
    public: dict[str, Any], gateway: Any, scope: str, replicate: int,
    token_cap: int, *, solver: Callable[..., dict[str, Any]],
    solver_config: dict[str, Any], resource_limits: dict[str, int],
    reference_loader: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Run ten fixed slots; reviewer transport exhaustion is an abstention."""
    public = validate_public_input(public)
    data = _instance_data(public)
    gateway.register(scope, len(STAGES), token_cap)
    state: dict[str, Any] = {"analysis_hashes": {}}
    views: list[dict[str, Any]] = []
    abstentions = 0
    for slot in range(len(STAGES)):
        payload = stage_payload(public, slot, state)
        prefix = digest({
            "problem": public, "replicate": replicate, "version": VERSION,
            "slot": slot, "payload": payload,
        })
        try:
            response = gateway.request(scope, payload, prefix, replicate, slot)
        except RequestUnavailable:
            if slot < 5:
                raise
            language = LANGUAGES[slot - 5]
            views.append({
                "language": language, "status": "abstained",
                "reason": "review_infrastructure_unavailable",
                "model_sha256": None, "objective": None,
            })
            abstentions += 1
            continue
        raw = response["text"]
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
                candidate_ir = json.loads(raw)
                surface = validate_ir_surface(candidate_ir)
                state["candidate_ir"] = candidate_ir
                state["candidate_sha256"] = surface["ir_sha256"]
                try:
                    admission = compile_ir(data, candidate_ir, resource_limits)
                except IRCompileError as exc:
                    state["canonical_admitted"] = False
                    state["canonical_admission_error"] = str(exc).split(":", 1)[0]
                    state["canonical_model_sha256"] = None
                else:
                    state["canonical_admitted"] = True
                    state["canonical_admission_error"] = None
                    state["canonical_model_sha256"] = admission["model_sha256"]
            else:
                language = LANGUAGES[slot - 5]
                try:
                    parsed = json.loads(raw)
                except (TypeError, ValueError, RecursionError):
                    parsed = None
                applied = apply_ir_review(
                    state["candidate_ir"], parsed, data=data, language=language,
                    resource_limits=resource_limits,
                )
                views.append(_solve_view(applied, solver, solver_config))
        except (IRCompileError, TypeError, ValueError, RecursionError) as exc:
            reason = str(exc) or "indexed_output_invalid"
            if slot == 4:
                reason = "canonical_ir_invalid"
            return _method_failure(public, reason, views)
    consensus = strict_majority(views, rtol=1e-5, atol=1e-6)
    reference = reference_loader()
    optimum = reference.get("optimum")
    accepted = (
        consensus["status"] == "selected" and reference.get("solver_status") == 2
        and type(optimum) in (int, float) and math.isfinite(float(optimum))
        and math.isclose(float(consensus["objective"]), float(optimum), rel_tol=1e-5, abs_tol=1e-6)
    )
    return {
        "schema": VERSION + "-private-result", "method": "OptiTrust-style-indexed-sidecar",
        "problem_id": public["id"], "public_input_sha256": payload_sha256(public),
        "status": "complete", "reason": None if consensus["status"] == "selected" else "no_strict_majority",
        "author_accept": bool(accepted), "canonical_ir_sha256": state["candidate_sha256"],
        "canonical_model_sha256": state["canonical_model_sha256"],
        "canonical_admitted": state["canonical_admitted"],
        "canonical_admission_error": state["canonical_admission_error"],
        "consensus": consensus, "views": views, "review_abstentions": abstentions,
    }
