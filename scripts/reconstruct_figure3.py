#!/usr/bin/env python3
"""Rebuild Figure 3 in a clean temporary tree and compare the sealed outputs."""

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


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements-figure3.txt"
RENDERER = "scripts/render_main_figure3.py"
SUPPORT = "scripts/audit_panel_alignment.py"
SOURCES = (
    "manuscript/source_data/figure3_retailopt_summary.csv",
    "manuscript/source_data/figure3_retailopt_diagnostics.csv",
)
STEM = "figure3_retailopt_confirmation"
FORMATS = ("pdf", "svg", "png", "tiff")
REQUIRED = ("requirements-figure3.txt", RENDERER, SUPPORT, *SOURCES)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def normalize(data: bytes, extension: str) -> bytes:
    if extension == "pdf":
        return re.sub(rb"/CreationDate\s*\(D:[^)]*\)", b"/CreationDate (D:REPRODUCIBLE_TIMESTAMP)", data, count=1)
    if extension == "svg":
        data = re.sub(rb"<dc:date>[^<]*</dc:date>", b"<dc:date>REPRODUCIBLE_TIMESTAMP</dc:date>", data, count=1)
        identities: dict[bytes, bytes] = {}
        counters = {b"m": 0, b"p": 0}
        def repl(match: re.Match[bytes]) -> bytes:
            value = match.group(0)
            if value not in identities:
                prefix = value[:1]
                identities[value] = prefix + f"{counters[prefix]:010d}".encode()
                counters[prefix] += 1
            return identities[value]
        return re.sub(rb"\b[mp][0-9a-f]{10}\b", repl, data)
    return data


def declared_versions() -> dict[str, str]:
    output = {}
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        output[name.lower().replace("_", "-")] = version
    return output


def tracked() -> set[str]:
    completed = subprocess.run(["git", "ls-files", "--", *REQUIRED], cwd=ROOT, check=True, text=True, capture_output=True)
    return set(completed.stdout.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    untracked = [path for path in REQUIRED if path not in tracked()]
    declared = declared_versions()
    installed = {dist.metadata["Name"].lower().replace("_", "-"): dist.version for dist in importlib.metadata.distributions() if dist.metadata.get("Name")}
    mismatches = {name: {"expected": version, "observed": installed.get(name)} for name, version in declared.items() if installed.get(name) != version}
    report: dict[str, object]
    if missing or untracked or mismatches:
        report = {"schema": "llm4or-figure3-clean-reconstruction-v1", "status": "preflight_failed", "missing": missing, "untracked": untracked, "environment_mismatches": mismatches}
    else:
        with tempfile.TemporaryDirectory(prefix="llm4or-figure3-") as directory:
            target = Path(directory)
            for relative in (RENDERER, SUPPORT, *SOURCES):
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)
            home = target / "home"; mpl = target / "mpl"; home.mkdir(); mpl.mkdir()
            environment = {"HOME": str(home), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "MPLCONFIGDIR": str(mpl), "FIGURE_QA_SCRIPTS": str(target / "scripts")}
            completed = subprocess.run([sys.executable, str(target / RENDERER)], cwd=target, env=environment, text=True, capture_output=True)
            comparisons = []
            if completed.returncode == 0:
                for extension in FORMATS:
                    reference = (ROOT / "manuscript" / "figures" / STEM).with_suffix(f".{extension}")
                    rebuilt = (target / "manuscript" / "figures" / STEM).with_suffix(f".{extension}")
                    comparisons.append({"format": extension, "reference_sha256": file_digest(reference), "rebuilt_sha256": file_digest(rebuilt), "equivalent": normalize(reference.read_bytes(), extension) == normalize(rebuilt.read_bytes(), extension)})
                alignment = json.loads(((target / "manuscript" / "figures" / STEM).with_suffix(".alignment.json")).read_text(encoding="utf-8"))
            else:
                alignment = {}
            passed = completed.returncode == 0 and alignment.get("verdict") == "PASS" and all(item["equivalent"] for item in comparisons)
            report = {
                "schema": "llm4or-figure3-clean-reconstruction-v1",
                "status": "passed_clean_temporary_reconstruction" if passed else "reconstruction_failed",
                "python": sys.version.split()[0],
                "declared_environment": declared,
                "required_inputs": {path: file_digest(ROOT / path) for path in REQUIRED},
                "renderer_returncode": completed.returncode,
                "alignment_verdict": alignment.get("verdict"),
                "comparisons": comparisons,
                "sanitized_environment_keys": sorted(environment),
                "execution": {"model_calls": 0, "api_calls": 0, "solver_calls": 0, "native_evaluator_calls": 0, "vm_calls": 0, "credentials_read": False},
                "claim_boundary": "The clean rebuild checks only Figure 3 rendering determinism from aggregate body-free Source Data.",
            }
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        path = Path(args.out)
        if not path.is_absolute(): path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "passed_clean_temporary_reconstruction" or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
