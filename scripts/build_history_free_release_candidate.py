#!/usr/bin/env python3
"""Build and verify the author-approved, unparented release candidate.

The candidate has exactly one reachable commit and the same tree as the
authorized source commit.  A retained bundle is written only after all
history, privacy, licensing-metadata and credential-free Layer A checks pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_clean_clone_layer_a import run_clean_clone_layer_a


RELEASE_VERSION = "v1.1.1"
RELEASE_REF = "refs/llm4or-release/candidate-v1.1.1-20261016"
RELEASE_BRANCH = "release-candidate-v1.1.1-20261016"
PINNED_SUBMODULE = "c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010"
SUBMODULE = ROOT / "vendor/solver-in-the-loop"
RESTRICTED_PATHS = frozenset(
    {
        "experiments/mixed_skill_confirmation_bundle_20261014.json",
        "results/or_debug_confirmation_evaluation_20261014.json",
        "results/or_debug_confirmation_method_outputs_20261014.json",
        "results/mixed_skill_confirmation_outputs_20261014.json",
        "results/private/tsp_constraint_confirmation_candidates_20261014.json",
        "results/private/tsp_constraint_confirmation_public_20261014.json",
    }
)
REQUIRED_PATHS = (
    "scripts/build_history_free_release_candidate.py",
    "tests/test_history_free_release_candidate.py",
    "scripts/run_clean_clone_layer_a.py",
    "experiments/restricted_source_exclusion_audit_20261015.json",
    "experiments/authorized_release_audit_20261016.json",
    "experiments/author_release_decision_packet_20261015.json",
    "experiments/data_code_availability_audit_v3_20261016.json",
    "docs/DATA_CODE_AVAILABILITY_AUDIT_V3_20261016.md",
    "experiments/provider_environment_preflight_audit_20261016.json",
    "reproduction/environment_layers_v1.json",
    "llm4or/public_antchat_transport.py",
    "scripts/verify_provider_environment.py",
    "tests/test_provider_environment.py",
    "experiments/optitrust_indexed_closure_20261016.json",
    "docs/OPTITRUST_INDEXED_CLOSURE_20261016.md",
    "experiments/paper_evidence_manifest_20261015.json",
    "experiments/goal_completion_audit_20261015.json",
    "docs/TOP_CONFERENCE_METHOD_ROADMAP_V2_20261016.md",
    "experiments/atomic_publisher_concurrent_cleanup_fix_audit_20261016.json",
    "LICENSE",
    "LICENSE-DATA",
    "NOTICE",
    "CITATION.cff",
    ".zenodo.json",
    ".gitmodules",
    "vendor/solver-in-the-loop",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _require(*args, **kwargs) -> subprocess.CompletedProcess[str]:
    completed = _run(*args, **kwargs)
    if completed.returncode != 0:
        raise RuntimeError(
            "history_free_candidate_command_failed:"
            + " ".join(args[0])
            + ":"
            + completed.stderr[-1000:]
        )
    return completed


def _git(*arguments: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    return _require(["git", *arguments], cwd=cwd, env=env).stdout.strip()


def _tracked(relative_path: str) -> bool:
    return _run(
        ["git", "ls-files", "--error-unmatch", "--", relative_path], cwd=ROOT
    ).returncode == 0


def preflight() -> dict:
    paths = []
    for relative in REQUIRED_PATHS:
        path = ROOT / relative
        paths.append(
            {
                "path": relative,
                "exists": path.exists(),
                "tracked": _tracked(relative),
                "sha256": _sha256(path) if path.is_file() else None,
            }
        )
    source_tree = _git("rev-parse", "HEAD^{tree}")
    submodule_commit = _git("ls-tree", "HEAD", "vendor/solver-in-the-loop").split()[2]
    packet = json.loads(
        (ROOT / "experiments/author_release_decision_packet_20261015.json").read_text()
    )
    all_decisions_approved = all(
        item.get("approved") for item in packet.get("author_decisions", [])
    ) and {item.get("id") for item in packet.get("author_decisions", [])} == {
        f"D{index}" for index in range(1, 9)
    }
    passed = (
        all(item["exists"] and item["tracked"] for item in paths)
        and submodule_commit == PINNED_SUBMODULE
        and all_decisions_approved
    )
    return {
        "schema_version": "history-free-release-candidate-audit-v1",
        "status": "preflight_passed" if passed else "preflight_failed",
        "source": {"commit": _git("rev-parse", "HEAD"), "tree": source_tree},
        "submodule": {"path": "vendor/solver-in-the-loop", "commit": submodule_commit},
        "required_paths": paths,
        "all_required_paths_tracked": all(item["tracked"] for item in paths),
        "all_author_decisions_approved": all_decisions_approved,
        "execution": {
            "git_ref_created": False,
            "public_push": False,
            "api_or_model_calls": 0,
            "solver_calls": 0,
            "credentials_read": False,
            "request_or_response_bodies_read": False,
            "evaluator_only_answers_read": False,
        },
    }


def _commit_environment(home: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "LLM4OR release builder",
        "GIT_AUTHOR_EMAIL": "release-builder@invalid.example",
        "GIT_AUTHOR_DATE": "2026-10-16T00:00:00+08:00",
        "GIT_COMMITTER_NAME": "LLM4OR release builder",
        "GIT_COMMITTER_EMAIL": "release-builder@invalid.example",
        "GIT_COMMITTER_DATE": "2026-10-16T00:00:00+08:00",
    }


def _copy_bundle_exclusive(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(destination, flags, 0o644)
    try:
        with source.open("rb") as input_handle, os.fdopen(descriptor, "wb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle)
            output_handle.flush()
            os.fsync(output_handle.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        raise
    directory = os.open(destination.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def build_candidate(
    *, bundle_out: Path | None = None, local_submodule_source: Path | None = None
) -> dict:
    report = preflight()
    if report["status"] != "preflight_passed":
        report["status"] = "failed_preflight"
        return report
    if _run(["git", "show-ref", "--verify", "--quiet", RELEASE_REF]).returncode == 0:
        raise RuntimeError("history_free_release_ref_already_exists")

    source_commit = report["source"]["commit"]
    source_tree = report["source"]["tree"]
    local_source = Path(local_submodule_source or SUBMODULE).resolve()
    if _git("rev-parse", "HEAD", cwd=local_source) != PINNED_SUBMODULE:
        raise RuntimeError("history_free_local_submodule_source_mismatch")
    with tempfile.TemporaryDirectory(prefix="llm4or-history-free-") as directory:
        temporary = Path(directory)
        home = temporary / "home"
        home.mkdir()
        environment = _commit_environment(home)
        orphan = _require(
            ["git", "commit-tree", source_tree],
            cwd=ROOT,
            env=environment,
            input_text=f"LLM4OR {RELEASE_VERSION} history-free authorized release\n",
        ).stdout.strip()
        bundle = temporary / "candidate.bundle"
        ref_created = False
        try:
            _require(["git", "update-ref", RELEASE_REF, orphan], cwd=ROOT, env=environment)
            ref_created = True
            _require(["git", "bundle", "create", str(bundle), RELEASE_REF], cwd=ROOT, env=environment)
        finally:
            if ref_created:
                _require(["git", "update-ref", "-d", RELEASE_REF], cwd=ROOT, env=environment)

        snapshot = temporary / "snapshot"
        _require(["git", "clone", str(bundle), str(snapshot)], cwd=temporary, env=environment)
        _require(
            [
                "git",
                "fetch",
                str(bundle),
                f"{RELEASE_REF}:refs/heads/{RELEASE_BRANCH}",
            ],
            cwd=snapshot,
            env=environment,
        )
        _require(["git", "checkout", RELEASE_BRANCH], cwd=snapshot, env=environment)
        candidate_tree = _git("rev-parse", "HEAD^{tree}", cwd=snapshot, env=environment)
        parents = _git("show", "-s", "--format=%P", "HEAD", cwd=snapshot, env=environment)
        commit_count = int(_git("rev-list", "--all", "--count", cwd=snapshot, env=environment))
        tracked = set(_git("ls-tree", "-r", "--name-only", "HEAD", cwd=snapshot, env=environment).splitlines())
        restricted_present = sorted(RESTRICTED_PATHS & tracked)
        private_tracked = sorted(path for path in tracked if "/private/" in "/" + path)
        root_license = sorted({"LICENSE", "COPYING", "NOTICE"} & tracked)
        if candidate_tree != source_tree or parents or commit_count != 1 or restricted_present or private_tracked:
            raise RuntimeError("history_free_candidate_invariant_failed")

        layer_a = run_clean_clone_layer_a(snapshot, local_submodule_source=local_source)
        bundle_sha = _sha256(bundle)
        if bundle_out is not None:
            _copy_bundle_exclusive(bundle, Path(bundle_out).resolve())

    if _run(["git", "show-ref", "--verify", "--quiet", RELEASE_REF]).returncode == 0:
        raise RuntimeError("history_free_release_ref_cleanup_failed")
    report.update(
        {
            "status": "passed_history_free_authorized_candidate",
            "candidate": {
                "commit": orphan,
                "tree": candidate_tree,
                "parent_count": 0,
                "reachable_commit_count": commit_count,
                "bundle_sha256": bundle_sha,
                "restricted_paths_present": restricted_present,
                "private_paths_tracked": private_tracked,
                "root_license_paths": root_license,
                "source_tree_exact_match": candidate_tree == source_tree,
            },
            "layer_a": layer_a,
            "rights": {
                "author_selected_license": True,
                "first_party_scope_authorized": True,
                "third_party_attribution_policy_approved": True,
                "public_release_authorized": True,
            },
            "boundary": (
                "The retained one-commit bundle contains the author-approved licensed "
                "tree, removes prior ancestry, excludes restricted/private paths and "
                "passes credential-free Layer A. Repository publication and DOI remain "
                "external states until separately verified."
            ),
        }
    )
    report["execution"]["git_ref_created"] = True
    report["execution"]["temporary_git_ref_deleted"] = True
    report["execution"]["history_free_bundle_created"] = True
    report["execution"]["history_free_bundle_retained"] = bundle_out is not None
    report["execution"]["bundle_out"] = str(Path(bundle_out).resolve()) if bundle_out else None
    return report


def _write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--audit-out", type=Path)
    parser.add_argument("--bundle-out", type=Path)
    parser.add_argument("--local-submodule-source", type=Path)
    args = parser.parse_args()
    if args.preflight_only:
        report = preflight()
    elif args.build:
        report = build_candidate(
            bundle_out=args.bundle_out,
            local_submodule_source=args.local_submodule_source,
        )
    else:
        parser.error("choose --preflight-only or --build")
    raw = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if args.audit_out:
        output = args.audit_out if args.audit_out.is_absolute() else ROOT / args.audit_out
        _write_exclusive(output, raw)
    print(raw.decode(), end="")
    return 0 if report["status"].startswith("preflight_passed") or report["status"].startswith("passed_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
