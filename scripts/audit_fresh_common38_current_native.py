"""Publish the independent audit of the current-method native run."""

import hashlib
import json
from pathlib import Path

from llm4or.fresh_common38_native_audit import build_audit, publish


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/fresh_common38_current_native_audit_20261015.json"


def main():
    audit = build_audit(ROOT)
    publish(OUTPUT, audit)
    print(json.dumps({"state": "published", "status": audit["status"],
                      "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                      "correct": audit["checks"]["aggregate"]["correct"],
                      "planned": audit["checks"]["aggregate"]["planned"],
                      "new_solver_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
