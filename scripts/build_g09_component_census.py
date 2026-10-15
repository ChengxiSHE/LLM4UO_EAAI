#!/usr/bin/env python3
"""Publish the G09 finite component census and its body-free report."""

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.g09_component_census import OUTPUT_PATH, REPORT_PATH, build_census, render_markdown
from llm4or.schema import canonical


def write_new(path: Path, raw: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, mode)
    except FileExistsError as exc:
        raise ValueError("output_exists") from exc
    try:
        view = memoryview(raw)
        while view:
            count = os.write(descriptor, view); view = view[count:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> None:
    value = build_census(ROOT); output = ROOT / OUTPUT_PATH; report = ROOT / REPORT_PATH
    write_new(output, (canonical(value) + "\n").encode(), 0o600)
    write_new(report, render_markdown(value).encode(), 0o644)
    print(json.dumps({
        "state": "published", "json_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "admission_population": value["admission_census"]["population"],
        "routing_population": value["routing_census"]["population"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
