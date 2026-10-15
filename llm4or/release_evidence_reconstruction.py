"""Credential-free Layer-A reconstruction of the public paper evidence chain."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping


EXPECTED_PAPER_PATHS = 81
EXPECTED_ASSERTIONS = 456
EXPECTED_BOUNDARIES = 17
EXPECTED_GOAL_REFERENCES = 173
EXPECTED_GOAL_UNIQUE_PATHS = 158
EXPECTED_CITATIONS = 18
EXPECTED_LIBRARY_IDENTITIES = 2985
PINNED_SOLVER_SUBMODULE = "c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010"

RESTRICTED_SOURCES = frozenset(
    {
        "experiments/mixed_skill_confirmation_bundle_20261014.json",
        "results/or_debug_confirmation_evaluation_20261014.json",
        "results/or_debug_confirmation_method_outputs_20261014.json",
        "results/mixed_skill_confirmation_outputs_20261014.json",
        "results/private/tsp_constraint_confirmation_candidates_20261014.json",
        "results/private/tsp_constraint_confirmation_public_20261014.json",
    }
)


class ReconstructionError(ValueError):
    """Layer-A evidence cannot be reconstructed exactly."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_path_hashes(root: Path, expected: Mapping[str, str]) -> None:
    """Fail closed unless every repository-relative file has the exact digest."""

    root = Path(root)
    for relative, digest in expected.items():
        path = root / relative
        observed = _sha256(path) if path.is_file() else None
        if observed != digest:
            raise ReconstructionError(f"path_hash_mismatch:{relative}")


def _collect_paper_paths(manifest: Any) -> dict[str, str]:
    pairs: list[tuple[str, str]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("sha256"), str):
                for name in ("path", "artifact", "file"):
                    if isinstance(node.get(name), str):
                        pairs.append((node[name], node["sha256"]))
                        break
            for key, value in node.items():
                if key.endswith("_sha256") and isinstance(value, str):
                    source_key = key[:-7]
                    if isinstance(node.get(source_key), str):
                        pairs.append((node[source_key], value))
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(manifest)
    result: dict[str, str] = {}
    for path, digest in pairs:
        if path in result and result[path] != digest:
            raise ReconstructionError(f"conflicting_path_hash:{path}")
        result[path] = digest
    return result


def _leaf_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_leaf_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(_leaf_count(child) for child in value)
    return 1


def _assertion_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(
            _leaf_count(child) if key == "assertions" else _assertion_count(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return sum(_assertion_count(child) for child in value)
    return 0


def _run_git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C"},
    )
    return completed.stdout


def _citation_report(root: Path) -> dict[str, Any]:
    text = (root / "manuscript/MANUSCRIPT_DRAFT.md").read_text(encoding="utf-8")
    text += "\n" + (root / "manuscript/SUPPLEMENTARY_THEORY.md").read_text(
        encoding="utf-8"
    )
    cited = set(re.findall(r"@([A-Za-z0-9_:-]+)", text))
    bibliography = (root / "manuscript/references.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\{\s*([^,\s]+)", bibliography))
    return {
        "cited_keys": len(cited),
        "bibliography_keys": len(keys),
        "missing": sorted(cited - keys),
        "uncited": sorted(keys - cited),
    }


def build_release_evidence_report(root: Path) -> dict[str, Any]:
    """Recompute the public evidence integrity result without credentials."""

    root = Path(root).resolve()
    paper = json.loads(
        (root / "experiments/paper_evidence_manifest_20261015.json").read_text(
            encoding="utf-8"
        )
    )
    paper_paths = _collect_paper_paths(paper)
    if len(paper_paths) != EXPECTED_PAPER_PATHS:
        raise ReconstructionError("paper_path_count")
    verify_path_hashes(root, paper_paths)
    assertions = _assertion_count(paper)
    boundaries = len(paper.get("global_claim_boundaries", []))
    if assertions != EXPECTED_ASSERTIONS or boundaries != EXPECTED_BOUNDARIES:
        raise ReconstructionError("paper_assertion_or_boundary_count")

    goal = json.loads(
        (root / "experiments/goal_completion_audit_20261015.json").read_text(
            encoding="utf-8"
        )
    )
    references = [
        item
        for requirement in goal["requirements"]
        for item in requirement.get("evidence", [])
    ]
    goal_paths: dict[str, str] = {}
    for item in references:
        path, digest = item["path"], item["sha256"]
        if path in goal_paths and goal_paths[path] != digest:
            raise ReconstructionError(f"goal_conflicting_hash:{path}")
        goal_paths[path] = digest
    if (
        len(references) != EXPECTED_GOAL_REFERENCES
        or len(goal_paths) != EXPECTED_GOAL_UNIQUE_PATHS
    ):
        raise ReconstructionError("goal_reference_count")
    verify_path_hashes(root, goal_paths)

    citations = _citation_report(root)
    if (
        citations["cited_keys"] != EXPECTED_CITATIONS
        or citations["bibliography_keys"] != EXPECTED_CITATIONS
        or citations["missing"]
        or citations["uncited"]
    ):
        raise ReconstructionError("citation_closure")

    tracked = set(_run_git(root, "ls-files").splitlines())
    restricted_tracked = sorted(RESTRICTED_SOURCES & tracked)
    if restricted_tracked:
        raise ReconstructionError("restricted_source_tracked")
    submodule = _run_git(root, "submodule", "status", "--recursive").strip("\n")
    if not submodule.startswith(f" {PINNED_SOLVER_SUBMODULE} vendor/solver-in-the-loop"):
        raise ReconstructionError("solver_submodule_identity")

    # Imported lazily so this verifier never imports a provider or solver path.
    from scripts.audit_current_library_reconstruction import (
        build_reconstruction_audit,
    )

    library = build_reconstruction_audit(root)
    if (
        not library["manifest_validation"]["passed"]
        or not library["mixed_identity"]["exact_identity_pass"]
        or library["mixed_identity"]["totals"]["exact_matches"]
        != EXPECTED_LIBRARY_IDENTITIES
    ):
        raise ReconstructionError("current_library_reconstruction")

    return {
        "schema": "llm4or-release-evidence-reconstruction-v1",
        "status": "passed_credential_free_layer_a",
        "paper_manifest": {
            "path_hashes": len(paper_paths),
            "path_hash_mismatches": 0,
            "assertions": assertions,
            "boundaries": boundaries,
        },
        "goal_evidence": {
            "references": len(references),
            "unique_paths": len(goal_paths),
            "mismatches": 0,
        },
        "citations": citations,
        "restricted_sources": {
            "declared": len(RESTRICTED_SOURCES),
            "tracked": restricted_tracked,
        },
        "solver_submodule": {
            "commit": PINNED_SOLVER_SUBMODULE,
            "path": "vendor/solver-in-the-loop",
            "initialized": True,
        },
        "current_library": {
            "library_sha256": library["manifest_validation"]["library_sha256"],
            "skill_sha256": library["manifest_validation"]["skill_sha256"],
            "operational_description_length_bits": library["manifest_validation"][
                "operational_description_length_bits"
            ],
            "identity_reconstruction_passed": library["mixed_identity"][
                "exact_identity_pass"
            ],
            "exact_identities": library["mixed_identity"]["totals"][
                "exact_matches"
            ],
        },
        "claim_boundary": {
            "solver_runtime_reexecuted": False,
            "provider_reexecuted": False,
            "figures_regenerated": False,
            "full_clean_clone_claimed": False,
            "allowed_claim": "The public evidence integrity layer is reconstructable from a credential-free recursive clone.",
        },
        "safety": {
            "api_or_model_calls": 0,
            "solver_calls": 0,
            "native_evaluator_calls": 0,
            "vm_calls": 0,
            "environment_values_read": False,
            "restricted_bodies_read": False,
            "evaluator_only_answers_read": False,
            "credentials_read": False,
        },
    }
