#!/usr/bin/env python3
"""Differentially audit the local BIND prompt adapter against pinned author code.

This is the only place that imports the reviewed upstream prompt-helper module.
Its SHA-256 is checked first; the module imports only Python standard-library
packages and performs no model-code execution.  Production inference uses the
non-executing AST/data adapter instead.
"""

from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.bind_official_adapter import (
    BindEvaluation, BindPromptSource, UPSTREAM_AGENTIC_SHA256,
    UPSTREAM_RUNNER_SHA256, repair_prompt,
)
from llm4or.schema import canonical, digest


UPSTREAM = ROOT / "data/raw/text2opt_bench_20261003"
DATA = UPSTREAM / "synthetic_dataset"
OUTPUT = ROOT / "results/bind_prompt_adapter_audit.json"


def _load_official():
    source = UPSTREAM / "main/evaluation/agentic_offload.py"
    spec = importlib.util.spec_from_file_location("pinned_bind_agentic_offload", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _official_evaluation(case: BindEvaluation):
    generated = SimpleNamespace(
        objective_value=case.objective_value,
        status=case.solver_status,
        num_vars=case.num_vars,
        num_constrs=case.num_constraints,
        stderr=case.stderr,
    )
    evaluation = SimpleNamespace(
        execution_succeeded=case.execution_succeeded,
        status_optimal=case.status_optimal,
        objective_matches=case.objective_matches,
        reference_optimum=case.reference_optimum,
        generated_solution=generated,
    )
    problem = {
        "meta": {
            "num_vars": case.reference_num_vars,
            "num_constraints": case.reference_num_constraints,
        },
        "gurobi_result": {"solver_status": case.reference_status},
    }
    return evaluation, problem


def main():
    adapter = BindPromptSource.load(UPSTREAM)
    official = _load_official()
    mismatches = []
    checked = 0
    for path in sorted(DATA.rglob("*.json")):
        try:
            problem = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(problem, dict) or not problem.get("instance_data"):
            continue
        virtual_path = "/bind_data/" + path.stem + ".json"
        expected = official.build_instance_data_prompt(problem, Path(virtual_path))
        actual = adapter.initial_prompt(problem, virtual_path)
        checked += 1
        if actual != expected:
            mismatches.append({
                "relative_path": str(path.relative_to(UPSTREAM)),
                "official_sha256": digest(expected),
                "adapter_sha256": digest(actual),
            })

    repair_cases = [
        BindEvaluation(False, False, False, None, 3.0, None, 2, None, None, 1, 0, "No code found"),
        BindEvaluation(True, True, False, 2.0, 3.0, 2, 2, 1, 0, 1, 0, ""),
        BindEvaluation(True, False, False, 4.0, 0.0, 3, 2, 2, 4, 1, 3, "tail"),
    ]
    repair_mismatches = []
    virtual_path = "/bind_data/audit.json"
    for index, case in enumerate(repair_cases):
        evaluation, problem = _official_evaluation(case)
        expected = official.build_repair_prompt(evaluation, Path(virtual_path), problem)
        actual = repair_prompt(case, virtual_path)
        if actual != expected:
            repair_mismatches.append({
                "case": index, "inputs": asdict(case),
                "official_sha256": digest(expected), "adapter_sha256": digest(actual),
            })

    result = {
        "schema": "bind-prompt-adapter-audit-v1",
        "upstream_commit": "1dac06be656c41d827ef20987cf8af0b48d382a2",
        "upstream_agentic_sha256": UPSTREAM_AGENTIC_SHA256,
        "upstream_runner_sha256": UPSTREAM_RUNNER_SHA256,
        "execution_scope": "hash_bound_reviewed_prompt_helper_only_no_generated_code",
        "instance_prompts_checked": checked,
        "instance_prompt_exact_matches": checked - len(mismatches),
        "instance_prompt_mismatch_count": len(mismatches),
        "instance_prompt_mismatch_examples": mismatches[:20],
        "repair_prompts_checked": len(repair_cases),
        "repair_prompt_exact_matches": len(repair_cases) - len(repair_mismatches),
        "repair_prompt_mismatch_count": len(repair_mismatches),
        "repair_prompt_mismatch_examples": repair_mismatches[:20],
        "passed": not mismatches and not repair_mismatches and checked > 0,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(canonical(result) + "\n")
    print(canonical(result))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
