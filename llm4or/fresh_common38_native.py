"""Frozen, resumable native evaluation for the fresh common-38 current method."""

from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess

from .fresh_common38 import SOURCE_RELATIVE, build_private_bundle
from .gurobi_cli_solver import DEFAULT_BINARY, VERSION as SOLVER_VERSION, execute
from .schema import canonical, digest
from .structured_or_skills import VERSION as SKILL_VERSION, compile_and_admit


VERSION = "fresh-common38-current-native-v1"
PACKET_READINESS = "experiments/fresh_common38_packet_readiness_20261015.json"
SKILL_READINESS = "experiments/fresh_common38_structured_skill_readiness_20261015.json"
CODE_PATHS = (
    "llm4or/fresh_common38_native.py",
    "llm4or/fresh_common38.py",
    "llm4or/structured_or_skills.py",
    "llm4or/gurobi_cli_solver.py",
    "llm4or/milp_schema.py",
    "llm4or/milp_solver.py",
    "scripts/freeze_fresh_common38_current_native.py",
    "scripts/run_fresh_common38_current_native.py",
    "scripts/score_fresh_common38_current_native.py",
)
TERMINAL = frozenset({"optimal", "infeasible", "unbounded", "limit", "unknown", "numerical_error", "exception"})


def require(ok, code):
    if not ok:
        raise ValueError(code)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _binary_version(binary):
    completed = subprocess.run([binary, "--version"], capture_output=True, text=True,
                               check=True, timeout=10)
    first = completed.stdout.splitlines()[0].strip()
    require(first, "solver_version")
    return first


def build_plan(root):
    root = Path(root).resolve()
    bundle = build_private_bundle(root)
    bindings = []
    for row in bundle["records"]:
        admitted = compile_and_admit(row["public_payload"])
        bindings.append({
            "id": row["id"], "family": row["family"],
            "public_payload_sha256": row["public_payload_sha256"],
            "model_sha256": admitted["model_sha256"],
            "metrics": admitted["metrics"],
        })
    binary = Path(DEFAULT_BINARY)
    require(binary.is_file(), "solver_binary")
    return {
        "schema": VERSION + "-plan",
        "status": "frozen_ready_for_local_native_run",
        "authorization": "approved_scheme_A_G07_G09_and_standing_no_reconfirmation",
        "source_revision": bundle["source_revision"],
        "packet_readiness_sha256": _sha(root / PACKET_READINESS),
        "skill_readiness_sha256": _sha(root / SKILL_READINESS),
        "skill_version": SKILL_VERSION,
        "code_sha256": {path: _sha(root / path) for path in CODE_PATHS},
        "solver": {
            "backend": SOLVER_VERSION,
            "binary_path": str(binary),
            "binary_sha256": _sha(binary),
            "version_line": _binary_version(str(binary)),
            "threads": 1,
            "time_limit_seconds": 20,
            "wall_seconds": 25,
            "physical_solver_calls_per_identity": 1,
        },
        "endpoint": {
            "solver_status": 2,
            "relative_tolerance": 1e-5,
            "absolute_tolerance": 1e-6,
        },
        "bindings": bindings,
        "output": {
            "private_run_directory": "results/private/fresh_common38_current_native_v1",
            "public_result": "experiments/fresh_common38_current_native_result_20261015.json",
        },
        "claim_boundary": {
            "api_calls": 0,
            "model_calls": 0,
            "one_local_solver_call_per_unfinished_identity": True,
            "individual_failures_continue": True,
            "objectives_points_and_reference_values_private": True,
            "common_external_comparison_complete": False,
        },
    }


def _write_new(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ValueError("output_exists") from exc
    raw = (canonical(value) + "\n").encode()
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(fd, raw[offset:])
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def publish_plan(path, plan):
    _write_new(path, plan)


def _cell_path(directory, problem_id):
    return Path(directory) / "cells" / (hashlib.sha256(problem_id.encode()).hexdigest() + ".json")


def _load_cell(path, binding, plan_sha):
    value = json.loads(Path(path).read_text())
    require(value.get("plan_sha256") == plan_sha and value.get("id") == binding["id"]
            and value.get("family") == binding["family"]
            and value.get("model_sha256") == binding["model_sha256"]
            and value.get("status") in TERMINAL, "checkpoint_binding")
    return value


def run_plan(root, plan, directory, solver=execute):
    root = Path(root).resolve(); directory = Path(directory)
    require(canonical(plan) == canonical(build_plan(root)), "plan_reconstruction")
    plan_sha = digest(plan)
    rows = {row["id"]: row for row in build_private_bundle(root)["records"]}
    directory.mkdir(parents=True, exist_ok=True)
    calls = 0; cells = []
    for binding in plan["bindings"]:
        path = _cell_path(directory, binding["id"])
        if path.exists():
            cells.append(_load_cell(path, binding, plan_sha)); continue
        row = rows[binding["id"]]
        admitted = compile_and_admit(row["public_payload"])
        require(admitted["model_sha256"] == binding["model_sha256"], "model_binding")
        calls += 1
        try:
            solved = solver(
                {"op": "solve", "model": admitted["model"]},
                time_limit=plan["solver"]["time_limit_seconds"],
                threads=plan["solver"]["threads"],
                wall_seconds=plan["solver"]["wall_seconds"],
            )
            status = solved.get("status")
            require(status in TERMINAL - {"exception"}, "solver_status")
            cell = {
                "schema": VERSION + "-private-cell",
                "plan_sha256": plan_sha,
                "id": binding["id"], "family": binding["family"],
                "model_sha256": binding["model_sha256"],
                "status": status, "reason": solved.get("reason"),
                "objective": solved.get("objective"), "point": solved.get("point"),
                "point_check": solved.get("point_check"),
                "backend": solved.get("backend"), "wall_seconds": solved.get("wall_seconds"),
            }
        except Exception as exc:
            cell = {
                "schema": VERSION + "-private-cell",
                "plan_sha256": plan_sha,
                "id": binding["id"], "family": binding["family"],
                "model_sha256": binding["model_sha256"],
                "status": "exception", "reason": type(exc).__name__,
                "objective": None, "point": None, "point_check": None,
                "backend": None, "wall_seconds": None,
            }
        _write_new(path, cell); cells.append(cell)
    return {"terminal": len(cells), "new_solver_calls": calls,
            "status_counts": dict(sorted(Counter(cell["status"] for cell in cells).items()))}


def load_cells(plan, directory):
    plan_sha = digest(plan)
    return [_load_cell(_cell_path(directory, row["id"]), row, plan_sha)
            for row in plan["bindings"]]


def load_references(root, plan):
    root = Path(root).resolve()
    bundle = build_private_bundle(root)
    rows = {row["id"]: row for row in bundle["records"]}
    references = {}
    source = root / SOURCE_RELATIVE
    for binding in plan["bindings"]:
        value = json.loads((source / rows[binding["id"]]["source_file"]).read_text())
        result = value.get("gurobi_result", {})
        optimum = result.get("theoretical_optimum")
        status = result.get("solver_status")
        require(type(optimum) in (int, float) and math.isfinite(optimum)
                and type(status) is int, "reference_endpoint")
        references[binding["id"]] = {"optimum": optimum, "solver_status": status}
    return references


def score_cells(plan, cells, references):
    by_id = {cell["id"]: cell for cell in cells}
    require(len(by_id) == len(cells) == len(plan["bindings"]) == 38, "score_denominator")
    result_rows = []; family = {name: Counter() for name in ("rcpsp", "vrptw")}
    total = Counter()
    for binding in plan["bindings"]:
        cell = by_id[binding["id"]]; reference = references[binding["id"]]
        correct = (
            cell["status"] == "optimal"
            and reference["solver_status"] == plan["endpoint"]["solver_status"]
            and type(cell.get("objective")) in (int, float)
            and math.isclose(cell["objective"], reference["optimum"],
                             rel_tol=plan["endpoint"]["relative_tolerance"],
                             abs_tol=plan["endpoint"]["absolute_tolerance"])
        )
        disposition = "correct" if correct else (
            "incorrect_objective" if cell["status"] == "optimal" else "solver_unavailable"
        )
        total[disposition] += 1; family[binding["family"]][disposition] += 1
        result_rows.append({"id": binding["id"], "family": binding["family"],
                            "model_sha256": binding["model_sha256"],
                            "solver_status": cell["status"], "disposition": disposition,
                            "correct": correct})
    return {
        "schema": VERSION + "-public-result",
        "status": "complete",
        "plan_sha256": digest(plan),
        "aggregate": {"planned": 38, **dict(total),
                      "accuracy": total["correct"] / 38},
        "families": {name: {"planned": sum(family[name].values()), **dict(family[name])}
                     for name in sorted(family)},
        "rows": result_rows,
        "privacy": {"contains_objectives": False, "contains_points": False,
                    "contains_reference_values": False, "contains_packet_bodies": False},
        "claim_boundary": {"current_method_only": True,
                           "common_external_comparison_complete": False,
                           "automatic_acquisition_supported": False},
    }


def publish_result(path, value):
    _write_new(path, value)


__all__ = ["build_plan", "load_cells", "load_references", "publish_plan",
           "publish_result", "run_plan", "score_cells"]
