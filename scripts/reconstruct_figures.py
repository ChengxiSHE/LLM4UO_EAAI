#!/usr/bin/env python3
"""Rebuild both main figures in a fresh temporary tree and compare them safely."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements-figures.txt"
RENDERERS = (
    "scripts/render_main_figure1.py",
    "scripts/render_main_figure2.py",
)
SUPPORT = "scripts/audit_panel_alignment.py"
SOURCE_DATA = (
    "manuscript/source_data/figure2_endpoint_summary.csv",
    "manuscript/source_data/figure2_group_summary.csv",
    "manuscript/source_data/figure2_router_identity.csv",
    "manuscript/source_data/figure2_tsp_by_size.csv",
)
FIGURES = (
    "figure1_knowledge_compilation",
    "figure2_endpoint_preservation",
)
FORMATS = ("pdf", "svg", "png", "tiff")
REQUIRED_PATHS = (
    "requirements-figures.txt",
    SUPPORT,
    *RENDERERS,
    *SOURCE_DATA,
)
SANITIZED_ENVIRONMENT_KEYS = (
    "FIGURE_QA_SCRIPTS",
    "HOME",
    "LANG",
    "LC_ALL",
    "MPLCONFIGDIR",
    "PATH",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONHASHSEED",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def normalize_svg(data: bytes) -> bytes:
    normalized = re.sub(
        rb"<dc:date>[^<]*</dc:date>",
        b"<dc:date>REPRODUCIBLE_TIMESTAMP</dc:date>",
        data,
        count=1,
    )
    identifiers: dict[bytes, bytes] = {}
    counts = {b"m": 0, b"p": 0}

    def replace_identifier(match: re.Match[bytes]) -> bytes:
        identifier = match.group(0)
        if identifier not in identifiers:
            prefix = identifier[:1]
            identifiers[identifier] = prefix + f"{counts[prefix]:010d}".encode()
            counts[prefix] += 1
        return identifiers[identifier]

    return re.sub(rb"\b[mp][0-9a-f]{10}\b", replace_identifier, normalized)


def normalize_pdf(data: bytes) -> bytes:
    return re.sub(
        rb"/CreationDate\s*\(D:[^)]*\)",
        b"/CreationDate (D:REPRODUCIBLE_TIMESTAMP)",
        data,
        count=1,
    )


def normalization_policy() -> dict[str, list[str]]:
    return {
        "pdf": ["CreationDate"],
        "svg": ["dc:date", "Matplotlib internal m/p identifier names"],
        "png": [],
        "tiff": [],
    }


def _requirement_versions(path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(f"unpinned requirement: {line}")
        name, version = line.split("==", 1)
        versions[name.lower().replace("_", "-")] = version
    return versions


def _installed_versions() -> dict[str, str]:
    return {
        distribution.metadata["Name"].lower().replace("_", "-"): distribution.version
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }


def _tracked_paths() -> set[str]:
    completed = subprocess.run(
        ["git", "ls-files", "--", *REQUIRED_PATHS],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return {line for line in completed.stdout.splitlines() if line}


def preflight() -> dict[str, Any]:
    tracked = _tracked_paths()
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).is_file()]
    untracked = [path for path in REQUIRED_PATHS if path not in tracked]
    inputs = {
        path: file_sha256(ROOT / path)
        for path in REQUIRED_PATHS
        if (ROOT / path).is_file()
    }
    passed = not missing and not untracked
    return {
        "schema": "llm4or-figure-reconstruction-preflight-v1",
        "status": "preflight_passed" if passed else "preflight_failed",
        "all_required_paths_tracked": not untracked,
        "missing_paths": missing,
        "untracked_paths": untracked,
        "input_sha256": inputs,
        "execution": {
            "model_calls": 0,
            "api_calls": 0,
            "solver_calls": 0,
            "native_evaluator_calls": 0,
            "vm_calls": 0,
            "request_or_response_bodies_read": False,
            "evaluator_only_answers_read": False,
            "credentials_read": False,
        },
    }


def _copy_inputs(target: Path) -> None:
    for relative in (*RENDERERS, SUPPORT, *SOURCE_DATA):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)


def _sanitized_environment(target: Path) -> dict[str, str]:
    home = target / "empty-home"
    mpl_config = target / "mpl-config"
    home.mkdir()
    mpl_config.mkdir()
    return {
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "MPLCONFIGDIR": str(mpl_config),
        "FIGURE_QA_SCRIPTS": str(target / "scripts"),
    }


def _pdf_text_summary(path: Path) -> dict[str, Any]:
    import fitz

    document = fitz.open(path)
    sizes: list[float] = []
    text_runs = 0
    for page in document:
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if str(span.get("text", "")).strip():
                        text_runs += 1
                        sizes.append(float(span["size"]))
    return {
        "pages": document.page_count,
        "text_runs": text_runs,
        "minimum_font_pt": min(sizes) if sizes else None,
        "minimum_required_pt": 5.0,
        "font_floor_passed": bool(sizes) and min(sizes) >= 5.0 - 1e-6,
    }


def _compare_output(reference: Path, rebuilt: Path, extension: str) -> dict[str, Any]:
    reference_bytes = reference.read_bytes()
    rebuilt_bytes = rebuilt.read_bytes()
    if extension == "svg":
        equivalent = normalize_svg(reference_bytes) == normalize_svg(rebuilt_bytes)
        comparison = "byte_identity_after_dc_date_and_internal_id_canonicalization"
    elif extension == "pdf":
        equivalent = normalize_pdf(reference_bytes) == normalize_pdf(rebuilt_bytes)
        comparison = "byte_identity_after_creation_date_normalization"
    else:
        equivalent = reference_bytes == rebuilt_bytes
        comparison = "raw_byte_identity"
    return {
        "format": extension,
        "reference_sha256": sha256(reference_bytes),
        "rebuilt_sha256": sha256(rebuilt_bytes),
        "comparison": comparison,
        "equivalent": equivalent,
    }


def reconstruct() -> dict[str, Any]:
    preflight_report = preflight()
    declared = _requirement_versions(REQUIREMENTS)
    installed = _installed_versions()
    mismatches = {
        name: {"expected": version, "observed": installed.get(name)}
        for name, version in declared.items()
        if installed.get(name) != version
    }
    if preflight_report["status"] != "preflight_passed" or mismatches:
        return {
            "schema": "llm4or-figure-reconstruction-audit-v1",
            "status": "preflight_failed",
            "preflight": preflight_report,
            "environment_mismatches": mismatches,
            "execution": preflight_report["execution"],
        }

    with tempfile.TemporaryDirectory(prefix="llm4or-figure-rebuild-") as directory:
        target = Path(directory)
        _copy_inputs(target)
        environment = _sanitized_environment(target)
        commands: list[dict[str, Any]] = []
        for relative in RENDERERS:
            completed = subprocess.run(
                [sys.executable, str(target / relative)],
                cwd=target,
                env=environment,
                text=True,
                capture_output=True,
            )
            commands.append({
                "renderer": relative,
                "returncode": completed.returncode,
                "stdout_sha256": sha256(completed.stdout.encode()),
                "stderr_sha256": sha256(completed.stderr.encode()),
            })
            if completed.returncode:
                return {
                    "schema": "llm4or-figure-reconstruction-audit-v1",
                    "status": "render_failed",
                    "preflight": preflight_report,
                    "environment_mismatches": {},
                    "commands": commands,
                    "execution": preflight_report["execution"],
                }

        figures: list[dict[str, Any]] = []
        for stem in FIGURES:
            rebuilt_base = target / "manuscript" / "figures" / stem
            reference_base = ROOT / "manuscript" / "figures" / stem
            alignment = json.loads(rebuilt_base.with_suffix(".alignment.json").read_text())
            outputs = [
                _compare_output(
                    reference_base.with_suffix(f".{extension}"),
                    rebuilt_base.with_suffix(f".{extension}"),
                    extension,
                )
                for extension in FORMATS
            ]
            text_summary = _pdf_text_summary(rebuilt_base.with_suffix(".pdf"))
            figures.append({
                "stem": stem,
                "alignment_verdict": alignment.get("verdict"),
                "alignment_summary": alignment.get("summary"),
                "outputs": outputs,
                "pdf_text": text_summary,
                "passed": (
                    alignment.get("verdict") == "PASS"
                    and all(output["equivalent"] for output in outputs)
                    and text_summary["font_floor_passed"]
                ),
            })

    passed = all(command["returncode"] == 0 for command in commands) and all(
        figure["passed"] for figure in figures
    )
    return {
        "schema": "llm4or-figure-reconstruction-audit-v1",
        "status": "passed_clean_temporary_figure_reconstruction" if passed else "comparison_failed",
        "python": sys.version.split()[0],
        "declared_environment": declared,
        "environment_mismatches": {},
        "preflight": preflight_report,
        "sanitized_environment_keys": list(SANITIZED_ENVIRONMENT_KEYS),
        "normalization_policy": normalization_policy(),
        "commands": commands,
        "figures": figures,
        "boundaries": [
            "PDF normalization is limited to CreationDate. SVG normalization is limited to dc:date and self-consistent Matplotlib internal m/p identifier names; drawing content and geometry are not normalized.",
            "PNG and TIFF require raw byte identity.",
            "The rebuild uses a new temporary tree and starts without prior figure outputs.",
            "Pixel identity transfers the already recorded collision and final-size visual QA only to these exact rebuilt pixels.",
            "This layer makes no provider, solver, native-evaluator or VM call and reads no credential.",
        ],
        "execution": preflight_report["execution"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--audit-out")
    args = parser.parse_args()
    report = preflight() if args.preflight_only else reconstruct()
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.audit_out:
        output = Path(args.audit_out)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    if args.check or args.preflight_only:
        return 0 if report["status"] in {
            "preflight_passed",
            "passed_clean_temporary_figure_reconstruction",
        } else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
