#!/usr/bin/env python3
"""Run credential-free Layer A in a fresh recursive no-local Git clone."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("experiments/clean_clone_layer_a_audit_20261015.json")
PINNED_SUBMODULE = "c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010"


def sanitized_environment(home: str) -> dict[str, str]:
    """Return a fixed environment without inheriting process secret values."""

    return {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": home,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }


def layer_a_commands() -> list[list[str]]:
    return [
        [
            "python3",
            "-m",
            "unittest",
            "tests.test_content_addressed_manifests",
            "tests.test_current_library_manifests",
            "tests.test_current_library_reconstruction",
            "tests.test_release_evidence_reconstruction",
            "tests.test_atomic_publisher",
            "tests.test_reconstruction_publishers",
            "tests.test_clean_clone_layer_a",
            "tests.test_verified_skill_library",
            "tests.test_audit_mixed_skill_confirmation",
            "tests.test_mixed_skill_execution",
        ],
        ["python3", "scripts/build_current_library_manifests.py", "--check"],
        ["python3", "scripts/audit_current_library_reconstruction.py", "--check"],
        ["python3", "scripts/reconstruct_release_evidence.py", "--check"],
    ]


def clone_commands(
    source_root: Path,
    clone: Path,
    branch: str,
    local_submodule_source: Path | None,
) -> list[list[str]]:
    """Return the main clone command for remote or explicit local fallback mode."""

    main = [
        "git",
        "clone",
        "--no-local",
    ]
    if local_submodule_source is None:
        main.append("--recurse-submodules")
    main.extend(["--branch", branch, str(source_root), str(clone)])
    if local_submodule_source is None:
        return [main]
    return [main]


def local_submodule_copy_commands(source: Path, target: Path) -> list[list[str]]:
    """Return a worktree-safe, network-free clone of the pinned local snapshot."""

    return [
        [
            "git",
            "clone",
            "--no-local",
            "--no-checkout",
            str(source),
            str(target),
        ],
        [
            "git",
            "-C",
            str(target),
            "checkout",
            "--detach",
            PINNED_SUBMODULE,
        ],
    ]


def _run(
    command: list[str], directory: Path, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=directory,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _require(
    command: list[str], directory: Path, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    result = _run(command, directory, environment)
    if result.returncode != 0:
        raise RuntimeError(
            "clean_clone_command_failed:"
            + " ".join(command)
            + "\nstdout_tail="
            + result.stdout[-2000:]
            + "\nstderr_tail="
            + result.stderr[-2000:]
        )
    return result


def _git_value(root: Path, environment: dict[str, str], *arguments: str) -> str:
    return _require(["git", *arguments], root, environment).stdout.strip()


def missing_object_ids(rev_list_output: str) -> list[str]:
    """Extract missing promisor-object markers from ``rev-list`` output."""

    return sorted(
        line[1:].split(None, 1)[0]
        for line in rev_list_output.splitlines()
        if line.startswith("?")
    )


def run_clean_clone_layer_a(
    source_root: Path,
    *,
    local_submodule_source: Path | None = None,
) -> dict[str, Any]:
    """Clone the committed branch and run only local credential-free checks."""

    source_root = Path(source_root).resolve()
    with tempfile.TemporaryDirectory(prefix="llm4or-clean-layer-a-") as temporary:
        temporary_root = Path(temporary)
        home = temporary_root / "home"
        home.mkdir()
        clone = temporary_root / "repository"
        environment = sanitized_environment(str(home))
        source_commit = _git_value(source_root, environment, "rev-parse", "HEAD")
        source_tree = _git_value(source_root, environment, "rev-parse", "HEAD^{tree}")
        branch = _git_value(source_root, environment, "rev-parse", "--abbrev-ref", "HEAD")
        if branch == "HEAD":
            raise RuntimeError("clean_clone_requires_named_branch")
        if local_submodule_source is not None:
            local_submodule_source = Path(local_submodule_source).resolve()
            local_submodule_commit = _git_value(
                local_submodule_source, environment, "rev-parse", "HEAD"
            )
            if local_submodule_commit != PINNED_SUBMODULE:
                raise RuntimeError("clean_clone_local_submodule_source_mismatch")
        commands = clone_commands(
            source_root, clone, branch, local_submodule_source
        )
        clone_result = _require(commands[0], temporary_root, environment)
        if local_submodule_source is not None:
            submodule_target = clone / "vendor/solver-in-the-loop"
            if submodule_target.exists():
                if any(submodule_target.iterdir()):
                    raise RuntimeError("clean_clone_local_submodule_target_not_empty")
                submodule_target.rmdir()
            for command in local_submodule_copy_commands(
                local_submodule_source, submodule_target
            ):
                _require(command, clone, environment)
            copied_commit = _git_value(
                submodule_target, environment, "rev-parse", "HEAD"
            )
            if copied_commit != PINNED_SUBMODULE:
                raise RuntimeError("clean_clone_copied_submodule_mismatch")
            _require(
                ["git", "submodule", "init", "vendor/solver-in-the-loop"],
                clone,
                environment,
            )
            _require(
                ["git", "submodule", "absorbgitdirs", "vendor/solver-in-the-loop"],
                clone,
                environment,
            )
        clone_commit = _git_value(clone, environment, "rev-parse", "HEAD")
        clone_tree = _git_value(clone, environment, "rev-parse", "HEAD^{tree}")
        if clone_commit != source_commit or clone_tree != source_tree:
            raise RuntimeError("clean_clone_identity_mismatch")
        before = _git_value(
            clone, environment, "status", "--porcelain=v1", "--untracked-files=all"
        )
        if before:
            raise RuntimeError("clean_clone_not_clean_before")
        submodule_line = _git_value(clone, environment, "submodule", "status", "--recursive")
        if not submodule_line.startswith(
            f"{PINNED_SUBMODULE} vendor/solver-in-the-loop"
        ) and not submodule_line.startswith(
            f" {PINNED_SUBMODULE} vendor/solver-in-the-loop"
        ):
            raise RuntimeError(f"clean_clone_submodule_mismatch:{submodule_line}")
        submodule_root = clone / "vendor/solver-in-the-loop"
        object_listing = _git_value(
            submodule_root,
            environment,
            "rev-list",
            "--objects",
            "--all",
            "--missing=print",
        )
        missing_objects = missing_object_ids(object_listing)
        if missing_objects:
            raise RuntimeError(
                "clean_clone_submodule_missing_objects:" + str(len(missing_objects))
            )
        _require(["git", "fsck", "--full"], submodule_root, environment)
        python_version = _require(["python3", "--version"], clone, environment)
        version_text = (python_version.stdout or python_version.stderr).strip()
        results = []
        for command in layer_a_commands():
            completed = _require(command, clone, environment)
            record: dict[str, Any] = {
                "command": command,
                "returncode": completed.returncode,
            }
            if "unittest" in command:
                match = re.search(r"Ran (\d+) tests?", completed.stderr)
                if match is None:
                    raise RuntimeError("clean_clone_test_count_missing")
                record["tests"] = int(match.group(1))
            results.append(record)
        after = _git_value(
            clone, environment, "status", "--porcelain=v1", "--untracked-files=all"
        )
        if after:
            raise RuntimeError("clean_clone_not_clean_after")
        return {
            "schema": "llm4or-clean-clone-layer-a-audit-v1",
            "audited_at_local_date": "2026-10-15",
            "status": (
                "passed_recursive_no_local_credential_free_layer_a"
                if local_submodule_source is None
                else "passed_no_local_credential_free_layer_a_with_local_complete_submodule_snapshot"
            ),
            "source": {
                "branch": branch,
                "commit": source_commit,
                "tree": source_tree,
            },
            "clone": {
                "mode": (
                    "git_clone_no_local_recurse_submodules"
                    if local_submodule_source is None
                    else "git_clone_no_local_plus_local_pinned_complete_submodule_snapshot"
                ),
                "commit": clone_commit,
                "tree": clone_tree,
                "clean_before": before == "",
                "clean_after": after == "",
                "clone_returncode": clone_result.returncode,
            },
            "environment": {
                "python": version_text,
                "inherited_environment_values": False,
                "environment_variable_names": sorted(environment),
                "credentials_available_to_commands": False,
            },
            "solver_submodule": {
                "path": "vendor/solver-in-the-loop",
                "commit": PINNED_SUBMODULE,
                "initialized": True,
                "solver_executed": False,
                "remote_acquisition_verified": local_submodule_source is None,
                "local_source_used": local_submodule_source is not None,
                "complete_object_graph_verified": len(missing_objects) == 0,
                "missing_reachable_objects": len(missing_objects),
                "fsck_full_passed": True,
            },
            "commands": results,
            "claim_boundary": {
                "layer_a_passed": True,
                "offline_analysis_layer_passed": False,
                "solver_native_layer_passed": False,
                "provider_layer_passed": False,
                "figure_regeneration_layer_passed": False,
                "rights_or_history_safe_release_passed": False,
                "external_submodule_remote_acquisition_passed": (
                    local_submodule_source is None
                ),
            },
            "safety": {
                "api_or_model_calls": 0,
                "solver_calls": 0,
                "native_evaluator_calls": 0,
                "vm_calls": 0,
                "environment_values_read_from_parent": False,
                "request_or_response_bodies_read": False,
                "evaluator_only_answers_read": False,
                "credentials_read": False,
            },
        }


def _render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def output_label(output: Path, root: Path = ROOT) -> str:
    """Use a repository-relative label when possible, otherwise an absolute path."""

    output = output.resolve()
    root = root.resolve()
    try:
        return str(output.relative_to(root))
    except ValueError:
        return str(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--local-submodule-source",
        type=Path,
        help=(
            "Copy an explicit pinned local solver checkout when the declared remote is "
            "unavailable; the audit independently verifies its reachable object graph "
            "and records that remote acquisition was not verified in this run."
        ),
    )
    arguments = parser.parse_args()
    output = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    local_submodule_source = arguments.local_submodule_source
    if local_submodule_source is not None and not local_submodule_source.is_absolute():
        local_submodule_source = ROOT / local_submodule_source
    raw = _render(
        run_clean_clone_layer_a(
            ROOT,
            local_submodule_source=local_submodule_source,
        )
    )
    if arguments.check:
        if output.read_bytes() != raw:
            raise ValueError("clean_clone_layer_a_audit_mismatch")
    else:
        _write_exclusive(output, raw)
    print(
        json.dumps(
            {
                "mode": "check" if arguments.check else "write",
                "output": output_label(output),
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
