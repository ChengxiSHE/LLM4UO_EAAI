"""Independent, body-free audit of the fresh common-38 one-call Base run."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from .fresh_common38_base import (
    PLAN_PATH, build_plan, ledger_summary, load_cells, load_references,
    publish_new, score_cells,
)
from .schema import canonical, digest


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ledger_checks(
    directory: Path, plan: dict[str, Any], accounting: dict[str, Any]
) -> dict[str, Any]:
    connection = sqlite3.connect(
        f"file:{directory / 'requests.sqlite3'}?mode=ro", uri=True,
    )
    try:
        metadata = connection.execute("SELECT config FROM metadata WHERE id=1").fetchone()
        scopes = connection.execute(
            "SELECT count(*),min(calls),max(calls),min(tokens),max(tokens) FROM scopes"
        ).fetchone()
        slots = connection.execute(
            "SELECT count(*),count(DISTINCT scope),min(slot),max(slot) FROM slots"
        ).fetchone()
        drift = connection.execute(
            "SELECT count(*) FROM (SELECT scope,slot,count(DISTINCT key) n FROM slots "
            "GROUP BY scope,slot HAVING n<>1)"
        ).fetchone()[0]
        attempts = dict(connection.execute(
            "SELECT status,count(*) FROM attempts GROUP BY status"
        ).fetchall())
        response_integrity = connection.execute(
            "SELECT response,response_hash FROM attempts WHERE status='complete'"
        ).fetchall()
    finally:
        connection.close()
    expected_config = canonical({
        "version": plan["gateway_version"], "plan": digest(plan),
        "offline": False, "directory": str(directory.resolve()),
    })
    if not metadata or metadata[0] != expected_config:
        raise ValueError("ledger_configuration")
    if scopes != (38, 1, 1, plan["token_cap"], plan["token_cap"]):
        raise ValueError("ledger_scopes")
    if slots != (38, 38, 0, 0) or drift:
        raise ValueError("ledger_slots")
    if set(attempts) - {"complete", "exhausted"} or sum(attempts.values()) != 38:
        raise ValueError("ledger_attempts")
    if accounting["logical_requests"] != 38:
        raise ValueError("ledger_logical_accounting")
    for response, expected_hash in response_integrity:
        if digest(json.loads(response)) != expected_hash:
            raise ValueError("ledger_response_integrity")
    return {
        "registered_scopes": scopes[0], "logical_slots": slots[0],
        "distinct_scopes_with_slots": slots[1], "slot_min": slots[2],
        "slot_max": slots[3], "slot_content_drift": drift,
        "attempt_status_counts": attempts,
        "complete_response_hashes_verified": len(response_integrity),
    }


def _with_explicit_zeros(value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "correct": value.get("correct", 0)}


def build_audit(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve(); plan_path = root / PLAN_PATH
    plan = json.loads(plan_path.read_text())
    if canonical(plan) != canonical(build_plan(root)):
        raise ValueError("plan_reconstruction")
    directory = root / plan["run_directory"]
    cells = load_cells(plan, directory); accounting = ledger_summary(directory)
    recomputed = score_cells(plan, cells, load_references(root, plan), accounting)
    result_path = root / plan["output"]["public_result"]
    published = json.loads(result_path.read_text())
    if canonical(recomputed) != canonical(published):
        raise ValueError("result_reconstruction")
    if accounting.get("halt") is not None:
        raise ValueError("terminal_halt")
    if any(value is not False for value in published["privacy"].values()):
        raise ValueError("public_privacy_flags")
    row_counts = Counter("correct" if row["correct"] else row["disposition"] for row in published["rows"])
    aggregate = _with_explicit_zeros(published["aggregate"])
    if aggregate["correct"] != row_counts["correct"] or aggregate["planned"] != len(published["rows"]):
        raise ValueError("aggregate_row_consistency")
    return {
        "schema": "fresh-common38-base-independent-audit-v1", "status": "passed",
        "plan_file_sha256": _sha(plan_path), "plan_object_sha256": digest(plan),
        "result_sha256": _sha(result_path),
        "ledger_sha256": _sha(directory / "requests.sqlite3"),
        "checks": {
            "plan_reconstructed": True, "private_terminal_cells": len(cells),
            "public_result_exactly_reconstructed": True, "aggregate": aggregate,
            "families": {name: _with_explicit_zeros(value) for name, value in published["families"].items()},
            "accounting": published["accounting"],
            "ledger": _ledger_checks(directory, plan, accounting),
        },
        "privacy": published["privacy"],
        "information_regime": published["information_regime"],
        "claim_boundary": published["claim_boundary"],
        "execution": {"new_api_calls": 0, "new_solver_calls": 0},
    }


def publish(path: str | Path, audit: dict[str, Any]) -> None:
    publish_new(path, audit)


__all__ = ["build_audit", "publish"]
