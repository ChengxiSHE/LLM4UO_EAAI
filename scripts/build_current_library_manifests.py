#!/usr/bin/env python3
"""Materialize or verify the frozen answer-free TSP/OR-Debug manifest set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.current_library_manifests import publish_current_manifest_set


DEFAULT_DIRECTORY = Path("artifacts/knowledge_manifests/current")


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    arguments = parser.parse_args()
    result = publish_current_manifest_set(
        ROOT,
        arguments.directory,
        check=arguments.check,
    )
    result["mode"] = "check" if arguments.check else "write"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
