#!/usr/bin/env python3
"""Build or check the public aggregate reviewer claim table."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.reviewer_claim_table import write_claim_table


DEFAULT_OUTPUT = ROOT / "results" / "reviewer_claim_table_v1_20261016.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    write_claim_table(ROOT, args.output, check=args.check)


if __name__ == "__main__":
    main()
