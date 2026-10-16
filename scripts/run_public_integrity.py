#!/usr/bin/env python3
"""Run the canonical credential-free public-integrity contract in this clone."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_clean_clone_layer_a import PINNED_SUBMODULE, layer_a_commands


EXPECTED_TEST_COUNT = 150


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _require(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = _run(command)
    if completed.returncode:
        raise RuntimeError(
            "public_integrity_command_failed:"
            + " ".join(command)
            + "\nstdout_tail="
            + completed.stdout[-2000:]
            + "\nstderr_tail="
            + completed.stderr[-2000:]
        )
    return completed


def build_report(*, run_commands: bool = True) -> dict:
    commands = layer_a_commands()
    report = {
        "schema": "llm4or-public-integrity-entrypoint-v1",
        "status": "not_executed",
        "expected_test_count": EXPECTED_TEST_COUNT,
        "pinned_submodule": PINNED_SUBMODULE,
        "commands": commands,
        "executed": False,
        "execution": {
            "api_or_model_calls": 0,
            "benchmark_solver_calls": 0,
            "native_evaluator_calls": 0,
            "vm_calls": 0,
            "credentials_read": False,
        },
        "boundary": (
            "This entrypoint verifies the released integrity/audit package. It does "
            "not rerun provider inference or independently rescore restricted "
            "benchmark endpoints from evaluator-only answers."
        ),
    }
    if not run_commands:
        return report

    submodule = _require(
        ["git", "-C", "vendor/solver-in-the-loop", "rev-parse", "HEAD"]
    ).stdout.strip()
    if submodule != PINNED_SUBMODULE:
        raise RuntimeError("public_integrity_submodule_mismatch")
    before = _require(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    if before:
        raise RuntimeError("public_integrity_requires_clean_checkout")

    results = []
    for command in commands:
        completed = _require(command)
        row = {"command": command, "returncode": completed.returncode}
        if "unittest" in command:
            match = re.search(r"Ran (\d+) tests?", completed.stderr)
            if match is None or int(match.group(1)) != EXPECTED_TEST_COUNT:
                raise RuntimeError("public_integrity_test_count_mismatch")
            row["tests"] = int(match.group(1))
        results.append(row)

    after = _require(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    if after:
        raise RuntimeError("public_integrity_checkout_changed")
    report.update(
        {
            "status": "passed_public_integrity_contract",
            "executed": True,
            "results": results,
            "clean_before_and_after": True,
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(build_report(), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
