#!/usr/bin/env python3
"""Verify the credential-free offline analysis environment with synthetic data.

The preflight path is standard-library only so it can explain a missing or
drifted analysis environment.  The full check re-executes this file in a
minimal environment and exercises only synthetic statistical, schema,
clustering, and integer-optimization examples.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON = "3.11.16"
EXPECTED_PACKAGES = {
    "numpy": "2.4.4",
    "scipy": "1.17.1",
    "jsonschema": "4.26.0",
    "scikit-learn": "1.9.0",
}
REQUIRED_PATHS = (
    "requirements-offline.txt",
    "scripts/verify_offline_analysis_environment.py",
    "tests/test_offline_analysis_environment.py",
    "llm4or/confirmatory_statistics.py",
    "llm4or/families.py",
    "llm4or/contracts.py",
    "llm4or/schema.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked(relative_path: str) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative_path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def preflight() -> dict:
    paths = []
    for relative_path in REQUIRED_PATHS:
        path = ROOT / relative_path
        exists = path.is_file()
        paths.append(
            {
                "path": relative_path,
                "exists": exists,
                "tracked": _tracked(relative_path),
                "sha256": _sha256(path) if exists else None,
            }
        )
    passed = all(item["exists"] and item["tracked"] for item in paths)
    return {
        "schema_version": "offline-analysis-environment-audit-v1",
        "status": "preflight_passed" if passed else "preflight_failed",
        "expected": {
            "python": EXPECTED_PYTHON,
            "packages": EXPECTED_PACKAGES,
        },
        "required_paths": paths,
        "all_required_paths_tracked": all(item["tracked"] for item in paths),
        "execution": {
            "credentials_read": False,
            "request_or_response_bodies_read": False,
            "evaluator_only_answers_read": False,
            "api_calls": 0,
            "external_solver_calls": 0,
            "native_evaluator_calls": 0,
            "virtual_machine_calls": 0,
        },
    }


def version_mismatches(python_version: str, observed_packages: dict[str, str]) -> dict:
    mismatches = {}
    if python_version != EXPECTED_PYTHON:
        mismatches["python"] = {"expected": EXPECTED_PYTHON, "observed": python_version}
    for package, expected in EXPECTED_PACKAGES.items():
        observed = observed_packages.get(package)
        if observed != expected:
            mismatches[package] = {"expected": expected, "observed": observed}
    return mismatches


def _child_checks() -> dict:
    observed = {
        package: importlib.metadata.version(package)
        for package in EXPECTED_PACKAGES
    }
    mismatches = version_mismatches(platform.python_version(), observed)

    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from jsonschema import Draft202012Validator

    from llm4or.confirmatory_statistics import (
        conditional_exact_delta_interval,
        exact_one_sided_mcnemar,
    )
    from llm4or.contracts import LP_SCHEMA
    from llm4or.families import group_candidates

    numeric_ok = bool(np.array([1, 2, 3], dtype=np.int64).dot(np.array([3, 2, 1])) == 10)
    integer_result = milp(
        c=np.array([1.0, 2.0]),
        integrality=np.array([1, 1]),
        bounds=Bounds([0.0, 0.0], [10.0, 10.0]),
        constraints=LinearConstraint([[1.0, 1.0]], [3.0], [np.inf]),
        options={"time_limit": 5.0},
    )
    integer_ok = bool(integer_result.success and abs(float(integer_result.fun) - 3.0) <= 1e-9)

    statistics_ok = (
        exact_one_sided_mcnemar(6, 0) == 0.015625
        and len(conditional_exact_delta_interval(6, 0, 10)) == 2
    )
    Draft202012Validator.check_schema(LP_SCHEMA)
    schema_ok = True

    records = [
        {"id": "a", "text": "A factory must produce 10 units with one machine."},
        {"id": "b", "text": "A factory must produce 20 units with one machine."},
        {"id": "c", "text": "Choose a shortest route between five cities."},
    ]
    _, membership, _ = group_candidates(records, threshold=0.99)
    clustering_ok = membership["a"] == membership["b"] and membership["a"] != membership["c"]

    checks = {
        "numpy_deterministic_numeric": numeric_ok,
        "scipy_internal_integer_milp": integer_ok,
        "confirmatory_statistics": statistics_ok,
        "jsonschema_contract": schema_ok,
        "sklearn_synthetic_grouping": clustering_ok,
    }
    return {
        "python": platform.python_version(),
        "packages": observed,
        "version_mismatches": mismatches,
        "checks": checks,
        "passed": not mismatches and all(checks.values()),
    }


def _run_child() -> dict:
    with tempfile.TemporaryDirectory(prefix="llm4or-offline-home-") as home:
        environment = {
            "HOME": home,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONPATH": str(ROOT),
        }
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError("offline_analysis_child_failed:" + completed.stderr.strip())
    return json.loads(completed.stdout)


def full_check() -> dict:
    report = preflight()
    if report["status"] != "preflight_passed":
        report["status"] = "failed_preflight"
        return report
    child = _run_child()
    report["observed"] = {"python": child["python"], "packages": child["packages"]}
    report["version_mismatches"] = child["version_mismatches"]
    report["synthetic_checks"] = child["checks"]
    report["execution"]["scipy_internal_milp_checks"] = 1
    report["status"] = (
        "passed_clean_offline_analysis_smoke"
        if child["passed"]
        else "failed_clean_offline_analysis_smoke"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--audit-out", type=Path)
    args = parser.parse_args()

    if args.child:
        print(json.dumps(_child_checks(), sort_keys=True, separators=(",", ":")))
        return 0
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
    return 0 if report["status"].startswith("preflight_passed") or report["status"].startswith("passed_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
