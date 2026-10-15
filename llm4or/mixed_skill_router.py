"""Fail-closed routing over public benchmark envelopes."""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath
from typing import Any


TSP_ROUTE = "tsp_constraint_xor_v2_scalable"
OR_DEBUG_ROUTE = "or_debug_typed_repair_v1"

_TSP_KEYS = {"public_text", "size", "question_sha256"}
_OR_DEBUG_KEYS = {"problem_nl", "model_file", "mps_sha256"}
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _matches_tsp(envelope: dict[str, Any]) -> bool:
    if set(envelope) != _TSP_KEYS:
        return False
    public_text = envelope["public_text"]
    size = envelope["size"]
    question_sha256 = envelope["question_sha256"]
    if not isinstance(public_text, str) or not public_text:
        return False
    if not isinstance(size, int) or isinstance(size, bool) or not 13 <= size <= 19:
        return False
    if not _is_sha256(question_sha256):
        return False
    return hashlib.sha256(public_text.encode("utf-8")).hexdigest() == question_sha256


def _matches_or_debug(envelope: dict[str, Any]) -> bool:
    if set(envelope) != _OR_DEBUG_KEYS:
        return False
    problem_nl = envelope["problem_nl"]
    model_file = envelope["model_file"]
    if not isinstance(problem_nl, str) or not problem_nl:
        return False
    if not isinstance(model_file, str) or not model_file:
        return False
    path = PurePosixPath(model_file)
    if path.is_absolute() or ".." in path.parts:
        return False
    return _is_sha256(envelope["mps_sha256"])


def route_public_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    """Return the sole matching route, otherwise abstain."""

    if not isinstance(envelope, dict):
        return {"route": None, "reason": "no_unique_public_guard"}
    matches = []
    if _matches_tsp(envelope):
        matches.append(TSP_ROUTE)
    if _matches_or_debug(envelope):
        matches.append(OR_DEBUG_ROUTE)
    if len(matches) != 1:
        return {"route": None, "reason": "no_unique_public_guard"}
    return {"route": matches[0], "reason": "unique_public_guard"}
