#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.formulationbench_same_knowledge import publish_new  # noqa: E402
from llm4or.nlequiv_custody import SourceIdentity, build_custody, publish_custody  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
parser.add_argument("--destination", required=True)
parser.add_argument("--write", action="store_true")
args = parser.parse_args()
identity = SourceIdentity("df7e53f58f97b551ded1cb816169bb47f84186da", "1be587fb3cbad4fa75ca8f2938f2dd55f8c6f12b")
entries, audit = build_custody(args.source, identity)
if args.write:
    publish_custody(args.destination, entries)
publish_new(ROOT / "experiments/nlequiv150_custody_audit_20261016.json", audit)
print(audit["status"])
