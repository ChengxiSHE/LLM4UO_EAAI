"""Verify a frozen plan against current files or exact bytes retained in Git history."""

from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess
from typing import Any, Callable

from .schema import canonical


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _historical_blob_matches(root: Path, relative: str, expected: str) -> bool:
    history = subprocess.run(
        ["git", "log", "--all", "--format=%H", "--", relative],
        cwd=root, capture_output=True, check=True, text=True,
    ).stdout.splitlines()
    for commit in history:
        shown = subprocess.run(
            ["git", "show", f"{commit}:{relative}"], cwd=root,
            capture_output=True, check=False,
        )
        if shown.returncode == 0 and _sha(shown.stdout) == expected:
            return True
    return False


def verify_plan_reconstruction(
    root: str | Path, plan: dict[str, Any], rebuild: Callable[[Path], dict[str, Any]],
) -> dict[str, Any]:
    root = Path(root).resolve(); current = rebuild(root)
    if canonical(current) == canonical(plan):
        return {"mode": "current_files", "historical_frozen_files": []}
    expected_files = plan.get("frozen_files"); current_files = current.get("frozen_files")
    if not isinstance(expected_files, dict) or set(expected_files) != set(current_files or {}):
        raise ValueError("plan_reconstruction")
    normalized = deepcopy(current); normalized["frozen_files"] = deepcopy(expected_files)
    if canonical(normalized) != canonical(plan):
        raise ValueError("plan_reconstruction")
    historical = []
    for relative, expected in sorted(expected_files.items()):
        path = root / relative
        if path.is_file() and _sha(path.read_bytes()) == expected:
            continue
        if not _historical_blob_matches(root, relative, expected):
            raise ValueError("frozen_file_not_reachable:" + relative)
        historical.append(relative)
    return {"mode": "git_retained_frozen_files", "historical_frozen_files": historical}


__all__ = ["verify_plan_reconstruction"]
