"""Answer-free execution boundary for frozen OR-Debug typed skills."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .or_debug_evolved_skill import (
    enumerate_typed_repair_candidates,
    select_unique_executable_candidate,
)
from .or_debug_gurobi import compute_iis, solve_mps_text
from .or_debug_mps import MpsRepairError, apply_repair


PUBLIC_FIELDS = {"problem_id", "problem_nl", "model_file", "mps_sha256"}


def _repair_sha(repair: dict[str, Any]) -> str:
    encoded = json.dumps(repair, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def execute_public_record(
    row: dict[str, Any],
    *,
    model_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    """Execute one public record without importing any answer-bearing module."""

    if not isinstance(row, dict) or set(row) != PUBLIC_FIELDS:
        raise ValueError("public record fields")
    problem_id = row["problem_id"]
    if not isinstance(problem_id, str) or not problem_id:
        raise ValueError("public problem id")
    root = Path(model_root).resolve()
    model_path = (root / row["model_file"]).resolve()
    if not model_path.is_relative_to(root) or not model_path.is_file():
        raise ValueError("public model path")
    mps_bytes = model_path.read_bytes()
    if hashlib.sha256(mps_bytes).hexdigest() != row["mps_sha256"]:
        raise ValueError("public MPS hash mismatch")
    mps_text = mps_bytes.decode("utf-8")
    work = Path(workspace)
    work.mkdir(parents=True, exist_ok=True)
    iis_result = compute_iis(model_path, workspace=work / "iis")
    if iis_result["status"] != "infeasible_iis":
        return {
            "problem_id": problem_id,
            "status": "infrastructure_unavailable",
            "reason": iis_result["status"],
            "solver_calls": 1,
        }
    candidates = enumerate_typed_repair_candidates(
        problem_nl=row["problem_nl"], mps_text=mps_text, iis=iis_result["iis"]
    )
    if not candidates:
        return {
            "problem_id": problem_id,
            "status": "abstained",
            "reason": "typed_candidate_set_empty",
            "candidate_count": 0,
            "solver_calls": 1,
            "iis_sha256": iis_result["iis_sha256"],
        }

    statuses: list[str] = []
    executions: list[tuple[dict[str, Any] | None, dict[str, Any] | None]] = []
    solver_calls = 1
    for index, candidate in enumerate(candidates):
        try:
            patched = apply_repair(mps_text, candidate["repair"])
        except MpsRepairError:
            statuses.append("patch_rejected")
            executions.append((None, None))
            continue
        solve = solve_mps_text(patched["mps"], workspace=work / f"candidate_{index}")
        solver_calls += 1
        statuses.append(solve["status"])
        executions.append((patched, solve))
    selected = select_unique_executable_candidate(candidates, statuses)
    status_counts = dict(sorted(Counter(statuses).items()))
    if selected["status"] != "proposed":
        return {
            "problem_id": problem_id,
            "status": "abstained",
            "reason": selected["reason"],
            "candidate_count": len(candidates),
            "candidate_status_counts": status_counts,
            "solver_calls": solver_calls,
            "iis_sha256": iis_result["iis_sha256"],
        }
    selected_index = next(index for index, candidate in enumerate(candidates) if candidate is selected)
    patched, solve = executions[selected_index]
    if patched is None or solve is None or solve["status"] != "optimal":
        raise RuntimeError("selected public candidate execution mismatch")
    repair = selected["repair"]
    collateral = (
        patched["audit"]["operation_count"] == len(repair["operations"])
        and len(patched["audit"]["changes"]) == len(repair["operations"])
    )
    return {
        "problem_id": problem_id,
        "status": "complete",
        "repair": repair,
        "repair_sha256": _repair_sha(repair),
        "candidate_count": len(candidates),
        "candidate_status_counts": status_counts,
        "iis_sha256": iis_result["iis_sha256"],
        "post_mps_sha256": patched["audit"]["post_sha256"],
        "operation_count": len(repair["operations"]),
        "collateral_change_pass": collateral,
        "solve_status": solve["status"],
        "solve_objective": solve["objective"],
        "solver_calls": solver_calls,
    }


__all__ = ["execute_public_record"]
