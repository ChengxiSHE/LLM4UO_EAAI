"""Byte-preserving adapters for the nine audited historical publishers.

The historical producers are immutable provenance.  These adapters verify each
source hash, capture its already serialized terminal bytes at the narrowest
existing write seam, and delegate ownership/durability to ``atomic_publisher``.
"""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Callable, Mapping

from .atomic_publisher import PublicationResult, publish_bundle
from .schema import canonical


class AdapterError(RuntimeError):
    """A historical producer or its captured output violates the frozen bind."""


@dataclass(frozen=True)
class PublisherSpec:
    identifier: str
    source_path: str
    source_sha256: str
    outputs: tuple[str, ...]
    builder: str


def encode_compact(value: object) -> bytes:
    return (canonical(value) + "\n").encode("utf-8")


def encode_pretty_strict(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def encode_pretty_default(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


PUBLISHERS = {
    spec.identifier: spec
    for spec in (
        PublisherSpec(
            "external-cohort-audit",
            "scripts/audit_external_comparison_cohorts.py",
            "88a3338ebeb60608b68a2b49067b73f9bb0f179d8dc9821b9ad653462383ea3d",
            ("results/external_comparison_cohort_audit.json",),
            "external_cohort_audit",
        ),
        PublisherSpec(
            "bind-common40",
            "scripts/evaluate_bind_common40_union.py",
            "4030011751843354d2d8eb0756cdddbb029046e5f079f56c66400ee9f1740c14",
            ("results/bind_fixed_common40.json",),
            "captured_compact_evaluate",
        ),
        PublisherSpec(
            "coe-common40",
            "scripts/evaluate_coe_common40_union.py",
            "8e86aa778069ec56de4172279b5cb8d0789f5c3594a3324878ef2caac5d04ab6",
            ("results/coe_fixed_common40.json",),
            "captured_compact_evaluate",
        ),
        PublisherSpec(
            "or-debug-confirmation-evaluation",
            "scripts/evaluate_or_debug_confirmation.py",
            "b7ae44c3d3367e5401ab3aee052de1b7ab9c9a0e4529d8429e0d59c122badd74",
            ("results/or_debug_confirmation_evaluation_20261014.json",),
            "redirected_output_main",
        ),
        PublisherSpec(
            "tsp-confirmation-evaluation",
            "scripts/evaluate_tsp_constraint_confirmation.py",
            "304445d047e119f0d1b64521975430efd963caf89c548a24ee243a06a769c1b0",
            (
                "results/private/tsp_constraint_confirmation_evaluation_20261014.json",
                "results/tsp_constraint_confirmation_evaluation_20261014.json",
            ),
            "captured_write_new_main",
        ),
        PublisherSpec(
            "tsp-promotion-evaluation",
            "scripts/evaluate_tsp_constraint_promotion.py",
            "0347b56d5cb11b6063537dbc775eae17f2cc9a72cf175265d997685a2e444ac7",
            (
                "results/private/tsp_constraint_promotion_evaluation_20261014.json",
                "results/tsp_constraint_promotion_evaluation_20261014.json",
            ),
            "captured_write_new_main",
        ),
        PublisherSpec(
            "or-debug-confirmation-methods",
            "scripts/run_or_debug_confirmation_methods.py",
            "3ecc7f014deba013a9d8305777b517873492205bbb81b96ed551470beab3f4e9",
            ("results/or_debug_confirmation_method_outputs_20261014.json",),
            "redirected_output_main",
        ),
        PublisherSpec(
            "tsp-confirmation-candidates",
            "scripts/run_tsp_constraint_confirmation.py",
            "ed977e5ca6c01ae4e95316c5ee02feffddbe2e322b15a5b5e5d274b799e33e75",
            (
                "results/private/tsp_constraint_confirmation_candidates_20261014.json",
                "results/tsp_constraint_confirmation_candidates_20261014.json",
            ),
            "captured_write_new_main",
        ),
        PublisherSpec(
            "external-common40-summary",
            "scripts/summarize_external_common40.py",
            "86208c6d9452890e5e5ef354576665f65a36b20ba665c330712c62046789e4aa",
            (
                "results/external_fixed_common40_summary.json",
                "docs/EXTERNAL_FIXED_COMMON40_RESULTS.md",
            ),
            "staged_external_summary",
        ),
    )
}


def _verify_source(root: Path, spec: PublisherSpec) -> Path:
    source = root / spec.source_path
    try:
        observed = hashlib.sha256(source.read_bytes()).hexdigest()
    except (FileNotFoundError, OSError) as exc:
        raise AdapterError("producer_source_missing") from exc
    if observed != spec.source_sha256:
        raise AdapterError("producer_source_sha256_mismatch")
    return source


def _load_source(root: Path, spec: PublisherSpec) -> ModuleType:
    source = _verify_source(root, spec)
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    module_name = "_llm4or_historical_" + spec.identifier.replace("-", "_")
    module_spec = importlib.util.spec_from_file_location(module_name, source)
    if module_spec is None or module_spec.loader is None:
        raise AdapterError("producer_import_spec")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    try:
        module_spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _relative(root: Path, path: Path | str) -> str:
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except (ValueError, OSError, RuntimeError) as exc:
        raise AdapterError("captured_output_path_escape") from exc


def _capture_compact_evaluate(
    root: Path, module: ModuleType, spec: PublisherSpec
) -> dict[str, bytes]:
    captured: dict[str, bytes] = {}
    original = module.write_json
    original_root = module.ROOT

    def capture(path, value):
        relative = _relative(root, path)
        if relative in captured:
            raise AdapterError("captured_output_duplicate")
        captured[relative] = encode_compact(value)

    module.ROOT = root
    module.write_json = capture
    try:
        module.evaluate()
    finally:
        module.write_json = original
        module.ROOT = original_root
    return captured


def _capture_write_new_main(
    root: Path, module: ModuleType, spec: PublisherSpec
) -> dict[str, bytes]:
    captured: dict[str, bytes] = {}
    original = module._write_new

    def capture(path, value):
        relative = _relative(root, path)
        if relative in captured:
            raise AdapterError("captured_output_duplicate")
        captured[relative] = module._encoded(value)

    module._write_new = capture
    try:
        module.main()
    finally:
        module._write_new = original
    return captured


def _redirected_output_main(
    root: Path, module: ModuleType, spec: PublisherSpec
) -> dict[str, bytes]:
    original = module.OUTPUT
    with tempfile.TemporaryDirectory(prefix="llm4or-publisher-stage-") as directory:
        staged = Path(directory) / Path(spec.outputs[0]).name
        module.OUTPUT = staged
        try:
            result = module.main()
            if result not in (None, 0):
                raise AdapterError("producer_nonzero_return")
            if not staged.is_file():
                raise AdapterError("producer_terminal_missing")
            return {spec.outputs[0]: staged.read_bytes()}
        finally:
            module.OUTPUT = original


def _external_cohort_audit(
    root: Path, module: ModuleType, spec: PublisherSpec
) -> dict[str, bytes]:
    return {spec.outputs[0]: encode_pretty_strict(module.audit(root))}


def _staged_external_summary(
    root: Path, module: ModuleType, spec: PublisherSpec
) -> dict[str, bytes]:
    with tempfile.TemporaryDirectory(prefix="llm4or-summary-stage-") as directory:
        stage = Path(directory)
        (stage / "data").symlink_to(root / "data", target_is_directory=True)
        (stage / "experiments").symlink_to(
            root / "experiments", target_is_directory=True
        )
        (stage / "results").mkdir()
        (stage / "docs").mkdir()
        for relative in module.REPORTS.values():
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(root / relative)
        module.summarize(stage)
        return {relative: (stage / relative).read_bytes() for relative in spec.outputs}


_BUILDERS: Mapping[
    str, Callable[[Path, ModuleType, PublisherSpec], dict[str, bytes]]
] = {
    "external_cohort_audit": _external_cohort_audit,
    "captured_compact_evaluate": _capture_compact_evaluate,
    "captured_write_new_main": _capture_write_new_main,
    "redirected_output_main": _redirected_output_main,
    "staged_external_summary": _staged_external_summary,
}


def _run_builder_quietly(
    builder: Callable[[Path, ModuleType, PublisherSpec], dict[str, bytes]],
    root: Path,
    module: ModuleType,
    spec: PublisherSpec,
) -> dict[str, bytes]:
    """Keep historical progress prints off the CLI's single-result channel."""

    with redirect_stdout(io.StringIO()):
        return builder(root, module, spec)


def _publish_captured(
    root: Path, spec: PublisherSpec, captured: Mapping[str, bytes]
) -> PublicationResult:
    expected = set(spec.outputs)
    if set(captured) != expected:
        raise AdapterError("captured_output_inventory")
    if any(type(value) is not bytes or not value for value in captured.values()):
        raise AdapterError("captured_output_bytes")
    return publish_bundle(root, dict(captured))


def run_publisher(name: str, root: Path) -> PublicationResult:
    """Run exactly one bound producer and durably publish its captured bytes."""

    try:
        spec = PUBLISHERS[name]
    except KeyError as exc:
        raise AdapterError("unknown_publisher") from exc
    root = Path(root).resolve(strict=True)
    module = _load_source(root, spec)
    try:
        builder = _BUILDERS[spec.builder]
    except KeyError as exc:
        raise AdapterError("unknown_builder") from exc
    captured = _run_builder_quietly(builder, root, module, spec)
    return _publish_captured(root, spec, captured)
