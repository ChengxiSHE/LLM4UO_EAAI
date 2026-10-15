#!/usr/bin/env python3
"""Classify the candidate release tree without inferring or granting rights."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = (
    "scripts/audit_release_rights_inventory.py",
    "tests/test_release_rights_inventory.py",
    ".gitmodules",
    "experiments/restricted_source_exclusion_audit_20261015.json",
)
ROOT_LICENSE_NAMES = frozenset({"LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "NOTICE"})
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


def _run(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )


def _tracked(relative: str) -> bool:
    return _run("ls-files", "--error-unmatch", "--", relative).returncode == 0


def _git_text(*arguments: str) -> str:
    completed = _run(*arguments)
    if completed.returncode != 0:
        raise RuntimeError("release_rights_git_identity_unavailable")
    return completed.stdout.decode("utf-8").strip()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def classify(path: str, mode: str) -> str:
    if mode == "160000":
        return "external_submodule"
    if path.startswith("data/manifests/"):
        return "source_metadata"
    if path.startswith("manuscript/figures/") or path.startswith("manuscript/source_data/"):
        return "generated_manuscript_artifact"
    if mode == "120000":
        return "symlink_requires_review"
    return "first_party_candidate"


def _tree_entries(source_commit: str) -> list[dict[str, str]]:
    completed = _run("ls-tree", "-r", "-z", "--full-tree", source_commit)
    if completed.returncode != 0:
        raise RuntimeError("release_rights_git_tree_unavailable")
    entries = []
    for item in completed.stdout.split(b"\0"):
        if not item:
            continue
        header, raw_path = item.split(b"\t", 1)
        mode, object_type, oid = header.decode("ascii").split()
        if object_type not in {"blob", "commit"}:
            raise RuntimeError("release_rights_unexpected_git_object")
        path = raw_path.decode("utf-8")
        entries.append({"path": path, "mode": mode, "oid": oid})
    return sorted(entries, key=lambda item: item["path"])


def preflight() -> dict:
    paths = [
        {"path": path, "exists": (ROOT / path).exists(), "tracked": _tracked(path)}
        for path in REQUIRED_PATHS
    ]
    passed = all(row["exists"] and row["tracked"] for row in paths)
    return {
        "schema_version": "release-rights-inventory-v1",
        "status": "preflight_passed" if passed else "preflight_failed",
        "required_paths": paths,
        "all_required_paths_tracked": all(row["tracked"] for row in paths),
        "decision": {
            "rights_clearance_claimed": False,
            "license_selected": False,
            "public_release_authorized": False,
        },
        "execution": {
            "file_contents_read": False,
            "api_or_model_calls": 0,
            "network_calls": 0,
            "credentials_read": False,
            "public_push": False,
        },
    }


def build_inventory(source_commit: str = "HEAD") -> dict:
    report = preflight()
    if report["status"] != "preflight_passed":
        report["status"] = "failed_preflight"
        return report
    resolved_commit = _git_text("rev-parse", source_commit)
    resolved_tree = _git_text("rev-parse", f"{resolved_commit}^{{tree}}")
    entries = _tree_entries(resolved_commit)
    classes: dict[str, list[str]] = {}
    for entry in entries:
        classes.setdefault(classify(entry["path"], entry["mode"]), []).append(entry["path"])
    class_counts = {name: len(paths) for name, paths in sorted(classes.items())}
    top_levels = Counter(path.split("/", 1)[0] for path in (entry["path"] for entry in entries))
    paths = {entry["path"] for entry in entries}
    restricted = sorted(paths & RESTRICTED_PATHS)
    private = sorted(path for path in paths if "/private/" in "/" + path)
    licenses = sorted(paths & ROOT_LICENSE_NAMES)
    symlinks = classes.get("symlink_requires_review", [])
    submodules = classes.get("external_submodule", [])
    valid = not restricted and not private and not symlinks and submodules == ["vendor/solver-in-the-loop"]
    report.update(
        {
            "status": "inventory_closed_rights_decisions_open" if valid else "inventory_requires_path_remediation",
            "source": {
                "commit": resolved_commit,
                "tree": resolved_tree,
                "scope": "git_tree_at_source_commit",
            },
            "tree": {
                "tracked_entries": len(entries),
                "tree_entry_identity_sha256": _sha256_bytes(
                    "\n".join(f"{row['mode']} {row['oid']} {row['path']}" for row in entries).encode()
                ),
                "path_set_sha256": _sha256_bytes(
                    ("\n".join(row["path"] for row in entries) + "\n").encode()
                ),
                "top_level_counts": dict(sorted(top_levels.items())),
                "class_counts": class_counts,
            },
            "external_submodules": submodules,
            "source_metadata_paths": classes.get("source_metadata", []),
            "generated_manuscript_artifact_count": len(classes.get("generated_manuscript_artifact", [])),
            "first_party_candidate_count": len(classes.get("first_party_candidate", [])),
            "restricted_paths_tracked": restricted,
            "private_paths_tracked": private,
            "symlinks_requiring_review": symlinks,
            "root_license_paths": licenses,
            "remaining_decisions": [
                "Authors must confirm ownership or permission for every first_party_candidate path.",
                "Authors must select a root license and approve a third-party attribution/NOTICE policy.",
                "Each source_metadata manifest must retain source-specific provenance and must not grant rights to upstream content.",
                "The solver-in-the-loop gitlink stays external under its own upstream license and is not vendored into the main snapshot.",
                "Generated manuscript artifacts inherit the rights and disclosure constraints of their source data and code.",
            ],
            "boundary": (
                "This inventory proves path separation and identifies the decisions. "
                "It does not infer authorship, ownership, permission, license compatibility, "
                "or redistribution rights from repository location."
            ),
        }
    )
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
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-commit", default="HEAD")
    args = parser.parse_args()
    if args.preflight_only:
        report = preflight()
    elif args.audit:
        report = build_inventory(args.source_commit)
    else:
        parser.error("choose --preflight-only or --audit")
    raw = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        _write_exclusive(output, raw)
    print(raw.decode(), end="")
    return 0 if report["status"] in {"preflight_passed", "inventory_closed_rights_decisions_open"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
