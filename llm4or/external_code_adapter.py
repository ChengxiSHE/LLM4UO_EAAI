"""Fail-closed adapters for code-emitting external NL2Opt baselines."""

import hashlib
import re
from typing import Any

from .milp_solver import execute
from .restricted_gurobi import (
    RestrictedCodeError, compile_gurobi_function_source, compile_gurobi_source,
    evaluate_optimization_function_source,
)
from .schema import digest

MAX_OUTPUT_BYTES = 4_000_000

_FENCES = [
    r"```python\s*\n(.*?)\n\s*```",
    r"```python\s*\n(.*?)```",
    r"```gurobi\s*\n(.*?)\n\s*```",
    r"```gurobi\s*\n(.*?)```",
    r"```py\s*\n(.*?)\n\s*```",
    r"```py\s*\n(.*?)```",
    r"```\s*\n(.*?)\n\s*```",
]


def extract_python_code(model_output: str) -> str | None:
    """Match Text2Opt's last-code-block extraction without executing it."""
    if not isinstance(model_output, str) or len(model_output.encode()) > MAX_OUTPUT_BYTES:
        return None
    text = model_output.strip()
    for pattern in _FENCES:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            code = matches[-1].strip()
            code = re.sub(r"^```(?:python|py|gurobi)?\s*\n", "", code)
            code = re.sub(r"\n\s*```\s*$", "", code)
            return code.strip()
    cleaned = text
    if cleaned.startswith("python\n"):
        cleaned = cleaned[len("python\n"):]
    cleaned = re.sub(r"\n\s*```\s*$", "", cleaned)
    if "from gurobipy import" in cleaned or "import gurobipy" in cleaned:
        return cleaned.strip()
    return None


def extract_coe_python_code(model_output: str) -> str | None:
    """Mirror CoE's released ``extract_code_from_string`` byte semantics."""
    if not isinstance(model_output, str) or len(model_output.encode()) > MAX_OUTPUT_BYTES:
        return None
    blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", model_output, re.DOTALL)
    if not blocks:
        return model_output
    if len(blocks) == 1:
        return blocks[0]
    return "\n".join(block for block in blocks if "pip" not in block)


def translate_generated_gurobi(model_output: str, *, data_files: dict[str, Any] | None = None) -> dict:
    """Translate a model response into ``milp-v1`` or a public-safe rejection."""
    code = extract_python_code(model_output)
    output_hash = hashlib.sha256(model_output.encode()).hexdigest() if isinstance(model_output, str) else None
    if code is None:
        return {"status": "rejected", "reason": "no_python_code", "output_sha256": output_hash}
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    try:
        compiled = compile_gurobi_source(code, data_files=data_files)
    except RestrictedCodeError as exc:
        return {
            "status": "rejected",
            "reason": str(exc),
            "output_sha256": output_hash,
            "code_sha256": code_hash,
        }
    except (ArithmeticError, IndexError, KeyError, TypeError, ValueError) as exc:
        return {
            "status": "rejected",
            "reason": "restricted_runtime_error:" + type(exc).__name__,
            "output_sha256": output_hash,
            "code_sha256": code_hash,
        }
    return {
        "status": "compiled",
        "output_sha256": output_hash,
        "code_sha256": code_hash,
        "model_sha256": digest(compiled),
        "model": compiled,
    }


def solve_generated_gurobi(model_output: str, *, data_files: dict[str, Any] | None = None,
                           wall_seconds: int | float = 30, rss_mb: int = 512) -> dict:
    """Translate first, then solve only the validated sparse model in the trusted worker."""
    translated = translate_generated_gurobi(model_output, data_files=data_files)
    if translated["status"] != "compiled":
        return translated
    solved = execute({"op": "solve", "model": translated["model"]},
                     wall_seconds=wall_seconds, rss_mb=rss_mb)
    return {
        "status": "solved" if solved.get("status") == "optimal" else "solver_nonoptimal",
        "output_sha256": translated["output_sha256"],
        "code_sha256": translated["code_sha256"],
        "model_sha256": translated["model_sha256"],
        "solve": solved,
    }


def translate_coe_gurobi_function(model_output: str, *, function_name: str,
                                  arguments: dict[str, Any]) -> dict:
    """Translate a native CoE function at its optimizer boundary.

    The generated function is parsed but never imported or executed.  Runtime
    arguments are detached JSON values, and solution-value code after the first
    ``optimize`` call is unreachable to the interpreter.
    """
    code = extract_coe_python_code(model_output)
    output_hash = hashlib.sha256(model_output.encode()).hexdigest() if isinstance(model_output, str) else None
    if code is None:
        return {"status": "rejected", "reason": "no_python_code", "output_sha256": output_hash}
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    try:
        compiled = compile_gurobi_function_source(code, function_name, arguments)
    except RestrictedCodeError as exc:
        return {"status": "rejected", "reason": str(exc), "output_sha256": output_hash,
                "code_sha256": code_hash}
    except (ArithmeticError, IndexError, KeyError, TypeError, ValueError) as exc:
        return {"status": "rejected", "reason": "restricted_runtime_error:" + type(exc).__name__,
                "output_sha256": output_hash, "code_sha256": code_hash}
    return {"status": "compiled", "output_sha256": output_hash, "code_sha256": code_hash,
            "model_sha256": digest(compiled), "model": compiled}


def solve_coe_gurobi_function(model_output: str, *, function_name: str,
                              arguments: dict[str, Any], wall_seconds: int | float = 30,
                              rss_mb: int = 512) -> dict:
    translated = translate_coe_gurobi_function(
        model_output, function_name=function_name, arguments=arguments,
    )
    if translated["status"] != "compiled":
        return translated
    solved = execute({"op": "solve", "model": translated["model"]},
                     wall_seconds=wall_seconds, rss_mb=rss_mb)
    return {"status": "solved" if solved.get("status") == "optimal" else "solver_nonoptimal",
            "output_sha256": translated["output_sha256"], "code_sha256": translated["code_sha256"],
            "model_sha256": translated["model_sha256"], "solve": solved}


def evaluate_coe_program(model_output: str, *, function_name: str,
                         arguments: dict[str, Any], solver: Any) -> dict:
    """Safely reproduce the generated function's observable return value."""
    code = extract_coe_python_code(model_output)
    output_hash = hashlib.sha256(model_output.encode()).hexdigest() if isinstance(model_output, str) else None
    if code is None:
        return {"status": "rejected", "reason": "no_python_code", "output_sha256": output_hash}
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    trace: dict[str, Any] = {"model_sha256": None, "solver_status": None, "objective": None}

    def traced(operation: dict[str, Any]) -> dict[str, Any]:
        trace["model_sha256"] = digest(operation["model"])
        result = solver(operation)
        trace["solver_status"] = result.get("status")
        trace["objective"] = result.get("objective")
        return result

    try:
        value = evaluate_optimization_function_source(code, function_name, arguments, traced)
    except RestrictedCodeError as exc:
        return {"status": "rejected", "reason": str(exc), "output_sha256": output_hash,
                "code_sha256": code_hash, **trace}
    except (ArithmeticError, IndexError, KeyError, TypeError, ValueError) as exc:
        return {"status": "rejected", "reason": "restricted_runtime_error:" + type(exc).__name__,
                "output_sha256": output_hash, "code_sha256": code_hash, **trace}
    return {"status": "evaluated", "output_sha256": output_hash, "code_sha256": code_hash,
            "returned_value": value, **trace}


__all__ = [
    "evaluate_coe_program", "extract_coe_python_code", "extract_python_code",
    "solve_coe_gurobi_function", "solve_generated_gurobi",
    "translate_coe_gurobi_function", "translate_generated_gurobi",
]
