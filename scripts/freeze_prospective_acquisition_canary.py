"""Freeze the approved eight-pair acquisition canary without dispatching it."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import time

from llm4or import antchat_object_pilot_contract as contract
from llm4or import prospective_acquisition_canary as canary
from llm4or.isolated_semantic_review import strict_json_loads
from llm4or.schema import canonical, digest


ROOT = Path(__file__).resolve().parents[1]
VERSION = "prospective-acquisition-canary-plan-v1"
APPROVAL = "experiments/prospective_research_program_decision_20261015.json"
REPAIR_INPUT = "results/dcp_typed_count_repair_input_20261014.json"
PREVIEW = "results/dcp_count_public_binding_preview_20261014.json"
PLAN = "experiments/prospective_acquisition_canary_plan.json"
BUNDLE = "results/private/prospective_acquisition_canary_payloads.json"
RUN = "results/private/prospective_acquisition_canary_20261015"
REPORT = "results/prospective_acquisition_canary_result.json"
AUDIT = "results/prospective_acquisition_canary_audit.json"

INPUT_FILES = (
    APPROVAL,
    REPAIR_INPUT,
    PREVIEW,
    "llm4or/__init__.py",
    "llm4or/antchat_object_pilot_contract.py",
    "llm4or/antchat_object_pilot_transport_v2.py",
    "llm4or/finite_count_model.py",
    "llm4or/isolated_semantic_review.py",
    "llm4or/prospective_acquisition_canary.py",
    "llm4or/schema.py",
    "llm4or/typed_count_cegis_revision.py",
    "llm4or/typed_count_skill.py",
    "scripts/freeze_prospective_acquisition_canary.py",
    "scripts/run_prospective_acquisition_canary.py",
    "scripts/audit_prospective_acquisition_canary.py",
    "docs/PROSPECTIVE_RESEARCH_PROGRAM_DECISION_20261015.md",
    "docs/superpowers/plans/2026-10-15-prospective-acquisition-canary.md",
)


class ProspectiveAcquisitionFreezeError(ValueError):
    """Fail-closed freeze error."""


def require(ok, code):
    if not ok:
        raise ProspectiveAcquisitionFreezeError(code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read_bytes(root, relative, maximum=16 * 1024 * 1024):
    root = Path(root).resolve()
    require(type(relative) is str and relative and not relative.startswith("/") and
            ".." not in Path(relative).parts, "relative_path")
    path = root / relative
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= maximum,
                "regular_file_" + relative.replace("/", "_"))
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(fd, min(1_048_576, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        require(len(raw) == info.st_size and len(raw) <= maximum,
                "stable_file_" + relative.replace("/", "_"))
        return raw
    finally:
        os.close(fd)


def _read_json(root, relative):
    raw = _read_bytes(root, relative)
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ProspectiveAcquisitionFreezeError("json_" + relative.replace("/", "_")) from exc
    require(type(value) is dict, "json_object_" + relative.replace("/", "_"))
    return value


def _file_sha(root, relative):
    return _sha(_read_bytes(root, relative))


def _write_new(root, relative, raw):
    root = Path(root).resolve()
    path = root / relative
    require(type(raw) is bytes and path.parent.is_dir() and
            not path.exists() and not path.is_symlink(),
            "output_precondition_" + relative.replace("/", "_"))
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL |
             getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            require(written > 0, "output_write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def cell_id(unit_id, arm, round_number):
    require(type(unit_id) is str and unit_id and arm in canary.ARMS and
            type(round_number) is int and 1 <= round_number <= canary.MAX_ROUNDS,
            "cell_identity")
    return f"{unit_id}__{arm}__r{round_number}"


def _approved(root):
    value = _read_json(root, APPROVAL)
    gate = value.get("implementation_gate")
    require(value.get("schema") == "llm4or-prospective-research-program-decision-v1" and
            value.get("status") == "approved_for_staged_implementation" and
            type(gate) is dict and gate.get("design_review_required") is False and
            gate.get("approved_program") == "A_staged_multi_unit_program" and
            gate.get("approval_statement") ==
            "批准方案A作为G07–G09前瞻实验的整体架构。",
            "program_approval")
    return value


def _inputs(root):
    _approved(root)
    source = _read_json(root, REPAIR_INPUT)
    preview = _read_json(root, PREVIEW)
    require(source.get("schema") == "typed-count-repair-input-v1" and
            type(source.get("candidate")) is dict,
            "repair_input")
    rows = preview.get("rows")
    require(type(rows) is list, "preview_rows")
    cases = sorted(
        [row["instance"] for row in rows
         if row.get("contract_kind_for_analysis_only") == "partial_fixed_tail"],
        key=lambda row: (row["n"], row["m"]),
    )
    require(bool(cases), "public_cases")
    return source["candidate"], cases


def build_bundle(root=ROOT):
    """Build the private payload bundle deterministically and without I/O side effects."""

    model_proposal, public_cases = _inputs(root)
    units = canary.select_units(model_proposal, public_cases)
    facts = canary.build_fact_ledger()
    trace = canary.build_teacher_trace(facts)
    cells = {}
    for unit in units:
        for arm in canary.ARMS:
            for round_number in range(1, canary.MAX_ROUNDS + 1):
                identity = cell_id(unit["unit_id"], arm, round_number)
                payload = canary.build_payload(
                    unit, arm, round_number, facts, trace
                )
                cells[identity] = {
                    "schema": canary.VERSION + "-cell",
                    "cell_id": identity,
                    "unit_id": unit["unit_id"],
                    "arm": arm,
                    "round": round_number,
                    "payload": payload,
                    "payload_sha256": digest(payload),
                }
    require(len(cells) == 48, "cell_count")
    return {
        "schema": canary.VERSION + "-private-bundle",
        "approved_program": "A_staged_multi_unit_program",
        "units": units,
        "facts": facts,
        "teacher_trace": trace,
        "cells": dict(sorted(cells.items())),
        "claim_boundary": {
            "private_payload_material": True,
            "engineering_canary_only": True,
            "confirmatory_effect_claimed": False,
            "benchmark_accuracy_claimed": False,
        },
    }


def build_plan(root, bundle, created_at):
    """Build the public, body-free executable plan from the exact private bundle."""

    root = Path(root).resolve()
    require(type(created_at) in (int, float) and 0 < created_at < 1e11,
            "created_at")
    expected = build_bundle(root)
    require(type(bundle) is dict and canonical(bundle) == canonical(expected),
            "bundle_identity")
    sources = {relative: _file_sha(root, relative) for relative in INPUT_FILES}
    rows = []
    total_reserved = 0
    request_keys = set()
    for identity, cell in sorted(bundle["cells"].items()):
        request = contract.identity(cell["payload"])
        require(request["request_key"] not in request_keys, "duplicate_request_key")
        request_keys.add(request["request_key"])
        total_reserved += request["reserved_tokens"]
        unit = next(row for row in bundle["units"]
                    if row["unit_id"] == cell["unit_id"])
        rows.append({
            "cell_id": identity,
            "unit_id": cell["unit_id"],
            "source_provenance": unit["provenance"],
            "source_candidate_sha256": unit["source_candidate_sha256"],
            "arm": cell["arm"],
            "round": cell["round"],
            "payload_sha256": cell["payload_sha256"],
            "request_key": request["request_key"],
            "request_body_sha256": request["request_body_sha256"],
            "request_bytes": request["request_bytes"],
            "reserved_tokens": request["reserved_tokens"],
        })
    require(len(rows) == 48 and len(request_keys) == 48, "request_inventory")
    return {
        "schema": VERSION,
        "status": "frozen_ready_for_bounded_dispatch",
        "approved_program": "A_staged_multi_unit_program",
        "approved_at_local_date": "2026-10-15",
        "model": contract.MODEL,
        "base_url": contract.BASE_URL,
        "created_at_unix": created_at,
        "expires_at_unix": created_at + 48 * 60 * 60,
        "private_bundle_path": BUNDLE,
        "private_bundle_sha256": digest(bundle),
        "run_directory": RUN,
        "public_report": REPORT,
        "public_audit": AUDIT,
        "source_sha256": sources,
        "fact_ledger_sha256": digest(bundle["facts"]),
        "teacher_trace_sha256": digest(bundle["teacher_trace"]),
        "limits": {
            "units": 8,
            "arms": 2,
            "maximum_rounds": canary.MAX_ROUNDS,
            "facts_per_round": canary.FACTS_PER_ROUND,
            "max_logical_requests": 48,
            "max_physical_attempts": 48,
            "max_attempts_per_request": 1,
            "max_concurrent_requests": 5,
            "request_seconds": 600,
            "max_completion_tokens": contract.MAX_COMPLETION_TOKENS,
            "max_total_reserved_or_reported_tokens": total_reserved,
        },
        "cells": rows,
        "missingness": {
            "invalid_or_unavailable_is_failure": True,
            "orphan_reservation_is_unavailable_and_never_resent": True,
            "skipped_after_success_is_success": True,
        },
        "progression_gate": {
            "minimum_treatment_only_wins": 2,
            "maximum_flat_only_wins": 0,
            "global_safety_failure_allowed": False,
            "significance_claimed": False,
        },
        "claim_boundary": {
            "engineering_canary_only": True,
            "independent_confirmation": False,
            "benchmark_accuracy_claimed": False,
            "library_promotion_authorized": False,
            "stage_2_authorized_by_canary_plan": False,
            "solver_native_vm_authorized": False,
        },
        "execution": {
            "model_calls_at_freeze": 0,
            "solver_calls_at_freeze": 0,
            "native_or_vm_calls_at_freeze": 0,
            "reference_answers_read": 0,
        },
    }


def freeze(root=ROOT, created_at=None):
    """Exclusively persist the private bundle and public plan."""

    root = Path(root).resolve()
    created_at = time.time() if created_at is None else created_at
    bundle = build_bundle(root)
    plan = build_plan(root, bundle, created_at)
    _write_new(root, BUNDLE, canonical(bundle).encode("utf-8"))
    _write_new(root, PLAN, canonical(plan).encode("utf-8"))
    return {
        "state": "frozen",
        "plan_sha256": digest(plan),
        "private_bundle_sha256": digest(bundle),
        "units": len(bundle["units"]),
        "cells": len(bundle["cells"]),
        "logical_request_ceiling": plan["limits"]["max_logical_requests"],
        "physical_attempt_ceiling": plan["limits"]["max_physical_attempts"],
        "model_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(freeze(ROOT), sort_keys=True))


if __name__ == "__main__":
    main()

