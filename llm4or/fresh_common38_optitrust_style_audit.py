"""Independent body-free audit for the OptiTrust-style common-38 row."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from .fresh_common38_optitrust_style import (
    PLAN_PATH, build_plan, ledger_summary, load_cells, publish_new, score_cells,
)
from .frozen_plan_history import verify_plan_reconstruction
from .schema import canonical, digest


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ledger_checks(
    directory: Path, plan: dict[str, Any], accounting: dict[str, Any],
    *, expected_offline: bool,
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
        per_scope = connection.execute(
            "SELECT scope,count(*),min(slot),max(slot) FROM slots "
            "GROUP BY scope ORDER BY scope"
        ).fetchall()
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
        "offline": expected_offline, "directory": str(directory.resolve()),
    })
    if not metadata or metadata[0] != expected_config:
        raise ValueError("ledger_configuration")
    if scopes != (38, 9, 9, plan["token_cap"], plan["token_cap"]):
        raise ValueError("ledger_scopes")
    if (
        slots[0] != accounting["logical_requests"]
        or slots[1] != 38 or slots[2] != 0 or not 0 <= slots[3] <= 8 or drift
    ):
        raise ValueError("ledger_slots")
    if len(per_scope) != 38 or any(
        count < 1 or count > 9 or minimum != 0 or maximum != count - 1
        for _scope, count, minimum, maximum in per_scope
    ):
        raise ValueError("ledger_scope_slot_contiguity")
    if set(attempts) - {"complete", "exhausted"}:
        raise ValueError("ledger_attempts")
    if sum(attempts.values()) != slots[0]:
        raise ValueError("ledger_fingerprint_count")
    for response, expected_hash in response_integrity:
        if digest(json.loads(response)) != expected_hash:
            raise ValueError("ledger_response_integrity")
    distribution = Counter(str(count) for _scope, count, _minimum, _maximum in per_scope)
    return {
        "registered_scopes": scopes[0], "logical_slots": slots[0],
        "distinct_scopes_with_slots": slots[1], "slot_min": slots[2],
        "slot_max": slots[3], "slot_content_drift": drift,
        "per_scope_slot_count_distribution": dict(sorted(distribution.items())),
        "all_scope_slots_contiguous": True,
        "attempt_status_counts": dict(sorted(attempts.items())),
        "complete_response_hashes_verified": len(response_integrity),
        "ledger_mode": "offline_simulation" if expected_offline else "authorized_live",
    }


def build_audit_from(
    root: str | Path, plan: dict[str, Any], plan_path: str | Path,
    directory: str | Path, result_path: str | Path, *, expected_offline: bool,
) -> dict[str, Any]:
    """Reconstruct one terminal run using only frozen files and private ledgers."""
    root = Path(root).resolve()
    plan_path = Path(plan_path)
    directory = Path(directory)
    result_path = Path(result_path)
    if canonical(json.loads(plan_path.read_text())) != canonical(plan):
        raise ValueError("plan_file_object_mismatch")
    reconstruction = verify_plan_reconstruction(root, plan, build_plan)
    cells = load_cells(plan, directory)
    accounting = ledger_summary(directory)
    recomputed = score_cells(plan, cells, accounting)
    published = json.loads(result_path.read_text())
    if canonical(recomputed) != canonical(published):
        raise ValueError("result_reconstruction")
    if accounting.get("halt") is not None:
        raise ValueError("terminal_halt")
    if any(value is not False for value in published["privacy"].values()):
        raise ValueError("public_privacy_flags")
    row_counts = Counter(row["disposition"] for row in published["rows"])
    aggregate = published["aggregate"]
    if aggregate["planned"] != len(published["rows"]):
        raise ValueError("aggregate_denominator")
    for key in (
        "correct", "incorrect", "method_failure", "infrastructure_unavailable",
    ):
        if aggregate[key] != row_counts[key]:
            raise ValueError("aggregate_row_consistency")
    ledger = _ledger_checks(
        directory, plan, accounting, expected_offline=expected_offline,
    )
    return {
        "schema": "fresh-common38-optitrust-style-independent-audit-v1",
        "status": "passed",
        "method": "OptiTrust-style-safe-sidecar",
        "plan_file_sha256": _sha(plan_path),
        "plan_object_sha256": digest(plan),
        "result_sha256": _sha(result_path),
        "ledger_sha256": _sha(directory / "requests.sqlite3"),
        "checks": {
            "plan_reconstructed": True,
            "plan_reconstruction_evidence": reconstruction,
            "private_terminal_cells": len(cells),
            "public_result_exactly_reconstructed": True,
            "aggregate": aggregate,
            "families": published["families"],
            "accounting": published["accounting"],
            "ledger": ledger,
        },
        "privacy": published["privacy"],
        "information_regime": published["information_regime"],
        "claim_boundary": published["claim_boundary"],
        "execution": {"new_api_calls": 0, "new_solver_calls": 0},
    }


def build_audit(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    plan_path = root / PLAN_PATH
    plan = json.loads(plan_path.read_text())
    return build_audit_from(
        root, plan, plan_path, root / plan["run_directory"],
        root / plan["output"]["public_result"], expected_offline=False,
    )


def publish_or_check(
    path: str | Path, audit: dict[str, Any], *, check: bool,
) -> None:
    path = Path(path)
    expected = (canonical(audit) + "\n").encode()
    if check:
        if not path.is_file() or path.read_bytes() != expected:
            raise ValueError("audit_byte_mismatch")
        return
    publish_new(path, audit)


__all__ = ["build_audit", "build_audit_from", "publish_or_check"]
