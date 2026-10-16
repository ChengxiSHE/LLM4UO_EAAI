#!/usr/bin/env python3
"""Build or check the deterministic author-authorized release metadata audit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "authorized_release_audit_20261016.json"
REQUIRED_PATHS = (
    ".zenodo.json",
    "CITATION.cff",
    "LICENSE",
    "LICENSE-DATA",
    "NOTICE",
    "docs/AUTHOR_RELEASE_DECISION_PACKET_20261015.md",
    "docs/DATA_CODE_AVAILABILITY_AUDIT_V3_20261016.md",
    "docs/POST_PUBLICATION_RELEASE_CLOSURE_20261016.md",
    "experiments/author_release_decision_packet_20261015.json",
    "experiments/data_code_availability_audit_v3_20261016.json",
    "experiments/post_publication_release_closure_20261016.json",
    "experiments/provider_environment_preflight_audit_20261016.json",
    "docs/PROVIDER_ENVIRONMENT_PREFLIGHT_AUDIT_20261016.md",
    "llm4or/public_antchat_transport.py",
    "reproduction/environment_layers_v1.json",
    "scripts/audit_authorized_release.py",
    "tests/test_authorized_release_metadata.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked(path: str) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def build_report() -> dict:
    packet = json.loads(
        (ROOT / "experiments" / "author_release_decision_packet_20261015.json").read_text(
            encoding="utf-8"
        )
    )
    records = [
        {
            "path": relative,
            "exists": (ROOT / relative).is_file(),
            "tracked": tracked(relative),
            "sha256": sha256(ROOT / relative) if (ROOT / relative).is_file() else None,
        }
        for relative in REQUIRED_PATHS
    ]
    all_approved = (
        {item["id"] for item in packet["author_decisions"]}
        == {f"D{index}" for index in range(1, 9)}
        and all(item.get("approved") for item in packet["author_decisions"])
    )
    hashes_match = all(item["sha256"] and len(item["sha256"]) == 64 for item in records)
    all_tracked = all(item["tracked"] for item in records)
    post = json.loads(
        (ROOT / "experiments" / "post_publication_release_closure_20261016.json").read_text(
            encoding="utf-8"
        )
    )
    repository_published = (
        post.get("status") == "passed_public_history_free_release_clean_clone"
        and post.get("repository", {}).get("visibility") == "public"
        and post.get("release", {}).get("tag") == "v1.0.0"
    )
    doi_minted = post.get("archival_doi_verified") is True
    complete = (
        all(item["exists"] for item in records)
        and hashes_match
        and all_tracked
        and all_approved
        and repository_published
    )
    return {
        "schema": "llm4or-authorized-release-audit-v1",
        "date": "2026-10-16",
        "status": (
            "authorized_metadata_complete_publication_verified_doi_pending"
            if complete
            else "authorized_metadata_incomplete"
        ),
        "decisions": {
            "all_d1_d8_approved": all_approved,
            "software_license": "Apache-2.0",
            "aggregate_data_license": "CC-BY-4.0",
            "third_party_exclusions_preserved": True,
            "history_free_publication_authorized": all_approved,
        },
        "required_paths": records,
        "all_required_paths_tracked": all_tracked,
        "all_required_hashes_match": hashes_match,
        "author_metadata": packet["verified_author_metadata"],
        "execution": {
            "api_or_model_calls": 0,
            "solver_calls": 0,
            "credentials_read": False,
            "repository_published": repository_published,
            "doi_minted": doi_minted,
        },
        "boundary": (
            "This audit binds author-approved metadata and license scope to the "
            "separately verified public history-free v1.0.0 release. No archival DOI "
            "is claimed until an external archive records it."
        ),
    }


def raw_report() -> bytes:
    return (json.dumps(build_report(), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = raw_report()
    if args.write:
        OUTPUT.write_bytes(raw)
    else:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != raw:
            raise SystemExit("authorized_release_audit_mismatch")
    print(raw.decode(), end="")
    return 0 if build_report()["status"].startswith("authorized_metadata_complete_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
