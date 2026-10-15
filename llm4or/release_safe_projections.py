"""Deterministic, metadata-only projections for paper evidence artifacts.

The source artifacts are intentionally richer than the public evidence surface.
These pure functions retain identities, aggregates, and content hashes while
removing task text, repair objects, evaluator-only identities, and objectives.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from typing import Any, Dict, Iterable, Mapping, Sequence


class ProjectionError(ValueError):
    """Raised when a source or projected artifact violates the public contract."""


FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "candidate",
        "corrected_repair_identity",
        "credential",
        "evaluator_answer",
        "point",
        "problem_nl",
        "public_envelope",
        "public_text",
        "reference_answer",
        "released_repair_identity",
        "repair",
        "request_body",
        "response_body",
        "solve_objective",
    }
)


def canonical_bytes(value: Any) -> bytes:
    """Return the compact canonical JSON representation used for binding hashes."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"not_canonical_json:{exc}") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectionError(f"invalid_mapping:{name}")
    return value


def _records(source: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    value = source.get("records")
    if not isinstance(value, list):
        raise ProjectionError("invalid_records")
    for index, record in enumerate(value):
        if not isinstance(record, Mapping):
            raise ProjectionError(f"invalid_record:{index}")
    return value


def _required(record: Mapping[str, Any], key: str, identity: Any = None) -> Any:
    if key not in record:
        suffix = "" if identity is None else f":{identity}"
        raise ProjectionError(f"missing_required:{key}{suffix}")
    return record[key]


def _unique(records: Iterable[Mapping[str, Any]], key: str) -> None:
    seen = set()
    for index, record in enumerate(records):
        identity = _required(record, key, index)
        if not isinstance(identity, str) or not identity:
            raise ProjectionError(f"invalid_identity:{key}:{index}")
        if identity in seen:
            raise ProjectionError(f"duplicate_identity:{identity}")
        seen.add(identity)


def _privacy() -> Dict[str, bool]:
    return {
        "contains_credentials": False,
        "contains_evaluator_answers": False,
        "contains_problem_text": False,
        "contains_repair_identity": False,
        "contains_repair_object": False,
        "contains_request_or_response_body": False,
        "contains_solver_objective_or_point": False,
    }


def validate_public_projection(value: Any) -> None:
    """Reject forbidden keys anywhere in a proposed public projection."""

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if not isinstance(key, str):
                    raise ProjectionError("non_string_key")
                if key.lower() in FORBIDDEN_KEYS:
                    raise ProjectionError(f"forbidden_key:{key}")
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    canonical_bytes(value)
    visit(value)


def _base(schema: str, raw: bytes) -> Dict[str, Any]:
    if not isinstance(raw, bytes):
        raise ProjectionError("invalid_source_bytes")
    return {
        "schema": schema,
        "source_bytes": len(raw),
        "source_sha256": _sha256(raw),
        "privacy": _privacy(),
    }


def project_mixed_bundle(source: Mapping[str, Any], raw: bytes) -> Dict[str, Any]:
    source = _mapping(source, "source")
    records = _records(source)
    _unique(records, "record_id")
    projected = _base("llm4or-release-mixed-bundle-projection-v1", raw)
    projected.update(
        {
            "source_schema": _required(source, "schema"),
            "counts": dict(_mapping(_required(source, "counts"), "counts")),
            "custody": _required(source, "custody"),
            "mixed_order_sha256": _required(source, "mixed_order_sha256"),
            "upstream_source_sha256": dict(
                _mapping(_required(source, "source_sha256"), "source_sha256")
            ),
            "records": [
                {
                    "record_id": _required(record, "record_id", index),
                    "source": _required(record, "source", index),
                    "public_envelope_sha256": _sha256(
                        canonical_bytes(_required(record, "public_envelope", index))
                    ),
                }
                for index, record in enumerate(records)
            ],
        }
    )
    if projected["counts"].get("total") != len(records):
        raise ProjectionError("count_mismatch:total")
    validate_public_projection(projected)
    return projected
def _evaluation_endpoint(endpoint: Any, identity: str) -> Dict[str, Any]:
    endpoint = _mapping(endpoint, identity)
    return {
        key: value
        for key, value in endpoint.items()
        if key not in {"corrected_repair_identity", "released_repair_identity"}
    }


def project_or_debug_evaluation(
    source: Mapping[str, Any], raw: bytes
) -> Dict[str, Any]:
    source = _mapping(source, "source")
    records = _records(source)
    _unique(records, "problem_id")
    projected = _base("llm4or-release-or-debug-evaluation-projection-v1", raw)
    safe_top = (
        "claim_guard",
        "comparison",
        "confirmation_inference",
        "confirmation_plan_sha256",
        "custody",
        "evaluation_plan_sha256",
        "execution",
        "method_output_sha256",
        "schema",
    )
    projected["source_metadata"] = {
        key: _required(source, key) for key in safe_top
    }
    projected["comparison"] = projected["source_metadata"]["comparison"]
    projected["confirmation_inference"] = projected["source_metadata"][
        "confirmation_inference"
    ]
    projected["records"] = [
        {
            "problem_id": _required(record, "problem_id", index),
            "shape_group": _required(record, "shape_group", index),
            "source_record_sha256": _sha256(canonical_bytes(record)),
            "static": _evaluation_endpoint(
                _required(record, "static", index), f"static:{index}"
            ),
            "evolved": _evaluation_endpoint(
                _required(record, "evolved", index), f"evolved:{index}"
            ),
        }
        for index, record in enumerate(records)
    ]
    if projected["comparison"].get("records") != len(records):
        raise ProjectionError("count_mismatch:comparison.records")
    validate_public_projection(projected)
    return projected


def _method_output(endpoint: Any, identity: str) -> Dict[str, Any]:
    endpoint = _mapping(endpoint, identity)
    safe = {
        key: value
        for key, value in endpoint.items()
        if key not in {"repair", "solve_objective"}
    }
    safe["output_sha256"] = _sha256(canonical_bytes(endpoint))
    return safe


def project_or_debug_outputs(source: Mapping[str, Any], raw: bytes) -> Dict[str, Any]:
    source = _mapping(source, "source")
    records = _records(source)
    _unique(records, "problem_id")
    projected = _base("llm4or-release-or-debug-outputs-projection-v1", raw)
    projected["source_metadata"] = {
        key: _required(source, key)
        for key in ("custody", "execution", "plan_sha256", "public_bundle_sha256", "schema")
    }
    projected["records"] = [
        {
            "problem_id": _required(record, "problem_id", index),
            "static": _method_output(
                _required(record, "static", index), f"static:{index}"
            ),
            "evolved": _method_output(
                _required(record, "evolved", index), f"evolved:{index}"
            ),
        }
        for index, record in enumerate(records)
    ]
    validate_public_projection(projected)
    return projected


def project_mixed_outputs(source: Mapping[str, Any], raw: bytes) -> Dict[str, Any]:
    source = _mapping(source, "source")
    records = _records(source)
    _unique(records, "record_id")
    route_counts: Dict[str, int] = {}
    projected_records = []
    for index, record in enumerate(records):
        route = _required(record, "route", index)
        if not isinstance(route, str) or not route:
            raise ProjectionError(f"invalid_route:{index}")
        route_counts[route] = route_counts.get(route, 0) + 1
        projected_records.append(
            {
                "record_id": _required(record, "record_id", index),
                "source": _required(record, "source", index),
                "route": route,
                "status": _required(record, "status", index),
                "output_sha256": _sha256(
                    canonical_bytes(_required(record, "output", index))
                ),
                "output_metadata": _method_output(
                    _required(record, "output", index), f"output:{index}"
                ),
            }
        )
    execution = _mapping(_required(source, "execution"), "execution")
    projected = _base("llm4or-release-mixed-outputs-projection-v1", raw)
    projected.update(
        {
            "source_metadata": {
                "bundle_sha256": _required(source, "bundle_sha256"),
                "code_sha256": _required(source, "code_sha256"),
                "execution": dict(execution),
                "schema": _required(source, "schema"),
            },
            "route_counts": dict(sorted(route_counts.items())),
            "status_counts": _required(execution, "status_counts"),
            "records": projected_records,
        }
    )
    validate_public_projection(projected)
    return projected


def project_tsp_public_input(source: Mapping[str, Any], raw: bytes) -> Dict[str, Any]:
    source = _mapping(source, "source")
    rows = source.get("rows")
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise ProjectionError("invalid_records")
    _unique(rows, "problem_id")
    records = []
    hashes_match = True
    for index, row in enumerate(rows):
        text = _required(row, "public_text", index)
        if not isinstance(text, str):
            raise ProjectionError(f"invalid_public_text:{index}")
        text_sha256 = _sha256(text.encode("utf-8"))
        question_sha256 = _required(row, "question_sha256", index)
        hashes_match = hashes_match and text_sha256 == question_sha256
        records.append(
            {
                "problem_id": _required(row, "problem_id", index),
                "size": _required(row, "size", index),
                "question_sha256": question_sha256,
                "public_text_sha256": text_sha256,
            }
        )
    projected = _base("llm4or-release-tsp-public-input-projection-v1", raw)
    projected.update(
        {
            "source_schema": _required(source, "schema"),
            "custody_boundary": _required(source, "custody_boundary"),
            "method_frozen_before_public_export": _required(
                source, "method_frozen_before_public_export"
            ),
            "method_sha256": _required(source, "method_sha256"),
            "upstream_source_sha256": _required(source, "source_sha256"),
            "split_sha256": _required(source, "split_sha256"),
            "all_question_hashes_match_text": hashes_match,
            "records": records,
        }
    )
    if not hashes_match:
        raise ProjectionError("question_text_hash_mismatch")
    validate_public_projection(projected)
    return projected


def _candidate_records(rows: Any, label: str) -> list[Dict[str, Any]]:
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise ProjectionError(f"invalid_records:{label}")
    _unique(rows, "problem_id")
    return [
        {
            "problem_id": _required(row, "problem_id", index),
            "size": _required(row, "size", index),
            "question_sha256": _required(row, "question_sha256", index),
            "candidate_sha256": _sha256(
                canonical_bytes(_required(row, "candidate", index))
            ),
        }
        for index, row in enumerate(rows)
    ]


def project_tsp_candidates(source: Mapping[str, Any], raw: bytes) -> Dict[str, Any]:
    source = _mapping(source, "source")
    static_records = _candidate_records(source.get("static_rows"), "static")
    skill_records = _candidate_records(source.get("skill_rows"), "skill")
    static_ids = {row["problem_id"] for row in static_records}
    skill_ids = {row["problem_id"] for row in skill_records}
    if static_ids != skill_ids:
        raise ProjectionError("arm_identity_mismatch")
    projected = _base("llm4or-release-tsp-candidates-projection-v1", raw)
    projected.update(
        {
            "counts": {"skill": len(skill_records), "static": len(static_records)},
            "static_records": static_records,
            "skill_records": skill_records,
        }
    )
    validate_public_projection(projected)
    return projected


def _saved_bytes(value: Any) -> bytes:
    validate_public_projection(value)
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"not_serializable:{exc}") from exc
    return (text + "\n").encode("utf-8")


def _safe_target(path: Any, repo_root: Any, create_parents: bool) -> tuple[Any, Any]:
    from pathlib import Path

    relative = Path(path)
    if relative.is_absolute():
        raise ProjectionError("absolute_path")
    if not relative.parts or any(part == ".." for part in relative.parts):
        raise ProjectionError("parent_component")
    if any(part in {"", "."} for part in relative.parts):
        raise ProjectionError("invalid_path_component")
    root = Path(repo_root).resolve(strict=True)
    if not root.is_dir():
        raise ProjectionError("invalid_repo_root")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ProjectionError(f"symlink_component:{part}")
        if current.exists():
            if not current.is_dir():
                raise ProjectionError(f"non_directory_component:{part}")
        elif create_parents:
            current.mkdir(mode=0o755)
        else:
            raise ProjectionError(f"missing_parent:{part}")
    target = current / relative.name
    if target.is_symlink():
        raise ProjectionError(f"symlink_component:{relative.name}")
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ProjectionError("root_escape") from exc
    return root, target


def publish_exclusive(
    path: Any, value: Any, repo_root: Any, *, check: bool = False
) -> str:
    """Durably publish a JSON artifact without overwriting an existing target.

    In check mode the existing file must already be byte-identical. Write mode
    reserves the terminal path before replacing that reservation with an
    fsynced exclusive temporary file.
    """

    raw = _saved_bytes(value)
    _, target = _safe_target(path, repo_root, create_parents=not check)
    digest = _sha256(raw)
    if check:
        if not target.is_file():
            raise ProjectionError("check_missing")
        if target.read_bytes() != raw:
            raise ProjectionError("check_mismatch")
        return digest
    if target.exists():
        raise ProjectionError("terminal_collision")

    parent = target.parent
    temporary = parent / f".{target.name}.tmp.{os.getpid()}.{secrets.token_hex(8)}"
    temporary_created = False
    target_reserved = False
    published = False
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
        temporary_created = True
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

        reservation = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        target_reserved = True
        os.close(reservation)
        os.replace(temporary, target)
        temporary_created = False
        published = True
        directory = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except FileExistsError as exc:
        raise ProjectionError("terminal_collision") from exc
    finally:
        if temporary_created:
            temporary.unlink(missing_ok=True)
        if target_reserved and not published:
            target.unlink(missing_ok=True)
    return digest
