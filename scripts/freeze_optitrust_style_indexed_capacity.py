#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.optitrust_style_indexed_capacity import (  # noqa: E402
    AUTH_PATH, PLAN_PATH, authorization, build_plan, publish_new,
)

plan = build_plan(ROOT)
publish_new(ROOT / PLAN_PATH, plan)
publish_new(ROOT / AUTH_PATH, authorization(ROOT, plan))
print(plan["schema"])
