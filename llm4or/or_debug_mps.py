"""Restricted MPS patcher for proof-carrying OR-Debug repairs.

The patcher accepts only inert operations from ``or_debug_repair_dsl``.  It
does not execute generated code and fails closed when a target is missing,
duplicated, or inconsistent with the declared old value.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import re
from typing import Any


MAX_MPS_BYTES = 1_000_000
NAME_RE = re.compile(r"[A-Za-z0-9_.:\-]+\Z")
HEADERS = {"NAME", "OBJSENSE", "ROWS", "COLUMNS", "RHS", "RANGES", "BOUNDS", "ENDATA"}
SENSE_TO_MPS = {"<=": "L", ">=": "G", "=": "E"}
MPS_TO_SENSE = {value: key for key, value in SENSE_TO_MPS.items()}


class MpsRepairError(ValueError):
    pass


def _name(value: Any) -> str:
    if not isinstance(value, str) or not NAME_RE.fullmatch(value):
        raise MpsRepairError("invalid MPS name")
    return value


def _number(value: Any) -> str:
    if not isinstance(value, str):
        raise MpsRepairError("numeric DSL values must be strings")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise MpsRepairError("invalid finite numeric value") from exc
    if not number.is_finite():
        raise MpsRepairError("invalid finite numeric value")
    normalized = format(number.normalize(), "f")
    return "0" if number == 0 else normalized


def _parse(text: str) -> list[dict[str, Any]]:
    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > MAX_MPS_BYTES:
        raise MpsRepairError("MPS byte limit")
    lines: list[dict[str, Any]] = []
    section: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            lines.append({"kind": "blank", "raw": raw, "section": section})
            continue
        if stripped.startswith("*"):
            lines.append({"kind": "comment", "raw": raw, "section": section})
            continue
        tokens = stripped.split()
        if tokens[0] in HEADERS:
            section = tokens[0]
            lines.append(
                {"kind": "header", "raw": raw, "tokens": tokens, "section": section}
            )
            continue
        if section is None:
            raise MpsRepairError("data before first MPS section")
        lines.append(
            {"kind": "data", "raw": raw, "tokens": tokens, "section": section}
        )
    sections = {line["section"] for line in lines if line["kind"] == "header"}
    required = {"NAME", "ROWS", "COLUMNS", "RHS", "BOUNDS", "ENDATA"}
    if not required <= sections:
        raise MpsRepairError("missing required MPS section")
    return lines


def _render(lines: list[dict[str, Any]]) -> str:
    rendered = []
    for line in lines:
        if line.get("deleted"):
            continue
        if line["kind"] == "data" and "tokens" in line:
            tokens = line["tokens"]
            section = line["section"]
            if section == "ROWS":
                rendered.append(f" {tokens[0]}  {tokens[1]}")
            elif section == "COLUMNS":
                if len(tokens) >= 3 and tokens[1] == "'MARKER'":
                    rendered.append(
                        f"    {tokens[0]:<8}  {tokens[1]:<8}                 {tokens[2]}"
                    )
                else:
                    value = f"    {tokens[0]:<10}  {tokens[1]:<8}  {tokens[2]}"
                    if len(tokens) == 5:
                        value += f"  {tokens[3]:<8}  {tokens[4]}"
                    rendered.append(value)
            elif section in {"RHS", "RANGES"}:
                value = f"    {tokens[0]:<10}  {tokens[1]:<8}  {tokens[2]}"
                if len(tokens) == 5:
                    value += f"  {tokens[3]:<8}  {tokens[4]}"
                rendered.append(value)
            elif section == "BOUNDS":
                value = f" {tokens[0]:<2} {tokens[1]:<10} {tokens[2]:<8}"
                if len(tokens) == 4:
                    value += f"  {tokens[3]}"
                rendered.append(value.rstrip())
            else:
                rendered.append(" ".join(tokens))
        else:
            rendered.append(line["raw"])
    return "\n".join(rendered) + "\n"


def _data(lines: list[dict[str, Any]], section: str) -> list[dict[str, Any]]:
    return [
        line
        for line in lines
        if not line.get("deleted") and line["kind"] == "data" and line["section"] == section
    ]


def _pairs(tokens: list[str], section: str) -> list[tuple[str, str]]:
    if section == "COLUMNS" and len(tokens) >= 3 and tokens[1] == "'MARKER'":
        return []
    if len(tokens) not in {3, 5}:
        raise MpsRepairError(f"unsupported {section} token count")
    return [(tokens[index], tokens[index + 1]) for index in range(1, len(tokens), 2)]


def _set_pairs(tokens: list[str], pairs: list[tuple[str, str]]) -> list[str]:
    result = [tokens[0]]
    for row, value in pairs:
        result.extend([row, value])
    return result


def _integer_variables(lines: list[dict[str, Any]]) -> set[str]:
    active = False
    variables: set[str] = set()
    for line in _data(lines, "COLUMNS"):
        tokens = line["tokens"]
        if len(tokens) >= 3 and tokens[1] == "'MARKER'":
            if tokens[2] == "'INTORG'":
                if active:
                    raise MpsRepairError("nested INTORG marker")
                active = True
            elif tokens[2] == "'INTEND'":
                if not active:
                    raise MpsRepairError("unmatched INTEND marker")
                active = False
            else:
                raise MpsRepairError("unknown integer marker")
        elif active:
            variables.add(tokens[0])
    if active:
        raise MpsRepairError("unterminated integer marker")
    return variables


def _row_lines(lines: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [
        line
        for line in _data(lines, "ROWS")
        if len(line["tokens"]) == 2 and line["tokens"][1] == name
    ]


def _remove_references(
    lines: list[dict[str, Any]], section: str, row_name: str
) -> int:
    removed = 0
    for line in _data(lines, section):
        tokens = line["tokens"]
        if section == "COLUMNS" and len(tokens) >= 3 and tokens[1] == "'MARKER'":
            continue
        pairs = _pairs(tokens, section)
        kept = []
        for pair in pairs:
            if pair[0] == row_name:
                removed += 1
            else:
                kept.append(pair)
        if len(kept) != len(pairs):
            if kept:
                line["tokens"] = _set_pairs(tokens, kept)
            else:
                line["deleted"] = True
    return removed


def _validate_structure(lines: list[dict[str, Any]]) -> None:
    row_types: dict[str, str] = {}
    for line in _data(lines, "ROWS"):
        tokens = line["tokens"]
        if len(tokens) != 2 or tokens[0] not in {"N", "L", "G", "E"}:
            raise MpsRepairError("invalid ROWS record")
        if tokens[1] in row_types:
            raise MpsRepairError("duplicate row name")
        row_types[tokens[1]] = tokens[0]
    if not any(value == "N" for value in row_types.values()):
        raise MpsRepairError("missing objective row")

    variables: set[str] = set()
    for line in _data(lines, "COLUMNS"):
        tokens = line["tokens"]
        if len(tokens) >= 3 and tokens[1] == "'MARKER'":
            continue
        variables.add(_name(tokens[0]))
        for row, value in _pairs(tokens, "COLUMNS"):
            if row not in row_types:
                raise MpsRepairError("column references unknown row")
            _number(value)
    for section in ("RHS", "RANGES"):
        for line in _data(lines, section):
            for row, value in _pairs(line["tokens"], section):
                if row not in row_types:
                    raise MpsRepairError(f"{section} references unknown row")
                _number(value)
    for line in _data(lines, "BOUNDS"):
        tokens = line["tokens"]
        if len(tokens) not in {3, 4} or tokens[0] not in {
            "BV", "UP", "LO", "FR", "FX", "LI", "UI", "MI", "PL"
        }:
            raise MpsRepairError("invalid BOUNDS record")
        if tokens[2] not in variables:
            raise MpsRepairError("bound references unknown variable")
        if len(tokens) == 4:
            _number(tokens[3])
    _integer_variables(lines)


def _preserve_bound_only_variables(
    lines: list[dict[str, Any]], original_integers: set[str]
) -> list[str]:
    """Declare orphaned auxiliary variables with a zero objective column."""

    objective_rows = [
        line["tokens"][1]
        for line in _data(lines, "ROWS")
        if len(line["tokens"]) == 2 and line["tokens"][0] == "N"
    ]
    if len(objective_rows) != 1:
        raise MpsRepairError("expected exactly one objective row")
    objective = objective_rows[0]
    column_variables = {
        line["tokens"][0]
        for line in _data(lines, "COLUMNS")
        if not (len(line["tokens"]) >= 3 and line["tokens"][1] == "'MARKER'")
    }
    bound_variables = {line["tokens"][2] for line in _data(lines, "BOUNDS")}
    missing = sorted(bound_variables - column_variables)
    if not missing:
        return []

    rhs_index = next(
        (index for index, line in enumerate(lines) if line["kind"] == "header" and line["section"] == "RHS"),
        None,
    )
    if rhs_index is None:
        raise MpsRepairError("missing RHS insertion boundary")
    for variable in reversed([name for name in missing if name not in original_integers]):
        lines.insert(
            rhs_index,
            {
                "kind": "data",
                "raw": "",
                "tokens": [variable, objective, "0"],
                "section": "COLUMNS",
            },
        )

    integer_missing = [name for name in missing if name in original_integers]
    if integer_missing:
        intend_index = next(
            (
                index
                for index, line in enumerate(lines)
                if line["kind"] == "data"
                and line["section"] == "COLUMNS"
                and len(line["tokens"]) >= 3
                and line["tokens"][1] == "'MARKER'"
                and line["tokens"][2] == "'INTEND'"
            ),
            None,
        )
        if intend_index is None:
            raise MpsRepairError("cannot preserve orphan integer variable")
        for variable in reversed(integer_missing):
            lines.insert(
                intend_index,
                {
                    "kind": "data",
                    "raw": "",
                    "tokens": [variable, objective, "0"],
                    "section": "COLUMNS",
                },
            )
    return missing


def _move_variable_out_of_integer_markers(
    lines: list[dict[str, Any]], variable: str
) -> None:
    active = False
    start_line: dict[str, Any] | None = None
    target_lines: list[dict[str, Any]] = []
    other_integer_data = False
    end_line: dict[str, Any] | None = None
    for line in _data(lines, "COLUMNS"):
        tokens = line["tokens"]
        if len(tokens) >= 3 and tokens[1] == "'MARKER'":
            if tokens[2] == "'INTORG'":
                if active:
                    raise MpsRepairError("nested INTORG marker")
                active = True
                start_line = line
                other_integer_data = False
            elif tokens[2] == "'INTEND'":
                if not active:
                    raise MpsRepairError("unmatched INTEND marker")
                active = False
                end_line = line
                if target_lines:
                    break
                start_line = None
                end_line = None
            continue
        if active:
            if tokens[0] == variable:
                target_lines.append(line)
            else:
                other_integer_data = True
    if active or start_line is None or end_line is None or not target_lines:
        raise MpsRepairError("continuous-domain target not found in one marker block")
    all_target_lines = [
        line
        for line in _data(lines, "COLUMNS")
        if not (len(line["tokens"]) >= 3 and line["tokens"][1] == "'MARKER'")
        and line["tokens"][0] == variable
    ]
    if set(map(id, all_target_lines)) != set(map(id, target_lines)):
        raise MpsRepairError("target variable spans integer and continuous regions")
    for line in target_lines:
        lines.remove(line)
    insert_at = lines.index(end_line) + 1
    for line in target_lines:
        lines.insert(insert_at, line)
        insert_at += 1
    if not other_integer_data:
        start_line["deleted"] = True
        end_line["deleted"] = True


def apply_repair(mps_text: str, repair: dict[str, Any]) -> dict[str, Any]:
    """Apply one validated repair object and return MPS plus an edit audit."""

    if set(repair) != {"error_type", "operations"}:
        raise MpsRepairError("repair object fields")
    if not isinstance(repair["error_type"], str):
        raise MpsRepairError("repair error_type")
    operations = repair["operations"]
    if not isinstance(operations, list) or not 1 <= len(operations) <= 16:
        raise MpsRepairError("repair operation count")
    lines = _parse(mps_text)
    _validate_structure(lines)
    original_integers = _integer_variables(lines)
    changes: list[dict[str, Any]] = []
    removed_constraints: list[str] = []

    for operation in operations:
        if not isinstance(operation, dict) or "op" not in operation:
            raise MpsRepairError("invalid operation")
        kind = operation["op"]
        if kind == "set_constraint_sense":
            if set(operation) != {"op", "constraint", "from", "to"}:
                raise MpsRepairError("sense operation fields")
            name = _name(operation["constraint"])
            rows = _row_lines(lines, name)
            if len(rows) != 1 or rows[0]["tokens"][0] == "N":
                raise MpsRepairError("sense target must be one constraint row")
            old = MPS_TO_SENSE.get(rows[0]["tokens"][0])
            if old != operation["from"] or operation["to"] not in SENSE_TO_MPS:
                raise MpsRepairError("declared old/new sense mismatch")
            rows[0]["tokens"][0] = SENSE_TO_MPS[operation["to"]]
            changes.append({"field": "constraint_sense", "target": name, "from": old, "to": operation["to"]})
        elif kind == "remove_constraint":
            if set(operation) != {"op", "constraint"}:
                raise MpsRepairError("remove operation fields")
            name = _name(operation["constraint"])
            rows = _row_lines(lines, name)
            if len(rows) != 1 or rows[0]["tokens"][0] == "N":
                raise MpsRepairError("remove target must be one constraint row")
            rows[0]["deleted"] = True
            references = 0
            for section in ("COLUMNS", "RHS", "RANGES"):
                references += _remove_references(lines, section, name)
            if references == 0:
                raise MpsRepairError("removed constraint had no model references")
            removed_constraints.append(name)
            changes.append({"field": "constraint", "target": name, "action": "remove", "references_removed": references})
        elif kind == "set_coefficient":
            if set(operation) != {"op", "constraint", "variable", "from", "to"}:
                raise MpsRepairError("coefficient operation fields")
            row = _name(operation["constraint"])
            variable = _name(operation["variable"])
            old = _number(operation["from"])
            new = _number(operation["to"])
            matches: list[tuple[dict[str, Any], int]] = []
            for line in _data(lines, "COLUMNS"):
                tokens = line["tokens"]
                if tokens[0] != variable or (len(tokens) >= 3 and tokens[1] == "'MARKER'"):
                    continue
                for index, pair in enumerate(_pairs(tokens, "COLUMNS")):
                    if pair[0] == row:
                        matches.append((line, index))
            if len(matches) != 1:
                raise MpsRepairError("coefficient target must occur exactly once")
            line, index = matches[0]
            pairs = _pairs(line["tokens"], "COLUMNS")
            if _number(pairs[index][1]) != old:
                raise MpsRepairError("declared old coefficient mismatch")
            pairs[index] = (row, new)
            line["tokens"] = _set_pairs(line["tokens"], pairs)
            changes.append({"field": "coefficient", "target": f"{row}:{variable}", "from": old, "to": new})
        elif kind == "set_constraint_rhs":
            if set(operation) != {"op", "constraint", "value"}:
                raise MpsRepairError("RHS operation fields")
            row = _name(operation["constraint"])
            value = _number(operation["value"])
            matches: list[tuple[dict[str, Any], int]] = []
            for line in _data(lines, "RHS"):
                for index, pair in enumerate(_pairs(line["tokens"], "RHS")):
                    if pair[0] == row:
                        matches.append((line, index))
            if len(matches) != 1:
                raise MpsRepairError("RHS target must occur exactly once")
            line, index = matches[0]
            pairs = _pairs(line["tokens"], "RHS")
            old = _number(pairs[index][1])
            pairs[index] = (row, value)
            line["tokens"] = _set_pairs(line["tokens"], pairs)
            changes.append({"field": "constraint_rhs", "target": row, "from": old, "to": value})
        elif kind == "set_variable_lower_bound":
            if set(operation) != {"op", "variable", "value"}:
                raise MpsRepairError("lower-bound operation fields")
            variable = _name(operation["variable"])
            value = _number(operation["value"])
            matches = [line for line in _data(lines, "BOUNDS") if line["tokens"][0] == "LO" and line["tokens"][2] == variable]
            if len(matches) != 1 or len(matches[0]["tokens"]) != 4:
                raise MpsRepairError("lower-bound target must occur exactly once")
            old = _number(matches[0]["tokens"][3])
            matches[0]["tokens"][3] = value
            changes.append({"field": "variable_lower_bound", "target": variable, "from": old, "to": value})
        elif kind == "set_variable_domain":
            if set(operation) != {"op", "variable", "domain", "upper_bound"} or operation["domain"] not in {"integer", "continuous"}:
                raise MpsRepairError("domain operation fields")
            variable = _name(operation["variable"])
            upper = _number(operation["upper_bound"])
            if variable not in _integer_variables(lines):
                raise MpsRepairError("domain target is outside integer markers")
            matches = [line for line in _data(lines, "BOUNDS") if line["tokens"][0] == "BV" and line["tokens"][2] == variable]
            if len(matches) != 1:
                raise MpsRepairError("binary bound target must occur exactly once")
            bound_set = matches[0]["tokens"][1]
            matches[0]["tokens"] = ["UP", bound_set, variable, upper]
            if operation["domain"] == "continuous":
                _move_variable_out_of_integer_markers(lines, variable)
            changes.append({"field": "variable_domain", "target": variable, "from": "binary", "to": operation["domain"], "upper_bound": upper})
        else:
            raise MpsRepairError("unsupported repair operation")

    zero_columns_added = _preserve_bound_only_variables(lines, original_integers)
    _validate_structure(lines)
    output = _render(lines)
    if output == mps_text:
        raise MpsRepairError("repair made no change")
    return {
        "mps": output,
        "audit": {
            "pre_sha256": hashlib.sha256(mps_text.encode("utf-8")).hexdigest(),
            "post_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            "operation_count": len(operations),
            "changes": changes,
            "removed_constraints": removed_constraints,
            "zero_columns_added": zero_columns_added,
            "certificate_scope": "exact_declared_MPS_fields_plus_structural_recheck",
        },
    }


__all__ = ["MAX_MPS_BYTES", "MpsRepairError", "apply_repair"]
