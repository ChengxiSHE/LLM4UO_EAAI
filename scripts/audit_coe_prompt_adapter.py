#!/usr/bin/env python3
"""Offline differential audit of the non-executing CoE prompt adapter."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.coe_official_adapter import CoEPromptSource, EXPERT_FILES, SOURCE_HASHES
from llm4or.pipeline import write_json
from llm4or.schema import digest


UPSTREAM = ROOT / "data/raw/xzymustbexzy__Chain-of-Experts_20261003"
OUTPUT = ROOT / "results/coe_prompt_adapter_audit.json"


def source(commit: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(UPSTREAM), "show", f"{commit}:{path}"], text=True,
    )


def class_values(text: str) -> tuple[str, dict[str, str]]:
    tree = ast.parse(text)
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if len(classes) != 1:
        raise RuntimeError("unexpected_class_count")
    values = {}
    for item in classes[0].body:
        if isinstance(item, ast.Assign) and len(item.targets) == 1 \
                and isinstance(item.targets[0], ast.Name) \
                and item.targets[0].id in {"ROLE_DESCRIPTION", "FORWARD_TASK"}:
            values[item.targets[0].id] = ast.literal_eval(item.value)
    if set(values) != {"ROLE_DESCRIPTION", "FORWARD_TASK"}:
        raise RuntimeError("prompt_constants_missing")
    return classes[0].name, values


def problems():
    for dataset in ("LPWP", "ComplexOR"):
        for directory in sorted((UPSTREAM / "dataset" / dataset).iterdir()):
            if not directory.is_dir():
                continue
            yield dataset, directory.name, (directory / "description.txt").read_text(), \
                (directory / "code_example.py").read_text()


def main():
    cases = list(problems())
    snapshots = {}
    total = 0
    mismatches = []
    for snapshot in ("paper", "current"):
        adapter = CoEPromptSource.load(UPSTREAM, snapshot)
        direct = {}
        for path in EXPERT_FILES:
            class_name, values = class_values(source(adapter.commit, path))
            direct[Path(path).stem] = (class_name, values)
        _, conductor = class_values(source(adapter.commit, "conductor.py"))
        _, reducer = class_values(source(adapter.commit, "reducer.py"))
        prompt_hashes = hashlib.sha256()
        for dataset, problem_id, description, code_example in cases:
            comments = []
            for expert in adapter.experts:
                expected = direct[expert.key][1]["ROLE_DESCRIPTION"] + "\n" + \
                    direct[expert.key][1]["FORWARD_TASK"].format(
                        problem_description=description,
                        code_example=code_example,
                        comments_text="There is no comment available, please ignore this section.\n",
                        knowledge="None",
                    )
                actual = adapter.expert_prompt(expert, description, code_example, comments)
                total += 1
                if actual != expected:
                    mismatches.append(f"{snapshot}:{dataset}:{problem_id}:{expert.key}")
                prompt_hashes.update(actual.encode())
            expected_reducer = reducer["ROLE_DESCRIPTION"] + "\n" + reducer["FORWARD_TASK"].format(
                problem_description=description,
                comment_text="There is no comment available, please ignore this section.\n",
            )
            actual_reducer = adapter.reducer_prompt(description, comments)
            total += 1
            if actual_reducer != expected_reducer:
                mismatches.append(f"{snapshot}:{dataset}:{problem_id}:reducer")
            prompt_hashes.update(actual_reducer.encode())

            names = [expert.name for expert in adapter.experts]
            commented = []
            remaining = list(set(names) - set(commented)) if snapshot == "paper" else names
            remaining_count = 5 - len(str(commented)) if snapshot == "paper" else 5
            expected_conductor = conductor["ROLE_DESCRIPTION"] + "\n" + conductor["FORWARD_TASK"].format(
                problem_description=description,
                experts_info="\n".join(str(expert) for expert in adapter.experts),
                commented_experts=str(commented),
                remaining_experts=str(remaining),
                max_collaborate_nums=5,
                remaining_collaborate_nums=remaining_count,
            )
            actual_conductor = adapter.conductor_prompt(description, comments, 5)
            total += 1
            if actual_conductor != expected_conductor:
                mismatches.append(f"{snapshot}:{dataset}:{problem_id}:conductor")
            prompt_hashes.update(actual_conductor.encode())
        snapshots[snapshot] = {
            "commit": adapter.commit,
            "source_hashes": SOURCE_HASHES[snapshot],
            "problems": len(cases),
            "prompts_checked": len(cases) * 9,
            "aggregate_prompt_sha256": prompt_hashes.hexdigest(),
            "expert_names": [expert.name for expert in adapter.experts],
        }
    report = {
        "schema": "coe-prompt-adapter-audit-v1",
        "status": "passed" if not mismatches else "failed",
        "production_executes_upstream_python": False,
        "audit_method": "independent AST literal extraction and direct source-format differential",
        "datasets": {"LPWP": 288, "ComplexOR": 18},
        "total_prompts_checked": total,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "snapshots": snapshots,
        "known_paper_snapshot_behaviors_preserved": [
            "duplicate Programming Expert name",
            "remaining-collaboration count uses rendered string length",
            "set-derived remaining-expert order",
            "selected experts may repeat",
        ],
        "report_sha256": None,
    }
    report["report_sha256"] = digest({key: value for key, value in report.items() if key != "report_sha256"})
    write_json(OUTPUT, report)
    print(json.dumps({"status": report["status"], "prompts": total,
                      "mismatches": len(mismatches), "output": str(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
