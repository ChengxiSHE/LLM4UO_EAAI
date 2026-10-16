"""Fail-closed custody primitives for the fixed MIPLIB-NL source snapshot."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import re
from typing import Any, Mapping

from llm4or.atomic_publisher import PublicationResult, publish_bundle


class CustodyError(ValueError):
    """The source or a custody projection violates the declared boundary."""


@dataclass(frozen=True)
class SourceIdentity:
    commit: str
    dataset_tree: str

    def __post_init__(self) -> None:
        for value in (self.commit, self.dataset_tree):
            if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
                raise CustodyError("invalid_source_identity")


@dataclass(frozen=True)
class CustodyBundle:
    entries: Mapping[str, bytes]
    public_audit: Mapping[str, Any]
    private_ledger: Mapping[str, Any]


_TOP_LEVEL_KEYS_WITH_FILES = frozenset(
    {"abstract_problem", "parameters", "files", "optimal_value"}
)
_TOP_LEVEL_KEYS_WITHOUT_FILES = frozenset(
    {"abstract_problem", "parameters", "optimal_value"}
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CustodyError("not_canonical_json") from exc


def _opaque_id(source: SourceIdentity, directory_name: str) -> str:
    return _sha256(f"{source.commit}\0{directory_name}".encode("utf-8"))


def _read_regular(path: Path, reason: str) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise CustodyError("missing_required_file") from exc
    if not stat.S_ISREG(info.st_mode):
        raise CustodyError(reason)
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0),
        )
    except OSError as exc:
        raise CustodyError(reason) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise CustodyError(reason)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def _reject_constant(_value: str) -> None:
    raise CustodyError("nonfinite_json")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CustodyError("duplicate_json_key")
        result[key] = value
    return result


def _load_json_mapping(path: Path) -> dict[str, Any]:
    raw = _read_regular(Path(path), "unsafe_required_file")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CustodyError("instance_json_not_utf8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_reject_constant,
        )
    except CustodyError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CustodyError("invalid_instance_json") from exc
    if not isinstance(value, dict):
        raise CustodyError("instance_not_mapping")
    return value


def load_instance(path: Path) -> dict[str, Any]:
    """Parse one strict MIPLIB-NL instance without echoing source values."""

    value = _load_json_mapping(path)
    keys = frozenset(value)
    if keys not in {_TOP_LEVEL_KEYS_WITH_FILES, _TOP_LEVEL_KEYS_WITHOUT_FILES}:
        raise CustodyError("top_level_keys")
    if not isinstance(value["abstract_problem"], str):
        raise CustodyError("invalid_abstract_problem")
    if not isinstance(value["parameters"], dict):
        raise CustodyError("invalid_parameters")
    if "files" not in value:
        value["files"] = {}
    if not isinstance(value["files"], dict):
        raise CustodyError("invalid_files")
    return value


def _canonical_data_relative(declared: str) -> PurePosixPath:
    if not isinstance(declared, str) or not declared or "\\" in declared:
        raise CustodyError("unsafe_data_path")
    supplied = PurePosixPath(declared)
    if supplied.is_absolute() or ".." in supplied.parts:
        raise CustodyError("unsafe_data_path")
    parts = tuple(part for part in supplied.parts if part != ".")
    if parts and parts[0] == "data":
        parts = parts[1:]
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise CustodyError("unsafe_data_path")
    return PurePosixPath(*parts)


def resolve_data_file(instance_directory: Path, declared: str) -> Path:
    """Resolve one declared data file beneath an instance without following links."""

    instance_directory = Path(instance_directory)
    relative = _canonical_data_relative(declared)
    data_root = instance_directory / "data"
    try:
        root_info = data_root.lstat()
    except FileNotFoundError as exc:
        raise CustodyError("missing_data_directory") from exc
    if not stat.S_ISDIR(root_info.st_mode):
        raise CustodyError("unsafe_data_directory")
    current = data_root
    for part in relative.parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError as exc:
            raise CustodyError("missing_data_file") from exc
        if not stat.S_ISDIR(info.st_mode):
            raise CustodyError("unsafe_data_path")
    terminal = data_root.joinpath(*relative.parts)
    _read_regular(terminal, "unsafe_data_file")
    return terminal


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CustodyError("nonfinite_json")
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise CustodyError("invalid_json_type")


def _schema_paths(value: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}

    def add(path: str, child: Any) -> None:
        kind = _json_type(child)
        counts.setdefault(path, {})[kind] = counts.setdefault(path, {}).get(kind, 0) + 1

    def visit(path: str, child: Any, wildcard_keys: bool) -> None:
        add(path, child)
        if isinstance(child, dict):
            for key, grandchild in sorted(child.items()):
                next_key = "*" if wildcard_keys else key
                visit(f"{path}.{next_key}", grandchild, wildcard_keys)
        elif isinstance(child, list):
            for grandchild in child:
                visit(f"{path}[]", grandchild, wildcard_keys)

    for key, child in sorted(value.items()):
        visit(f"$.{key}", child, key in {"parameters"})
    return {path: dict(sorted(kinds.items())) for path, kinds in sorted(counts.items())}


def _merge_schema_paths(
    destination: dict[str, dict[str, int]], source: Mapping[str, Mapping[str, int]]
) -> None:
    for path, kinds in source.items():
        target = destination.setdefault(path, {})
        for kind, count in kinds.items():
            target[kind] = target.get(kind, 0) + count


def _required_regular(instance: Path, name: str, *, optional: bool = False) -> bool:
    path = instance / name
    try:
        info = path.lstat()
    except FileNotFoundError:
        if optional:
            return False
        raise CustodyError("missing_required_file")
    if not stat.S_ISREG(info.st_mode):
        raise CustodyError("unsafe_required_file")
    _read_regular(path, "unsafe_required_file")
    return True


def build_schema_census(
    dataset_root: Path, source: SourceIdentity
) -> dict[str, Any]:
    """Return field paths and types only; never return source values or names."""

    dataset_root = Path(dataset_root)
    try:
        root_info = dataset_root.lstat()
    except FileNotFoundError as exc:
        raise CustodyError("missing_dataset_root") from exc
    if not stat.S_ISDIR(root_info.st_mode):
        raise CustodyError("unsafe_dataset_root")
    instances = sorted(dataset_root.iterdir(), key=lambda item: item.name.encode("utf-8"))
    if not instances:
        raise CustodyError("empty_dataset")
    names: list[str] = []
    opaque_ids: list[str] = []
    schema_paths: dict[str, dict[str, int]] = {}
    top_level_key_sets: dict[tuple[str, ...], int] = {}
    models = 0
    data_files = 0
    for instance in instances:
        info = instance.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise CustodyError("unsafe_instance_directory")
        names.append(instance.name)
        opaque = _opaque_id(source, instance.name)
        opaque_ids.append(opaque)
        _required_regular(instance, "instance.json")
        _required_regular(instance, "solve.py")
        models += int(_required_regular(instance, "model.md", optional=True))
        value = _load_json_mapping(instance / "instance.json")
        key_set = tuple(sorted(value))
        top_level_key_sets[key_set] = top_level_key_sets.get(key_set, 0) + 1
        _merge_schema_paths(schema_paths, _schema_paths(value))
        seen: set[str] = set()
        files = value.get("files")
        if isinstance(files, dict):
            for entry in files.values():
                if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                    raise CustodyError("invalid_file_entry")
                relative = _canonical_data_relative(entry["path"]).as_posix()
                if relative in seen:
                    raise CustodyError("duplicate_data_path")
                seen.add(relative)
                data_files += 1
        elif isinstance(files, list):
            data_files += len(files)
    name_bytes = "".join(f"{name}\n" for name in names).encode("utf-8")
    opaque_bytes = "".join(f"{identity}\n" for identity in sorted(opaque_ids)).encode(
        "ascii"
    )
    return {
        "schema": "llm4or-miplib-nl-schema-census-v1",
        "source": {
            "commit": source.commit,
            "dataset_tree": source.dataset_tree,
            "directory_name_set_sha256": _sha256(name_bytes),
            "opaque_identity_set_sha256": _sha256(opaque_bytes),
        },
        "counts": {
            "instances": len(instances),
            "instance_json": len(instances),
            "solve_py": len(instances),
            "model_md_present": models,
            "model_md_absent": len(instances) - models,
            "declared_data_files": data_files,
        },
        "schema_paths": {
            path: dict(sorted(kinds.items()))
            for path, kinds in sorted(schema_paths.items())
        },
        "top_level_key_sets": [
            {"keys": list(keys), "count": count}
            for keys, count in sorted(top_level_key_sets.items())
        ],
        "privacy": {
            "contains_credentials": False,
            "contains_data_values": False,
            "contains_instance_names": False,
            "contains_model_text": False,
            "contains_optimal_values": False,
            "contains_reference_code": False,
            "contains_task_text": False,
        },
        "execution": {
            "api_calls": 0,
            "model_calls": 0,
            "native_calls": 0,
            "solver_calls": 0,
            "vm_calls": 0,
        },
    }


_SENSITIVE_KEYS = frozenset(
    {
        "answer",
        "best_bound",
        "evaluator_answer",
        "gap",
        "incumbent",
        "mip_gap",
        "objective_value",
        "optimal_value",
        "reference_answer",
        "reference_objective",
        "reference_output",
        "reference_solution",
        "solution",
        "solve_status",
    }
)


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _reject_sensitive_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CustodyError("non_string_json_key")
            if _normalized_key(key) in _SENSITIVE_KEYS:
                raise CustodyError("sensitive_key")
            _reject_sensitive_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive_keys(child)


def _parameter_structure(value: Any) -> Any:
    kind = _json_type(value)
    if isinstance(value, Mapping):
        return {
            "type": kind,
            "fields": {
                key: _parameter_structure(child)
                for key, child in sorted(value.items())
            },
        }
    if isinstance(value, list):
        child_types: dict[str, int] = {}
        for child in value:
            child_kind = _json_type(child)
            child_types[child_kind] = child_types.get(child_kind, 0) + 1
        return {"type": kind, "length": len(value), "element_types": child_types}
    return {"type": kind}


def _walk_data_files(data_root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}

    try:
        root_info = data_root.lstat()
    except FileNotFoundError:
        return result
    if not stat.S_ISDIR(root_info.st_mode):
        raise CustodyError("unsafe_data_directory")

    def visit(directory: Path, prefix: tuple[str, ...]) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name.encode("utf-8"))
        except OSError as exc:
            raise CustodyError("unsafe_data_directory") from exc
        for entry in entries:
            relative = PurePosixPath(*prefix, entry.name).as_posix()
            try:
                if entry.is_symlink():
                    raise CustodyError("unsafe_data_file")
                if entry.is_dir(follow_symlinks=False):
                    visit(Path(entry.path), (*prefix, entry.name))
                elif entry.is_file(follow_symlinks=False):
                    result[relative] = Path(entry.path)
                else:
                    raise CustodyError("unsafe_data_file")
            except OSError as exc:
                raise CustodyError("unsafe_data_file") from exc

    visit(data_root, ())
    return result


def build_materialization_audit(
    dataset_root: Path, source: SourceIdentity
) -> dict[str, Any]:
    """Compare declared and materialized input paths without exposing either."""

    dataset_root = Path(dataset_root)
    census = build_schema_census(dataset_root, source)
    instances = sorted(
        dataset_root.iterdir(), key=lambda item: item.name.encode("utf-8")
    )
    totals = {
        "instances": len(instances),
        "exact_instances": 0,
        "mismatched_instances": 0,
        "declared_data_files": 0,
        "actual_data_files": 0,
        "missing_declared_data_files": 0,
        "undeclared_actual_data_files": 0,
        "missing_data_directories": 0,
    }
    mismatches: list[dict[str, Any]] = []
    for instance in instances:
        value = load_instance(instance / "instance.json")
        declared: set[str] = set()
        for file_entry in value["files"].values():
            if not isinstance(file_entry, Mapping) or not isinstance(
                file_entry.get("path"), str
            ):
                raise CustodyError("invalid_file_entry")
            relative = _canonical_data_relative(file_entry["path"]).as_posix()
            if relative in declared:
                raise CustodyError("duplicate_data_path")
            declared.add(relative)
        data_root = instance / "data"
        try:
            data_root.lstat()
        except FileNotFoundError:
            totals["missing_data_directories"] += 1
        actual = set(_walk_data_files(data_root))
        missing = declared - actual
        undeclared = actual - declared
        totals["declared_data_files"] += len(declared)
        totals["actual_data_files"] += len(actual)
        totals["missing_declared_data_files"] += len(missing)
        totals["undeclared_actual_data_files"] += len(undeclared)
        if missing or undeclared:
            totals["mismatched_instances"] += 1
            mismatches.append(
                {
                    "opaque_id": _opaque_id(source, instance.name),
                    "declared_data_files": len(declared),
                    "actual_data_files": len(actual),
                    "missing_declared_data_files": len(missing),
                    "undeclared_actual_data_files": len(undeclared),
                }
            )
        else:
            totals["exact_instances"] += 1
    passed = totals["mismatched_instances"] == 0
    return {
        "schema": "llm4or-miplib-nl-materialization-audit-v1",
        "status": "passed" if passed else "failed_source_materialization",
        "source": dict(census["source"]),
        "counts": totals,
        "mismatches": sorted(mismatches, key=lambda row: row["opaque_id"]),
        "schema_census_sha256": _sha256(_canonical_json(census)),
        "privacy": {
            "contains_credentials": False,
            "contains_data_values": False,
            "contains_evaluator_answers": False,
            "contains_instance_names": False,
            "contains_model_text": False,
            "contains_reference_code": False,
            "contains_task_bodies": False,
        },
        "execution": {
            "api_calls": 0,
            "model_calls": 0,
            "native_calls": 0,
            "solver_calls": 0,
            "vm_calls": 0,
        },
        "dispatch_allowed": passed,
    }


def _csv_summary(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CustodyError("data_not_utf8") from exc
    row_count = 0
    minimum_columns: int | None = None
    maximum_columns = 0
    try:
        for row in csv.reader(io.StringIO(text, newline="")):
            width = len(row)
            if row_count == 0:
                normalized = [_normalized_key(cell) for cell in row]
                if any(cell in _SENSITIVE_KEYS for cell in normalized if cell):
                    raise CustodyError("sensitive_csv_header")
            row_count += 1
            minimum_columns = width if minimum_columns is None else min(minimum_columns, width)
            maximum_columns = max(maximum_columns, width)
    except CustodyError:
        raise
    except csv.Error as exc:
        raise CustodyError("invalid_csv") from exc
    minimum = minimum_columns if minimum_columns is not None else 0
    return {
        "rows": row_count,
        "minimum_columns": minimum,
        "maximum_columns": maximum_columns,
        "ragged": minimum != maximum_columns,
    }


def _validate_optimal_value(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise CustodyError("invalid_optimal_value")
    if isinstance(value, float) and not math.isfinite(value):
        raise CustodyError("invalid_optimal_value")


def _aggregate_hash(entries: Mapping[str, bytes]) -> str:
    manifest = [
        {"path": path, "bytes": len(raw), "sha256": _sha256(raw)}
        for path, raw in sorted(entries.items())
    ]
    return _sha256(_canonical_json(manifest))


def build_custody_bundle(
    dataset_root: Path, source: SourceIdentity
) -> CustodyBundle:
    """Build disjoint deterministic projections without publishing them."""

    dataset_root = Path(dataset_root)
    census = build_schema_census(dataset_root, source)
    instances = sorted(dataset_root.iterdir(), key=lambda item: item.name.encode("utf-8"))
    output_entries: dict[str, bytes] = {}
    ledger_records: list[dict[str, Any]] = []
    opaque_seen: set[str] = set()
    totals = {
        "instances": 0,
        "declared_data_files": 0,
        "model_md_present": 0,
        "model_md_absent": 0,
        "csv_rows": 0,
        "csv_columns": 0,
    }
    for instance in instances:
        opaque = _opaque_id(source, instance.name)
        if opaque in opaque_seen:
            raise CustodyError("duplicate_opaque_identity")
        opaque_seen.add(opaque)
        value = load_instance(instance / "instance.json")
        _reject_sensitive_keys(value["parameters"])
        _reject_sensitive_keys(value["files"])
        _validate_optimal_value(value["optimal_value"])
        raw_instance = _read_regular(instance / "instance.json", "unsafe_required_file")
        solve_raw = _read_regular(instance / "solve.py", "unsafe_required_file")
        model_path = instance / "model.md"
        model_present = model_path.exists()
        model_raw = (
            _read_regular(model_path, "unsafe_required_file")
            if model_present
            else None
        )
        actual_files = _walk_data_files(instance / "data")
        declared: dict[str, Path] = {}
        for file_entry in value["files"].values():
            if not isinstance(file_entry, Mapping) or not isinstance(
                file_entry.get("path"), str
            ):
                raise CustodyError("invalid_file_entry")
            relative = _canonical_data_relative(file_entry["path"]).as_posix()
            if relative in declared:
                raise CustodyError("duplicate_data_path")
            if PurePosixPath(relative).suffix.lower() != ".csv":
                raise CustodyError("data_extension")
            declared[relative] = resolve_data_file(instance, file_entry["path"])
        if frozenset(actual_files) != frozenset(declared):
            raise CustodyError("undeclared_data_file")

        inference = {
            "abstract_problem": value["abstract_problem"],
            "files": value["files"],
            "parameters": value["parameters"],
        }
        inference_raw = _canonical_json(inference)
        output_entries[f"inference/{opaque}/instance.json"] = inference_raw
        csv_files: list[dict[str, Any]] = []
        row_total = 0
        maximum_columns = 0
        ragged_files = 0
        for relative, path in sorted(declared.items()):
            raw = _read_regular(path, "unsafe_data_file")
            summary = _csv_summary(raw)
            row_total += summary["rows"]
            maximum_columns = max(maximum_columns, summary["maximum_columns"])
            ragged_files += int(summary["ragged"])
            output_entries[f"inference/{opaque}/data/{relative}"] = raw
            csv_files.append(
                {
                    "relative_path_sha256": _sha256(relative.encode("utf-8")),
                    "bytes": len(raw),
                    "rows": summary["rows"],
                    "minimum_columns": summary["minimum_columns"],
                    "maximum_columns": summary["maximum_columns"],
                    "ragged": summary["ragged"],
                    "sha256": _sha256(raw),
                }
            )

        optimal_raw = _canonical_json(value["optimal_value"])
        reference = {
            "schema": "llm4or-miplib-nl-evaluator-reference-v1",
            "opaque_id": opaque,
            "source_commit": source.commit,
            "dataset_tree": source.dataset_tree,
            "source_instance_sha256": _sha256(raw_instance),
            "optimal_value": value["optimal_value"],
            "optimal_value_sha256": _sha256(optimal_raw),
        }
        reference_raw = _canonical_json(reference)
        output_entries[f"evaluator/{opaque}/reference.json"] = reference_raw
        output_entries[f"evaluator/{opaque}/solve.py"] = solve_raw
        if model_raw is not None:
            output_entries[f"evaluator/{opaque}/model.md"] = model_raw

        metadata = {
            "schema": "llm4or-miplib-nl-answer-free-metadata-v1",
            "opaque_id": opaque,
            "source_commit": source.commit,
            "dataset_tree": source.dataset_tree,
            "source_instance_bytes": len(raw_instance),
            "source_instance_sha256": _sha256(raw_instance),
            "inference_instance_bytes": len(inference_raw),
            "inference_instance_sha256": _sha256(inference_raw),
            "parameter_structure": _parameter_structure(value["parameters"]),
            "declared_file_count": len(csv_files),
            "csv": {
                "files": len(csv_files),
                "rows": row_total,
                "maximum_columns": maximum_columns,
                "ragged_files": ragged_files,
                "bytes": sum(item["bytes"] for item in csv_files),
                "file_descriptors": csv_files,
            },
            "reference_model_present": model_present,
            "privacy": {
                "contains_data_values": False,
                "contains_optimal_value": False,
                "contains_reference_code": False,
                "contains_task_text": False,
            },
        }
        metadata_raw = _canonical_json(metadata)
        output_entries[f"metadata/{opaque}.json"] = metadata_raw
        ledger_records.append(
            {
                "source_directory": instance.name,
                "opaque_id": opaque,
                "source_instance_sha256": _sha256(raw_instance),
                "inference_instance_sha256": _sha256(inference_raw),
                "metadata_sha256": _sha256(metadata_raw),
                "reference_sha256": _sha256(reference_raw),
                "solve_py_sha256": _sha256(solve_raw),
                "model_md_sha256": _sha256(model_raw) if model_raw is not None else None,
                "data": csv_files,
            }
        )
        totals["instances"] += 1
        totals["declared_data_files"] += len(csv_files)
        totals["model_md_present"] += int(model_present)
        totals["model_md_absent"] += int(not model_present)
        totals["csv_rows"] += row_total
        totals["csv_columns"] += sum(item["maximum_columns"] for item in csv_files)

    private_ledger: dict[str, Any] = {
        "schema": "llm4or-miplib-nl-private-custody-ledger-v1",
        "source": {
            "commit": source.commit,
            "dataset_tree": source.dataset_tree,
            "directory_name_set_sha256": census["source"][
                "directory_name_set_sha256"
            ],
        },
        "records": ledger_records,
        "counts": dict(totals),
    }
    ledger_raw = _canonical_json(private_ledger)
    output_entries["private/ledger.json"] = ledger_raw
    public_audit: dict[str, Any] = {
        "schema": "llm4or-miplib-nl-custody-audit-v1",
        "status": "built_not_published",
        "source": dict(census["source"]),
        "counts": dict(totals),
        "schema_census_sha256": _sha256(_canonical_json(census)),
        "private_ledger_sha256": _sha256(ledger_raw),
        "bundle_sha256": _aggregate_hash(output_entries),
        "privacy": {
            "contains_credentials": False,
            "contains_data_values": False,
            "contains_evaluator_answers": False,
            "contains_instance_names": False,
            "contains_model_text": False,
            "contains_reference_code": False,
            "contains_task_bodies": False,
        },
        "execution": {
            "api_calls": 0,
            "credentials_read": False,
            "model_calls": 0,
            "native_calls": 0,
            "solver_calls": 0,
            "vm_calls": 0,
        },
        "claim_boundary": (
            "This audit proves deterministic custody projection only; it does not "
            "authorize inference or report benchmark accuracy."
        ),
    }
    return CustodyBundle(
        entries=dict(sorted(output_entries.items())),
        public_audit=public_audit,
        private_ledger=private_ledger,
    )


def publish_custody_bundle(
    root: Path, bundle: CustodyBundle
) -> PublicationResult:
    """Publish every private custody terminal in one recoverable transaction."""

    return publish_bundle(Path(root), bundle.entries)


def _collect_terminal_files(root: Path) -> set[str]:
    terminals: set[str] = set()

    def visit(directory: Path, prefix: tuple[str, ...]) -> None:
        try:
            entries = sorted(
                os.scandir(directory), key=lambda item: item.name.encode("utf-8")
            )
        except OSError as exc:
            raise CustodyError("check_unsafe_path") from exc
        for entry in entries:
            if not prefix and entry.name == ".llm4or-publication-journal":
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    raise CustodyError("check_unsafe_path")
                continue
            if entry.is_symlink():
                raise CustodyError("check_unsafe_path")
            relative = PurePosixPath(*prefix, entry.name).as_posix()
            try:
                if entry.is_dir(follow_symlinks=False):
                    visit(Path(entry.path), (*prefix, entry.name))
                elif entry.is_file(follow_symlinks=False):
                    terminals.add(relative)
                else:
                    raise CustodyError("check_unsafe_path")
            except OSError as exc:
                raise CustodyError("check_unsafe_path") from exc

    visit(root, ())
    return terminals


def check_custody_bundle(root: Path, bundle: CustodyBundle) -> None:
    """Read-only verification of every terminal and the complete file set."""

    root = Path(root)
    try:
        info = root.lstat()
    except FileNotFoundError as exc:
        raise CustodyError("check_root_missing") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CustodyError("check_root_unsafe")
    expected_paths = set(bundle.entries)
    if _collect_terminal_files(root) != expected_paths:
        raise CustodyError("check_path_set_drift")
    for relative, expected in sorted(bundle.entries.items()):
        supplied = PurePosixPath(relative)
        if supplied.is_absolute() or any(
            part in ("", ".", "..") for part in supplied.parts
        ):
            raise CustodyError("check_unsafe_expected_path")
        path = root.joinpath(*supplied.parts)
        try:
            observed = _read_regular(path, "check_unsafe_path")
        except CustodyError as exc:
            raise CustodyError("check_drift") from exc
        if observed != expected:
            raise CustodyError("check_drift")
