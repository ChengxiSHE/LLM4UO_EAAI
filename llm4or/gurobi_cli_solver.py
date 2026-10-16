"""Trusted Gurobi CLI backend for validated ``milp-v1`` models.

Generated Python never reaches this module.  The controller serializes an
already validated sparse model to LP, invokes a fixed local optimizer command,
and independently checks any returned point before reporting an objective.
"""

import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any

from .milp_schema import model as validate_model
from .milp_solver import check_point


VERSION = "trusted-gurobi-cli-solver-v1"
DEFAULT_BINARY = "/usr/local/bin/gurobi_cl"


def _number(value: float | int) -> str:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("nonfinite_lp_value")
    return format(value, ".17g")


def _expression(coefficients: dict[str, float]) -> str:
    if not coefficients:
        return "0"
    terms = []
    for name, coefficient in sorted(coefficients.items()):
        if coefficient == 0:
            continue
        sign = "+" if coefficient > 0 else "-"
        terms.append(f" {sign} {_number(abs(coefficient))} {name}")
    return "".join(terms).lstrip() or "0"


def model_to_lp(value: dict[str, Any]) -> str:
    model = validate_model(value)
    lines = ["Minimize" if model["objective"]["sense"] == "min" else "Maximize"]
    lines.append(" obj: " + _expression(model["objective"]["coefficients"]))
    lines.append("Subject To")
    symbols = {"le": "<=", "ge": ">=", "eq": "="}
    for row in model["constraints"]:
        lines.append(
            f" {row['id']}: {_expression(row['coefficients'])} "
            f"{symbols[row['sense']]} {_number(row['rhs'])}"
        )
    lines.append("Bounds")
    integers, binaries = [], []
    for variable in model["variables"]:
        name = variable["id"]
        lower, upper = variable["lower"], variable["upper"]
        if variable["domain"] == "binary":
            intrinsic_lower, intrinsic_upper = 0.0, 1.0
            lower = intrinsic_lower if lower is None else max(float(lower), intrinsic_lower)
            upper = intrinsic_upper if upper is None else min(float(upper), intrinsic_upper)
            binaries.append(name)
        elif variable["domain"] == "integer":
            integers.append(name)
        if lower is None and upper is None:
            lines.append(f" {name} free")
        elif lower is None:
            lines.append(f" -infinity <= {name} <= {_number(upper)}")
        elif upper is None:
            lines.append(f" {_number(lower)} <= {name}")
        else:
            lines.append(f" {_number(lower)} <= {name} <= {_number(upper)}")
    if integers:
        lines.append("Generals")
        lines.extend(" " + name for name in integers)
    if binaries:
        lines.append("Binaries")
        lines.extend(" " + name for name in binaries)
    lines.append("End")
    return "\n".join(lines) + "\n"


def _float(text: str) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _solution(path: Path) -> tuple[float | None, dict[str, float] | None]:
    if not path.is_file():
        return None, None
    objective = None
    point = {}
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("# Objective value ="):
            objective = _float(line.split("=", 1)[1].strip())
        elif line and not line.startswith("#"):
            parts = line.split()
            if len(parts) == 2:
                value = _float(parts[1])
                if value is not None:
                    point[parts[0]] = value
    return objective, point or None


def _status(log: str) -> str:
    if "Optimal solution found" in log or "Optimal objective" in log:
        return "optimal"
    if "Model is infeasible" in log:
        return "infeasible"
    if "Unbounded model" in log or "Model is unbounded" in log:
        return "unbounded"
    if "Infeasible or unbounded model" in log:
        return "unknown"
    if "Time limit reached" in log:
        return "limit"
    return "unknown"


def _best(log: str) -> tuple[float | None, float | None]:
    matches = re.findall(
        r"Best objective\s+([^,\s]+),\s+best bound\s+([^,\s]+),", log,
        flags=re.IGNORECASE,
    )
    if not matches:
        return None, None
    return _float(matches[-1][0]), _float(matches[-1][1])


def execute(operation: dict[str, Any], *, binary: str = DEFAULT_BINARY,
            time_limit: float = 100.0, threads: int = 1,
            wall_seconds: float = 110.0) -> dict[str, Any]:
    if set(operation) != {"op", "model"} or operation["op"] != "solve":
        raise ValueError("gurobi_cli_operation")
    model = validate_model(operation["model"])
    if not Path(binary).is_file() or not 0 < time_limit <= 100 or not 1 <= threads <= 4:
        raise ValueError("gurobi_cli_configuration")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="llm4or-gurobi-") as directory:
        root = Path(directory)
        model_path, solution_path, log_path = root / "model.lp", root / "result.sol", root / "solve.log"
        model_path.write_text(model_to_lp(model))
        command = [
            binary, f"ResultFile={solution_path}", f"LogFile={log_path}",
            f"TimeLimit={_number(time_limit)}", f"Threads={threads}",
            "MIPGap=0", "MIPGapAbs=0", str(model_path),
        ]
        try:
            completed = subprocess.run(
                command, cwd=root, capture_output=True, text=True, timeout=wall_seconds,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "limit", "objective": None, "incumbent_objective": None,
                "objective_bound": None, "point": None, "reason": "gurobi_cli_wall_timeout",
                "wall_seconds": time.monotonic() - started, "backend": VERSION,
            }
        log = log_path.read_text(errors="replace") if log_path.exists() else completed.stdout
        status = _status(log)
        reported_objective, point = _solution(solution_path)
        expected_ids = {variable["id"] for variable in model["variables"]}
        if point is not None and set(point) != expected_ids:
            point = None
        point_check = check_point(model, point) if point is not None else None
        if point_check is not None and not point_check["feasible"]:
            status, point = "numerical_error", None
        objective = None
        incumbent = None
        if point is not None:
            incumbent = math.fsum(
                model["objective"]["coefficients"].get(name, 0.0) * value
                for name, value in point.items()
            ) + model["objective"]["offset"]
            if reported_objective is not None and not math.isclose(
                incumbent - model["objective"]["offset"], reported_objective,
                rel_tol=1e-7, abs_tol=1e-7,
            ):
                status, point, incumbent = "numerical_error", None, None
            elif status == "optimal":
                objective = incumbent
        best_objective, best_bound = _best(log)
        offset = model["objective"]["offset"]
        bound = best_bound + offset if best_bound is not None else None
        return {
            "status": status, "objective": objective, "incumbent_objective": incumbent,
            "objective_bound": bound, "point": point, "point_check": point_check,
            "reported_best_objective": best_objective + offset if best_objective is not None else None,
            "return_code": completed.returncode,
            "reason": None if status in {"optimal", "infeasible", "unbounded", "limit"}
                      else "gurobi_cli_status_unresolved",
            "wall_seconds": time.monotonic() - started, "backend": VERSION,
            "configured_limits": {"time_limit": time_limit, "threads": threads, "wall_seconds": wall_seconds},
            "certificate_scope": "gurobi_status_plus_independent_primal_recheck",
        }


__all__ = ["DEFAULT_BINARY", "VERSION", "execute", "model_to_lp"]
