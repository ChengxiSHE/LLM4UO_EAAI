"""Independent, body-free audit of the fresh common-38 CoE-safe run."""

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from .fresh_common38_coe import (
    PLAN_PATH, build_plan, ledger_summary, load_cells, publish_new, score_cells,
)
from .frozen_plan_history import verify_plan_reconstruction
from .schema import canonical, digest


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ledger_checks(
    directory: Path, plan: dict[str, Any], accounting: dict[str, Any]
) -> dict[str, Any]:
    path = directory / "requests.sqlite3"
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = connection.execute("SELECT config FROM metadata WHERE id=1").fetchone()
        scopes = connection.execute(
            "SELECT count(*),min(calls),max(calls),min(tokens),max(tokens) FROM scopes"
        ).fetchone()
        slots = connection.execute(
            "SELECT count(*),count(DISTINCT scope),min(slot),max(slot) FROM slots"
        ).fetchone()
        per_scope_slots = connection.execute(
            "SELECT scope,count(*),min(slot),max(slot) FROM slots "
            "GROUP BY scope ORDER BY scope"
        ).fetchall()
        drift = connection.execute(
            "SELECT count(*) FROM (SELECT scope,slot,count(DISTINCT key) n FROM slots "
            "GROUP BY scope,slot HAVING n<>1)"
        ).fetchone()[0]
        attempts = connection.execute(
            "SELECT status,count(*) FROM attempts GROUP BY status"
        ).fetchall()
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
    if scopes != (38, 11, 11, plan["token_cap"], plan["token_cap"]):
        raise ValueError("ledger_scopes")
    logical_requests = accounting["logical_requests"]
    if slots != (logical_requests, 38, 0, 10) or drift:
        raise ValueError("ledger_slots")
    if len(per_scope_slots) != 38 or any(
        count < 1 or count > 11 or minimum != 0 or maximum != count - 1
        for _scope, count, minimum, maximum in per_scope_slots
    ):
        raise ValueError("ledger_scope_slot_contiguity")
    if dict(attempts) != {"complete": logical_requests}:
        raise ValueError("ledger_attempts")
    for response, expected_hash in response_integrity:
        if digest(json.loads(response)) != expected_hash:
            raise ValueError("ledger_response_integrity")
    distribution: dict[str, int] = {}
    for _scope, count, _minimum, _maximum in per_scope_slots:
        key = str(count)
        distribution[key] = distribution.get(key, 0) + 1
    return {
        "registered_scopes": scopes[0], "logical_slots": slots[0],
        "distinct_scopes_with_slots": slots[1], "slot_min": slots[2],
        "slot_max": slots[3], "slot_content_drift": drift,
        "per_scope_slot_count_distribution": distribution,
        "all_scope_slots_contiguous": True,
        "complete_attempt_rows": dict(attempts)["complete"],
        "complete_response_hashes_verified": len(response_integrity),
    }


def build_audit(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    plan_path = root / PLAN_PATH
    plan = json.loads(plan_path.read_text())
    reconstruction = verify_plan_reconstruction(root, plan, build_plan)
    directory = root / plan["run_directory"]
    cells = load_cells(plan, directory)
    accounting = ledger_summary(directory)
    recomputed = score_cells(plan, cells, accounting)
    result_path = root / plan["output"]["public_result"]
    published = json.loads(result_path.read_text())
    if canonical(recomputed) != canonical(published):
        raise ValueError("result_reconstruction")
    if accounting.get("halt") is not None:
        raise ValueError("terminal_halt")
    if any(value is not False for value in published["privacy"].values()):
        raise ValueError("public_privacy_flags")
    ledger = _ledger_checks(directory, plan, accounting)
    return {
        "schema": "fresh-common38-coe-current-independent-audit-v1",
        "status": "passed",
        "plan_file_sha256": _sha(plan_path),
        "plan_object_sha256": digest(plan),
        "result_sha256": _sha(result_path),
        "ledger_sha256": _sha(directory / "requests.sqlite3"),
        "checks": {
            "plan_reconstructed": True,
            "plan_reconstruction_evidence": reconstruction,
            "private_terminal_cells": len(cells),
            "public_result_exactly_reconstructed": True,
            "aggregate": published["aggregate"],
            "tolerance_secondary": published["tolerance_secondary"],
            "families": published["families"],
            "accounting": published["accounting"],
            "ledger": ledger,
        },
        "privacy": published["privacy"],
        "information_regime": published["information_regime"],
        "claim_boundary": published["claim_boundary"],
        "execution": {"new_api_calls": 0, "new_solver_calls": 0},
    }


def publish(path: str | Path, audit: dict[str, Any]) -> None:
    publish_new(path, audit)


__all__ = ["build_audit", "publish"]
