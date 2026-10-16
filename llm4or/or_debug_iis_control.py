"""Answer-free generic IIS control for OR-Debug-Bench.

The module parses a Gurobi-generated IIS in LP format and emits one bounded,
inert repair object.  It never reads benchmark-saved IIS members, target names,
reference repairs, or objectives.  The policy is deliberately generic: remove
all rows in one small IIS, or reset one conflicting nonnegative lower bound.
Its semantic limitations are measured by the evaluator rather than hidden.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any


MAX_IIS_BYTES = 1_000_000
MAX_IIS_CONSTRAINTS = 8
NAME = r"[A-Za-z0-9_.:\-]+"
NUMBER = r"[+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+\-]?\d+)?"
SECTION_NAMES = {
    "maximize": "objective",
    "minimize": "objective",
    "subject to": "constraints",
    "such that": "constraints",
    "bounds": "bounds",
    "generals": "generals",
    "general": "generals",
    "binaries": "binaries",
    "binary": "binaries",
    "end": "end",
}


class IisParseError(ValueError):
    pass


def _number(value: str) -> str:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise IisParseError("invalid numeric literal") from exc
    if not number.is_finite():
        raise IisParseError("numeric literal must be finite")
    normalized = format(number.normalize(), "f")
    return "0" if number == 0 else normalized


def _finish_constraint(
    pending: tuple[str, list[str]] | None,
    constraints: list[dict[str, str]],
) -> None:
    if pending is None:
        return
    name, fragments = pending
    expression = " ".join(fragments)
    match = re.search(rf"(<=|>=|=)\s*({NUMBER})\s*\Z", expression)
    if not match:
        raise IisParseError("constraint lacks a finite terminal relation")
    constraints.append(
        {"name": name, "sense": match.group(1), "rhs": _number(match.group(2))}
    )


def _parse_bound(line: str) -> dict[str, str | None]:
    free = re.fullmatch(rf"({NAME})\s+free", line, flags=re.IGNORECASE)
    if free:
        return {"variable": free.group(1), "lower": None, "upper": None}

    two_sided = re.fullmatch(
        rf"({NUMBER}|-infinity)\s*<=\s*({NAME})\s*<=\s*({NUMBER}|\+?infinity)",
        line,
        flags=re.IGNORECASE,
    )
    if two_sided:
        lower = None if two_sided.group(1).lower() == "-infinity" else _number(two_sided.group(1))
        upper = None if "infinity" in two_sided.group(3).lower() else _number(two_sided.group(3))
        return {"variable": two_sided.group(2), "lower": lower, "upper": upper}

    upper = re.fullmatch(rf"({NAME})\s*<=\s*({NUMBER})", line)
    if upper:
        return {"variable": upper.group(1), "lower": None, "upper": _number(upper.group(2))}
    lower = re.fullmatch(rf"({NAME})\s*>=\s*({NUMBER})", line)
    if lower:
        return {"variable": lower.group(1), "lower": _number(lower.group(2)), "upper": None}
    fixed = re.fullmatch(rf"({NAME})\s*=\s*({NUMBER})", line)
    if fixed:
        value = _number(fixed.group(2))
        return {"variable": fixed.group(1), "lower": value, "upper": value}
    raise IisParseError("unsupported IIS bound")


def parse_gurobi_iis_lp(text: str) -> dict[str, Any]:
    """Parse the public solver's LP-format IIS into a small inert certificate."""

    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > MAX_IIS_BYTES:
        raise IisParseError("IIS LP byte limit")
    section: str | None = None
    pending: tuple[str, list[str]] | None = None
    constraints: list[dict[str, str]] = []
    bounds: list[dict[str, str | None]] = []
    generals: list[str] = []
    binaries: list[str] = []
    saw_end = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("\\"):
            continue
        section_name = SECTION_NAMES.get(line.lower())
        if section_name is not None:
            _finish_constraint(pending, constraints)
            pending = None
            section = section_name
            if section == "end":
                saw_end = True
            continue
        if saw_end:
            raise IisParseError("content after IIS End")
        if section == "constraints":
            named = re.match(rf"({NAME}):\s*(.*)\Z", line)
            if named:
                _finish_constraint(pending, constraints)
                pending = (named.group(1), [named.group(2)])
            elif pending is not None:
                pending[1].append(line)
            else:
                raise IisParseError("constraint continuation without name")
        elif section == "bounds":
            bounds.append(_parse_bound(line))
        elif section == "generals":
            generals.extend(line.split())
        elif section == "binaries":
            binaries.extend(line.split())
        elif section != "objective":
            raise IisParseError("IIS content outside a supported section")

    _finish_constraint(pending, constraints)
    if not saw_end:
        raise IisParseError("missing IIS End")
    constraint_names = [row["name"] for row in constraints]
    if len(constraint_names) != len(set(constraint_names)):
        raise IisParseError("duplicate constraint name")
    bound_names = [row["variable"] for row in bounds]
    if len(bound_names) != len(set(bound_names)):
        raise IisParseError("duplicate bound variable")
    if any(not re.fullmatch(NAME, value) for value in generals + binaries):
        raise IisParseError("invalid domain variable")
    if len(generals) != len(set(generals)) or len(binaries) != len(set(binaries)):
        raise IisParseError("duplicate domain variable")
    if set(generals) & set(binaries):
        raise IisParseError("variable appears in two domain sections")
    return {
        "constraints": constraints,
        "bounds": bounds,
        "general_variables": generals,
        "binary_variables": binaries,
    }


def _abstain(reason: str) -> dict[str, str]:
    return {
        "schema": "or-debug-static-iis-control-v1",
        "status": "abstained",
        "reason": reason,
    }


def build_generic_iis_repair(iis: dict[str, Any]) -> dict[str, Any]:
    """Emit the frozen generic repair or abstain on an unsupported IIS shape."""

    required = {"constraints", "bounds", "general_variables", "binary_variables"}
    if not isinstance(iis, dict) or set(iis) != required:
        raise ValueError("IIS certificate fields")
    constraints = iis["constraints"]
    bounds = iis["bounds"]
    if not isinstance(constraints, list) or not isinstance(bounds, list):
        raise ValueError("IIS constraints and bounds must be lists")
    if constraints:
        if len(constraints) > MAX_IIS_CONSTRAINTS:
            return _abstain("iis_constraint_limit")
        names = [row.get("name") if isinstance(row, dict) else None for row in constraints]
        if any(not isinstance(name, str) or not re.fullmatch(NAME, name) for name in names):
            raise ValueError("invalid IIS constraint")
        if len(names) != len(set(names)):
            raise ValueError("duplicate IIS constraint")
        return {
            "schema": "or-debug-static-iis-control-v1",
            "status": "proposed",
            "repair": {
                "error_type": "solver_iis_static_v1",
                "operations": [
                    {"op": "remove_constraint", "constraint": name} for name in names
                ],
            },
            "evidence": {
                "source": "fresh_solver_iis",
                "iis_constraint_count": len(names),
                "iis_bound_count": len(bounds),
            },
        }

    if len(bounds) == 1 and isinstance(bounds[0], dict):
        bound = bounds[0]
        variable = bound.get("variable")
        lower = bound.get("lower")
        upper = bound.get("upper")
        if isinstance(variable, str) and isinstance(lower, str) and isinstance(upper, str):
            try:
                is_conflict = Decimal(lower) > Decimal(upper)
                accepts_zero = Decimal(upper) >= 0
            except InvalidOperation:
                is_conflict = accepts_zero = False
            if is_conflict and accepts_zero:
                return {
                    "schema": "or-debug-static-iis-control-v1",
                    "status": "proposed",
                    "repair": {
                        "error_type": "solver_iis_static_v1",
                        "operations": [
                            {
                                "op": "set_variable_lower_bound",
                                "variable": variable,
                                "value": "0",
                            }
                        ],
                    },
                    "evidence": {
                        "source": "fresh_solver_iis",
                        "iis_constraint_count": 0,
                        "iis_bound_count": 1,
                    },
                }
    return _abstain("unsupported_iis_shape")


__all__ = [
    "IisParseError",
    "build_generic_iis_repair",
    "parse_gurobi_iis_lp",
]
