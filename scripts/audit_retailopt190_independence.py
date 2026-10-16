#!/usr/bin/env python3
"""Compare RetailOpt-190 to all previously used public modeling sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.atomic_publisher import publish_bytes
from llm4or.benchmark_independence import audit_overlap, canonical, sha256
from llm4or.benchmark_registry import load_public_registry


def _business_description(text: str) -> str:
    marker = re.search(r"^\[BUSINESS DESCRIPTION\]\s*$", text, re.MULTILINE)
    if marker is None:
        raise ValueError("business_description_marker")
    value = text[marker.end() :].strip()
    if not value:
        raise ValueError("business_description_empty")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retailopt-root", type=Path, required=True)
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument("--text2opt-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    candidates = []
    for path in sorted((arguments.retailopt_root / "scenarios" / "prompts").glob("*.base.txt")):
        identity = path.name.removesuffix(".base.txt")
        candidates.append((identity, _business_description(path.read_text(encoding="utf-8"))))
    references = []
    legacy = load_public_registry(arguments.legacy_root)
    for row in legacy:
        public = row["public"]
        text = public["text"] + "\n" + "\n".join(value["definition"] for value in public["parameters"])
        references.append((f"legacy:{row['benchmark']}:{row['id']}", "legacy_six_source", text))
    text2opt_files = 0
    for path in sorted(arguments.text2opt_root.rglob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        if isinstance(value, dict) and isinstance(value.get("LLM_description"), str):
            relative = path.relative_to(arguments.text2opt_root).as_posix()
            references.append((f"text2opt:{relative}", "text2opt", value["LLM_description"]))
            text2opt_files += 1
    overlap = audit_overlap(candidates, references)
    audit = {
        "schema": "llm4or-retailopt190-independence-audit-v1",
        "status": "passed_no_exact_or_near_duplicate",
        "candidate": {
            "name": "RetailOpt-190",
            "commit": "d809c6bbeb42cb99b0564c41bfb8f331f0156b9d",
            "records": len(candidates),
            "field": "business_description_only",
        },
        "reference_corpora": {
            "legacy_six_source_records": len(legacy),
            "text2opt_records": text2opt_files,
            "total_records": len(references),
            "text2opt_commit": "1dac06be656c41d827ef20987cf8af0b48d382a2",
        },
        "method": {
            "tokenization": "lowercase ASCII word and decimal tokens",
            "numeric_template": "replace every decimal token with one numeric placeholder",
            "shingle_width": 5,
            "near_duplicate_gate": "no candidate with maximum Jaccard >= 0.8 in either mode",
        },
        "overlap": overlap,
        "privacy": {
            "contains_problem_bodies": False,
            "contains_candidate_or_reference_ids": False,
            "contains_nearest_neighbor_identities": False,
            "contains_answers_or_objectives": False,
        },
        "execution": {"api_calls": 0, "model_calls": 0, "solver_calls": 0, "credentials_read": False},
        "claim_boundary": "This audit rules out exact and high lexical/template overlap with the enumerated project sources; it cannot rule out pretraining contamination or conceptual similarity.",
    }
    if any(
        mode["exact_normalized_matches"] != 0
        or mode["candidate_counts_at_or_above_threshold"]["0.8"] != 0
        for mode in overlap.values()
    ):
        audit["status"] = "failed_overlap_gate"
    payload = (json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    relative = arguments.output.resolve().relative_to(ROOT.resolve())
    result = publish_bytes(ROOT, relative, payload)
    print(json.dumps({"status": audit["status"], "sha256": sha256(payload), "transaction": result.transaction_id}, sort_keys=True))
    return 0 if audit["status"].startswith("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
