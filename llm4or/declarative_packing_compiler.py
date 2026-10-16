"""Trusted interpreter for inert one-dimensional bin-packing skill configs.

The proposer controls only literal parsing metadata and symbolic field
references.  The two-index assignment formulation and solver remain fixed,
trusted, and hash-bound outside the evolving skill package.
"""

from __future__ import annotations

import math
import re
import time
from typing import Any

from .benchmark_inputs import validate_public_input
from .milp_schema import model as validate_model


VERSION = "declarative-bin-packing-compiler-v1"
CONFIG_SCHEMA = "declarative-bin-packing-v1"
NUMERIC = re.compile(r"[-+]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)")


class DeclarativePackingError(ValueError):
    pass


def optimal_bin_count(weights: list[float], capacity: float, *, wall_seconds: int = 20,
                      node_limit: int = 2_000_000) -> int:
    """Solve one-dimensional bin packing by exact bounded branch and bound."""
    if not weights or not math.isfinite(capacity) or capacity <= 0 \
            or any(not math.isfinite(weight) or weight <= 0 or weight > capacity for weight in weights):
        raise DeclarativePackingError("invalid_bin_packing_instance")
    ordered = sorted((float(weight) for weight in weights), reverse=True)
    tolerance = max(1e-9, abs(capacity) * 1e-10)
    lower = int(math.ceil((sum(ordered) - tolerance) / capacity))

    first_fit_loads: list[float] = []
    for weight in ordered:
        for index, load in enumerate(first_fit_loads):
            if load + weight <= capacity + tolerance:
                first_fit_loads[index] += weight
                break
        else:
            first_fit_loads.append(weight)
    best = len(first_fit_loads)
    if best == lower:
        return best

    suffix = [0.0] * (len(ordered) + 1)
    for index in range(len(ordered) - 1, -1, -1):
        suffix[index] = suffix[index + 1] + ordered[index]
    deadline = time.monotonic() + max(0.01, wall_seconds)
    nodes = 0
    memo: set[tuple[int, tuple[int, ...]]] = set()
    scale = max(tolerance, 1e-8)

    def search(item_index: int, loads: list[float]) -> None:
        nonlocal best, nodes
        nodes += 1
        if nodes > node_limit or time.monotonic() > deadline:
            raise DeclarativePackingError("exact_bin_packing_limit")
        if best == lower:
            return
        if item_index == len(ordered):
            best = min(best, len(loads)); return
        free = sum(capacity - load for load in loads)
        additional = int(math.ceil(max(0.0, suffix[item_index] - free - tolerance) / capacity))
        if len(loads) + additional >= best:
            return
        state = (item_index, tuple(sorted(int(round(load / scale)) for load in loads)))
        if state in memo:
            return
        memo.add(state)
        weight = ordered[item_index]
        seen_loads: set[int] = set()
        # Try fuller bins first to reduce residual fragmentation.
        for bin_index in sorted(range(len(loads)), key=lambda index: loads[index], reverse=True):
            key = int(round(loads[bin_index] / scale))
            if key in seen_loads:
                continue
            seen_loads.add(key)
            if loads[bin_index] + weight <= capacity + tolerance:
                loads[bin_index] += weight
                search(item_index + 1, loads)
                loads[bin_index] -= weight
                if best == lower:
                    return
        if len(loads) + 1 < best:
            loads.append(weight)
            search(item_index + 1, loads)
            loads.pop()

    search(1, [ordered[0]])
    return best


def _exact_keys(value: Any, expected: set[str], reason: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise DeclarativePackingError(reason)


def _literal(value: Any, *, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise DeclarativePackingError("invalid_literal")
    if any(ord(character) < 32 and character != "\t" for character in value):
        raise DeclarativePackingError("control_character")
    return value


def validate_configuration(configuration: Any) -> dict[str, Any]:
    _exact_keys(configuration, {
        "schema", "record_rule", "capacity_rule", "item_weight_field",
        "capacity_scalar", "objective", "assignment", "capacity_constraint",
        "symmetry_breaking", "minimum_records", "maximum_records",
    }, "invalid_configuration_fields")
    if configuration["schema"] != CONFIG_SCHEMA:
        raise DeclarativePackingError("invalid_configuration_schema")
    record = configuration["record_rule"]
    _exact_keys(record, {"line_prefixes", "id_suffix", "numeric_fields"},
                "invalid_record_rule")
    if not isinstance(record["line_prefixes"], list) or not record["line_prefixes"] \
            or len(record["line_prefixes"]) > 64:
        raise DeclarativePackingError("invalid_line_prefixes")
    for prefix in record["line_prefixes"]:
        _literal(prefix)
    if len(set(record["line_prefixes"])) != len(record["line_prefixes"]):
        raise DeclarativePackingError("duplicate_line_prefix")
    _literal(record["id_suffix"])
    fields = record["numeric_fields"]
    if not isinstance(fields, list) or not fields or len(fields) > 8:
        raise DeclarativePackingError("invalid_numeric_fields")
    names = []
    for field in fields:
        _exact_keys(field, {"name", "position"}, "invalid_numeric_field")
        names.append(_literal(field["name"], maximum=80))
        if type(field["position"]) is not int or not 0 <= field["position"] <= 15:
            raise DeclarativePackingError("invalid_numeric_position")
    if len(names) != len(set(names)):
        raise DeclarativePackingError("duplicate_field_name")
    capacity = configuration["capacity_rule"]
    _exact_keys(capacity, {"name", "required_any", "forbidden_any", "numeric_position"},
                "invalid_capacity_rule")
    _literal(capacity["name"], maximum=80)
    for key in ("required_any", "forbidden_any"):
        if not isinstance(capacity[key], list) or len(capacity[key]) > 64:
            raise DeclarativePackingError("invalid_capacity_phrases")
        for phrase in capacity[key]:
            _literal(phrase)
    if not capacity["required_any"] or type(capacity["numeric_position"]) is not int \
            or not 0 <= capacity["numeric_position"] <= 15:
        raise DeclarativePackingError("invalid_capacity_position")
    if configuration["item_weight_field"] not in names \
            or configuration["capacity_scalar"] != capacity["name"]:
        raise DeclarativePackingError("invalid_field_reference")
    if configuration["objective"] != "minimize_used_bins" \
            or configuration["assignment"] != "each_item_exactly_once" \
            or configuration["capacity_constraint"] != "sum_weight_le_capacity_times_used" \
            or configuration["symmetry_breaking"] != "used_bins_prefix":
        raise DeclarativePackingError("invalid_formulation_contract")
    for key in ("minimum_records", "maximum_records"):
        if type(configuration[key]) is not int or not 1 <= configuration[key] <= 1_000:
            raise DeclarativePackingError("invalid_record_limit")
    if configuration["minimum_records"] > configuration["maximum_records"]:
        raise DeclarativePackingError("invalid_record_limit_order")
    return configuration


def parse_packing_text(text: str, configuration: Any) -> dict[str, Any]:
    config = validate_configuration(configuration)
    if not isinstance(text, str):
        raise DeclarativePackingError("text_required")
    records = []
    rule = config["record_rule"]
    for raw_line in text.splitlines():
        line = raw_line.strip()
        matching = [prefix for prefix in rule["line_prefixes"]
                    if line.casefold().startswith(prefix.casefold())]
        if not matching:
            continue
        longest = max(map(len, matching))
        matching = [prefix for prefix in matching if len(prefix) == longest]
        if len(matching) != 1:
            raise DeclarativePackingError("line_prefix_not_unique")
        remainder = line[len(matching[0]):]
        cut = remainder.find(rule["id_suffix"])
        if cut <= 0:
            raise DeclarativePackingError("record_identifier_missing")
        identifier = remainder[:cut].strip()
        if not identifier or len(identifier) > 200:
            raise DeclarativePackingError("invalid_record_identifier")
        payload = remainder[cut + len(rule["id_suffix"]):]
        values = [float(value.replace(",", "")) for value in NUMERIC.findall(payload)]
        fields = {}
        for field in rule["numeric_fields"]:
            if field["position"] >= len(values):
                raise DeclarativePackingError("numeric_field_missing")
            value = values[field["position"]]
            if not math.isfinite(value) or value <= 0 or value > 1e12:
                raise DeclarativePackingError("invalid_item_value")
            fields[field["name"]] = value
        records.append({"id": identifier, "fields": fields})
    if not config["minimum_records"] <= len(records) <= config["maximum_records"]:
        raise DeclarativePackingError("record_count_out_of_bounds")
    if len({record["id"] for record in records}) != len(records):
        raise DeclarativePackingError("duplicate_record_identifier")

    capacity = config["capacity_rule"]
    candidates = []
    for raw_line in text.splitlines():
        folded = raw_line.casefold()
        if not any(phrase.casefold() in folded for phrase in capacity["required_any"]) \
                or any(phrase.casefold() in folded for phrase in capacity["forbidden_any"]):
            continue
        values = [float(value.replace(",", "")) for value in NUMERIC.findall(raw_line)]
        if capacity["numeric_position"] < len(values):
            candidates.append(values[capacity["numeric_position"]])
    if len(candidates) != 1:
        raise DeclarativePackingError("capacity_line_not_unique")
    if not math.isfinite(candidates[0]) or candidates[0] <= 0:
        raise DeclarativePackingError("invalid_capacity")
    weights = [record["fields"][config["item_weight_field"]] for record in records]
    if any(weight > candidates[0] for weight in weights):
        raise DeclarativePackingError("item_exceeds_capacity")
    return {"records": records, "capacity": candidates[0]}


def compile_packing_model(text: str, configuration: Any) -> dict[str, Any]:
    config = validate_configuration(configuration)
    parsed = parse_packing_text(text, config)
    n = len(parsed["records"])
    variables = []
    for bin_index in range(n):
        variables.append({
            "id": f"used_{bin_index:04d}", "meaning": f"candidate bin {bin_index} is used",
            "unit": "binary", "domain": "binary", "lower": 0, "upper": 1,
        })
    for item_index, record in enumerate(parsed["records"]):
        for bin_index in range(n):
            variables.append({
                "id": f"assign_{item_index:04d}_{bin_index:04d}",
                "meaning": f"assign item {record['id']} to candidate bin {bin_index}",
                "unit": "binary", "domain": "binary", "lower": 0, "upper": 1,
            })
    constraints = []
    for item_index in range(n):
        constraints.append({
            "id": f"assign_once_{item_index:04d}",
            "coefficients": {f"assign_{item_index:04d}_{bin_index:04d}": 1
                             for bin_index in range(n)},
            "sense": "eq", "rhs": 1,
        })
    for bin_index in range(n):
        coefficients = {
            f"assign_{item_index:04d}_{bin_index:04d}":
                parsed["records"][item_index]["fields"][config["item_weight_field"]]
            for item_index in range(n)
        }
        coefficients[f"used_{bin_index:04d}"] = -parsed["capacity"]
        constraints.append({
            "id": f"capacity_{bin_index:04d}", "coefficients": coefficients,
            "sense": "le", "rhs": 0,
        })
    for bin_index in range(n - 1):
        constraints.append({
            "id": f"used_prefix_{bin_index:04d}",
            "coefficients": {f"used_{bin_index + 1:04d}": 1,
                             f"used_{bin_index:04d}": -1},
            "sense": "le", "rhs": 0,
        })
    return validate_model({
        "schema": "milp-v1", "variables": variables, "constraints": constraints,
        "objective": {
            "coefficients": {f"used_{bin_index:04d}": 1 for bin_index in range(n)},
            "sense": "min", "unit": "bins", "offset": 0,
        },
    })


def solve_declarative_packing(public_problem: Any, limits: Any,
                              configuration: Any) -> dict[str, Any]:
    public = validate_public_input(public_problem)
    config = validate_configuration(configuration)
    if len(public["text"].encode()) > limits["max_input_bytes"]:
        raise DeclarativePackingError("input_limit")
    model = compile_packing_model(public["text"], config)
    if len(model["variables"]) > limits["max_variables"] \
            or len(model["constraints"]) > limits["max_constraints"]:
        raise DeclarativePackingError("model_limit")
    parsed = parse_packing_text(public["text"], config)
    objective = optimal_bin_count(
        [record["fields"][config["item_weight_field"]] for record in parsed["records"]],
        parsed["capacity"], wall_seconds=min(20, max(1, limits["wall_seconds"] - 2)),
    )
    return {"status": "optimal", "objective": objective,
            "certificate": "trusted_exact_bin_packing_branch_and_bound",
            "compiler_version": VERSION}


__all__ = [
    "CONFIG_SCHEMA", "DeclarativePackingError", "VERSION", "compile_packing_model",
    "optimal_bin_count", "parse_packing_text", "solve_declarative_packing",
    "validate_configuration",
]
