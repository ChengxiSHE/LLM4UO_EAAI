#!/usr/bin/env python3
"""Bind the local Gurobi and OR-Debug runtime without exposing license data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path("/usr/local/bin/gurobi_cl")
SUBMODULE = ROOT / "vendor/solver-in-the-loop"
EXPECTED_GUROBI_VERSION = "13.0.1"
EXPECTED_SUBMODULE_COMMIT = "c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010"
EXPECTED_THREADS = 1
EXPECTED_SOLVER_TIMEOUT_SECONDS = 15
EXPECTED_WALL_TIMEOUT_SECONDS = 25
EXPECTED_MAX_MPS_BYTES = 1_000_000
EXPECTED_MODEL_COUNT = 4962
REQUIRED_PATHS = (
    "scripts/verify_solver_native_environment.py",
    "tests/test_solver_native_environment.py",
    "llm4or/gurobi_cli_solver.py",
    "llm4or/or_debug_gurobi.py",
    "llm4or/or_debug_iis_control.py",
    "llm4or/or_debug_mps.py",
    "llm4or/milp_solver.py",
    "llm4or/milp_schema.py",
    "vendor/solver-in-the-loop",
)


SYNTHETIC_MILP = {
    "schema": "milp-v1",
    "variables": [
        {"id": "x", "meaning": "units", "unit": "1", "domain": "integer", "lower": 0, "upper": 3},
        {"id": "y", "meaning": "switch", "unit": "1", "domain": "binary", "lower": None, "upper": None},
    ],
    "constraints": [
        {"id": "cap", "coefficients": {"x": 1, "y": 1}, "sense": "le", "rhs": 3},
    ],
    "objective": {"coefficients": {"x": 2, "y": 1}, "sense": "max", "unit": "1", "offset": 5},
}

SYNTHETIC_INFEASIBLE_MPS = """NAME          IISMINI
ROWS
 N  OBJ
 G  lower
 L  upper
COLUMNS
    x           OBJ       0  lower     1
    x           upper     1
RHS
    rhs         lower     2  upper     1
BOUNDS
 LO bnd         x         0
ENDATA
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
    )


def _tracked(relative_path: str) -> bool:
    return _git("ls-files", "--error-unmatch", "--", relative_path).returncode == 0


def parse_gurobi_version(output: str) -> str:
    match = re.search(r"Gurobi Optimizer version\s+(\d+\.\d+\.\d+)\b", output)
    if not match:
        raise ValueError("unrecognized_gurobi_version")
    return match.group(1)


def _binary_identity() -> dict:
    if not BINARY.is_file():
        return {"present": False, "path": str(BINARY)}
    completed = subprocess.run(
        [str(BINARY), "--version"], text=True, capture_output=True, check=False, timeout=10
    )
    output = (completed.stdout + completed.stderr).strip()
    try:
        version = parse_gurobi_version(output)
    except ValueError:
        version = None
    resolved = BINARY.resolve()
    return {
        "present": True,
        "path": str(BINARY),
        "resolved_path": str(resolved),
        "resolved_sha256": _sha256(resolved),
        "version": version,
        "version_matches": version == EXPECTED_GUROBI_VERSION,
        "version_command_returncode": completed.returncode,
    }


def _submodule_identity() -> dict:
    if not (SUBMODULE / ".git").exists():
        return {"initialized": False, "path": "vendor/solver-in-the-loop"}
    head = _git("rev-parse", "HEAD", cwd=SUBMODULE)
    status = _git("status", "--porcelain", cwd=SUBMODULE)
    models = _git("ls-files", "or_debug_bench/models/*.mps", cwd=SUBMODULE)
    listed = set(models.stdout.splitlines())
    required = {"LICENSE", "README.md", "or_debug_bench/dataset.json"}
    tracked = set(_git("ls-files", *sorted(required), cwd=SUBMODULE).stdout.splitlines())
    commit = head.stdout.strip() if head.returncode == 0 else None
    return {
        "initialized": head.returncode == 0,
        "path": "vendor/solver-in-the-loop",
        "commit": commit,
        "commit_matches": commit == EXPECTED_SUBMODULE_COMMIT,
        "clean": status.returncode == 0 and not status.stdout.strip(),
        "tracked_model_count": len(listed),
        "tracked_model_count_matches": len(listed) == EXPECTED_MODEL_COUNT,
        "required_paths_tracked": tracked == required,
        "dataset_contents_read": False,
        "license_contents_read": False,
    }


def preflight() -> dict:
    paths = []
    for relative_path in REQUIRED_PATHS:
        path = ROOT / relative_path
        exists = path.exists()
        paths.append({
            "path": relative_path,
            "exists": exists,
            "tracked": _tracked(relative_path),
            "sha256": _sha256(path) if exists and path.is_file() else None,
        })
    binary = _binary_identity()
    submodule = _submodule_identity()
    passed = (
        all(item["exists"] and item["tracked"] for item in paths)
        and binary.get("version_matches") is True
        and binary.get("version_command_returncode") == 0
        and submodule.get("commit_matches") is True
        and submodule.get("clean") is True
        and submodule.get("tracked_model_count_matches") is True
        and submodule.get("required_paths_tracked") is True
    )
    return {
        "schema_version": "solver-native-environment-audit-v1",
        "status": "preflight_passed_external_license_required" if passed else "preflight_failed",
        "contract": {
            "gurobi_version": EXPECTED_GUROBI_VERSION,
            "submodule_commit": EXPECTED_SUBMODULE_COMMIT,
            "threads": EXPECTED_THREADS,
            "solver_timeout_seconds": EXPECTED_SOLVER_TIMEOUT_SECONDS,
            "wall_timeout_seconds": EXPECTED_WALL_TIMEOUT_SECONDS,
            "max_mps_bytes": EXPECTED_MAX_MPS_BYTES,
        },
        "binary": binary,
        "submodule": submodule,
        "required_paths": paths,
        "all_required_paths_tracked": all(item["tracked"] for item in paths),
        "execution": {
            "binary_version_calls": 1 if binary.get("present") else 0,
            "synthetic_solver_calls": 0,
            "license_file_contents_read_by_verifier": False,
            "benchmark_dataset_contents_read": False,
            "request_or_response_bodies_read": False,
            "evaluator_only_answers_read": False,
            "provider_api_calls": 0,
            "virtual_machine_calls": 0,
        },
        "external_license_boundary": (
            "The vendor binary may resolve a user-provisioned license internally. "
            "The verifier does not locate, read, hash, copy, or report license material."
        ),
    }


def full_check() -> dict:
    report = preflight()
    if report["status"] != "preflight_passed_external_license_required":
        report["status"] = "failed_preflight"
        return report

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from llm4or.gurobi_cli_solver import execute
    from llm4or.or_debug_gurobi import compute_iis, solve_mps_text
    from llm4or.or_debug_iis_control import build_generic_iis_repair
    from llm4or.or_debug_mps import apply_repair

    declarative = execute(
        {"op": "solve", "model": SYNTHETIC_MILP},
        binary=str(BINARY), time_limit=5, threads=EXPECTED_THREADS, wall_seconds=10,
    )
    with tempfile.TemporaryDirectory(prefix="llm4or-solver-native-") as directory:
        root = Path(directory)
        source = root / "source.mps"
        source.write_text(SYNTHETIC_INFEASIBLE_MPS, encoding="utf-8")
        iis = compute_iis(source, workspace=root / "iis", binary=str(BINARY))
        proposal = build_generic_iis_repair(iis["iis"]) if iis.get("status") == "infeasible_iis" else None
        patched = apply_repair(SYNTHETIC_INFEASIBLE_MPS, proposal["repair"]) if proposal else None
        solved = (
            solve_mps_text(patched["mps"], workspace=root / "solve", binary=str(BINARY))
            if patched else {"status": "not_run", "objective": None}
        )

    checks = {
        "declarative_milp_optimal": declarative.get("status") == "optimal",
        "declarative_objective_rechecked": declarative.get("objective") == 11.0,
        "declarative_primal_feasible": declarative.get("point_check", {}).get("feasible") is True,
        "fresh_iis_computed": iis.get("status") == "infeasible_iis",
        "generic_iis_repair_constructed": proposal is not None,
        "repaired_mps_optimal": solved.get("status") == "optimal",
        "repaired_mps_objective": solved.get("objective") == "0",
    }
    report["synthetic_checks"] = checks
    report["execution"]["synthetic_solver_calls"] = 3
    report["status"] = (
        "passed_local_solver_native_smoke_external_license"
        if all(checks.values())
        else "failed_local_solver_native_smoke"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--audit-out", type=Path)
    args = parser.parse_args()
    if args.preflight_only:
        report = preflight()
    elif args.check:
        report = full_check()
    else:
        parser.error("choose --preflight-only or --check")
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.audit_out:
        output = args.audit_out if args.audit_out.is_absolute() else ROOT / args.audit_out
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if "passed" in report["status"] and not report["status"].startswith("failed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
