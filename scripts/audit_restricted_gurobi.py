#!/usr/bin/env python3
"""Audit restricted Gurobi translation against official Text2Opt gold models.

The upstream programs are parsed and interpreted by ``restricted_gurobi``;
they are never imported, executed, or allowed to read files.  Every translated
linear model is compared coefficient-by-coefficient with Text2Opt's symbolic
variables and constraints.  Published objective answers are not needed.
"""

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.restricted_gurobi import compile_gurobi_source

DEFAULT_SOURCE = ROOT / "data/raw/text2opt_bench_20261003"
DEFAULT_OUTPUT = ROOT / "results/restricted_gurobi_official_audit.json"


def _number(value):
    if value is None:
        return None
    if isinstance(value, str) and value.lower() in {"inf", "infinity", "+inf"}:
        return None
    return float(value)


def _close(left, right):
    if left is None or right is None:
        return left is right
    return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-8)


def _row_signature(coefficients, sense, rhs):
    sense = {"<=": "le", ">=": "ge", "==": "eq", "=": "eq",
             "le": "le", "ge": "ge", "eq": "eq"}[sense]
    rhs = float(rhs)
    values = {key: float(value) for key, value in coefficients.items()
              if abs(float(value)) > 1e-10}
    if not values:
        truth = (0 <= rhs + 1e-9) if sense == "le" else (
            (0 >= rhs - 1e-9) if sense == "ge" else abs(rhs) <= 1e-9)
        return ("constant", truth)
    if sense == "ge":
        values = {key: -value for key, value in values.items()}
        rhs = -rhs
        sense = "le"
    if sense == "eq":
        first = next(value for key, value in sorted(values.items()) if abs(value) > 1e-10)
        if first < 0:
            values = {key: -value for key, value in values.items()}
            rhs = -rhs
    return (tuple(sorted((key, round(value, 8)) for key, value in values.items())),
            sense, round(rhs, 8))


def _equivalence_reasons(compiled, upstream):
    reasons = []
    source_variables = upstream["variables"]
    names = {variable["id"]: variable["meaning"] for variable in compiled["variables"]}
    if len(source_variables) != len(compiled["variables"]):
        reasons.append("variable_count")
    domains = {"Continuous": "continuous", "Integer": "integer", "Binary": "binary"}
    for variable in compiled["variables"]:
        source = source_variables.get(variable["meaning"])
        if source is None:
            reasons.append("variable_name")
            continue
        if variable["domain"] != domains.get(source.get("type")):
            reasons.append("domain")
        lower, upper = map(_number, source.get("range", [0, None]))
        actual_lower, actual_upper = variable["lower"], variable["upper"]
        if variable["domain"] == "binary":
            actual_lower = max(0, actual_lower) if actual_lower is not None else 0
            actual_upper = min(1, actual_upper) if actual_upper is not None else 1
        if not _close(actual_lower, lower):
            reasons.append("lower_bound")
        if not _close(actual_upper, upper):
            reasons.append("upper_bound")
    objective = {names[key]: value for key, value in compiled["objective"]["coefficients"].items()}
    if any(not _close(objective.get(name, 0), source.get("objective_linear_coefficient", 0))
           for name, source in source_variables.items()):
        reasons.append("objective_coefficients")
    expected_sense = {"MINIMIZE": "min", "MAXIMIZE": "max"}[upstream["meta"]["goal"]]
    if compiled["objective"]["sense"] != expected_sense:
        reasons.append("objective_sense")
    actual_rows = Counter(
        _row_signature({names[key]: value for key, value in row["coefficients"].items()},
                       row["sense"], row["rhs"])
        for row in compiled["constraints"]
    )
    expected_rows = Counter()
    for row_name, row in upstream["constraints"].items():
        coefficients = {
            name: source.get("resource_costs", {}).get(row_name, 0)
            for name, source in source_variables.items()
        }
        expected_rows[_row_signature(coefficients, row["sense"], row["rhs"])] += 1
    if actual_rows != expected_rows:
        reasons.append("constraints")
    return sorted(set(reasons))


def audit(source_root):
    dataset = source_root / "synthetic_dataset"
    if not dataset.exists():
        raise SystemExit(f"Text2Opt snapshot missing: {dataset}")
    totals = Counter()
    categories = defaultdict(Counter)
    rejection_reasons = Counter()
    mismatch_reasons = Counter()
    rejection_examples = defaultdict(list)
    mismatch_examples = defaultdict(list)
    for path in sorted(dataset.rglob("*.json")):
        try:
            upstream = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        source = upstream.get("gold_solution") or upstream.get("solution_code")
        if not isinstance(source, str):
            continue
        category = str(path.relative_to(dataset).parent)
        relative = str(path.relative_to(source_root))
        totals["programs"] += 1
        categories[category]["programs"] += 1
        try:
            compiled = compile_gurobi_source(source)
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            totals["rejected"] += 1
            categories[category]["rejected"] += 1
            rejection_reasons[reason] += 1
            if len(rejection_examples[reason]) < 3:
                rejection_examples[reason].append(relative)
            continue
        totals["compiled"] += 1
        categories[category]["compiled"] += 1
        reasons = _equivalence_reasons(compiled, upstream)
        if reasons:
            key = ",".join(reasons)
            totals["mismatched"] += 1
            categories[category]["mismatched"] += 1
            mismatch_reasons[key] += 1
            if len(mismatch_examples[key]) < 3:
                mismatch_examples[key].append(relative)
        else:
            totals["structurally_equivalent"] += 1
            categories[category]["structurally_equivalent"] += 1
    revision = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"], capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    compiler = ROOT / "llm4or/restricted_gurobi.py"
    return {
        "schema": "restricted-gurobi-official-audit-v1",
        "source": {
            "repository": "https://github.com/SprocketLab/text2opt-bench",
            "revision": revision,
            "license": "MIT",
        },
        "safety": {
            "upstream_python_executed": False,
            "real_file_access": False,
            "network_access": False,
            "translation": "bounded whitelist AST interpreter to milp-v1",
            "compiler_sha256": hashlib.sha256(compiler.read_bytes()).hexdigest(),
        },
        "scope": "official linear and mixed-integer gold_solution/solution_code programs",
        "totals": dict(totals),
        "rates": {
            "compile_coverage": totals["compiled"] / totals["programs"],
            "structural_equivalence_given_compiled": (
                totals["structurally_equivalent"] / totals["compiled"] if totals["compiled"] else 0
            ),
        },
        "rejections": [
            {"reason": reason, "count": count, "examples": rejection_examples[reason]}
            for reason, count in rejection_reasons.most_common()
        ],
        "mismatches": [
            {"reason": reason, "count": count, "examples": mismatch_examples[reason]}
            for reason, count in mismatch_reasons.most_common()
        ],
        "categories": {key: dict(value) for key, value in sorted(categories.items())},
        "interpretation": (
            "Structural equivalence checks domains, effective bounds, objective direction and coefficients, "
            "and the multiset of normalized sparse constraints. Opposite-signed equivalent inequalities "
            "and truth-equivalent constant rows are canonicalized. Rejected programs remain failures; they "
            "are not executed through a fallback Python path."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit(args.source_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "totals": result["totals"],
                      "rates": result["rates"]}, sort_keys=True))


if __name__ == "__main__":
    main()
