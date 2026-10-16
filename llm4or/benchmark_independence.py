"""Body-free exact and shingle-overlap audits for prospective benchmarks."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import re
from typing import Any, Iterable, Sequence


class IndependenceAuditError(ValueError):
    pass


_TOKEN = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?")


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def tokens(text: str, *, template: bool) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        raise IndependenceAuditError("empty_text")
    result = _TOKEN.findall(text.lower())
    if not result:
        raise IndependenceAuditError("no_tokens")
    if template:
        result = ["<num>" if re.fullmatch(r"\d+(?:\.\d+)?", token) else token for token in result]
    return result


def normalized(text: str, *, template: bool) -> str:
    return " ".join(tokens(text, template=template))


def shingles(text: str, *, template: bool, width: int = 5) -> frozenset[tuple[str, ...]]:
    if width <= 0:
        raise IndependenceAuditError("shingle_width")
    values = tokens(text, template=template)
    if len(values) < width:
        return frozenset({tuple(values)})
    return frozenset(tuple(values[index : index + width]) for index in range(len(values) - width + 1))


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(probability * (len(ordered) - 1)))]


def audit_overlap(
    candidates: Iterable[tuple[str, str]],
    references: Iterable[tuple[str, str, str]],
    *,
    shingle_width: int = 5,
    thresholds: Sequence[float] = (0.2, 0.5, 0.8),
) -> dict[str, Any]:
    """Return aggregate overlap evidence without exposing texts or nearest identities."""

    candidate_rows = list(candidates)
    reference_rows = list(references)
    if not candidate_rows or not reference_rows:
        raise IndependenceAuditError("empty_corpus")
    if len({identity for identity, _text in candidate_rows}) != len(candidate_rows):
        raise IndependenceAuditError("duplicate_candidate_identity")
    if len({identity for identity, _kind, _text in reference_rows}) != len(reference_rows):
        raise IndependenceAuditError("duplicate_reference_identity")
    if any(not (0.0 <= value <= 1.0) for value in thresholds):
        raise IndependenceAuditError("threshold")

    result: dict[str, Any] = {}
    for template in (False, True):
        reference_hashes: set[str] = set()
        reference_sets: list[frozenset[tuple[str, ...]]] = []
        inverted: dict[tuple[str, ...], list[int]] = defaultdict(list)
        reference_kinds: list[str] = []
        reference_descriptors = []
        for index, (identity, kind, text) in enumerate(reference_rows):
            digest = sha256(normalized(text, template=template).encode("utf-8"))
            reference_hashes.add(digest)
            values = shingles(text, template=template, width=shingle_width)
            reference_sets.append(values)
            reference_kinds.append(kind)
            for value in values:
                inverted[value].append(index)
            reference_descriptors.append({"identity_sha256": sha256(identity.encode()), "kind": kind, "normalized_sha256": digest})

        exact = 0
        maxima: list[float] = []
        best_kinds: Counter[str] = Counter()
        candidate_descriptors = []
        for identity, text in candidate_rows:
            digest = sha256(normalized(text, template=template).encode("utf-8"))
            exact += int(digest in reference_hashes)
            candidate_set = shingles(text, template=template, width=shingle_width)
            intersections: Counter[int] = Counter()
            for value in candidate_set:
                intersections.update(inverted.get(value, ()))
            best = 0.0
            best_index: int | None = None
            for index, intersection in intersections.items():
                denominator = len(candidate_set) + len(reference_sets[index]) - intersection
                score = intersection / denominator if denominator else 1.0
                if score > best:
                    best, best_index = score, index
            maxima.append(best)
            if best_index is not None:
                best_kinds[reference_kinds[best_index]] += 1
            candidate_descriptors.append({"identity_sha256": sha256(identity.encode()), "normalized_sha256": digest})

        mode = "numeric_template" if template else "lexical"
        result[mode] = {
            "exact_normalized_matches": exact,
            "maximum_shingle_jaccard": {
                "min": min(maxima),
                "median": _quantile(maxima, 0.5),
                "p90": _quantile(maxima, 0.9),
                "p95": _quantile(maxima, 0.95),
                "p99": _quantile(maxima, 0.99),
                "max": max(maxima),
            },
            "candidate_counts_at_or_above_threshold": {
                format(value, ".6g"): sum(score >= value for score in maxima) for value in thresholds
            },
            "nearest_reference_kind_counts": dict(sorted(best_kinds.items())),
            "candidate_descriptor_set_sha256": sha256(canonical(sorted(candidate_descriptors, key=lambda value: value["identity_sha256"]))),
            "reference_descriptor_set_sha256": sha256(canonical(sorted(reference_descriptors, key=lambda value: value["identity_sha256"]))),
        }
    return result


__all__ = [
    "IndependenceAuditError",
    "audit_overlap",
    "canonical",
    "normalized",
    "sha256",
    "shingles",
    "tokens",
]
