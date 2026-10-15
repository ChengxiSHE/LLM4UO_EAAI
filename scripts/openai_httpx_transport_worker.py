#!/usr/bin/env python3
"""Bounded stdin/stdout adapter for the pinned preparation environment."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm4or.openai_httpx_worker import execute_one  # noqa: E402
from llm4or.schema import canonical  # noqa: E402


def main() -> int:
    try:
        if len(sys.argv) != 3:
            raise ValueError("arguments")
        seconds = int(sys.argv[1])
        output_bytes = int(sys.argv[2])
        raw = sys.stdin.buffer.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("stdin_limit")
        body = json.loads(raw)
        result = execute_one(body, seconds=seconds, output_bytes=output_bytes)
    except Exception as exc:
        result = {
            "error": "worker_" + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__),
            "usage_source": "unavailable",
        }
    sys.stdout.write(canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
