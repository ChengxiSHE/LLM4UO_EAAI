#!/usr/bin/env python3
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import (  # noqa: E402
    AUDIT_PATH, PLAN_PATH, build_capacity_material, offline_audit,
)
from llm4or.schema import canonical  # noqa: E402

plan = json.loads((ROOT / PLAN_PATH).read_text())
_rebuilt, entries = build_capacity_material(ROOT)
observed = offline_audit(ROOT, plan, entries)
expected = json.loads((ROOT / AUDIT_PATH).read_text())
if canonical(observed) != canonical(expected):
    raise SystemExit("offline_audit_drift")
print(observed["status"])
