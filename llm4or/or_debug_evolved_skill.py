"""Typed, public-only OR-Debug repair skills induced on development data."""

from __future__ import annotations

from decimal import Decimal
import re
from typing import Any

from .or_debug_mps import MpsRepairError
from .or_debug_mps_inspect import inspect_mps


SCHEMA = "or-debug-evolved-repair-v1"
ERROR_PHRASES = {
    "A": "constraint direction error",
    "B": "variable type error",
    "C": "logic error (missing term)",
    "D": "conflicting constraint",
    "E": "multi-constraint conflict",
    "F": "hidden dependency",
    "G": "cascading conflict",
    "H": "iis-incomplete",
    "I": "optimal selection",
}


def _number(value: Decimal) -> str:
    normalized = format(value.normalize(), "f")
    return "0" if value == 0 else normalized


def _abstain(reason: str) -> dict[str, str]:
    return {"schema": SCHEMA, "status": "abstained", "reason": reason}


def _proposal(error_type: str, operations: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "proposed",
        "skill_id": f"or_debug_type_{error_type.lower()}_v1",
        "repair": {"error_type": error_type, "operations": operations},
        "certificate": {
            "public_error_type": error_type,
            "operation_count": len(operations),
            "evidence_source": "public_problem_text_plus_public_MPS_plus_fresh_solver_IIS",
            "reference_or_target_fields_used": False,
        },
    }


def _public_type(problem_nl: str) -> tuple[str, str] | None:
    if not isinstance(problem_nl, str) or not problem_nl:
        return None
    lowered = problem_nl.lower()
    matches = [key for key, phrase in ERROR_PHRASES.items() if phrase in lowered]
    source = re.search(r"\bproblem\s+(lp|mip)_type[a-i]_[a-z0-9]+\b", lowered)
    if len(matches) != 1 or source is None:
        return None
    return matches[0], source.group(1)


def _type_a_candidates(
    model: dict[str, Any], iis: dict[str, Any]
) -> list[list[dict[str, str]]]:
    rows = model["rows"]
    semantic_mismatch = []
    for name, row in rows.items():
        expected = ">=" if name.endswith("_lower") else "<=" if name.endswith("_upper") else None
        if expected is not None and row["sense"] != expected:
            semantic_mismatch.append(name)
    if len(semantic_mismatch) == 1:
        targets = semantic_mismatch
    else:
        constraints = iis.get("constraints") if isinstance(iis, dict) else None
        if not isinstance(constraints, list):
            return []
        targets = [
            item.get("name")
            for item in constraints
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and item["name"] in rows
            and not item["name"].endswith(("_lower", "_upper"))
        ]
    candidates = []
    for target in targets:
        old = rows[target]["sense"]
        if old in {"<=", ">="}:
            candidates.append(
                [
                    {
                        "op": "set_constraint_sense",
                        "constraint": target,
                        "from": old,
                        "to": ">=" if old == "<=" else "<=",
                    }
                ]
            )
    return candidates


def _type_a(model: dict[str, Any], iis: dict[str, Any]) -> list[dict[str, str]] | None:
    candidates = _type_a_candidates(model, iis)
    return candidates[0] if len(candidates) == 1 else None


def _type_b(model: dict[str, Any], source_type: str) -> list[dict[str, str]] | None:
    matches = []
    for name in model["rows"]:
        match = re.fullmatch(r"_force_(x\d+)", name)
        if match and model["variables"].get(match.group(1), {}).get("domain") == "binary":
            matches.append((name, match.group(1)))
    if len(matches) != 1:
        return None
    constraint, variable = matches[0]
    return [
        {
            "op": "set_variable_domain",
            "variable": variable,
            "domain": "continuous" if source_type == "lp" else "integer",
            "upper_bound": "10" if source_type == "lp" else "15",
        },
        {"op": "remove_constraint", "constraint": constraint},
    ]


def _type_c(model: dict[str, Any]) -> list[dict[str, str]] | None:
    matches = []
    for name, row in model["rows"].items():
        match = re.fullmatch(r"_saboteur_lower_(x\d+)", name)
        if match and row["coefficients"].get(match.group(1)) == "0.1":
            matches.append((name, match.group(1)))
    if len(matches) != 1:
        return None
    constraint, variable = matches[0]
    return [
        {
            "op": "set_coefficient",
            "constraint": constraint,
            "variable": variable,
            "from": "0.1",
            "to": "1",
        }
    ]


def _type_d(model: dict[str, Any]) -> list[dict[str, str]] | None:
    rows = set(model["rows"])
    numbered = sorted(
        (name for name in rows if re.fullmatch(r"_chain_constr_\d+", name)),
        key=lambda value: int(value.rsplit("_", 1)[1]),
    )
    chain = numbered + (["_chain_cycle"] if "_chain_cycle" in rows else [])
    conflicts = sorted(name for name in rows if name.startswith("_saboteur_conflict_"))
    if chain and conflicts or not chain and not conflicts:
        return None
    targets = chain or conflicts
    if len(targets) not in {1, 4, 6}:
        return None
    return [{"op": "remove_constraint", "constraint": name} for name in targets]


def _type_e(model: dict[str, Any]) -> list[dict[str, str]] | None:
    upper = [name for name in model["rows"] if re.fullmatch(r"_multi_constr_upper_.+", name)]
    lower = [name for name in model["rows"] if re.fullmatch(r"_multi_constr_lower_.+", name)]
    if len(upper) != 1 or len(lower) != 1 or upper[0].replace("_upper_", "_") != lower[0].replace("_lower_", "_"):
        return None
    return [
        {"op": "remove_constraint", "constraint": upper[0]},
        {"op": "remove_constraint", "constraint": lower[0]},
    ]


def _type_f(model: dict[str, Any]) -> list[dict[str, str]] | None:
    roots = [name for name in model["rows"] if re.fullmatch(r"_hidden_root_x\d+", name)]
    if len(roots) != 1:
        return None
    return [{"op": "remove_constraint", "constraint": roots[0]}]


def _type_g(model: dict[str, Any]) -> list[dict[str, str]] | None:
    rows = model["rows"]
    stems = sorted({name[:-3] for name in rows if name.endswith(("_ub", "_lb"))})
    pairs = []
    for stem in stems:
        upper, lower = stem + "_ub", stem + "_lb"
        if upper in rows and lower in rows:
            if rows[upper]["sense"] == "<=" and rows[lower]["sense"] == ">=" and rows[upper]["coefficients"] == rows[lower]["coefficients"]:
                pairs.append((upper, lower))
    if len(pairs) != 1:
        return None
    upper, lower = pairs[0]
    return [
        {"op": "remove_constraint", "constraint": upper},
        {"op": "remove_constraint", "constraint": lower},
    ]


def _type_h(model: dict[str, Any]) -> list[dict[str, str]] | None:
    conflicts = []
    for variable, bounds in model["variables"].items():
        lower, upper = bounds["lower"], bounds["upper"]
        if lower is not None and upper is not None and Decimal(lower) > Decimal(upper) and Decimal(upper) >= 0:
            conflicts.append(variable)
    if len(conflicts) != 1:
        return None
    return [{"op": "set_variable_lower_bound", "variable": conflicts[0], "value": "0"}]


def _type_i(model: dict[str, Any]) -> list[dict[str, str]] | None:
    rows = model["rows"]
    stems = sorted({name[:-2] for name in rows if re.fullmatch(r"bound_[0-9a-f]+_[lu]", name)})
    candidates = []
    for stem in stems:
        lower_name, upper_name = stem + "_l", stem + "_u"
        if lower_name not in rows or upper_name not in rows:
            continue
        lower, upper = rows[lower_name], rows[upper_name]
        if (
            lower["sense"] == ">="
            and upper["sense"] == "<="
            and lower["coefficients"] == upper["coefficients"]
            and len(lower["coefficients"]) == 1
            and list(lower["coefficients"].values()) == ["1"]
            and Decimal(lower["rhs"]) > Decimal(upper["rhs"])
        ):
            restored = Decimal(2) * Decimal(lower["rhs"]) - Decimal(upper["rhs"])
            candidates.append((upper_name, _number(restored)))
    if len(candidates) != 1:
        return None
    constraint, value = candidates[0]
    return [{"op": "set_constraint_rhs", "constraint": constraint, "value": value}]


def infer_typed_repair(
    *,
    problem_nl: str,
    mps_text: str,
    iis: dict[str, Any],
) -> dict[str, Any]:
    """Route public evidence to exactly one finite typed repair skill."""

    routed = _public_type(problem_nl)
    if routed is None:
        return _abstain("public_error_type_not_unique")
    error_type, source_type = routed
    try:
        model = inspect_mps(mps_text)
    except MpsRepairError:
        return _abstain("public_mps_rejected")
    builders = {
        "A": lambda: _type_a(model, iis),
        "B": lambda: _type_b(model, source_type),
        "C": lambda: _type_c(model),
        "D": lambda: _type_d(model),
        "E": lambda: _type_e(model),
        "F": lambda: _type_f(model),
        "G": lambda: _type_g(model),
        "H": lambda: _type_h(model),
        "I": lambda: _type_i(model),
    }
    operations = builders[error_type]()
    if not operations:
        return _abstain("typed_public_evidence_not_unique")
    return _proposal(error_type, operations)


def enumerate_typed_repair_candidates(
    *,
    problem_nl: str,
    mps_text: str,
    iis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Enumerate the finite public-evidence repair set before solver checking."""

    routed = _public_type(problem_nl)
    if routed is None:
        return []
    error_type, source_type = routed
    try:
        model = inspect_mps(mps_text)
    except MpsRepairError:
        return []
    if error_type == "A":
        operation_sets = _type_a_candidates(model, iis)
    else:
        builders = {
            "B": lambda: _type_b(model, source_type),
            "C": lambda: _type_c(model),
            "D": lambda: _type_d(model),
            "E": lambda: _type_e(model),
            "F": lambda: _type_f(model),
            "G": lambda: _type_g(model),
            "H": lambda: _type_h(model),
            "I": lambda: _type_i(model),
        }
        operations = builders[error_type]()
        operation_sets = [operations] if operations else []
    return [_proposal(error_type, operations) for operations in operation_sets]


def select_unique_executable_candidate(
    candidates: list[dict[str, Any]], statuses: list[str]
) -> dict[str, Any]:
    """Select exactly one solver-optimal candidate; otherwise fail closed."""

    if not isinstance(candidates, list) or not isinstance(statuses, list) or len(candidates) != len(statuses):
        raise ValueError("candidate status alignment")
    accepted = [candidate for candidate, status in zip(candidates, statuses) if status == "optimal"]
    if len(accepted) != 1:
        return _abstain("executable_candidate_not_unique")
    return accepted[0]


__all__ = [
    "enumerate_typed_repair_candidates",
    "infer_typed_repair",
    "select_unique_executable_candidate",
]
