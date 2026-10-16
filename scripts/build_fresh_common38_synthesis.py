#!/usr/bin/env python3
"""Publish the body-free fresh common-38 common-protocol synthesis."""

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.fresh_common38_base import publish_new
from llm4or.fresh_common38_synthesis import OUTPUT_PATH, REPORT_PATH, build_synthesis, render_markdown


def write_text_new(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o644)
    except FileExistsError as exc:
        raise ValueError("output_exists") from exc
    raw = text.encode()
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> None:
    value = build_synthesis(ROOT); output = ROOT / OUTPUT_PATH; report = ROOT / REPORT_PATH
    publish_new(output, value); write_text_new(report, render_markdown(value))
    print(json.dumps({
        "state": "published", "json_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "current_correct": value["method_native_rows"][0]["correct"], "planned": 38,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
