"""Forward-only native Chain-of-Experts runner with a safe evaluation boundary."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any, Callable

from .benchmark_inputs import payload_sha256, validate_public_input
from .coe_official_adapter import Comment, CoEPromptSource
from .external_code_adapter import evaluate_coe_program
from .formal_gateway import atomic_text
from .milp_solver import execute
from .schema import canonical, digest


VERSION = "coe-native-forward-safe-v1"
PROMPT_VERSION = "coe-official-forward-prompts-v1"
TEXT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}


def _payload(public: dict[str, Any], instruction: str, snapshot: str,
             stage: str, step: int) -> dict[str, Any]:
    return {
        "version": PROMPT_VERSION,
        "instruction": instruction,
        "problem": public,
        "context": {"method": "Chain-of-Experts", "snapshot": snapshot,
                    "stage": stage, "step": step},
        "output_contract": {"text": "Complete official-method response."},
        "response_schema": TEXT_RESPONSE_SCHEMA,
    }


def _text(response: dict[str, Any]) -> str:
    parsed = json.loads(response["text"])
    if isinstance(parsed, dict) and set(parsed) == {"text"} and isinstance(parsed["text"], str):
        return parsed["text"]
    if isinstance(parsed, dict):
        # AntChat JSON-object mode can satisfy the official prompt directly
        # instead of using the transport-only `text` wrapper. Preserve those
        # exact response bytes as the official method response; do not infer,
        # repair, or discard fields based on their content.
        return response["text"]
    raise ValueError("coe_transport_response_shape")


def _checkpoint(path: str | Path | None, result: dict[str, Any]) -> None:
    if path is not None:
        atomic_text(Path(path), canonical(result))


def _evaluate_samples(final_answer: str, function_name: str, samples: list[dict[str, Any]],
                      solver: Callable[..., dict[str, Any]]) -> list[dict[str, Any]]:
    evaluated = []
    for index, sample in enumerate(samples):
        expected = sample.get("output")
        evaluated_program = evaluate_coe_program(
            final_answer, function_name=function_name, arguments=sample.get("input"), solver=solver,
        )
        returned = evaluated_program.get("returned_value")
        expected_scalar = expected[0] if isinstance(expected, list) and len(expected) == 1 else None
        exact = bool(evaluated_program["status"] == "evaluated" and returned == expected_scalar)
        tolerant = bool(
            type(returned) in (int, float) and type(expected_scalar) in (int, float)
            and math.isclose(float(returned), float(expected_scalar), rel_tol=1e-7, abs_tol=1e-7)
        )
        evaluated.append({
            "sample_index": index,
            "translation_status": evaluated_program["status"],
            "translation_reason": evaluated_program.get("reason"),
            "code_sha256": evaluated_program.get("code_sha256"),
            "model_sha256": evaluated_program.get("model_sha256"),
            "solver_status": evaluated_program.get("solver_status"),
            "objective": evaluated_program.get("objective"),
            "returned_value_type": type(returned).__name__ if evaluated_program["status"] == "evaluated" else None,
            "author_exact_match": exact,
            "tolerance_match": tolerant,
        })
    return evaluated


def run_coe_forward(
    public_problem: dict[str, Any],
    native_problem: dict[str, str],
    function_name: str,
    gateway: Any,
    scope: str,
    replicate: int,
    token_cap: int,
    prompts: CoEPromptSource,
    reference_loader: Callable[[], list[dict[str, Any]]],
    *,
    max_collaborations: int = 5,
    rng_seed: int = 0,
    solver: Callable[..., dict[str, Any]] = execute,
    checkpoint_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the official forward controller and evaluate only after checkpointing.

    Reflection is deliberately outside this function because the author path
    executes generated Python to create feedback.  A reflection reproduction
    requires a separately frozen safe feedback adapter.
    """
    public = validate_public_input(public_problem)
    if set(native_problem) != {"description", "code_example"} \
            or not all(isinstance(value, str) and value for value in native_problem.values()):
        raise ValueError("coe_native_problem_shape")
    if type(max_collaborations) is not int or max_collaborations <= 0:
        raise ValueError("coe_collaboration_budget")
    calls = 2 * max_collaborations + 1
    gateway.register(scope, calls, token_cap)
    rng = random.Random(rng_seed)
    comments: list[Comment] = []
    result = {
        "schema": "coe-native-forward-safe-result-v1",
        "version": VERSION,
        "method": f"CoE-{prompts.snapshot}-forward",
        "upstream_commit": prompts.commit,
        "problem_id": public["id"],
        "public_input_sha256": payload_sha256(public),
        "maximum_collaborations": max_collaborations,
        "rng_seed": rng_seed,
        "prompt_transport": "official_prompt_plus_minimal_text_wrapper",
        "generated_python_execution": "none_restricted_translation_only",
        "reflection": False,
        "steps": [],
        "status": "running",
    }
    for step in range(max_collaborations):
        conductor_prompt = prompts.conductor_prompt(
            native_problem["description"], comments, max_collaborations,
        )
        conductor_response = gateway.request(
            scope,
            _payload(public, conductor_prompt, prompts.snapshot, "conductor", step),
            digest({"method": PROMPT_VERSION, "snapshot": prompts.snapshot,
                    "problem": public["id"], "stage": "conductor", "step": step,
                    "comments": [(comment.expert_key, hashlib.sha256((comment.text or "").encode()).hexdigest())
                                 for comment in comments]}),
            replicate,
            2 * step,
        )
        conductor_answer = _text(conductor_response)
        expert = prompts.choose_expert(conductor_answer, comments, rng)
        expert_prompt = prompts.expert_prompt(
            expert, native_problem["description"], native_problem["code_example"], comments,
        )
        expert_response = gateway.request(
            scope,
            _payload(public, expert_prompt, prompts.snapshot, expert.key, step),
            digest({"method": PROMPT_VERSION, "snapshot": prompts.snapshot,
                    "problem": public["id"], "stage": expert.key, "step": step,
                    "expert": expert.name, "conductor_sha256": hashlib.sha256(conductor_answer.encode()).hexdigest()}),
            replicate,
            2 * step + 1,
        )
        raw = _text(expert_response)
        processed = prompts.process_expert_output(expert, raw)
        comments.append(Comment(expert.key, expert.name, processed))
        result["steps"].append({
            "step": step + 1,
            "expert_key": expert.key,
            "expert_name": expert.name,
            "conductor_output_sha256": hashlib.sha256(conductor_answer.encode()).hexdigest(),
            "expert_output_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "processed_output_sha256": hashlib.sha256(processed.encode()).hexdigest(),
        })
        _checkpoint(checkpoint_path, result)

    reducer_prompt = prompts.reducer_prompt(native_problem["description"], comments)
    reducer_response = gateway.request(
        scope,
        _payload(public, reducer_prompt, prompts.snapshot, "reducer", max_collaborations),
        digest({"method": PROMPT_VERSION, "snapshot": prompts.snapshot,
                "problem": public["id"], "stage": "reducer",
                "comments": [(comment.expert_key, hashlib.sha256((comment.text or "").encode()).hexdigest())
                             for comment in comments]}),
        replicate,
        2 * max_collaborations,
    )
    final_answer = _text(reducer_response)
    result["final_output_sha256"] = hashlib.sha256(final_answer.encode()).hexdigest()
    result["status"] = "inference_checkpointed"
    _checkpoint(checkpoint_path, result)

    # Evaluator-only sample inputs and outputs are loaded after the final model
    # response is durably committed to the gateway and checkpoint.
    samples = reference_loader()
    if not isinstance(samples, list) or not samples:
        raise ValueError("coe_reference_samples")
    result["samples"] = _evaluate_samples(final_answer, function_name, samples, solver)
    result["author_accept"] = all(sample["author_exact_match"] for sample in result["samples"])
    result["tolerance_accept"] = all(sample["tolerance_match"] for sample in result["samples"])
    result["adapter_supported"] = all(sample["translation_status"] == "evaluated" for sample in result["samples"])
    result["status"] = "completed"
    result["usage"] = gateway.scope_usage(scope)
    _checkpoint(checkpoint_path, result)
    return result


__all__ = ["TEXT_RESPONSE_SCHEMA", "VERSION", "run_coe_forward"]
