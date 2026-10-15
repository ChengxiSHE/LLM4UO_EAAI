"""Finite typed synthesis for the partial fixed-tail counting contract.

The grammar and bound registry are authored.  This module only searches that
finite space and checks candidates against an independent direct predicate and
the existing trusted finite-count compiler.
"""
from itertools import product

from .finite_count_model import (
    VERSION as COUNT_SCHEMA,
    compile_count_model,
    validate_count_model,
)
from .schema import canonical, digest, loads


SCHEMA = "typed-partial-count-skill-v1"
MAX_N = 60
MAX_VALUE = 1_000_000

_FIXED = {
    "schema": SCHEMA,
    "count_targets": "prefix_0_through_n",
}
_ENUMS = {
    "tail_role": ("fixed_parameter", "count_target"),
    "counted_scope": ("whole_vector", "count_target_prefix"),
    "relation": ("count_equals_cell", "truth_iff_count"),
    "bound_strategy": ("declared_length", "ordinary_conservation"),
    "zero_tail_policy": ("ordinary_only", "union_exception"),
    "resource_policy": ("compiler_exact", "estimate_only"),
}
_FIELDS = frozenset((*_FIXED, *_ENUMS))
_SEMANTIC_GRID = ((1, 0), (1, 2), (2, 0), (2, 1),
                  (3, 0), (3, 1), (3, 6), (4, 2))


class TypedCountSkillError(ValueError):
    """A fail-closed typed-skill validation error."""


def _require(ok, code):
    if not ok:
        raise TypedCountSkillError(code)


def _integer(value, code, lower=0, upper=MAX_VALUE):
    _require(type(value) is int and lower <= value <= upper, code)
    return value


def _parameters(n, m):
    return (_integer(n, "n", 1, MAX_N), _integer(m, "m"))


def validate_candidate(value):
    _require(type(value) is dict and set(value) == _FIELDS, "candidate_fields")
    for key, expected in _FIXED.items():
        _require(type(value[key]) is str and value[key] == expected, key)
    for key, choices in _ENUMS.items():
        _require(type(value[key]) is str and value[key] in choices, key)
    return loads(canonical(value))


def enumerate_candidates():
    keys = tuple(_ENUMS)
    return [
        validate_candidate({**_FIXED, **dict(zip(keys, values))})
        for values in product(*(_ENUMS[key] for key in keys))
    ]


def oracle_partial(n, m, vector):
    n, m = _parameters(n, m)
    length = n + 2
    _require(type(vector) is list and len(vector) == length, "vector_length")
    clean = [_integer(value, "vector_value") for value in vector]
    _require(clean[-1] == m, "fixed_tail")
    return _oracle_clean(n, clean)


def _oracle_clean(n, vector):
    return all(vector[index] == sum(value == index for value in vector)
               for index in range(n + 1))


def _target_domains(candidate, n, m):
    length = n + 2
    if candidate["bound_strategy"] == "declared_length":
        domains = [{"lower": 0, "upper": length} for _ in range(n + 1)]
    else:
        counted_total = length if m <= n else length - 1
        weighted_total = counted_total + m if m <= n else counted_total
        domains = [{"lower": 0, "upper": n}]
        domains.extend(
            {"lower": 0, "upper": min(n, weighted_total // index)}
            for index in range(1, n + 1)
        )
    if candidate["relation"] == "truth_iff_count":
        domains = [{"lower": 0, "upper": 1} for _ in domains]
    return domains


def _model(candidate, n, m, exceptional=False):
    length = n + 2
    if exceptional:
        domains = [{"lower": n + 1, "upper": n + 1}]
        domains.extend({"lower": 0, "upper": 0} for _ in range(n))
    else:
        domains = _target_domains(candidate, n, m)
    domains.append({"lower": m, "upper": m})
    positions = (list(range(length)) if candidate["counted_scope"] == "whole_vector"
                 else list(range(n + 1)))
    constraints = []
    targets = list(range(n + 1))
    if candidate["tail_role"] == "count_target":
        targets.append(n + 1)
    for index in targets:
        row = {
            "kind": candidate["relation"],
            "scope": "counted",
            "value": index,
            "target": index,
        }
        if candidate["relation"] == "truth_iff_count":
            row["count"] = index
        constraints.append(row)
    return validate_count_model({
        "schema": COUNT_SCHEMA,
        "domains": domains,
        "scopes": [{"id": "counted", "positions": positions}],
        "constraints": constraints,
    })


def build_partial_models(candidate, n, m):
    candidate = validate_candidate(candidate)
    n, m = _parameters(n, m)
    models = [_model(candidate, n, m)]
    if m == 0 and candidate["zero_tail_policy"] == "union_exception":
        models.append(_model(candidate, n, m, exceptional=True))
    return models


def model_accepts(spec, vector):
    spec = validate_count_model(spec)
    _require(type(vector) is list and len(vector) == len(spec["domains"]),
             "vector_length")
    _require(all(type(value) is int and abs(value) <= MAX_VALUE for value in vector),
             "vector_value")
    return _model_accepts_clean(spec, vector)


def _model_accepts_clean(spec, vector):
    if any(not (domain["lower"] <= value <= domain["upper"])
           for domain, value in zip(spec["domains"], vector)):
        return False
    scopes = {scope["id"]: scope["positions"] for scope in spec["scopes"]}
    for row in spec["constraints"]:
        count = sum(vector[position] == row["value"]
                    for position in scopes[row["scope"]])
        if row["kind"] == "count_equals_cell":
            if count != vector[row["target"]]:
                return False
        elif vector[row["target"]] != int(count == row["count"]):
            return False
    return True


def _public_cases(value):
    _require(type(value) is list and 1 <= len(value) <= 64, "public_cases")
    clean = []
    seen = set()
    for row in value:
        _require(type(row) is dict and set(row) == {"n", "m"},
                 "public_case_fields")
        n, m = _parameters(row["n"], row["m"])
        _require((n, m) not in seen, "duplicate_public_case")
        seen.add((n, m))
        clean.append({"n": n, "m": m})
    return sorted(clean, key=lambda row: (row["n"], row["m"]))


def _empty_semantic():
    return {
        "passed": False,
        "grid_cases": len(_SEMANTIC_GRID),
        "assignments_checked": 0,
        "counterexample": None,
        "error": None,
    }


def _semantic_check(candidate):
    result = _empty_semantic()
    checked = 0
    for n, m in _SEMANTIC_GRID:
        try:
            specs = build_partial_models(candidate, n, m)
        except ValueError as exc:
            result.update(assignments_checked=checked, error=str(exc))
            return result, "semantic_model_rejected"
        length = n + 2
        for prefix in product(range(length + 1), repeat=n + 1):
            vector = list(prefix) + [m]
            expected = _oracle_clean(n, vector)
            actual = any(_model_accepts_clean(spec, vector) for spec in specs)
            checked += 1
            if expected != actual:
                result.update(
                    assignments_checked=checked,
                    counterexample={
                        "n": n,
                        "m": m,
                        "expected": expected,
                        "actual": actual,
                        "assignment_sha256": digest({"n": n, "m": m,
                                                     "assignment": vector}),
                    },
                )
                return result, "semantic_counterexample"
    result.update(passed=True, assignments_checked=checked)
    return result, None


def _compiled_metrics(spec):
    compiled = compile_count_model(spec)
    model = compiled["model"]
    return {
        "cells": len(spec["domains"]),
        "domain_indicators": sum(domain["upper"] - domain["lower"] + 1
                                 for domain in spec["domains"]),
        "compiled_columns": len(model["variables"]),
        "compiled_rows": len(model["constraints"]),
        "compiled_nonzeros": sum(len(row["coefficients"])
                                 for row in model["constraints"]),
        "compiled_bytes": len(canonical(model).encode("utf-8")),
    }


def _resource_check(candidate, public_cases):
    result = {
        "policy": candidate["resource_policy"],
        "passed": False,
        "cases": [],
        "error": None,
    }
    if candidate["resource_policy"] != "compiler_exact":
        result["error"] = "estimate_only_is_not_admissible"
        return result, "untrusted_resource_policy"
    for row in public_cases:
        try:
            specs = build_partial_models(candidate, row["n"], row["m"])
            metrics = [_compiled_metrics(spec) for spec in specs]
        except ValueError as exc:
            result["error"] = str(exc)
            return result, "resource_model_rejected"
        keys = tuple(metrics[0])
        result["cases"].append({
            **row,
            "alternatives": len(specs),
            "models": metrics,
            "totals": {key: sum(item[key] for item in metrics) for key in keys},
        })
    result["passed"] = True
    return result, None


def measure_candidate_components(candidate, public_cases):
    """Measure semantic and resource gates independently for ablation studies."""
    candidate = validate_candidate(candidate)
    public_cases = _public_cases(public_cases)
    semantic, semantic_failure = _semantic_check(candidate)
    resources, resource_failure = _resource_check(candidate, public_cases)
    semantic_passed = bool(semantic["passed"])
    resource_passed = bool(resources["passed"])
    return {
        "schema": "typed-count-component-measurement-v1",
        "candidate": candidate,
        "candidate_sha256": digest(candidate),
        "public_parameters_sha256": digest(public_cases),
        "semantic": semantic,
        "semantic_failure_code": semantic_failure,
        "resources": resources,
        "resource_failure_code": resource_failure,
        "gate_cell": f"semantic_{int(semantic_passed)}_resource_{int(resource_passed)}",
        "safe_admission": semantic_passed and resource_passed,
    }


def verify_candidate(candidate, public_cases):
    candidate = validate_candidate(candidate)
    public_cases = _public_cases(public_cases)
    semantic, failure = _semantic_check(candidate)
    resources = {
        "policy": candidate["resource_policy"],
        "passed": False,
        "cases": [],
        "error": "not_checked_after_semantic_failure" if failure else None,
    }
    if failure is None:
        resources, failure = _resource_check(candidate, public_cases)
    return {
        "schema": "typed-count-candidate-verification-v1",
        "candidate": candidate,
        "candidate_sha256": digest(candidate),
        "public_parameters_sha256": digest(public_cases),
        "passed": failure is None,
        "failure_code": failure,
        "semantic": semantic,
        "resources": resources,
    }


def _complexity(verification):
    candidate = verification["candidate"]
    alternatives = max(row["alternatives"]
                       for row in verification["resources"]["cases"])
    return (
        alternatives,
        0 if candidate["relation"] == "count_equals_cell" else 1,
        0 if candidate["bound_strategy"] == "ordinary_conservation" else 1,
        canonical(candidate),
    )


def synthesize(public_cases):
    public_cases = _public_cases(public_cases)
    verifications = [verify_candidate(candidate, public_cases)
                     for candidate in enumerate_candidates()]
    survivors = [item for item in verifications if item["passed"]]
    _require(bool(survivors), "no_verified_candidate")
    best = min(_complexity(item) for item in survivors)
    minima = [item for item in survivors if _complexity(item) == best]
    _require(len(minima) == 1, "ambiguous_verified_candidate")
    rejected = {}
    for item in verifications:
        if item["failure_code"] is not None:
            rejected[item["failure_code"]] = rejected.get(item["failure_code"], 0) + 1
    selected = minima[0]
    return {
        "schema": "typed-partial-count-synthesis-v1",
        "grammar_size": len(verifications),
        "survivor_count": len(survivors),
        "rejected_by_failure": dict(sorted(rejected.items())),
        "selected": selected["candidate"],
        "selected_candidate_sha256": selected["candidate_sha256"],
        "selected_verification": selected,
    }


def render_knowledge(candidate):
    candidate = validate_candidate(candidate)
    value = {
        "schema": "typed-partial-count-knowledge-v1",
        "candidate": candidate,
        "applicability": {
            "n": "exact integer at least 1",
            "m": "exact nonnegative integer",
            "length": "n+2",
            "count_targets": "coordinates 0 through n",
            "counted_scope": "all n+2 coordinates including the fixed tail",
            "tail": "fixed to m and excluded from count targets",
        },
        "registry_semantics": {
            "ordinary_branch": {
                "counted_total": "n+2 when m<=n, otherwise n+1",
                "weighted_total": "counted_total+m when m<=n, otherwise counted_total",
                "bounds": "s0<=n; si<=min(n,floor(weighted_total/i)) for i>0",
            },
            "zero_tail_exception": "s0=n+1; s1..sn=0; tail=0",
            "original_relations_retained": True,
        },
        "provenance": {
            "method": "author_scaffolded_finite_synthesis",
            "search_family": "SyGuS/CEGIS within the declared 64-candidate grammar",
            "registry_is_learned": False,
        },
        "claim_boundary": {
            "finite_grid_equivalence_only": True,
            "unbounded_theorem_claimed": False,
            "benchmark_accuracy_claimed": False,
        },
    }
    text = canonical(value)
    _require(len(text.encode("utf-8")) <= 10_000, "render_size")
    return text
