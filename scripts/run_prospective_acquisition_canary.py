#!/usr/bin/env python3
"""Run the frozen prospective acquisition canary once per request key.

The runner is deliberately conservative.  A durable reservation precedes each
physical send, and a reservation without a terminal record is never replayed.
Request and response material remains under the private run directory.  The
public result contains identities, terminal classes, and accounting only.
"""

import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import stat
import threading
import time

from llm4or import antchat_object_pilot_contract as contract
from llm4or import antchat_object_pilot_transport_v2 as transport
from llm4or.isolated_semantic_review import strict_json_loads
from llm4or.schema import canonical, digest, loads
from llm4or.typed_count_skill import validate_candidate, verify_candidate
from scripts import freeze_prospective_acquisition_canary as freezer


ROOT = Path(__file__).resolve().parents[1]
VERSION = "prospective-acquisition-canary-run-v1"
TERMINAL = frozenset({
    "accepted_candidate",
    "invalid_candidate",
    "infrastructure_unavailable",
    "global_safety_failure",
    "global_halt_not_dispatched",
    "skipped_after_success",
})


class ProspectiveAcquisitionRunError(ValueError):
    """Fail-closed execution error."""


def require(ok, code):
    if not ok:
        raise ProspectiveAcquisitionRunError(code)


def sha(raw):
    require(type(raw) is bytes, "sha_bytes")
    return hashlib.sha256(raw).hexdigest()


def _safe_path(root, relative):
    root = Path(root).resolve()
    require(type(relative) is str and relative and not relative.startswith("/") and
            ".." not in Path(relative).parts, "relative_path")
    path = (root / relative).resolve()
    require(path != root and root in path.parents, "path_containment")
    return path


def _read_bytes(path, maximum=16 * 1024 * 1024):
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= maximum, "regular_file")
        chunks = []
        remaining = maximum + 1
        while remaining:
            block = os.read(fd, min(1_048_576, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        raw = b"".join(chunks)
        require(len(raw) == info.st_size and len(raw) <= maximum, "stable_file")
        return raw
    finally:
        os.close(fd)


def read_json(path):
    raw = _read_bytes(path)
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ProspectiveAcquisitionRunError("json") from exc
    require(type(value) is dict, "json_object")
    return value


def write_new_json(path, value):
    """Publish one canonical JSON object with exclusive terminal ownership."""

    path = Path(path)
    require(type(value) is dict and path.parent.is_dir() and
            not path.exists() and not path.is_symlink(), "write_precondition")
    raw = canonical(value).encode("utf-8")
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL |
             getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            require(count > 0, "write_progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def reservation_for(plan, cell):
    require(type(plan) is dict and type(cell) is dict, "reservation_input")
    return {
        "schema": VERSION + "-reservation",
        "plan_sha256": digest(plan),
        "cell_id": cell["cell_id"],
        "request_key": cell["request_key"],
        "request_body_sha256": cell["request_body_sha256"],
        "payload_sha256": cell["payload_sha256"],
        "reserved_tokens": cell["reserved_tokens"],
        "attempt_ordinal": 1,
        "maximum_attempts": 1,
    }


def _load_frozen(root):
    root = Path(root).resolve()
    plan_path = _safe_path(root, freezer.PLAN)
    bundle_path = _safe_path(root, freezer.BUNDLE)
    plan = read_json(plan_path)
    bundle = read_json(bundle_path)
    require(plan.get("schema") == freezer.VERSION and
            bundle.get("schema") == "prospective-acquisition-canary-v1-private-bundle",
            "frozen_schema")
    require(digest(bundle) == plan.get("private_bundle_sha256"), "bundle_digest")
    expected = freezer.build_plan(root, bundle, plan.get("created_at_unix"))
    require(canonical(plan) == canonical(expected), "plan_binding")
    require(plan.get("model") == contract.MODEL and
            plan.get("base_url") == contract.BASE_URL and
            plan.get("limits", {}).get("max_concurrent_requests") == 5 and
            plan["limits"].get("max_attempts_per_request") == 1 and
            plan["limits"].get("max_physical_attempts") == 48,
            "execution_limits")
    require(time.time() <= plan["expires_at_unix"], "plan_expired")
    cells = plan.get("cells")
    require(type(cells) is list and len(cells) == 48 and
            len({row["cell_id"] for row in cells}) == 48 and
            len({row["request_key"] for row in cells}) == 48,
            "cell_inventory")
    bundle_cells = bundle.get("cells")
    require(type(bundle_cells) is dict and set(bundle_cells) ==
            {row["cell_id"] for row in cells}, "bundle_cells")
    return root, plan, bundle


def _directories(root, plan):
    run = _safe_path(root, plan["run_directory"])
    run.mkdir(parents=True, exist_ok=True)
    require(run.is_dir() and not run.is_symlink(), "run_directory")
    result = {"run": run}
    for name in ("reservations", "envelopes", "candidates", "cells", "rounds"):
        path = run / name
        path.mkdir(exist_ok=True)
        require(path.is_dir() and not path.is_symlink(), "run_subdirectory")
        result[name] = path
    return result


def _cell_path(directories, kind, cell_id):
    require(type(cell_id) is str and cell_id and "/" not in cell_id and
            ".." not in cell_id, "cell_id")
    return directories[kind] / (cell_id + ".json")


def _terminal(plan, cell, status, reason, *, usage=None,
              physical_send_completed=False, response_sha256=None):
    require(status in TERMINAL and (reason is None or type(reason) is str),
            "terminal_status")
    require(usage is None or (type(usage) is dict and set(usage) ==
            {"prompt_tokens", "completion_tokens", "total_tokens"}), "terminal_usage")
    value = {
        "schema": VERSION + "-terminal",
        "plan_sha256": digest(plan),
        "cell_id": cell["cell_id"],
        "unit_id": cell["unit_id"],
        "arm": cell["arm"],
        "round": cell["round"],
        "request_key": cell["request_key"],
        "status": status,
        "reason": reason,
        "usage": usage,
        "physical_send_completed": physical_send_completed,
        "response_sha256": response_sha256,
    }
    return value


def _bound_terminal(plan, cell, value):
    require(type(value) is dict and value.get("schema") == VERSION + "-terminal" and
            value.get("plan_sha256") == digest(plan) and
            value.get("cell_id") == cell["cell_id"] and
            value.get("unit_id") == cell["unit_id"] and
            value.get("arm") == cell["arm"] and value.get("round") == cell["round"] and
            value.get("request_key") == cell["request_key"] and
            value.get("status") in TERMINAL and
            type(value.get("physical_send_completed")) is bool,
            "terminal_binding")
    usage = value.get("usage")
    require(usage is None or (type(usage) is dict and
            all(type(usage.get(key)) is int and usage[key] >= 0 for key in
                ("prompt_tokens", "completion_tokens", "total_tokens")) and
            usage["prompt_tokens"] + usage["completion_tokens"] == usage["total_tokens"]),
            "terminal_usage")
    return value


def _public_cell(value):
    return {
        "cell_id": value["cell_id"],
        "unit_id": value["unit_id"],
        "arm": value["arm"],
        "round": value["round"],
        "status": value["status"],
        "reason": value["reason"],
        "terminal_sha256": digest(value),
    }


def _candidate_outcome(raw_content, public_cases):
    try:
        value = strict_json_loads(raw_content.decode("utf-8"))
        candidate = validate_candidate(value)
    except (UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        return "invalid_candidate", "candidate_schema_invalid", None
    verification = verify_candidate(candidate, public_cases)
    return (
        "accepted_candidate" if verification["passed"] else "invalid_candidate",
        None if verification["passed"] else verification["failure_code"],
        {"candidate": candidate, "verification": verification},
    )


def _build_report(plan, cells, directories):
    require(len(cells) == 48, "terminal_cell_count")
    statuses = Counter(row["status"] for row in cells)
    reservations = list(directories["reservations"].glob("*.json"))
    usage = {key: 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    for cell in cells:
        if cell["usage"] is not None:
            for key in usage:
                usage[key] += cell["usage"][key]
    halt_path = directories["run"] / "global_halt.json"
    halt = read_json(halt_path) if halt_path.exists() else None
    report = {
        "schema": VERSION + "-public-result",
        "status": "terminal",
        "approved_program": plan["approved_program"],
        "plan_sha256": digest(plan),
        "model": plan["model"],
        "configured_concurrency": plan["limits"]["max_concurrent_requests"],
        "cells": [_public_cell(row) for row in sorted(cells, key=lambda x: x["cell_id"])],
        "status_counts": dict(sorted(statuses.items())),
        "accounting": {
            "logical_cells": len(cells),
            "physical_attempts_reserved": len(reservations),
            "physical_attempts_completed": sum(row["physical_send_completed"] for row in cells),
            "reserved_tokens": sum(read_json(path)["reserved_tokens"] for path in reservations),
            "usage": usage,
        },
        "global_halt": {
            "triggered": halt is not None,
            "reason": None if halt is None else halt["reason"],
            "cell_id": None if halt is None else halt["cell_id"],
        },
        "claim_boundary": {
            "engineering_canary_only": True,
            "confirmatory_effect_claimed": False,
            "benchmark_accuracy_claimed": False,
            "library_promotion_authorized": False,
        },
    }
    require(report["accounting"]["physical_attempts_reserved"] <= 48 and
            report["accounting"]["physical_attempts_completed"] <=
            report["accounting"]["physical_attempts_reserved"], "attempt_accounting")
    return report


def _load_terminal_report(root, plan, directories):
    report_path = _safe_path(root, plan["public_report"])
    if not report_path.exists():
        return None
    report = read_json(report_path)
    require(report.get("schema") == VERSION + "-public-result" and
            report.get("status") == "terminal" and
            report.get("plan_sha256") == digest(plan), "report_binding")
    by_id = {row["cell_id"]: row for row in plan["cells"]}
    terminals = []
    for public in report.get("cells", []):
        require(type(public) is dict and public.get("cell_id") in by_id,
                "report_cell")
        terminal = read_json(_cell_path(directories, "cells", public["cell_id"]))
        terminal = _bound_terminal(plan, by_id[public["cell_id"]], terminal)
        require(canonical(public) == canonical(_public_cell(terminal)), "report_cell_binding")
        terminals.append(terminal)
    require(len(terminals) == 48 and canonical(report) ==
            canonical(_build_report(plan, terminals, directories)), "report_recompute")
    return report


def execute(root=ROOT, request_once=transport.request_once):
    """Execute or safely resume the frozen 48-cell canary."""

    root, plan, bundle = _load_frozen(root)
    directories = _directories(root, plan)
    existing_report = _load_terminal_report(root, plan, directories)
    if existing_report is not None:
        return existing_report

    public_cases = freezer._inputs(root)[1]
    plan_cells = {row["cell_id"]: row for row in plan["cells"]}
    terminals = {}
    state_lock = threading.Lock()
    stop = threading.Event()
    halt_state = {"reason": None, "cell_id": None}
    halt_path = directories["run"] / "global_halt.json"
    if halt_path.exists():
        saved_halt = read_json(halt_path)
        require(saved_halt.get("schema") == VERSION + "-global-halt" and
                saved_halt.get("plan_sha256") == digest(plan), "global_halt_binding")
        halt_state.update(reason=saved_halt["reason"], cell_id=saved_halt["cell_id"])
        stop.set()

    def publish_terminal(cell, value):
        path = _cell_path(directories, "cells", cell["cell_id"])
        if path.exists():
            existing = _bound_terminal(plan, cell, read_json(path))
            require(canonical(existing) == canonical(value), "terminal_immutable")
            value = existing
        else:
            write_new_json(path, value)
        with state_lock:
            terminals[cell["cell_id"]] = value
        return value

    def set_halt(cell, reason):
        with state_lock:
            if stop.is_set():
                return
            value = {
                "schema": VERSION + "-global-halt",
                "plan_sha256": digest(plan),
                "cell_id": cell["cell_id"],
                "reason": reason,
            }
            write_new_json(halt_path, value)
            halt_state.update(reason=reason, cell_id=cell["cell_id"])
            stop.set()

    # Bind existing terminals first.  A bare reservation is an uncertain send,
    # and the protocol deliberately sacrifices that cell rather than replay it.
    for cell in plan["cells"]:
        terminal_path = _cell_path(directories, "cells", cell["cell_id"])
        reservation_path = _cell_path(directories, "reservations", cell["cell_id"])
        if terminal_path.exists():
            terminals[cell["cell_id"]] = _bound_terminal(
                plan, cell, read_json(terminal_path)
            )
        elif reservation_path.exists():
            require(canonical(read_json(reservation_path)) ==
                    canonical(reservation_for(plan, cell)), "reservation_binding")
            publish_terminal(cell, _terminal(
                plan, cell, "infrastructure_unavailable",
                "orphaned_reservation_no_replay",
            ))

    def one(cell):
        if stop.is_set():
            return publish_terminal(cell, _terminal(
                plan, cell, "global_halt_not_dispatched", "global_safety_halt"
            ))
        private = bundle["cells"][cell["cell_id"]]
        payload = private["payload"]
        identity = contract.identity(payload)
        require(identity["request_key"] == cell["request_key"] and
                identity["request_body_sha256"] == cell["request_body_sha256"] and
                identity["payload_sha256"] == cell["payload_sha256"] and
                identity["reserved_tokens"] == cell["reserved_tokens"],
                "request_binding")
        reservation_path = _cell_path(directories, "reservations", cell["cell_id"])
        write_new_json(reservation_path, reservation_for(plan, cell))
        body = contract.request_body(payload)
        outcome = request_once(body, transport.VERIFIED_CA_SHA256, 600)
        require(type(outcome) is dict, "transport_result")
        if outcome.get("error") is not None:
            reason = outcome.get("error")
            require(type(reason) is str and type(outcome.get("global_halt")) is bool,
                    "transport_failure_shape")
            envelope_record = {
                "schema": VERSION + "-transport-failure",
                "plan_sha256": digest(plan),
                "cell_id": cell["cell_id"],
                "error": reason,
                "global_halt": outcome["global_halt"],
            }
            write_new_json(_cell_path(directories, "envelopes", cell["cell_id"]),
                           envelope_record)
            if outcome["global_halt"]:
                set_halt(cell, reason)
                status = "global_safety_failure"
            else:
                status = "infrastructure_unavailable"
            return publish_terminal(cell, _terminal(
                plan, cell, status, reason, physical_send_completed=True
            ))
        require(outcome.get("global_halt") is False and
                type(outcome.get("envelope_base64")) is str, "transport_success_shape")
        try:
            envelope = base64.b64decode(outcome["envelope_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            set_halt(cell, "transport_envelope_base64")
            return publish_terminal(cell, _terminal(
                plan, cell, "global_safety_failure", "transport_envelope_base64",
                physical_send_completed=True,
            ))
        parsed = contract.parse_envelope(envelope, "B")
        envelope_record = {
            "schema": VERSION + "-provider-envelope",
            "plan_sha256": digest(plan),
            "cell_id": cell["cell_id"],
            "envelope_base64": outcome["envelope_base64"],
            "envelope_sha256": sha(envelope),
        }
        write_new_json(_cell_path(directories, "envelopes", cell["cell_id"]),
                       envelope_record)
        if parsed["status"] != "complete":
            reason = parsed["error"]
            if parsed["global_halt"]:
                set_halt(cell, reason)
                status = "global_safety_failure"
            else:
                status = "infrastructure_unavailable"
            return publish_terminal(cell, _terminal(
                plan, cell, status, reason, usage=parsed["usage"],
                physical_send_completed=True, response_sha256=parsed["raw_sha256"],
            ))
        status, reason, candidate_record = _candidate_outcome(
            parsed["raw"], public_cases
        )
        if candidate_record is not None:
            write_new_json(_cell_path(directories, "candidates", cell["cell_id"]), {
                "schema": VERSION + "-private-candidate",
                "plan_sha256": digest(plan),
                "cell_id": cell["cell_id"],
                **candidate_record,
            })
        return publish_terminal(cell, _terminal(
            plan, cell, status, reason, usage=parsed["usage"],
            physical_send_completed=True, response_sha256=parsed["raw_sha256"],
        ))

    for round_number in range(1, 4):
        jobs = []
        round_cells = [row for row in plan["cells"] if row["round"] == round_number]
        for cell in round_cells:
            if cell["cell_id"] in terminals:
                continue
            earlier = [
                value for value in terminals.values()
                if value["unit_id"] == cell["unit_id"] and
                value["arm"] == cell["arm"] and value["round"] < round_number
            ]
            if any(value["status"] == "accepted_candidate" for value in earlier):
                publish_terminal(cell, _terminal(
                    plan, cell, "skipped_after_success", "prior_round_accepted"
                ))
            elif stop.is_set():
                publish_terminal(cell, _terminal(
                    plan, cell, "global_halt_not_dispatched", "global_safety_halt"
                ))
            else:
                jobs.append(cell)
        if jobs:
            with ThreadPoolExecutor(max_workers=5,
                                    thread_name_prefix="acquisition-canary") as pool:
                futures = [pool.submit(one, cell) for cell in jobs]
                for future in as_completed(futures):
                    future.result()
        round_summary = {
            "schema": VERSION + "-round",
            "plan_sha256": digest(plan),
            "round": round_number,
            "cells": [
                {"cell_id": cell["cell_id"],
                 "terminal_sha256": digest(terminals[cell["cell_id"]])}
                for cell in sorted(round_cells, key=lambda row: row["cell_id"])
            ],
            "global_halt": stop.is_set(),
        }
        round_path = directories["rounds"] / f"round-{round_number}.json"
        if round_path.exists():
            require(canonical(read_json(round_path)) == canonical(round_summary),
                    "round_checkpoint")
        else:
            write_new_json(round_path, round_summary)

    # A resumed global halt can predate a round checkpoint.  Close every logical
    # cell without creating new reservations.
    for cell in plan["cells"]:
        if cell["cell_id"] not in terminals:
            publish_terminal(cell, _terminal(
                plan, cell, "global_halt_not_dispatched", "global_safety_halt"
            ))
    ordered = [_bound_terminal(plan, cell, terminals[cell["cell_id"]])
               for cell in plan["cells"]]
    report = _build_report(plan, ordered, directories)
    report_path = _safe_path(root, plan["public_report"])
    require(report_path.parent.is_dir(), "report_parent")
    write_new_json(report_path, report)
    return report


if __name__ == "__main__":
    print(canonical(execute()))
