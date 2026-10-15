"""Publish body-free readiness evidence for the common-38 typed skills."""

import hashlib
import json
from pathlib import Path

from llm4or.structured_or_readiness import build_audit, publish


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/fresh_common38_structured_skill_readiness_20261015.json"


def main():
    audit = build_audit(ROOT)
    publish(OUTPUT, audit)
    print(json.dumps({
        "state": "published",
        "path": str(OUTPUT.relative_to(ROOT)),
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "compiled_and_admitted": audit["aggregate"]["compiled_and_admitted"],
        "exact_source_count_matches": audit["aggregate"]["exact_source_count_matches"],
        "api_calls": audit["execution"]["api_calls"],
        "solver_calls": audit["execution"]["solver_calls"],
        "ready_to_dispatch": audit["decision"]["ready_to_dispatch"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
