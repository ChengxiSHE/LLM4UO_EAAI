#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import (  # noqa: E402
    AUDIT_PATH, AUTH_PATH, PLAN_PATH, authorization, build_capacity_material,
    offline_audit, publish_new, publish_private_requests,
)

plan, entries = build_capacity_material(ROOT)
audit = offline_audit(ROOT, plan, entries)
if audit["status"] != "passed":
    raise SystemExit("offline_gate_failed")
publish_private_requests(ROOT, entries)
publish_new(ROOT / PLAN_PATH, plan)
publish_new(ROOT / AUTH_PATH, authorization(ROOT, plan))
publish_new(ROOT / AUDIT_PATH, audit)
print(plan["schema"])
