"""Fail-closed custody for the fixed RetailOpt-190 source snapshot.

The public audit emitted by this module contains hashes and aggregate counts only.
Problem statements, structured data, source identities and evaluator targets stay
inside the ignored custody directory.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

from .atomic_publisher import PublicationResult, publish_bundle


class RetailOptCustodyError(ValueError):
    """The fixed source violates the declared custody contract."""


@dataclass(frozen=True)
class SourceIdentity:
    commit: str
    dataset_sha256: str

    def __post_init__(self) -> None:
        if len(self.commit) != 40 or any(c not in "0123456789abcdef" for c in self.commit):
            raise RetailOptCustodyError("invalid_source_commit")
        if len(self.dataset_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.dataset_sha256):
            raise RetailOptCustodyError("invalid_dataset_sha256")


@dataclass(frozen=True)
class CustodyBundle:
    entries: Mapping[str, bytes]
    public_audit: Mapping[str, Any]
    private_ledger: Mapping[str, Any]


_ROW_KEYS = frozenset(
    {
        "data",
        "prompt_full",
        "prompt_schema",
        "reference_objective",
        "reference_status",
        "scenario_id",
    }
)
_ID = re.compile(r"retail_f([1-8])_([a-z0-9_]+)_v([0-4])\Z")
_FAMILY_COUNTS = {1: 20, 2: 30, 3: 20, 4: 30, 5: 20, 6: 20, 7: 30, 8: 20}
_ALLOWED_STATUS = frozenset({"OPTIMAL", "OPTIMAL (TL)"})


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RetailOptCustodyError("noncanonical_value") from exc


def _read_regular(path: Path, reason: str = "unsafe_source_file") -> bytes:
    path = Path(path)
    try:
        info = path.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise RetailOptCustodyError("missing_source_file") from exc
    if not stat.S_ISREG(info.st_mode):
        raise RetailOptCustodyError(reason)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RetailOptCustodyError(reason) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise RetailOptCustodyError(reason)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def _reject_constant(_value: str) -> None:
    raise RetailOptCustodyError("nonfinite_json")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RetailOptCustodyError("duplicate_json_key")
        result[key] = value
    return result


def _loads(raw: bytes, reason: str) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except RetailOptCustodyError:
        raise
    except (UnicodeError, TypeError, ValueError) as exc:
        raise RetailOptCustodyError(reason) from exc


def _jsonl(raw: bytes) -> list[dict[str, Any]]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise RetailOptCustodyError("dataset_not_utf8") from exc
    if not lines or any(not line.strip() for line in lines):
        raise RetailOptCustodyError("dataset_jsonl_shape")
    rows = []
    for line in lines:
        value = _loads(line.encode("utf-8"), "dataset_jsonl_row")
        if not isinstance(value, dict) or frozenset(value) != _ROW_KEYS:
            raise RetailOptCustodyError("dataset_row_schema")
        rows.append(value)
    return rows


def _csv_rows(raw: bytes) -> dict[str, dict[str, str]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise RetailOptCustodyError("benchmark_csv_not_utf8") from exc
    reader = csv.DictReader(io.StringIO(text))
    expected = ["scenario", "status", "objective", "objective_numeric", "time_sec"]
    if reader.fieldnames != expected:
        raise RetailOptCustodyError("benchmark_csv_schema")
    rows: dict[str, dict[str, str]] = {}
    for row in reader:
        identity = row.get("scenario")
        if not identity or identity in rows:
            raise RetailOptCustodyError("benchmark_csv_identity")
        rows[identity] = dict(row)
    return rows


def _opaque(identity: SourceIdentity, source_id: str) -> str:
    return _sha(f"{identity.commit}\0{source_id}".encode("utf-8"))


def _quantiles(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    if not ordered:
        raise RetailOptCustodyError("empty_sizes")
    return {
        "min": ordered[0],
        "median": ordered[len(ordered) // 2],
        "p95": ordered[int(0.95 * (len(ordered) - 1))],
        "max": ordered[-1],
        "total": sum(ordered),
    }


def build_custody(source_root: str | Path, identity: SourceIdentity) -> CustodyBundle:
    """Validate the source and separate inference material from evaluator labels."""

    root = Path(source_root)
    dataset_raw = _read_regular(root / "retailopt_190.jsonl")
    if _sha(dataset_raw) != identity.dataset_sha256:
        raise RetailOptCustodyError("dataset_hash_mismatch")
    license_raw = _read_regular(root / "LICENSE")
    readme_raw = _read_regular(root / "README.md")
    card_raw = _read_regular(root / "DATASET_CARD.md")
    solver_raw = _read_regular(root / "solvers" / "universal_retail_solver.py")
    csv_raw = _read_regular(root / "eval" / "benchmark_results.csv")
    rows = _jsonl(dataset_raw)
    csv_by_id = _csv_rows(csv_raw)
    if len(rows) != 190 or len(csv_by_id) != 190:
        raise RetailOptCustodyError("source_count")

    seen: set[str] = set()
    archetype_variants: dict[tuple[int, str], set[int]] = {}
    family_counts = {family: 0 for family in range(1, 9)}
    status_counts: dict[str, int] = {}
    prompt_full_sizes: list[int] = []
    prompt_schema_sizes: list[int] = []
    data_sizes: list[int] = []
    entries: dict[str, bytes] = {}
    private_records: list[dict[str, Any]] = []
    public_descriptors: list[dict[str, Any]] = []

    for row in rows:
        source_id = row.get("scenario_id")
        match = _ID.fullmatch(source_id) if isinstance(source_id, str) else None
        if match is None or source_id in seen:
            raise RetailOptCustodyError("scenario_identity")
        seen.add(source_id)
        family, archetype, variant = int(match.group(1)), match.group(2), int(match.group(3))
        family_counts[family] += 1
        variants = archetype_variants.setdefault((family, archetype), set())
        if variant in variants:
            raise RetailOptCustodyError("duplicate_archetype_variant")
        variants.add(variant)

        prompt_schema = row.get("prompt_schema")
        prompt_full = row.get("prompt_full")
        data_text = row.get("data")
        status = row.get("reference_status")
        objective = row.get("reference_objective")
        if not all(isinstance(value, str) and value for value in (prompt_schema, prompt_full, data_text)):
            raise RetailOptCustodyError("inference_field_type")
        if status not in _ALLOWED_STATUS:
            raise RetailOptCustodyError("reference_status")
        if isinstance(objective, bool) or not isinstance(objective, (int, float)) or not math.isfinite(objective):
            raise RetailOptCustodyError("reference_objective")

        disk_schema = _read_regular(root / "scenarios" / "prompts" / f"{source_id}.scenario.txt")
        disk_full = _read_regular(root / "scenarios" / "prompts" / f"{source_id}.full.txt")
        _read_regular(root / "scenarios" / "prompts" / f"{source_id}.base.txt")
        disk_data_raw = _read_regular(root / "scenarios" / "data" / f"{source_id}.json")
        try:
            schema_raw = prompt_schema.encode("utf-8")
            full_raw = prompt_full.encode("utf-8")
            data_raw = data_text.encode("utf-8")
        except UnicodeError as exc:
            raise RetailOptCustodyError("inference_not_utf8") from exc
        if schema_raw != disk_schema or full_raw != disk_full:
            raise RetailOptCustodyError("prompt_projection_mismatch")
        disk_data = _loads(disk_data_raw, "scenario_data_json")
        row_data = _loads(data_raw, "dataset_data_json")
        if not isinstance(disk_data, dict) or row_data != disk_data or disk_data.get("name") != source_id:
            raise RetailOptCustodyError("data_projection_mismatch")

        csv_row = csv_by_id.get(source_id)
        if csv_row is None or csv_row["status"] != status:
            raise RetailOptCustodyError("benchmark_csv_alignment")
        try:
            csv_objective = float(csv_row["objective_numeric"])
        except (TypeError, ValueError) as exc:
            raise RetailOptCustodyError("benchmark_csv_objective") from exc
        if not math.isclose(csv_objective, float(objective), rel_tol=0.0, abs_tol=1e-9):
            raise RetailOptCustodyError("benchmark_csv_objective")

        opaque = _opaque(identity, source_id)
        inference = {
            "schema": "llm4or-retailopt190-inference-v1",
            "opaque_id": opaque,
            "source_commit": identity.commit,
            "prompt_full": prompt_full,
        }
        evaluator = {
            "schema": "llm4or-retailopt190-evaluator-v1",
            "opaque_id": opaque,
            "source_commit": identity.commit,
            "reference_objective": float(objective),
            "reference_status": status,
        }
        inference_raw = _canonical(inference)
        evaluator_raw = _canonical(evaluator)
        metadata = {
            "schema": "llm4or-retailopt190-answer-free-metadata-v1",
            "opaque_id": opaque,
            "source_commit": identity.commit,
            "family": family,
            "variant": variant,
            "inference_bytes": len(inference_raw),
            "inference_sha256": _sha(inference_raw),
        }
        metadata_raw = _canonical(metadata)
        entries[f"inference/{opaque}/request.json"] = inference_raw
        entries[f"evaluator/{opaque}/label.json"] = evaluator_raw
        entries[f"metadata/{opaque}.json"] = metadata_raw
        private_records.append(
            {
                "opaque_id": opaque,
                "source_id": source_id,
                "family": family,
                "archetype": archetype,
                "variant": variant,
                "reference_status": status,
                "reference_objective": float(objective),
                "inference_sha256": _sha(inference_raw),
                "evaluator_sha256": _sha(evaluator_raw),
            }
        )
        public_descriptors.append(
            {
                "opaque_id": opaque,
                "family": family,
                "variant": variant,
                "inference_bytes": len(inference_raw),
                "inference_sha256": _sha(inference_raw),
                "metadata_sha256": _sha(metadata_raw),
            }
        )
        status_counts[status] = status_counts.get(status, 0) + 1
        prompt_full_sizes.append(len(full_raw))
        prompt_schema_sizes.append(len(schema_raw))
        data_sizes.append(len(data_raw))

    if family_counts != _FAMILY_COUNTS:
        raise RetailOptCustodyError("family_counts")
    if len(archetype_variants) != 38 or any(variants != set(range(5)) for variants in archetype_variants.values()):
        raise RetailOptCustodyError("archetype_variant_grid")
    if set(csv_by_id) != seen:
        raise RetailOptCustodyError("benchmark_csv_membership")

    ledger = {
        "schema": "llm4or-retailopt190-private-custody-ledger-v1",
        "source": {
            "commit": identity.commit,
            "dataset_sha256": identity.dataset_sha256,
            "license_sha256": _sha(license_raw),
            "readme_sha256": _sha(readme_raw),
            "dataset_card_sha256": _sha(card_raw),
            "reference_solver_sha256": _sha(solver_raw),
            "benchmark_csv_sha256": _sha(csv_raw),
        },
        "records": sorted(private_records, key=lambda value: value["opaque_id"]),
    }
    ledger_raw = _canonical(ledger)
    entries["private/ledger.json"] = ledger_raw
    entries = dict(sorted(entries.items()))
    public_projection = {
        path: _sha(payload)
        for path, payload in entries.items()
        if path.startswith(("inference/", "metadata/"))
    }
    audit = {
        "schema": "llm4or-retailopt190-source-custody-audit-v1",
        "status": "passed_source_custody_only",
        "source": {
            "commit": identity.commit,
            "dataset_sha256": identity.dataset_sha256,
            "license_sha256": _sha(license_raw),
            "readme_sha256": _sha(readme_raw),
            "dataset_card_sha256": _sha(card_raw),
            "reference_solver_sha256": _sha(solver_raw),
            "benchmark_csv_sha256": _sha(csv_raw),
        },
        "counts": {
            "records": len(rows),
            "families": len(family_counts),
            "archetypes": len(archetype_variants),
            "variants_per_archetype": 5,
            "inference_records": len(rows),
            "evaluator_records": len(rows),
        },
        "family_counts": {str(key): value for key, value in sorted(family_counts.items())},
        "size_bytes": {
            "prompt_full": _quantiles(prompt_full_sizes),
            "prompt_schema": _quantiles(prompt_schema_sizes),
            "data": _quantiles(data_sizes),
        },
        "public_descriptor_set_sha256": _sha(_canonical(sorted(public_descriptors, key=lambda value: value["opaque_id"]))),
        "inference_metadata_projection_sha256": _sha(_canonical(public_projection)),
        "private_ledger_sha256": _sha(ledger_raw),
        "source_consistency": {
            "jsonl_to_prompt_files_exact": True,
            "jsonl_to_data_files_semantic_exact": True,
            "jsonl_to_benchmark_csv_exact": True,
            "unique_scenario_ids": True,
            "complete_archetype_variant_grid": True,
            "finite_reference_objectives": True,
            "allowed_reference_statuses_only": True,
        },
        "license_boundary": {
            "root_license_name": "ReLoop Research and Education License v1.0",
            "readme_code_badge_claim": "MIT",
            "dataset_card_data_claim": "CC-BY-4.0",
            "metadata_conflict_recorded": True,
            "redistribute_source_bodies": False,
            "attribution_required": True,
        },
        "privacy": {
            "contains_problem_bodies": False,
            "contains_structured_data_values": False,
            "contains_source_scenario_ids": False,
            "contains_reference_objectives": False,
            "contains_reference_statuses": False,
            "contains_reference_solver_body": False,
        },
        "execution": {
            "api_calls": 0,
            "model_calls": 0,
            "solver_calls": 0,
            "native_calls": 0,
            "credentials_read": False,
        },
        "claim_boundary": (
            "This audit establishes source completeness, projection consistency and "
            "inference/evaluator separation only. It does not establish model accuracy, "
            "benchmark independence, solver reproducibility or a confirmatory split."
        ),
    }
    return CustodyBundle(entries=entries, public_audit=audit, private_ledger=ledger)


def publish_custody(destination: str | Path, entries: Mapping[str, bytes]) -> PublicationResult:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    return publish_bundle(destination, entries)


__all__ = [
    "CustodyBundle",
    "RetailOptCustodyError",
    "SourceIdentity",
    "build_custody",
    "publish_custody",
]
