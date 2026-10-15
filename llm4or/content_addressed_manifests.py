"""Strict content-addressed manifests for versioned skill libraries.

This module validates inert JSON before any referenced implementation is
imported.  It deliberately contains no dynamic import, evaluator, model, or
solver hook.  A manifest is an identity and reconstruction contract, not an
authorization to execute its closure.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, Sequence


SKILL_SCHEMA = "llm4or.skill_manifest.v1"
LIBRARY_SCHEMA = "llm4or.library_manifest.v1"
SHA256_RE = re.compile(r"[0-9a-f]{64}")
SEMVER_RE = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
)
FORBIDDEN_MANIFEST_KEYS = frozenset(
    {
        "api_key",
        "credential",
        "credentials",
        "evaluator_answer",
        "evaluator_only_answer",
        "problem_text",
        "reference_answer",
        "reference_solution",
        "request_body",
        "response_body",
        "solver_objective",
        "solver_point",
    }
)
POINTER_ONLY_KEYS = frozenset({"path", "sha256", "uri", "ref", "reference"})


class ManifestError(ValueError):
    """A manifest or referenced first-party closure violates the contract."""


def canonical_manifest_bytes(value: Any) -> bytes:
    """Return the only accepted UTF-8 representation for a manifest value."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ManifestError(f"invalid_json:{exc}") from exc


def _digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _body_without_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(child) for key, child in value.items() if key != "content_sha256"}


def attach_content_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    """Detach a JSON body and bind its digest, excluding the digest field itself."""

    if not isinstance(value, Mapping):
        raise ManifestError("manifest_mapping")
    body = _body_without_digest(value)
    detached = json.loads(canonical_manifest_bytes(body))
    detached["content_sha256"] = _digest_bytes(canonical_manifest_bytes(body))
    return json.loads(canonical_manifest_bytes(detached))


def _exact_fields(value: Any, expected: set[str], reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ManifestError(reason)
    return value


def _string(value: Any, reason: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ManifestError(reason)
    return value


def _sha256(value: Any, reason: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ManifestError(reason)
    return value


def _semver(value: Any, reason: str) -> str:
    if not isinstance(value, str) or SEMVER_RE.fullmatch(value) is None:
        raise ManifestError(reason)
    return value


def _bounded_json(value: Any, reason: str, depth: int = 0) -> Any:
    if depth > 24:
        raise ManifestError(f"{reason}:depth")
    if value is None or type(value) in (bool, int):
        return deepcopy(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ManifestError(f"{reason}:nonfinite")
        return value
    if isinstance(value, str):
        if len(value) > 100_000:
            raise ManifestError(f"{reason}:string")
        return value
    if isinstance(value, list):
        if len(value) > 10_000:
            raise ManifestError(f"{reason}:list")
        return [_bounded_json(child, reason, depth + 1) for child in value]
    if isinstance(value, Mapping):
        if len(value) > 10_000:
            raise ManifestError(f"{reason}:mapping")
        result = {}
        for key, child in value.items():
            if not isinstance(key, str) or not key or len(key) > 500:
                raise ManifestError(f"{reason}:key")
            result[key] = _bounded_json(child, reason, depth + 1)
        return result
    raise ManifestError(f"{reason}:type")


def _reject_forbidden_manifest_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str) and key.casefold() in FORBIDDEN_MANIFEST_KEYS:
                raise ManifestError(f"forbidden_manifest_key:{key}")
            _reject_forbidden_manifest_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_manifest_keys(child)


def _reject_pointer_only_semantics(payload: Mapping[str, Any]) -> None:
    for role, component in payload.items():
        if isinstance(component, Mapping) and (
            not component or set(component).issubset(POINTER_ONLY_KEYS)
        ):
            raise ManifestError(f"pointer_only_semantics:{role}")


def _relative_path(value: Any, root: Path, *, must_exist: bool) -> Path:
    text = _string(value, "invalid_path", 4096)
    pure = PurePosixPath(text)
    if pure.is_absolute():
        raise ManifestError("absolute_path")
    if not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        if ".." in pure.parts:
            raise ManifestError("parent_component")
        raise ManifestError("invalid_path_component")
    if "\\" in text:
        raise ManifestError("non_posix_path")
    root = root.resolve()
    current = root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            raise ManifestError("symlink_component")
    try:
        current.resolve(strict=must_exist).relative_to(root)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise ManifestError("root_escape_or_missing") from exc
    return current


def _closure(value: Any, root: Path, reason: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ManifestError(f"{reason}:closure")
    detached = []
    seen = set()
    for index, entry in enumerate(value):
        entry = _exact_fields(entry, {"path", "sha256"}, f"{reason}:entry_fields:{index}")
        path_text = _string(entry["path"], f"{reason}:path:{index}", 4096)
        if path_text in seen:
            raise ManifestError(f"{reason}:duplicate_path")
        seen.add(path_text)
        expected = _sha256(entry["sha256"], f"{reason}:sha256:{index}")
        path = _relative_path(path_text, root, must_exist=True)
        if not path.is_file():
            raise ManifestError(f"{reason}:not_file")
        if _digest_bytes(path.read_bytes()) != expected:
            raise ManifestError("closure_hash_mismatch")
        detached.append({"path": path_text, "sha256": expected})
    return detached


def _claim_boundary(value: Any, reason: str) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise ManifestError(reason)
    return [_string(item, reason, 2000) for item in value]


def _check_content_digest(value: Mapping[str, Any]) -> None:
    declared = _sha256(value.get("content_sha256"), "content_sha256")
    actual = _digest_bytes(canonical_manifest_bytes(_body_without_digest(value)))
    if declared != actual:
        raise ManifestError("content_digest_mismatch")


def _role(value: Any, root: Path, name: str) -> None:
    role = _exact_fields(
        value,
        {"interface", "semantic_version", "implementation_closure"},
        f"{name}_fields",
    )
    _string(role["interface"], f"{name}_interface", 300)
    _semver(role["semantic_version"], f"{name}_semantic_version")
    _closure(role["implementation_closure"], root, name)


def validate_skill_manifest(value: Any, root: Path) -> dict[str, Any]:
    """Validate a complete skill manifest and every first-party closure hash."""

    fields = {
        "schema",
        "skill_id",
        "family",
        "semantic_version",
        "guard",
        "extractor",
        "transform",
        "semantic_verifier",
        "resource_checker",
        "provenance",
        "fallback_contract",
        "semantic_payload",
        "implementation_closure",
        "claim_boundary",
        "content_sha256",
    }
    manifest = _exact_fields(value, fields, "skill_fields")
    if manifest["schema"] != SKILL_SCHEMA:
        raise ManifestError("skill_schema")
    _reject_forbidden_manifest_keys(manifest)
    _string(manifest["skill_id"], "skill_id", 200)
    _string(manifest["family"], "family", 200)
    _semver(manifest["semantic_version"], "skill_semantic_version")
    _check_content_digest(manifest)
    for name in ("guard", "extractor", "transform", "semantic_verifier", "resource_checker"):
        _role(manifest[name], root, name)
    provenance = _exact_fields(
        manifest["provenance"],
        {
            "authorship_mode",
            "parent_proposal_sha256",
            "construction_split_sha256",
            "verifier_sha256",
            "decision_sha256",
        },
        "provenance_fields",
    )
    _string(provenance["authorship_mode"], "authorship_mode", 100)
    _sha256(provenance["parent_proposal_sha256"], "parent_proposal_sha256", nullable=True)
    for field in ("construction_split_sha256", "verifier_sha256", "decision_sha256"):
        _sha256(provenance[field], field)
    fallback = _exact_fields(
        manifest["fallback_contract"],
        {"target", "zero_match", "multiple_match"},
        "fallback_contract_fields",
    )
    for field in fallback:
        _string(fallback[field], f"fallback_{field}", 500)
    payload = _exact_fields(
        manifest["semantic_payload"],
        {"guard", "extractor", "transform", "semantic_verifier", "resource_checker", "fallback"},
        "semantic_payload_fields",
    )
    _bounded_json(payload, "semantic_payload")
    _reject_pointer_only_semantics(payload)
    _closure(manifest["implementation_closure"], root, "implementation")
    _claim_boundary(manifest["claim_boundary"], "claim_boundary")
    return json.loads(canonical_manifest_bytes(manifest))


def _ledger_refs(value: Any, root: Path, name: str) -> None:
    if not isinstance(value, list) or len(value) > 100_000:
        raise ManifestError(f"{name}_list")
    seen = set()
    for index, entry in enumerate(value):
        entry = _exact_fields(entry, {"path", "sha256"}, f"{name}_fields:{index}")
        path = _string(entry["path"], f"{name}_path:{index}", 4096)
        if path in seen:
            raise ManifestError(f"{name}_duplicate")
        seen.add(path)
        expected = _sha256(entry["sha256"], f"{name}_sha256:{index}")
        resolved = _relative_path(path, root, must_exist=True)
        if not resolved.is_file() or _digest_bytes(resolved.read_bytes()) != expected:
            raise ManifestError(f"ledger_hash_mismatch:{name}:{index}")


def validate_library_manifest(
    value: Any,
    root: Path,
    skill_manifests: Mapping[str, Mapping[str, Any]],
    *,
    ancestor_manifests: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate a library identity and its links to already validated skills."""

    fields = {
        "schema",
        "library_version",
        "parent_library_sha256",
        "rollback_library_sha256",
        "skills",
        "router",
        "verifier_closure",
        "endpoint_identities",
        "promotion_decision",
        "accepted_ledger_refs",
        "rejected_ledger_refs",
        "release_boundary",
        "claim_boundary",
        "content_sha256",
    }
    manifest = _exact_fields(value, fields, "library_fields")
    if manifest["schema"] != LIBRARY_SCHEMA:
        raise ManifestError("library_schema")
    _reject_forbidden_manifest_keys(manifest)
    _string(manifest["library_version"], "library_version", 300)
    _check_content_digest(manifest)
    parent = _sha256(manifest["parent_library_sha256"], "parent_library_sha256", nullable=True)
    rollback = _sha256(manifest["rollback_library_sha256"], "rollback_library_sha256", nullable=True)
    if (parent is None) != (rollback is None):
        raise ManifestError("successor_rollback")
    if parent is not None:
        if ancestor_manifests is None:
            raise ManifestError("ancestor_manifests_required")
        for role, digest in (("parent", parent), ("rollback", rollback)):
            ancestor = ancestor_manifests.get(digest)
            if not isinstance(ancestor, Mapping):
                raise ManifestError(f"missing_{role}_manifest")
            if ancestor.get("schema") != LIBRARY_SCHEMA:
                raise ManifestError(f"{role}_schema")
            _check_content_digest(ancestor)
            if ancestor.get("content_sha256") != digest:
                raise ManifestError(f"{role}_binding")

    skills = manifest["skills"]
    if not isinstance(skills, list) or not skills:
        raise ManifestError("skills_list")
    expected_order = sorted(skills, key=lambda item: (item.get("family", ""), item.get("skill_id", "")))
    if skills != expected_order:
        raise ManifestError("skills_not_sorted")
    identities = set()
    for index, reference in enumerate(skills):
        reference = _exact_fields(
            reference,
            {"family", "skill_id", "manifest_sha256", "path"},
            f"skill_reference_fields:{index}",
        )
        identity = (
            _string(reference["family"], f"skill_family:{index}", 200),
            _string(reference["skill_id"], f"skill_id:{index}", 200),
        )
        if identity in identities:
            raise ManifestError("duplicate_skill_identity")
        identities.add(identity)
        digest = _sha256(reference["manifest_sha256"], f"skill_digest:{index}")
        _relative_path(reference["path"], root, must_exist=False)
        bound = skill_manifests.get(digest)
        if bound is None:
            raise ManifestError("missing_skill_manifest")
        validate_skill_manifest(bound, root)
        if bound.get("content_sha256") != digest or (bound.get("family"), bound.get("skill_id")) != identity:
            raise ManifestError("skill_manifest_binding")

    router = _exact_fields(
        manifest["router"],
        {
            "interface",
            "semantic_version",
            "implementation_closure",
            "semantic_payload",
            "exact_match_policy",
            "zero_match_fallback",
            "multiple_match_fallback",
        },
        "router_fields",
    )
    _string(router["interface"], "router_interface", 300)
    _semver(router["semantic_version"], "router_semantic_version")
    _closure(router["implementation_closure"], root, "router")
    _bounded_json(router["semantic_payload"], "router_semantic_payload")
    if router["exact_match_policy"] != "exactly_one":
        raise ManifestError("router_exactly_one")
    _string(router["zero_match_fallback"], "router_zero_fallback", 500)
    _string(router["multiple_match_fallback"], "router_multiple_fallback", 500)
    _closure(manifest["verifier_closure"], root, "verifier")

    endpoints = manifest["endpoint_identities"]
    if not isinstance(endpoints, list) or not endpoints:
        raise ManifestError("endpoint_identities")
    endpoint_ids = set()
    for index, endpoint in enumerate(endpoints):
        endpoint = _exact_fields(
            endpoint,
            {"endpoint_id", "schema", "plan_sha256", "evidence_sha256"},
            f"endpoint_fields:{index}",
        )
        endpoint_id = _string(endpoint["endpoint_id"], f"endpoint_id:{index}", 300)
        if endpoint_id in endpoint_ids:
            raise ManifestError("duplicate_endpoint")
        endpoint_ids.add(endpoint_id)
        _string(endpoint["schema"], f"endpoint_schema:{index}", 300)
        _sha256(endpoint["plan_sha256"], f"endpoint_plan:{index}")
        _sha256(endpoint["evidence_sha256"], f"endpoint_evidence:{index}")

    decision = _exact_fields(
        manifest["promotion_decision"], {"status", "decision_sha256"}, "promotion_decision_fields"
    )
    if decision["status"] not in {"genesis", "accepted"}:
        raise ManifestError("promotion_status")
    if parent is None and decision["status"] != "genesis":
        raise ManifestError("genesis_status")
    if parent is not None and decision["status"] != "accepted":
        raise ManifestError("successor_status")
    _sha256(decision["decision_sha256"], "promotion_decision_sha256")
    _ledger_refs(manifest["accepted_ledger_refs"], root, "accepted_ledger_refs")
    _ledger_refs(manifest["rejected_ledger_refs"], root, "rejected_ledger_refs")
    _claim_boundary(manifest["release_boundary"], "release_boundary")
    _claim_boundary(manifest["claim_boundary"], "claim_boundary")
    return json.loads(canonical_manifest_bytes(manifest))


def _verify_bound_skill_files(
    manifest: Mapping[str, Any],
    root: Path,
    skill_manifests: Mapping[str, Mapping[str, Any]],
) -> None:
    for index, reference in enumerate(manifest["skills"]):
        digest = reference["manifest_sha256"]
        path = _relative_path(reference["path"], root, must_exist=True)
        if path.name != f"{digest}.json":
            raise ManifestError(f"bound_skill_filename:{index}")
        raw = path.read_bytes()
        bound = skill_manifests[digest]
        if raw != canonical_manifest_bytes(bound):
            raise ManifestError(f"bound_skill_bytes:{index}")


def _prefix_free_envelope(payloads: Sequence[Any]) -> bytes:
    result = bytearray(b"LLM4OR-KNOWLEDGE-ENVELOPE-V1\x00")
    result.extend(len(payloads).to_bytes(8, "big"))
    for payload in payloads:
        raw = canonical_manifest_bytes(payload)
        result.extend(len(raw).to_bytes(8, "big"))
        result.extend(raw)
    return bytes(result)


def operational_description_length_bits(
    skill_manifests: Sequence[Mapping[str, Any]], router: Mapping[str, Any]
) -> int:
    """Measure only semantic knowledge, excluding paths, hashes and outcomes."""

    if not isinstance(skill_manifests, Sequence) or not skill_manifests:
        raise ManifestError("description_skills")
    ordered = sorted(
        skill_manifests,
        key=lambda skill: _sha256(skill.get("content_sha256"), "description_skill_digest"),
    )
    payloads = [_bounded_json(skill.get("semantic_payload"), "description_payload") for skill in ordered]
    if not isinstance(router, Mapping) or "semantic_payload" not in router:
        raise ManifestError("description_router")
    payloads.append(_bounded_json(router["semantic_payload"], "description_router_payload"))
    return 8 * len(_prefix_free_envelope(payloads))


def _parse_strict_json(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError("invalid_utf8") from exc

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ManifestError("duplicate_json_key")
            result[key] = value
        return result

    def constant(_value):
        raise ManifestError("nonfinite_json")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except ManifestError:
        raise
    except (ValueError, RecursionError) as exc:
        raise ManifestError("invalid_json") from exc


def _ensure_directory(relative: Path, root: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ManifestError("output_directory_path")
    root = root.resolve()
    current = root
    for part in relative.parts:
        if part in {"", "."}:
            raise ManifestError("output_directory_component")
        current = current / part
        if current.is_symlink():
            raise ManifestError("symlink_component")
        if current.exists() and not current.is_dir():
            raise ManifestError("output_directory_not_directory")
        if not current.exists():
            current.mkdir(mode=0o755)
            parent_fd = os.open(current.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
    return current


def publish_content_addressed_manifest(
    manifest: Mapping[str, Any],
    output_directory: Path,
    root: Path,
    *,
    kind: str,
    skill_manifests: Mapping[str, Mapping[str, Any]] | None = None,
    ancestor_manifests: Mapping[str, Mapping[str, Any]] | None = None,
) -> Path:
    """Publish once under ``<content_sha256>.json`` with durable ownership.

    A crash-created partial terminal remains an explicit collision and must be
    removed only by an external, audited abandoned-file procedure.
    """

    root = Path(root)
    if kind == "skill":
        validate_skill_manifest(manifest, root)
    elif kind == "library":
        if skill_manifests is None:
            raise ManifestError("library_publication_requires_bound_skill_validation")
        validate_library_manifest(
            manifest,
            root,
            skill_manifests,
            ancestor_manifests=ancestor_manifests,
        )
        _verify_bound_skill_files(manifest, root, skill_manifests)
    else:
        raise ManifestError("manifest_kind")
    digest = _sha256(manifest.get("content_sha256"), "content_sha256")
    directory = _ensure_directory(Path(output_directory), root)
    path = directory / f"{digest}.json"
    raw = canonical_manifest_bytes(manifest)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o644)
    except FileExistsError as exc:
        raise ManifestError("terminal_collision") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # The terminal is deliberately retained as an abandoned reservation.
        raise
    directory_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return path.relative_to(root.resolve())


def load_content_addressed_manifest(
    relative_path: Path,
    root: Path,
    *,
    kind: str,
    skill_manifests: Mapping[str, Mapping[str, Any]] | None = None,
    ancestor_manifests: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Strictly load canonical bytes and validate filename, digest and closure."""

    path = _relative_path(Path(relative_path).as_posix(), Path(root), must_exist=True)
    raw = path.read_bytes()
    value = _parse_strict_json(raw)
    if raw != canonical_manifest_bytes(value):
        raise ManifestError("noncanonical_bytes")
    if not isinstance(value, Mapping):
        raise ManifestError("manifest_mapping")
    declared = _sha256(value.get("content_sha256"), "content_sha256")
    if path.name != f"{declared}.json":
        raise ManifestError("filename_digest_mismatch")
    if kind == "skill":
        return validate_skill_manifest(value, Path(root))
    if kind == "library":
        if skill_manifests is None:
            raise ManifestError("library_skill_manifests_required")
        validated = validate_library_manifest(
            value,
            Path(root),
            skill_manifests,
            ancestor_manifests=ancestor_manifests,
        )
        _verify_bound_skill_files(validated, Path(root), skill_manifests)
        return validated
    raise ManifestError("manifest_kind")
