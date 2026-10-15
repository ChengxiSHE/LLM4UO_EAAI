"""Local dispatcher for the frozen mixed-skill composition experiment."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .mixed_skill_router import (
    OR_DEBUG_ROUTE,
    TSP_ROUTE,
    route_public_envelope,
)
from .or_debug_public_runner import execute_public_record
from .schema import digest
from .tsp_constraint_skill_scalable import run_tsp_constraint_scalable_cascade


def compact_tsp_output(candidate: dict[str, Any]) -> dict[str, Any]:
    """Apply the historical TSP confirmation compaction convention."""

    out = {key: value for key, value in candidate.items() if key != "semantic_evidence"}
    if "semantic_evidence" in candidate:
        out["semantic_evidence_sha256"] = digest(candidate["semantic_evidence"])
    return out


def execute_mixed_record(
    record: dict[str, Any],
    *,
    model_root: Path,
    workspace: Path,
    router: Callable[[dict[str, Any]], dict[str, Any]] = route_public_envelope,
    tsp_executor: Callable[[str, int], dict[str, Any]] = run_tsp_constraint_scalable_cascade,
    or_debug_executor: Callable[..., dict[str, Any]] = execute_public_record,
) -> dict[str, Any]:
    """Route and execute one public record, localizing all record failures."""

    if not isinstance(record, dict) or set(record) != {
        "record_id",
        "source",
        "public_envelope",
    }:
        return {
            "record_id": None,
            "source": None,
            "route": None,
            "status": "execution_failed",
            "reason": "invalid_outer_record",
        }
    record_id = record["record_id"]
    source = record["source"]
    envelope = record["public_envelope"]
    if not isinstance(record_id, str) or not record_id or not isinstance(envelope, dict):
        return {
            "record_id": record_id if isinstance(record_id, str) else None,
            "source": source,
            "route": None,
            "status": "execution_failed",
            "reason": "invalid_outer_record",
        }

    decision = router(envelope)
    route = decision.get("route")
    base = {"record_id": record_id, "source": source, "route": route}
    if route is None:
        return {
            **base,
            "status": "abstained",
            "reason": decision.get("reason", "no_unique_public_guard"),
        }
    try:
        if route == TSP_ROUTE:
            output = tsp_executor(envelope["public_text"], envelope["size"])
            output = compact_tsp_output(output)
        elif route == OR_DEBUG_ROUTE:
            output = or_debug_executor(
                {"problem_id": record_id, **envelope},
                model_root=Path(model_root),
                workspace=Path(workspace),
            )
        else:
            return {
                **base,
                "status": "execution_failed",
                "reason": "unknown_route",
            }
    except Exception as exc:
        return {
            **base,
            "status": "execution_failed",
            "reason": type(exc).__name__,
        }
    return {**base, "status": "complete", "output": output}


__all__ = ["compact_tsp_output", "execute_mixed_record"]
