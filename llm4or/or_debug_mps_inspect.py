"""Read-only normalized public-model view for OR-Debug typed repair skills."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .or_debug_mps import (
    MPS_TO_SENSE,
    MpsRepairError,
    _data,
    _integer_variables,
    _number,
    _pairs,
    _parse,
)


def _add(left: str, right: str) -> str:
    return _number(str(Decimal(left) + Decimal(right)))


def inspect_mps(mps_text: str) -> dict[str, Any]:
    """Return constraints and variable domains from public MPS content only."""

    lines = _parse(mps_text)
    row_types: dict[str, str] = {}
    objective_rows: list[str] = []
    for line in _data(lines, "ROWS"):
        tokens = line["tokens"]
        if len(tokens) != 2 or tokens[1] in row_types:
            raise MpsRepairError("invalid or duplicate row")
        row_types[tokens[1]] = tokens[0]
        if tokens[0] == "N":
            objective_rows.append(tokens[1])
        elif tokens[0] not in MPS_TO_SENSE:
            raise MpsRepairError("unsupported row sense")
    if len(objective_rows) != 1:
        raise MpsRepairError("expected one objective row")

    coefficients: dict[str, dict[str, str]] = {
        name: {} for name, kind in row_types.items() if kind != "N"
    }
    variables: dict[str, dict[str, str | None]] = {}
    integer_variables = _integer_variables(lines)
    for line in _data(lines, "COLUMNS"):
        tokens = line["tokens"]
        if len(tokens) >= 3 and tokens[1] == "'MARKER'":
            continue
        variable = tokens[0]
        variables.setdefault(
            variable,
            {
                "domain": "integer" if variable in integer_variables else "continuous",
                "lower": "0",
                "upper": None,
            },
        )
        for row, value in _pairs(tokens, "COLUMNS"):
            if row in objective_rows:
                continue
            if row not in coefficients:
                raise MpsRepairError("coefficient references unknown row")
            normalized = _number(value)
            prior = coefficients[row].get(variable)
            coefficients[row][variable] = normalized if prior is None else _add(prior, normalized)

    rhs: dict[str, str] = {name: "0" for name in coefficients}
    for line in _data(lines, "RHS"):
        for row, value in _pairs(line["tokens"], "RHS"):
            if row in objective_rows:
                continue
            if row not in rhs or rhs[row] != "0":
                raise MpsRepairError("duplicate or unknown RHS row")
            rhs[row] = _number(value)

    for line in _data(lines, "BOUNDS"):
        tokens = line["tokens"]
        if len(tokens) not in {3, 4} or tokens[2] not in variables:
            raise MpsRepairError("invalid public bound")
        kind, variable = tokens[0], tokens[2]
        value = _number(tokens[3]) if len(tokens) == 4 else None
        target = variables[variable]
        if kind == "BV":
            target.update({"domain": "binary", "lower": "0", "upper": "1"})
        elif kind == "LO" and value is not None:
            target["lower"] = value
        elif kind == "UP" and value is not None:
            target["upper"] = value
        elif kind == "FR":
            target.update({"lower": None, "upper": None})
        elif kind == "FX" and value is not None:
            target.update({"lower": value, "upper": value})
        elif kind == "LI" and value is not None:
            target.update({"domain": "integer", "lower": value})
        elif kind == "UI" and value is not None:
            target.update({"domain": "integer", "upper": value})
        elif kind == "MI":
            target["lower"] = None
        elif kind == "PL":
            target["upper"] = None
        else:
            raise MpsRepairError("unsupported public bound")

    rows = {
        name: {
            "sense": MPS_TO_SENSE[row_types[name]],
            "rhs": rhs[name],
            "coefficients": dict(sorted(coefficients[name].items())),
        }
        for name in sorted(coefficients)
    }
    return {
        "objective_rows": objective_rows,
        "rows": rows,
        "variables": dict(sorted(variables.items())),
    }


__all__ = ["inspect_mps"]
