#!/usr/bin/env python3
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.optitrust_style_indexed_capacity import (  # noqa: E402
    AUDIT_PATH, PLAN_PATH, RESULT_PATH, build_audit_from,
)
from llm4or.schema import canonical  # noqa: E402

plan = json.loads((ROOT / PLAN_PATH).read_text())
audit = build_audit_from(
    ROOT, plan, ROOT / PLAN_PATH, ROOT / plan["run_directory"],
    ROOT / RESULT_PATH, expected_offline=False,
)
expected = json.loads((ROOT / AUDIT_PATH).read_text())
if canonical(audit) != canonical(expected):
    raise SystemExit("audit_drift")
print(audit["status"])
