#!/usr/bin/env python3
"""List or explicitly run one D5 reconstruction publisher adapter."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.reconstruction_publishers import PUBLISHERS, run_publisher


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--publisher", choices=sorted(PUBLISHERS))
    arguments = parser.parse_args()
    if arguments.list:
        print(
            json.dumps(
                {
                    "publishers": [
                        {
                            "id": spec.identifier,
                            "source": spec.source_path,
                            "outputs": list(spec.outputs),
                        }
                        for spec in PUBLISHERS.values()
                    ],
                    "implicit_execution": False,
                },
                sort_keys=True,
            )
        )
        return 0
    result = run_publisher(arguments.publisher, ROOT)
    print(
        json.dumps(
            {
                "publisher": arguments.publisher,
                "transaction_id": result.transaction_id,
                "created": list(result.created),
                "identical": list(result.identical),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
