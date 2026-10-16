"""Body-free source validation for the fixed FormulationBench snapshot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
from typing import Any, Callable, Mapping

from llm4or.atomic_publisher import (
    PublicationBoundaryError,
    PublicationResult,
    publish_bundle,
)


class CustodyError(ValueError):
    """The source violates the declared answer-blind boundary."""


@dataclass(frozen=True)
class SourceIdentity:
    commit: str
    dataset_tree: str

    def __post_init__(self) -> None:
        for value in (self.commit, self.dataset_tree):
            if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
                raise CustodyError("invalid_source_identity")


@dataclass(frozen=True)
class CensusCounts:
    problems: int
    formulations: int
    pairs: int
    proofs: int

    def __post_init__(self) -> None:
        if any(value < 0 for value in self.__dict__.values()):
            raise CustodyError("invalid_expected_counts")


OFFICIAL_COUNTS = CensusCounts(problems=20, formulations=109, pairs=89, proofs=63)


@dataclass(frozen=True)
class CustodyBundle:
    entries: Mapping[str, bytes]
    public_audit: Mapping[str, Any]
    private_ledger: Mapping[str, Any]

_ROOT_FILES = frozenset(
    {
        ".gitignore",
        "AGENTS.md",
        "CLAUDE.md",
        "Common.lean",
        "LICENSE.md",
        "README.md",
        "dataset.json",
        "lake-manifest.json",
        "lakefile.toml",
        "lean-toolchain",
        "ref.bib",
    }
)
_ROOT_DIRECTORIES = frozenset({"problems", "reformulations"})
_PROBLEM_REQUIRED = frozenset(
    {"data.json", "description.md", "formulations", "problem.json", "solution.json"}
)
_PROBLEM_OPTIONAL = frozenset({"gen_data.py", "gen_data_mps.py"})
_FORMULATION_FILES = frozenset(
    {"Formulation.lean", "formulation.json", "gen_params.py"}
)
_PAIR_REQUIRED = frozenset({"map.json"})
_PAIR_OPTIONAL = frozenset({"Reformulation.lean"})
_PROBLEM = re.compile(r"p([0-9]+)\Z")
_FORMULATION = re.compile(r"[a-z]+\Z")
_PAIR = re.compile(r"([a-z]+)_([a-z]+)\Z")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: Any) -> bytes:
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


def _scan(root: Path) -> dict[str, tuple[str, int]]:
    """Return relative path types/sizes without opening any file body."""

    root = Path(root)
    try:
        root_info = root.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise CustodyError("source_root_missing_or_unsafe") from exc
    if not stat.S_ISDIR(root_info.st_mode):
        raise CustodyError("source_root_missing_or_unsafe")

    rows: dict[str, tuple[str, int]] = {}
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise CustodyError("unsafe_source_entry") from exc
        for entry in entries:
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise CustodyError("unsafe_source_entry") from exc
            relative = Path(entry.path).relative_to(root).as_posix()
            if stat.S_ISDIR(info.st_mode):
                rows[relative] = ("directory", 0)
                pending.append(Path(entry.path))
            elif stat.S_ISREG(info.st_mode):
                rows[relative] = ("file", info.st_size)
            else:
                raise CustodyError("unsafe_source_entry")
    return rows


def _children(rows: dict[str, tuple[str, int]], parent: str) -> dict[str, str]:
    prefix = f"{parent}/" if parent else ""
    result: dict[str, str] = {}
    for path, (kind, _size) in rows.items():
        if not path.startswith(prefix):
            continue
        remainder = path[len(prefix) :]
        if "/" not in remainder:
            result[remainder] = kind
    return result


def _require_file(rows: dict[str, tuple[str, int]], path: str) -> None:
    if rows.get(path, (None, 0))[0] != "file":
        raise CustodyError("missing_required_file")


def _require_directory(rows: dict[str, tuple[str, int]], path: str) -> None:
    if rows.get(path, (None, 0))[0] != "directory":
        raise CustodyError("missing_required_directory")


def _exact_children(
    rows: dict[str, tuple[str, int]],
    parent: str,
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
) -> dict[str, str]:
    children = _children(rows, parent)
    if not required.issubset(children):
        missing = required - children.keys()
        if any(name.endswith((".json", ".md", ".py", ".lean")) for name in missing):
            raise CustodyError("missing_required_file")
        raise CustodyError("missing_required_directory")
    if set(children) - required - optional:
        raise CustodyError("unknown_source_entry")
    return children


def census_source(
    dataset_root: Path,
    source: SourceIdentity,
    *,
    expected: CensusCounts = OFFICIAL_COUNTS,
) -> dict[str, Any]:
    """Validate the fixed tree shape without opening benchmark file bodies."""

    rows = _scan(Path(dataset_root))
    _exact_children(
        rows,
        "",
        required=_ROOT_FILES | _ROOT_DIRECTORIES,
    )

    problem_children = _children(rows, "problems")
    canonical_problem_ids: set[int] = set()
    formulation_ids: dict[int, set[str]] = {}
    formulation_count = 0
    for name, kind in problem_children.items():
        match = _PROBLEM.fullmatch(name)
        if kind != "directory" or match is None:
            raise CustodyError("unknown_source_entry")
        canonical = int(match.group(1))
        if canonical in canonical_problem_ids:
            raise CustodyError("duplicate_problem_identity")
        canonical_problem_ids.add(canonical)
        parent = f"problems/{name}"
        _exact_children(
            rows,
            parent,
            required=_PROBLEM_REQUIRED,
            optional=_PROBLEM_OPTIONAL,
        )
        formulations_parent = f"{parent}/formulations"
        formulation_children = _children(rows, formulations_parent)
        if not formulation_children:
            raise CustodyError("missing_formulations")
        ids: set[str] = set()
        for formulation_id, formulation_kind in formulation_children.items():
            if formulation_kind != "directory" or not _FORMULATION.fullmatch(
                formulation_id
            ):
                raise CustodyError("invalid_formulation_identity")
            if formulation_id.casefold() in {value.casefold() for value in ids}:
                raise CustodyError("duplicate_formulation_identity")
            ids.add(formulation_id)
            formulation_parent = f"{formulations_parent}/{formulation_id}"
            _exact_children(
                rows,
                formulation_parent,
                required=_FORMULATION_FILES,
            )
        formulation_ids[canonical] = ids
        formulation_count += len(ids)

    reformulation_children = _children(rows, "reformulations")
    pair_opaque_ids: list[str] = []
    pair_count = 0
    proof_count = 0
    for problem_name, problem_kind in reformulation_children.items():
        match = _PROBLEM.fullmatch(problem_name)
        if problem_kind != "directory" or match is None:
            raise CustodyError("unknown_source_entry")
        canonical = int(match.group(1))
        if canonical not in canonical_problem_ids:
            raise CustodyError("pair_problem_missing")
        pair_parent = f"reformulations/{problem_name}"
        pair_children = _children(rows, pair_parent)
        for pair_name, pair_kind in pair_children.items():
            pair_match = _PAIR.fullmatch(pair_name)
            if pair_kind != "directory" or pair_match is None:
                raise CustodyError("invalid_pair_identity")
            left, right = pair_match.groups()
            if (
                left == right
                or left not in formulation_ids[canonical]
                or right not in formulation_ids[canonical]
            ):
                raise CustodyError("pair_side_missing")
            files = _exact_children(
                rows,
                f"{pair_parent}/{pair_name}",
                required=_PAIR_REQUIRED,
                optional=_PAIR_OPTIONAL,
            )
            pair_count += 1
            proof_count += int("Reformulation.lean" in files)
            pair_opaque_ids.append(
                _sha256(
                    f"{source.commit}\0{canonical}\0{pair_name}".encode("utf-8")
                )
            )

    observed = CensusCounts(
        problems=len(canonical_problem_ids),
        formulations=formulation_count,
        pairs=pair_count,
        proofs=proof_count,
    )
    if observed != expected:
        raise CustodyError("source_count_mismatch")

    structural_rows = [
        {"path_sha256": _sha256(path.encode("utf-8")), "type": kind, "size": size}
        for path, (kind, size) in sorted(rows.items())
    ]
    return {
        "counts": {
            "formulations": observed.formulations,
            "pairs": observed.pairs,
            "problems": observed.problems,
            "proofs": observed.proofs,
        },
        "pair_opaque_identity_set_sha256": _sha256(
            _canonical_json(sorted(pair_opaque_ids))
        ),
        "path_structure_sha256": _sha256(_canonical_json(structural_rows)),
        "privacy": {
            "contains_data_values": False,
            "contains_formulation_bodies": False,
            "contains_labels": False,
            "contains_problem_bodies": False,
            "contains_proof_bodies": False,
            "contains_solutions": False,
        },
        "schema": "llm4or-formulationbench-source-census-v1",
        "source": {"commit": source.commit, "dataset_tree": source.dataset_tree},
        "status": "passed_body_free_source_census",
    }


def _read_regular(path: Path, reason: str = "unsafe_required_file") -> bytes:
    try:
        info = path.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise CustodyError("missing_required_file") from exc
    if not stat.S_ISREG(info.st_mode):
        raise CustodyError(reason)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
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


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CustodyError("duplicate_json_key")
        result[key] = value
    return result


def _load_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = _read_regular(path)
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except CustodyError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CustodyError("invalid_source_json") from exc
    if not isinstance(value, dict):
        raise CustodyError("source_json_not_mapping")
    return raw, value


def _sanitize(value: Any, *, omit: frozenset[str]) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in sorted(value.items()):
            if not isinstance(key, str):
                raise CustodyError("non_string_json_key")
            if key in omit or key in {"code", "metadata"}:
                continue
            result[key] = _sanitize(child, omit=omit)
        return result
    if isinstance(value, list):
        return [_sanitize(child, omit=omit) for child in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise CustodyError("invalid_json_value")


def _reject_inference_sensitive_keys(value: Any) -> None:
    forbidden = {"answer", "code", "label", "metadata", "proof", "solution", "valid"}
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
            if normalized in forbidden:
                raise CustodyError("inference_sensitive_key")
            _reject_inference_sensitive_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_inference_sensitive_keys(child)


def _opaque_pair_id(
    source: SourceIdentity, problem_id: int, pair_id: str
) -> str:
    return _sha256(
        f"{source.commit}\0{problem_id}\0{pair_id}".encode("utf-8")
    )


def _aggregate_hash(entries: Mapping[str, bytes]) -> str:
    manifest = [
        {"path": path, "bytes": len(raw), "sha256": _sha256(raw)}
        for path, raw in sorted(entries.items())
    ]
    return _sha256(_canonical_json(manifest))


def _structural_counts(value: Any) -> dict[str, int]:
    counts = {"arrays": 0, "booleans": 0, "mappings": 0, "nulls": 0, "numbers": 0, "strings": 0}

    def visit(child: Any) -> None:
        if isinstance(child, Mapping):
            counts["mappings"] += 1
            for grandchild in child.values():
                visit(grandchild)
        elif isinstance(child, list):
            counts["arrays"] += 1
            for grandchild in child:
                visit(grandchild)
        elif child is None:
            counts["nulls"] += 1
        elif isinstance(child, bool):
            counts["booleans"] += 1
        elif isinstance(child, (int, float)):
            counts["numbers"] += 1
        elif isinstance(child, str):
            counts["strings"] += 1
        else:
            raise CustodyError("invalid_json_value")

    visit(value)
    return counts


def build_custody_bundle(
    dataset_root: Path,
    source: SourceIdentity,
    *,
    expected: CensusCounts = OFFICIAL_COUNTS,
) -> CustodyBundle:
    """Build isolated projections after validating the complete fixed source."""

    dataset_root = Path(dataset_root)
    census = census_source(dataset_root, source, expected=expected)
    entries: dict[str, bytes] = {}
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    common_lean = _read_regular(dataset_root / "Common.lean")
    entries["evaluator/shared/Common.lean"] = common_lean

    reformulations = dataset_root / "reformulations"
    for problem_path in sorted(
        reformulations.iterdir(), key=lambda path: path.name.encode("utf-8")
    ):
        problem_match = _PROBLEM.fullmatch(problem_path.name)
        if problem_match is None:
            raise CustodyError("invalid_problem_identity")
        problem_id = int(problem_match.group(1))
        source_problem = dataset_root / "problems" / problem_path.name
        description_raw = _read_regular(source_problem / "description.md")
        try:
            description = description_raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CustodyError("problem_description_not_utf8") from exc
        problem_raw, problem = _load_json(source_problem / "problem.json")
        data_raw, _data = _load_json(source_problem / "data.json")
        solution_raw, _solution = _load_json(source_problem / "solution.json")
        problem_inference = _sanitize(problem, omit=frozenset({"name"}))

        optional_problem_code: dict[str, bytes] = {}
        for optional_name in sorted(_PROBLEM_OPTIONAL):
            optional_path = source_problem / optional_name
            try:
                optional_path.lstat()
            except FileNotFoundError:
                continue
            optional_problem_code[optional_name] = _read_regular(optional_path)

        for pair_path in sorted(
            problem_path.iterdir(), key=lambda path: path.name.encode("utf-8")
        ):
            pair_match = _PAIR.fullmatch(pair_path.name)
            if pair_match is None:
                raise CustodyError("invalid_pair_identity")
            left_id, right_id = pair_match.groups()
            opaque = _opaque_pair_id(source, problem_id, pair_path.name)
            if opaque in seen:
                raise CustodyError("duplicate_opaque_identity")
            seen.add(opaque)

            left_root = source_problem / "formulations" / left_id
            right_root = source_problem / "formulations" / right_id
            left_raw, left = _load_json(left_root / "formulation.json")
            right_raw, right = _load_json(right_root / "formulation.json")
            map_raw, parameter_map = _load_json(pair_path / "map.json")
            if not isinstance(left.get("valid"), bool) or not isinstance(
                right.get("valid"), bool
            ):
                raise CustodyError("missing_formulation_validity")
            if not left["valid"]:
                raise CustodyError("invalid_pair_source_formulation")
            proof_path = pair_path / "Reformulation.lean"
            try:
                proof_info = proof_path.lstat()
            except FileNotFoundError:
                proof_present = False
                proof_raw = None
            else:
                if not stat.S_ISREG(proof_info.st_mode):
                    raise CustodyError("unsafe_required_file")
                proof_present = True
                proof_raw = _read_regular(proof_path)
            if right["valid"] != proof_present:
                raise CustodyError("label_proof_mismatch")

            inference = {
                "schema": "llm4or-formulationbench-inference-pair-v1",
                "opaque_id": opaque,
                "source_commit": source.commit,
                "source_tree": source.dataset_tree,
                "problem_description": description,
                "problem": problem_inference,
                "formulation_a": _sanitize(
                    left, omit=frozenset({"imports", "valid"})
                ),
                "formulation_b": _sanitize(
                    right, omit=frozenset({"imports", "valid"})
                ),
                "parameter_map": _sanitize(parameter_map, omit=frozenset()),
            }
            _reject_inference_sensitive_keys(inference)
            inference_raw = _canonical_json(inference)
            entries[f"inference/{opaque}/pair.json"] = inference_raw

            label_raw = _canonical_json(
                {
                    "schema": "llm4or-formulationbench-evaluator-label-v1",
                    "opaque_id": opaque,
                    "equivalent": right["valid"],
                    "source_commit": source.commit,
                    "source_tree": source.dataset_tree,
                }
            )
            evaluator_prefix = f"evaluator/{opaque}"
            entries[f"{evaluator_prefix}/label.json"] = label_raw
            entries[f"{evaluator_prefix}/description.md"] = description_raw
            entries[f"{evaluator_prefix}/problem.json"] = problem_raw
            entries[f"{evaluator_prefix}/data.json"] = data_raw
            entries[f"{evaluator_prefix}/solution.json"] = solution_raw
            entries[f"{evaluator_prefix}/map.json"] = map_raw
            entries[f"{evaluator_prefix}/formulation_a/formulation.json"] = left_raw
            entries[f"{evaluator_prefix}/formulation_b/formulation.json"] = right_raw
            for arm, formulation_root in (
                ("a", left_root),
                ("b", right_root),
            ):
                entries[
                    f"{evaluator_prefix}/formulation_{arm}/Formulation.lean"
                ] = _read_regular(formulation_root / "Formulation.lean")
                entries[
                    f"{evaluator_prefix}/formulation_{arm}/gen_params.py"
                ] = _read_regular(formulation_root / "gen_params.py")
            for name, raw in sorted(optional_problem_code.items()):
                entries[f"{evaluator_prefix}/problem_code/{name}"] = raw
            if proof_raw is not None:
                entries[f"{evaluator_prefix}/Reformulation.lean"] = proof_raw

            metadata = {
                "schema": "llm4or-formulationbench-answer-free-metadata-v1",
                "opaque_id": opaque,
                "source_commit": source.commit,
                "source_tree": source.dataset_tree,
                "inference_bytes": len(inference_raw),
                "inference_sha256": _sha256(inference_raw),
                "inference_structure": _structural_counts(inference),
                "privacy": {
                    "contains_code_bodies": False,
                    "contains_data_values": False,
                    "contains_solutions": False,
                    "contains_source_paths": False,
                },
            }
            metadata_raw = _canonical_json(metadata)
            entries[f"metadata/{opaque}.json"] = metadata_raw
            records.append(
                {
                    "opaque_id": opaque,
                    "source_problem": problem_path.name,
                    "source_pair": pair_path.name,
                    "equivalent": right["valid"],
                    "proof_present": proof_present,
                    "inference_sha256": _sha256(inference_raw),
                    "metadata_sha256": _sha256(metadata_raw),
                    "label_sha256": _sha256(label_raw),
                    "raw_hashes": {
                        "data": _sha256(data_raw),
                        "description": _sha256(description_raw),
                        "formulation_a": _sha256(left_raw),
                        "formulation_b": _sha256(right_raw),
                        "map": _sha256(map_raw),
                        "problem": _sha256(problem_raw),
                        "solution": _sha256(solution_raw),
                        "proof": _sha256(proof_raw) if proof_raw is not None else None,
                    },
                }
            )

    private_ledger: dict[str, Any] = {
        "schema": "llm4or-formulationbench-private-custody-ledger-v1",
        "source": {"commit": source.commit, "dataset_tree": source.dataset_tree},
        "records": records,
    }
    ledger_raw = _canonical_json(private_ledger)
    entries["private/ledger.json"] = ledger_raw
    public_entries = {
        path: raw
        for path, raw in entries.items()
        if path.startswith(("inference/", "metadata/"))
    }
    evaluator_entries = {
        path: raw for path, raw in entries.items() if path.startswith("evaluator/")
    }
    public_audit: dict[str, Any] = {
        "schema": "llm4or-formulationbench-custody-audit-v1",
        "status": "built_not_published",
        "source": {"commit": source.commit, "dataset_tree": source.dataset_tree},
        "counts": dict(census["counts"]),
        "census_sha256": _sha256(_canonical_json(census)),
        "inference_metadata_projection_sha256": _aggregate_hash(public_entries),
        "evaluator_projection_sha256": _aggregate_hash(evaluator_entries),
        "private_ledger_sha256": _sha256(ledger_raw),
        "bundle_sha256": _aggregate_hash(entries),
        "privacy": {
            "contains_code_bodies": False,
            "contains_data_values": False,
            "contains_pair_labels": False,
            "contains_problem_bodies": False,
            "contains_proof_bodies": False,
            "contains_solutions": False,
            "contains_source_paths": False,
        },
        "execution": {
            "api_calls": 0,
            "credentials_read": False,
            "lean_calls": 0,
            "model_calls": 0,
            "solver_calls": 0,
            "vm_calls": 0,
        },
        "claim_boundary": (
            "This audit proves deterministic source separation only; it does not "
            "authorize inference or report benchmark accuracy."
        ),
    }
    return CustodyBundle(
        entries=dict(sorted(entries.items())),
        public_audit=public_audit,
        private_ledger=private_ledger,
    )


FaultHook = Callable[[str], None]


def _invoke_fault(hook: FaultHook | None, phase: str) -> None:
    if hook is not None:
        hook(phase)


def publish_custody_bundle(
    root: Path,
    bundle: CustodyBundle,
    *,
    _fault: FaultHook | None = None,
) -> PublicationResult:
    """Publish a complete generation with no partially visible terminal root."""

    root = Path(root)
    if root.name in {"", ".", ".."}:
        raise PublicationBoundaryError("publication_path_escape")
    parent = root.parent
    try:
        parent_info = parent.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise PublicationBoundaryError("publication_root_parent_missing") from exc
    if not stat.S_ISDIR(parent_info.st_mode):
        raise PublicationBoundaryError("publication_root_parent_unsafe")
    try:
        root_info = root.lstat()
    except FileNotFoundError:
        root_info = None
    if root_info is not None:
        if not stat.S_ISDIR(root_info.st_mode):
            raise PublicationBoundaryError("publication_terminal_not_directory")
        check_custody_bundle(root, bundle)
        return PublicationResult(
            transaction_id=str(bundle.public_audit["bundle_sha256"]),
            created=(),
            identical=tuple(sorted(bundle.entries)),
        )

    transaction = str(bundle.public_audit["bundle_sha256"])
    staging = parent / f".{root.name}.llm4or-{transaction}.tmp"
    try:
        staging_info = staging.lstat()
    except FileNotFoundError:
        staging_info = None
    if staging_info is not None:
        if not stat.S_ISDIR(staging_info.st_mode):
            raise PublicationBoundaryError("publication_staging_unsafe")
        shutil.rmtree(staging)
    staging.mkdir(mode=0o700)
    try:
        publish_bundle(staging, bundle.entries)
        check_custody_bundle(staging, bundle)
        _invoke_fault(_fault, "stage_complete")
        if root.exists():
            check_custody_bundle(root, bundle)
            shutil.rmtree(staging)
            return PublicationResult(
                transaction_id=transaction,
                created=(),
                identical=tuple(sorted(bundle.entries)),
            )
        os.rename(staging, root)
        parent_descriptor = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
        _invoke_fault(_fault, "published")
        return PublicationResult(
            transaction_id=transaction,
            created=tuple(sorted(bundle.entries)),
            identical=(),
        )
    except Exception:
        try:
            staging_info = staging.lstat()
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISDIR(staging_info.st_mode):
                shutil.rmtree(staging)
        raise


def _terminal_files(root: Path) -> set[str]:
    terminals: set[str] = set()
    pending = [(root, ())]
    while pending:
        directory, prefix = pending.pop()
        try:
            children = list(os.scandir(directory))
        except OSError as exc:
            raise CustodyError("check_unsafe_path") from exc
        for child in children:
            if not prefix and child.name == ".llm4or-publication-journal":
                if child.is_symlink() or not child.is_dir(follow_symlinks=False):
                    raise CustodyError("check_unsafe_path")
                continue
            relative = PurePosixPath(*prefix, child.name).as_posix()
            if child.is_symlink():
                raise CustodyError("check_unsafe_path")
            if child.is_dir(follow_symlinks=False):
                pending.append((Path(child.path), (*prefix, child.name)))
            elif child.is_file(follow_symlinks=False):
                terminals.add(relative)
            else:
                raise CustodyError("check_unsafe_path")
    return terminals


def check_custody_bundle(root: Path, bundle: CustodyBundle) -> None:
    """Verify exact path and byte identity for a published custody generation."""

    root = Path(root)
    try:
        info = root.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise CustodyError("check_root_missing") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CustodyError("check_root_unsafe")
    if _terminal_files(root) != set(bundle.entries):
        raise CustodyError("check_path_set_drift")
    for relative, expected in sorted(bundle.entries.items()):
        supplied = PurePosixPath(relative)
        if supplied.is_absolute() or any(
            part in {"", ".", ".."} for part in supplied.parts
        ):
            raise CustodyError("check_unsafe_expected_path")
        observed = _read_regular(root.joinpath(*supplied.parts), "check_unsafe_path")
        if observed != expected:
            raise CustodyError("check_drift")
