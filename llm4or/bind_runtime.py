"""Durable common-backbone runner for the official BIND instance-data method."""

from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Any, Callable

from .benchmark_inputs import payload_sha256, validate_public_input
from .bind_official_adapter import (
    BindEvaluation, BindPromptSource, objective_match, repair_prompt,
)
from .external_code_adapter import translate_generated_gurobi
from .formal_gateway import atomic_text
from .milp_solver import execute
from .schema import canonical, digest


VERSION = "text2opt-bind-common-backbone-v3"
PROMPT_VERSION = "text2opt-bind-common-backbone-v1"
BIND_SOLVER_LIMITS = {
    "solve_seconds": 20.0, "total_seconds": 25.0,
    "node_limit": 100000, "max_queries": 1,
}
CODE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"code": {"type": "string", "minLength": 1}},
    "required": ["code"],
    "additionalProperties": False,
}


def public_bind_projection(problem_data: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields consumed by the official initial prompt."""
    meta = problem_data.get("meta", {})
    return {
        "meta": {
            "problem_type": meta.get("problem_type", "optimization"),
            "goal": meta.get("goal", ""),
        },
        "instance_data": deepcopy(problem_data.get("instance_data", {})),
        "LLM_description": problem_data.get("LLM_description", ""),
        "LLM_description_template": problem_data.get("LLM_description_template", ""),
    }


def bind_reference_projection(problem_data: dict[str, Any]) -> dict[str, Any]:
    """Evaluator-only projection matching the official Text2Opt evaluator."""
    meta = problem_data.get("meta", {})
    result = problem_data.get("gurobi_result", {})
    optimum = result.get("theoretical_optimum", meta.get("theoretical_optimum", 0.0))
    status = result.get("solver_status", meta.get("solver_status"))
    reference = {
        "optimum": optimum,
        "solver_status": status,
        "num_vars": meta.get("num_vars"),
        "num_constraints": meta.get("num_constraints"),
    }
    if type(optimum) not in (int, float) or not math.isfinite(float(optimum)):
        raise ValueError("invalid_bind_reference_optimum")
    if status is not None and type(status) is not int:
        raise ValueError("invalid_bind_reference_status")
    for name in ("num_vars", "num_constraints"):
        if reference[name] is not None and (type(reference[name]) is not int or reference[name] < 0):
            raise ValueError("invalid_bind_reference_structure")
    return reference


def _response_payload(
    public: dict[str, Any], instruction: str, round_index: int, transport_adapter: str,
) -> dict[str, Any]:
    return {
        "version": PROMPT_VERSION,
        "instruction": instruction,
        "problem": public,
        "context": {
            "method": "Text2Opt/BIND",
            "upstream_mode": "instance_data",
            "round": round_index,
            "transport_adapter": transport_adapter,
        },
        "output_contract": {
            "code": "One complete fenced Python block following the official BIND prompt.",
        },
        "response_schema": CODE_RESPONSE_SCHEMA,
    }


def _flatten_transcript(system: str, turns: list[tuple[str, str]]) -> str:
    sections = ["Official BIND system message:\n" + system]
    for role, content in turns:
        sections.append(f"Official BIND {role} message:\n{content}")
    sections.append(
        "Transport requirement: place the complete official-method response in the `code` field. "
        "The field value itself must contain exactly one fenced Python block."
    )
    return "\n\n".join(sections)


def _gurobi_status(solve: dict[str, Any] | None) -> int | None:
    if not solve:
        return None
    return {"optimal": 2, "infeasible": 3, "unbounded": 5}.get(solve.get("status"))


def _evaluate(code: str, instance_data: dict[str, Any], virtual_path: str,
              reference: dict[str, Any], solver: Callable[..., dict[str, Any]]) -> tuple[BindEvaluation, dict]:
    translated = translate_generated_gurobi(code, data_files={virtual_path: instance_data})
    solved = None
    model = translated.get("model")
    if translated["status"] == "compiled":
        operation = {"op": "solve", "model": deepcopy(model)}
        solved = (
            solver(operation, wall_seconds=30, limits=BIND_SOLVER_LIMITS)
            if solver is execute else solver(operation)
        )
    status = _gurobi_status(solved)
    value = solved.get("objective") if solved else None
    execution_succeeded = translated["status"] == "compiled" and isinstance(solved, dict)
    status_optimal = status == reference["solver_status"]
    matched = objective_match(value, float(reference["optimum"]))
    if translated["status"] != "compiled":
        stderr = translated.get("reason", "translation_rejected")
    elif solved.get("status") != "optimal":
        stderr = solved.get("reason") or solved.get("message") or solved.get("status", "solver_failure")
    else:
        stderr = ""
    evaluation = BindEvaluation(
        execution_succeeded=execution_succeeded,
        status_optimal=status_optimal,
        objective_matches=matched,
        objective_value=value,
        reference_optimum=float(reference["optimum"]),
        solver_status=status,
        reference_status=reference["solver_status"],
        num_vars=len(model["variables"]) if model else None,
        num_constraints=len(model["constraints"]) if model else None,
        reference_num_vars=reference["num_vars"],
        reference_num_constraints=reference["num_constraints"],
        stderr=str(stderr)[:1600],
    )
    public_result = {
        "translation_status": translated["status"],
        "translation_reason": translated.get("reason"),
        "output_sha256": translated.get("output_sha256"),
        "code_sha256": translated.get("code_sha256"),
        "model_sha256": translated.get("model_sha256"),
        "solver_status": solved.get("status") if solved else None,
        "objective": value,
        "execution_succeeded": execution_succeeded,
        "status_matches": status_optimal,
        "objective_matches": matched,
        "num_vars": evaluation.num_vars,
        "num_constraints": evaluation.num_constraints,
    }
    return evaluation, public_result


def _checkpoint(path: str | Path | None, result: dict[str, Any]) -> None:
    if path is not None:
        atomic_text(Path(path), canonical(result))


def run_bind_instance_data(
    public_problem: dict[str, Any],
    bind_problem: dict[str, Any],
    gateway: Any,
    scope: str,
    replicate: int,
    token_cap: int,
    prompt_source: BindPromptSource,
    reference_loader: Callable[[], dict[str, Any]],
    *,
    max_rounds: int = 3,
    solver: Callable[..., dict[str, Any]] = execute,
    checkpoint_path: str | Path | None = None,
    transport_adapter: str = "stateless_transcript_flattening",
) -> dict[str, Any]:
    """Run BIND while loading evaluator-only references after each saved response.

    The Codex CLI is stateless, so the official message sequence is flattened
    verbatim into each request.  This transport-only deviation is disclosed in
    the result and does not change the official prompts or repair budget.
    """
    public = validate_public_input(public_problem)
    prompt_problem = public_bind_projection(bind_problem)
    if not prompt_problem["instance_data"]:
        raise ValueError("bind_instance_data_required")
    if type(max_rounds) is not int or not 1 <= max_rounds <= 3:
        raise ValueError("bind_round_budget")
    if transport_adapter not in {
        "stateless_transcript_flattening", "stateless_antchat_chat_completions",
    }:
        raise ValueError("bind_transport_adapter")
    gateway.register(scope, max_rounds, token_cap)
    virtual_path = "/bind_data/" + digest({
        "problem_id": public["id"], "instance_data": prompt_problem["instance_data"],
    }) + ".json"
    initial = prompt_source.initial_prompt(prompt_problem, virtual_path)
    turns: list[tuple[str, str]] = [("user", initial)]
    result = {
        "schema": "text2opt-bind-common-backbone-result-v1",
        "version": VERSION,
        "method": "BIND-common-backbone-oracle-repair",
        "upstream_commit": "1dac06be656c41d827ef20987cf8af0b48d382a2",
        "problem_id": public["id"],
        "public_input_sha256": payload_sha256(public),
        "prompt_transport": (
            "official_messages_flattened_for_stateless_codex_cli"
            if transport_adapter == "stateless_transcript_flattening"
            else "official_messages_flattened_for_" + transport_adapter
        ),
        "generated_code_execution": "none_restricted_translation_only",
        "maximum_rounds": max_rounds,
        "rounds": [],
        "success": False,
        "status": "running",
    }
    reference = None
    for slot in range(max_rounds):
        round_index = slot + 1
        instruction = _flatten_transcript(prompt_source.system_prompt, turns)
        payload = _response_payload(public, instruction, round_index, transport_adapter)
        prefix = digest({
            "method": PROMPT_VERSION, "problem": public["id"], "replicate": replicate,
            "round": round_index, "transcript_sha256": digest(turns),
        })
        response = gateway.request(scope, payload, prefix, replicate, slot)
        parsed = json.loads(response["text"])
        code = parsed["code"]

        # The gateway has durably committed the inference response before this
        # callback can expose evaluator-only answers to the repair controller.
        if reference is None:
            reference = reference_loader()
        required_reference = {"optimum", "solver_status", "num_vars", "num_constraints"}
        if not isinstance(reference, dict) or set(reference) != required_reference:
            raise ValueError("bind_reference_shape")
        evaluation, round_result = _evaluate(
            code, prompt_problem["instance_data"], virtual_path, reference, solver,
        )
        round_result.update({
            "round": round_index,
            "request_total_tokens": response.get("total_tokens"),
            "official_oracle_feedback_available_after_round": round_index < max_rounds,
        })
        result["rounds"].append(round_result)
        result["success"] = (
            evaluation.execution_succeeded and evaluation.status_optimal
            and evaluation.objective_matches
        )
        result["status"] = "completed_success" if result["success"] else "running"
        _checkpoint(checkpoint_path, result)
        if result["success"]:
            break
        if round_index < max_rounds:
            turns.append(("assistant", code))
            turns.append(("user", repair_prompt(evaluation, virtual_path)))
    if not result["success"]:
        result["status"] = "completed_failure"
    result["rounds_used"] = len(result["rounds"])
    result["usage"] = gateway.scope_usage(scope)
    _checkpoint(checkpoint_path, result)
    return result


__all__ = [
    "CODE_RESPONSE_SCHEMA", "VERSION", "bind_reference_projection",
    "public_bind_projection", "run_bind_instance_data",
]
