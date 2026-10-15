"""Durable, root-confined, no-clobber publication of pre-serialized bytes.

This module deliberately knows nothing about scientific schemas or JSON
serialization.  Callers supply the exact terminal bytes they want to publish.
"""

from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Callable, Mapping
import uuid


class PublicationConflict(RuntimeError):
    """A durable reservation or terminal contains different bytes."""


class PublicationBoundaryError(ValueError):
    """A publication path violates the trusted-root or file-type boundary."""


@dataclass(frozen=True)
class PublicationResult:
    transaction_id: str
    created: tuple[str, ...]
    identical: tuple[str, ...]


FaultHook = Callable[[str], None]
_JOURNAL_DIRECTORY = ".llm4or-publication-journal"


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _normalized_root(root: Path | str) -> Path:
    try:
        value = Path(root).resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        raise PublicationBoundaryError("publication_root_missing_or_invalid") from exc
    if not value.is_dir():
        raise PublicationBoundaryError("publication_root_not_directory")
    return value


def _relative_path(
    root: Path, path: Path | str, *, lexical_root: Path | None = None
) -> str:
    supplied = Path(path)
    if supplied.is_absolute():
        absolute = Path(os.path.abspath(os.fspath(supplied)))
        roots = (lexical_root, root) if lexical_root is not None else (root,)
        for candidate_root in roots:
            try:
                supplied = absolute.relative_to(candidate_root)
                break
            except ValueError:
                continue
        else:
            raise PublicationBoundaryError("publication_path_escape")
    if any(part == ".." for part in supplied.parts):
        raise PublicationBoundaryError("publication_path_escape")
    normalized = os.path.normpath(os.fspath(supplied))
    candidate = Path(normalized)
    if (
        normalized in ("", ".")
        or candidate.is_absolute()
        or any(part in ("", ".", "..") for part in candidate.parts)
    ):
        raise PublicationBoundaryError("publication_path_escape")
    return candidate.as_posix()


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _open_parent(root: Path, relative: str, *, create: bool) -> tuple[int, str]:
    parts = Path(relative).parts
    descriptor = os.open(root, _directory_flags())
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, _directory_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, 0o755, dir_fd=descriptor)
                    os.fsync(descriptor)
                except FileExistsError:
                    pass
                try:
                    child = os.open(part, _directory_flags(), dir_fd=descriptor)
                except OSError as exc:
                    raise PublicationBoundaryError(
                        "publication_parent_not_safe_directory"
                    ) from exc
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise PublicationBoundaryError(
                        "publication_parent_not_safe_directory"
                    ) from exc
                raise
            os.close(descriptor)
            descriptor = child
        return descriptor, parts[-1]
    except Exception:
        os.close(descriptor)
        raise


def _read_descriptor(descriptor: int) -> bytes:
    chunks = []
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _read_regular(parent: int, name: str) -> bytes | None:
    try:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise PublicationBoundaryError("publication_terminal_not_regular")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise PublicationBoundaryError("publication_terminal_not_regular") from exc
        raise
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise PublicationBoundaryError("publication_terminal_not_regular")
        return _read_descriptor(descriptor)
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("publication_short_write")
        view = view[written:]


def _link_bytes(parent: int, name: str, payload: bytes, *, mode: int = 0o644) -> bool:
    """Publish bytes under *name* without replacement; return True if created."""

    existing = _read_regular(parent, name)
    if existing is not None:
        if existing != payload:
            raise PublicationConflict("publication_existing_bytes_differ")
        return False
    temporary = f".{name}.llm4or-{uuid.uuid4().hex}.tmp"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(temporary, flags, mode, dir_fd=parent)
    linked = False
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(
                temporary,
                name,
                src_dir_fd=parent,
                dst_dir_fd=parent,
                follow_symlinks=False,
            )
            linked = True
            os.fsync(parent)
            return True
        except FileExistsError:
            existing = _read_regular(parent, name)
            if existing != payload:
                raise PublicationConflict("publication_existing_bytes_differ")
            return False
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)
        except FileNotFoundError:
            if not linked:
                pass


def _remove_exact(parent: int, name: str, expected: bytes) -> None:
    current = _read_regular(parent, name)
    if current is None:
        return
    if current != expected:
        raise PublicationConflict("publication_reservation_changed")
    try:
        os.unlink(name, dir_fd=parent)
    except FileNotFoundError:
        # A concurrent byte-identical replay may have completed the same cleanup
        # after our exact-byte check.  No differing owner can reach this point.
        return
    os.fsync(parent)


def _invoke_fault(hook: FaultHook | None, phase: str) -> None:
    if hook is not None:
        hook(phase)


def publish_bytes(
    root: Path | str,
    path: Path | str,
    payload: bytes,
    *,
    _fault: FaultHook | None = None,
) -> PublicationResult:
    """Publish one immutable terminal or confirm a byte-identical terminal."""

    return publish_bundle(root, {path: payload}, _fault=_fault)


def publish_bundle(
    root: Path | str,
    entries: Mapping[Path | str, bytes],
    *,
    _fault: FaultHook | None = None,
) -> PublicationResult:
    """Publish all entries as one replay-recoverable no-clobber transaction."""

    lexical_root = Path(os.path.abspath(os.fspath(root)))
    trusted_root = _normalized_root(root)
    if not entries:
        raise PublicationBoundaryError("publication_bundle_empty")
    normalized: dict[str, bytes] = {}
    for supplied_path, payload in entries.items():
        if type(payload) is not bytes or not payload:
            raise PublicationBoundaryError(
                "publication_payload_must_be_nonempty_bytes"
            )
        relative = _relative_path(
            trusted_root, supplied_path, lexical_root=lexical_root
        )
        if relative in normalized:
            raise PublicationBoundaryError("publication_duplicate_normalized_path")
        normalized[relative] = payload

    manifest = {
        "schema": "llm4or-publication-transaction-v1",
        "entries": [
            {
                "path": relative,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for relative, payload in sorted(normalized.items())
        ],
    }
    manifest_bytes = _canonical(manifest)
    transaction_id = hashlib.sha256(manifest_bytes).hexdigest()
    journal_relative = f"{_JOURNAL_DIRECTORY}/{transaction_id}.json"

    destinations: list[dict[str, object]] = []
    for relative, payload in sorted(normalized.items()):
        parent, name = _open_parent(trusted_root, relative, create=True)
        try:
            before = _read_regular(parent, name)
            if before is not None and before != payload:
                raise PublicationConflict("publication_existing_bytes_differ")
            reservation_name = f".{name}.llm4or-reservation.json"
            reservation = _canonical(
                {
                    "schema": "llm4or-publication-reservation-v1",
                    "transaction_id": transaction_id,
                    "path": relative,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
            destinations.append(
                {
                    "relative": relative,
                    "payload": payload,
                    "parent": parent,
                    "name": name,
                    "reservation_name": reservation_name,
                    "reservation": reservation,
                    "reservation_created": False,
                }
            )
        except Exception:
            os.close(parent)
            for item in destinations:
                os.close(item["parent"])
            raise

    journal_parent = -1
    journal_name = ""
    journal_created = False
    try:
        journal_parent, journal_name = _open_parent(
            trusted_root, journal_relative, create=True
        )
        journal_created = _link_bytes(
            journal_parent, journal_name, manifest_bytes, mode=0o600
        )
        os.fsync(journal_parent)
        _invoke_fault(_fault, "journal_durable")

        for item in destinations:
            item["reservation_created"] = _link_bytes(
                item["parent"],
                item["reservation_name"],
                item["reservation"],
                mode=0o600,
            )
        _invoke_fault(_fault, "reservations_durable")

        created_paths = []
        identical_paths = []
        for item in destinations:
            created = _link_bytes(
                item["parent"], item["name"], item["payload"]
            )
            (created_paths if created else identical_paths).append(item["relative"])
            _invoke_fault(_fault, f"after_publish:{item['relative']}")
        _invoke_fault(_fault, "destinations_durable")
        _invoke_fault(_fault, "before_cleanup")

        for item in destinations:
            _remove_exact(
                item["parent"], item["reservation_name"], item["reservation"]
            )
        _remove_exact(journal_parent, journal_name, manifest_bytes)
        try:
            root_descriptor = os.open(trusted_root, _directory_flags())
            try:
                os.rmdir(_JOURNAL_DIRECTORY, dir_fd=root_descriptor)
                os.fsync(root_descriptor)
            except OSError as exc:
                if exc.errno not in (errno.ENOTEMPTY, errno.ENOENT):
                    raise
            finally:
                os.close(root_descriptor)
        finally:
            _invoke_fault(_fault, "complete")
        return PublicationResult(
            transaction_id=transaction_id,
            created=tuple(created_paths),
            identical=tuple(identical_paths),
        )
    except PublicationConflict:
        for item in reversed(destinations):
            if item["reservation_created"]:
                _remove_exact(
                    item["parent"], item["reservation_name"], item["reservation"]
                )
        if journal_parent >= 0 and journal_created:
            _remove_exact(journal_parent, journal_name, manifest_bytes)
        raise
    finally:
        for item in destinations:
            os.close(item["parent"])
        if journal_parent >= 0:
            os.close(journal_parent)
