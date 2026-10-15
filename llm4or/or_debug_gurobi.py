"""Fixed Gurobi CLI boundary for OR-Debug MPS validation and fresh IIS data."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re
import subprocess
import time
from typing import Any

from .or_debug_iis_control import parse_gurobi_iis_lp


DEFAULT_BINARY = "/usr/local/bin/gurobi_cl"
SOLVER_TIMEOUT_SECONDS = 15
WALL_TIMEOUT_SECONDS = 25
MAX_MPS_BYTES = 1_000_000


def _number(value: str) -> str:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid solver objective") from exc
    if not number.is_finite():
        raise ValueError("invalid solver objective")
    normalized = format(number.normalize(), "f")
    return "0" if number == 0 else normalized


def _run(command: list[str], *, timeout: int) -> tuple[int | None, str, float, bool]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, time.monotonic() - started, False
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        return None, output, time.monotonic() - started, True


def _workspace(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=False)
    return path


def compute_iis(
    model_path: Path,
    *,
    workspace: Path,
    binary: str = DEFAULT_BINARY,
) -> dict[str, Any]:
    """Compute one fresh solver IIS without using benchmark-saved IIS labels."""

    model_path = model_path.resolve()
    if not model_path.is_file() or model_path.stat().st_size > MAX_MPS_BYTES:
        raise ValueError("invalid MPS input")
    root = _workspace(Path(workspace))
    iis_path = root / "iis.ilp"
    log_path = root / "gurobi.log"
    command = [
        binary,
        "Threads=1",
        f"TimeLimit={SOLVER_TIMEOUT_SECONDS}",
        "DualReductions=0",
        "InfUnbdInfo=1",
        "MIPGap=0",
        "MIPGapAbs=0",
        "LogToConsole=0",
        f"LogFile={log_path}",
        f"ResultFile={iis_path}",
        str(model_path),
    ]
    returncode, output, elapsed, timed_out = _run(command, timeout=WALL_TIMEOUT_SECONDS)
    log = (log_path.read_text() if log_path.is_file() else "") + output
    if timed_out:
        return {"status": "timeout", "returncode": None, "elapsed_seconds": elapsed}
    if returncode != 0:
        return {"status": "solver_error", "returncode": returncode, "elapsed_seconds": elapsed}
    if not iis_path.is_file():
        status = "not_infeasible" if "Optimal" in log or "unbounded" in log.lower() else "iis_missing"
        return {"status": status, "returncode": returncode, "elapsed_seconds": elapsed}
    iis_text = iis_path.read_text()
    return {
        "status": "infeasible_iis",
        "returncode": returncode,
        "elapsed_seconds": elapsed,
        "iis_sha256": hashlib.sha256(iis_text.encode("utf-8")).hexdigest(),
        "iis": parse_gurobi_iis_lp(iis_text),
    }


def _solver_status(log: str) -> str:
    lower = log.lower()
    if "optimal solution found" in lower or "optimal objective" in lower:
        return "optimal"
    if "model is infeasible" in lower:
        return "infeasible"
    if "model is unbounded" in lower:
        return "unbounded"
    if "time limit reached" in lower:
        return "time_limit"
    return "unknown"


def _solution_objective(solution_path: Path, log: str) -> str | None:
    if solution_path.is_file():
        match = re.search(
            r"^#\s*Objective value\s*=\s*([^\s]+)\s*$",
            solution_path.read_text(),
            flags=re.MULTILINE,
        )
        if match:
            return _number(match.group(1))
    match = re.search(r"Optimal objective\s+([^\s]+)", log)
    return _number(match.group(1)) if match else None


def solve_mps_text(
    mps_text: str,
    *,
    workspace: Path,
    binary: str = DEFAULT_BINARY,
) -> dict[str, Any]:
    """Solve one bounded MPS string and return status/objective without raw logs."""

    if not isinstance(mps_text, str) or not mps_text:
        raise ValueError("MPS text must be nonempty")
    encoded = mps_text.encode("utf-8")
    if len(encoded) > MAX_MPS_BYTES:
        raise ValueError("MPS byte limit")
    root = _workspace(Path(workspace))
    model_path = root / "model.mps"
    solution_path = root / "solution.sol"
    log_path = root / "gurobi.log"
    model_path.write_bytes(encoded)
    command = [
        binary,
        "Threads=1",
        f"TimeLimit={SOLVER_TIMEOUT_SECONDS}",
        "DualReductions=0",
        "InfUnbdInfo=1",
        "MIPGap=0",
        "MIPGapAbs=0",
        "LogToConsole=0",
        f"LogFile={log_path}",
        f"ResultFile={solution_path}",
        str(model_path),
    ]
    returncode, output, elapsed, timed_out = _run(command, timeout=WALL_TIMEOUT_SECONDS)
    log = (log_path.read_text() if log_path.is_file() else "") + output
    if timed_out:
        return {"status": "timeout", "objective": None, "returncode": None, "elapsed_seconds": elapsed}
    if returncode != 0:
        return {"status": "solver_error", "objective": None, "returncode": returncode, "elapsed_seconds": elapsed}
    status = _solver_status(log)
    objective = _solution_objective(solution_path, log) if status == "optimal" else None
    if status == "optimal" and objective is None:
        status = "objective_missing"
    return {
        "status": status,
        "objective": objective,
        "returncode": returncode,
        "elapsed_seconds": elapsed,
        "model_sha256": hashlib.sha256(encoded).hexdigest(),
    }


__all__ = ["compute_iis", "solve_mps_text"]
