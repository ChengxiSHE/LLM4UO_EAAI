"""Trusted interpreter for inert binary-selection skill configurations.

The configuration contains literal delimiters and algebraic field references,
never Python or regular expressions.  A proposer can therefore induce a new
parser/formulation skill while the executable compiler and solver remain fixed
and hash-bound outside the self-improving loop.
"""

from __future__ import annotations

import math
import re
from typing import Any

from .benchmark_inputs import validate_public_input
from .milp_schema import model as validate_model
from .milp_solver import execute


VERSION = "declarative-binary-selection-compiler-v4"
CONFIG_SCHEMA = "declarative-binary-selection-v1"
CONFIG_SCHEMA_V2 = "declarative-binary-selection-v2"
CONFIG_SCHEMA_V3 = "declarative-binary-selection-v3"
CONFIG_SCHEMA_V4 = "declarative-binary-selection-v4"
NUMERIC = re.compile(r"[-+]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)")


class DeclarativeSkillError(ValueError):
    pass


def _exact_keys(value: Any, expected: set[str], reason: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise DeclarativeSkillError(reason)


def _literal(value: Any, *, empty: bool = False, maximum: int = 300) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value):
        raise DeclarativeSkillError("invalid_literal")
    if any(ord(character) < 32 and character not in "\t" for character in value):
        raise DeclarativeSkillError("control_character")
    return value


def validate_configuration(configuration: Any) -> dict[str, Any]:
    if not isinstance(configuration, dict) or configuration.get("schema") not in {
        CONFIG_SCHEMA, CONFIG_SCHEMA_V2, CONFIG_SCHEMA_V3, CONFIG_SCHEMA_V4,
    }:
        raise DeclarativeSkillError("invalid_configuration_schema")
    if configuration["schema"] in {CONFIG_SCHEMA_V3, CONFIG_SCHEMA_V4}:
        _exact_keys(configuration, {
            "schema", "record_rule", "scalar_rules", "variable_domain", "objective",
            "constraints", "minimum_records", "maximum_records",
        }, "invalid_configuration_fields")
        record = configuration["record_rule"]
        _exact_keys(record, {"line_prefixes", "id_suffix", "numeric_fields"},
                    "invalid_numeric_record_rule")
        if not isinstance(record["line_prefixes"], list) or not record["line_prefixes"] \
                or len(record["line_prefixes"]) > 32:
            raise DeclarativeSkillError("invalid_line_prefixes")
        for prefix in record["line_prefixes"]:
            _literal(prefix)
        if len(set(record["line_prefixes"])) != len(record["line_prefixes"]):
            raise DeclarativeSkillError("duplicate_line_prefix")
        _literal(record["id_suffix"])
        if not isinstance(record["numeric_fields"], list) or not record["numeric_fields"] \
                or len(record["numeric_fields"]) > 16:
            raise DeclarativeSkillError("invalid_numeric_fields")
        names = []
        for field in record["numeric_fields"]:
            expected_field = {"name", "position", "normalizer"} \
                if configuration["schema"] == CONFIG_SCHEMA_V4 else {"name", "position"}
            _exact_keys(field, expected_field, "invalid_numeric_field")
            names.append(_literal(field["name"], maximum=80))
            if type(field["position"]) is not int or not 0 <= field["position"] <= 31:
                raise DeclarativeSkillError("invalid_numeric_position")
            if configuration["schema"] == CONFIG_SCHEMA_V4 \
                    and field["normalizer"] not in {"identity", "currency_thousands"}:
                raise DeclarativeSkillError("invalid_numeric_normalizer")
        if len(names) != len(set(names)):
            raise DeclarativeSkillError("duplicate_field_name")
        scalar_rules = configuration["scalar_rules"]
        if not isinstance(scalar_rules, list) or not scalar_rules or len(scalar_rules) > 16:
            raise DeclarativeSkillError("invalid_scalar_rules")
        scalar_names = []
        for scalar in scalar_rules:
            _exact_keys(scalar, {"name", "required_any", "forbidden_any", "numeric_position"},
                        "invalid_numeric_scalar_rule")
            scalar_names.append(_literal(scalar["name"], maximum=80))
            for key in ("required_any", "forbidden_any"):
                if not isinstance(scalar[key], list) or len(scalar[key]) > 32:
                    raise DeclarativeSkillError("invalid_scalar_phrases")
                for phrase in scalar[key]:
                    _literal(phrase)
            if not scalar["required_any"] or type(scalar["numeric_position"]) is not int \
                    or not 0 <= scalar["numeric_position"] <= 31:
                raise DeclarativeSkillError("invalid_scalar_numeric_position")
        if len(scalar_names) != len(set(scalar_names)):
            raise DeclarativeSkillError("duplicate_scalar_name")
        _validate_algebra(configuration, names, scalar_names)
        return configuration
    expected = {"schema", "scalar_rules", "variable_domain", "objective", "constraints",
                "minimum_records", "maximum_records"}
    expected.add("record_rule" if configuration["schema"] == CONFIG_SCHEMA else "record_rules")
    _exact_keys(configuration, expected, "invalid_configuration_fields")
    records = [configuration["record_rule"]] if configuration["schema"] == CONFIG_SCHEMA \
        else configuration["record_rules"]
    if not isinstance(records, list) or not records or len(records) > 32:
        raise DeclarativeSkillError("invalid_record_rules")
    field_names = None
    for record in records:
        _exact_keys(record, {"line_prefix", "id_suffix", "fields"}, "invalid_record_rule")
        _literal(record["line_prefix"]); _literal(record["id_suffix"])
        if not isinstance(record["fields"], list) or not 2 <= len(record["fields"]) <= 16:
            raise DeclarativeSkillError("invalid_record_fields")
        names = []
        for field in record["fields"]:
            _exact_keys(field, {"name", "left", "right"}, "invalid_record_field")
            name = _literal(field["name"], maximum=80)
            if not name.replace("_", "").isalnum():
                raise DeclarativeSkillError("invalid_field_name")
            names.append(name)
            _literal(field["left"]); _literal(field["right"], empty=True)
        if len(names) != len(set(names)):
            raise DeclarativeSkillError("duplicate_field_name")
        if field_names is None:
            field_names = names
        elif names != field_names:
            raise DeclarativeSkillError("record_rule_field_mismatch")
    names = field_names or []
    scalar_rules = configuration["scalar_rules"]
    if not isinstance(scalar_rules, list) or not scalar_rules or len(scalar_rules) > 16:
        raise DeclarativeSkillError("invalid_scalar_rules")
    scalar_names = []
    for scalar in scalar_rules:
        expected_scalar = {"name", "left", "right"} if configuration["schema"] == CONFIG_SCHEMA \
            else {"name", "alternatives"}
        _exact_keys(scalar, expected_scalar, "invalid_scalar_rule")
        name = _literal(scalar["name"], maximum=80)
        if not name.replace("_", "").isalnum():
            raise DeclarativeSkillError("invalid_scalar_name")
        scalar_names.append(name)
        alternatives = [scalar] if configuration["schema"] == CONFIG_SCHEMA else scalar["alternatives"]
        if not isinstance(alternatives, list) or not alternatives or len(alternatives) > 32:
            raise DeclarativeSkillError("invalid_scalar_alternatives")
        for alternative in alternatives:
            if configuration["schema"] == CONFIG_SCHEMA_V2:
                _exact_keys(alternative, {"left", "right"}, "invalid_scalar_alternative")
            _literal(alternative["left"]); _literal(alternative["right"], empty=True)
    if len(scalar_names) != len(set(scalar_names)):
        raise DeclarativeSkillError("duplicate_scalar_name")
    _validate_algebra(configuration, names, scalar_names)
    return configuration


def _validate_algebra(configuration: dict[str, Any], names: list[str],
                      scalar_names: list[str]) -> None:
    if configuration["variable_domain"] != "binary":
        raise DeclarativeSkillError("unsupported_variable_domain")
    objective = configuration["objective"]
    _exact_keys(objective, {"sense", "coefficient_field", "offset"}, "invalid_objective")
    if objective["sense"] not in {"min", "max"} or objective["coefficient_field"] not in names:
        raise DeclarativeSkillError("invalid_objective_reference")
    if type(objective["offset"]) not in (int, float) or not math.isfinite(objective["offset"]):
        raise DeclarativeSkillError("invalid_objective_offset")
    constraints = configuration["constraints"]
    if not isinstance(constraints, list) or not constraints or len(constraints) > 16:
        raise DeclarativeSkillError("invalid_constraints")
    constraint_ids = []
    for constraint in constraints:
        _exact_keys(constraint, {
            "id", "coefficient_field", "sense", "rhs_scalar",
        }, "invalid_constraint")
        identifier = _literal(constraint["id"], maximum=80)
        constraint_ids.append(identifier)
        if constraint["coefficient_field"] not in names \
                or constraint["rhs_scalar"] not in scalar_names \
                or constraint["sense"] not in {"le", "eq", "ge"}:
            raise DeclarativeSkillError("invalid_constraint_reference")
    if len(constraint_ids) != len(set(constraint_ids)):
        raise DeclarativeSkillError("duplicate_constraint_id")
    for key in ("minimum_records", "maximum_records"):
        if type(configuration[key]) is not int or not 1 <= configuration[key] <= 20_000:
            raise DeclarativeSkillError("invalid_record_limit")
    if configuration["minimum_records"] > configuration["maximum_records"]:
        raise DeclarativeSkillError("invalid_record_limit_order")


def _number_between(text: str, left: str, right: str) -> float:
    folded = text.casefold(); marker = left.casefold()
    starts = [match.start() for match in re.finditer(re.escape(marker), folded)]
    if len(starts) != 1:
        raise DeclarativeSkillError("literal_occurrence_not_unique")
    start = starts[0] + len(left)
    tail = text[start:]
    if right:
        end = tail.casefold().find(right.casefold())
        if end < 0:
            raise DeclarativeSkillError("right_literal_missing")
        raw = tail[:end].strip()
        if tail.casefold().find(right.casefold(), end + len(right)) >= 0:
            raise DeclarativeSkillError("right_literal_not_unique")
    else:
        match = NUMERIC.match(tail.lstrip())
        if match is None:
            raise DeclarativeSkillError("numeric_value_missing")
        raw = match.group(0)
    if not NUMERIC.fullmatch(raw.replace(",", "")):
        raise DeclarativeSkillError("invalid_numeric_value")
    value = float(raw.replace(",", ""))
    if not math.isfinite(value) or abs(value) > 1e12:
        raise DeclarativeSkillError("numeric_value_out_of_range")
    return value


def _typed_number(match: re.Match[str], payload: str, normalizer: str) -> float:
    raw = match.group(0)
    value = float(raw.replace(",", ""))
    if normalizer == "currency_thousands":
        before = payload[:match.start()].rstrip()
        if "," in raw and before.endswith("$"):
            value /= 1000
    if not math.isfinite(value) or abs(value) > 1e12:
        raise DeclarativeSkillError("numeric_value_out_of_range")
    return value


def parse_selection_text(text: str, configuration: Any) -> dict[str, Any]:
    config = validate_configuration(configuration)
    if not isinstance(text, str):
        raise DeclarativeSkillError("text_required")
    if config["schema"] in {CONFIG_SCHEMA_V3, CONFIG_SCHEMA_V4}:
        rule = config["record_rule"]
        records = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            matching = [prefix for prefix in rule["line_prefixes"]
                        if line.casefold().startswith(prefix.casefold())]
            if not matching:
                continue
            if len(matching) != 1:
                raise DeclarativeSkillError("line_prefix_not_unique")
            remainder = line[len(matching[0]):]
            cut = remainder.find(rule["id_suffix"])
            if cut <= 0:
                raise DeclarativeSkillError("record_identifier_missing")
            identifier = remainder[:cut].strip()
            if not identifier or len(identifier) > 200:
                raise DeclarativeSkillError("invalid_record_identifier")
            payload = remainder[cut + len(rule["id_suffix"]):]
            matches = list(NUMERIC.finditer(payload))
            fields = {}
            for field in rule["numeric_fields"]:
                if field["position"] >= len(matches):
                    raise DeclarativeSkillError("numeric_field_missing")
                normalizer = field.get("normalizer", "identity")
                fields[field["name"]] = _typed_number(
                    matches[field["position"]], payload, normalizer,
                )
            records.append({"id": identifier, "fields": fields})
        if not config["minimum_records"] <= len(records) <= config["maximum_records"]:
            raise DeclarativeSkillError("record_count_out_of_bounds")
        if len({record["id"] for record in records}) != len(records):
            raise DeclarativeSkillError("duplicate_record_identifier")
        scalars = {}
        for scalar in config["scalar_rules"]:
            candidates = []
            for raw_line in text.splitlines():
                folded = raw_line.casefold()
                if not any(phrase.casefold() in folded for phrase in scalar["required_any"]) \
                        or any(phrase.casefold() in folded for phrase in scalar["forbidden_any"]):
                    continue
                values = [float(value.replace(",", "")) for value in NUMERIC.findall(raw_line)]
                if scalar["numeric_position"] < len(values):
                    candidates.append(values[scalar["numeric_position"]])
            if len(candidates) != 1:
                raise DeclarativeSkillError("scalar_line_not_unique")
            scalars[scalar["name"]] = candidates[0]
        return {"records": records, "scalars": scalars}
    rules = [config["record_rule"]] if config["schema"] == CONFIG_SCHEMA else config["record_rules"]
    candidates = []
    for record_rule in rules:
        records = []
        try:
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line.casefold().startswith(record_rule["line_prefix"].casefold()):
                    continue
                remainder = line[len(record_rule["line_prefix"]):]
                cut = remainder.find(record_rule["id_suffix"])
                if cut <= 0:
                    raise DeclarativeSkillError("record_identifier_missing")
                identifier = remainder[:cut].strip()
                if not identifier or len(identifier) > 200:
                    raise DeclarativeSkillError("invalid_record_identifier")
                fields = {
                    field["name"]: _number_between(line, field["left"], field["right"])
                    for field in record_rule["fields"]
                }
                records.append({"id": identifier, "fields": fields})
            if config["minimum_records"] <= len(records) <= config["maximum_records"]:
                candidates.append(records)
        except DeclarativeSkillError:
            continue
    if len(candidates) != 1:
        raise DeclarativeSkillError("record_rule_not_unique")
    records = candidates[0]
    if len({record["id"] for record in records}) != len(records):
        raise DeclarativeSkillError("duplicate_record_identifier")
    scalars = {}
    for scalar in config["scalar_rules"]:
        alternatives = [scalar] if config["schema"] == CONFIG_SCHEMA else scalar["alternatives"]
        values = []
        for alternative in alternatives:
            try:
                values.append(_number_between(text, alternative["left"], alternative["right"]))
            except DeclarativeSkillError:
                continue
        if len(values) != 1:
            raise DeclarativeSkillError("scalar_rule_not_unique")
        scalars[scalar["name"]] = values[0]
    return {"records": records, "scalars": scalars}


def compile_selection_model(text: str, configuration: Any) -> dict[str, Any]:
    config = validate_configuration(configuration)
    parsed = parse_selection_text(text, config)
    variables = []
    objective = {}
    for index, record in enumerate(parsed["records"]):
        variable = f"select_{index:05d}"
        variables.append({
            "id": variable,
            "meaning": "select record " + record["id"],
            "unit": "binary",
            "domain": "binary",
            "lower": 0,
            "upper": 1,
        })
        objective[variable] = record["fields"][config["objective"]["coefficient_field"]]
    constraints = []
    for rule in config["constraints"]:
        constraints.append({
            "id": rule["id"],
            "coefficients": {
                f"select_{index:05d}": record["fields"][rule["coefficient_field"]]
                for index, record in enumerate(parsed["records"])
            },
            "sense": rule["sense"],
            "rhs": parsed["scalars"][rule["rhs_scalar"]],
        })
    return validate_model({
        "schema": "milp-v1",
        "variables": variables,
        "constraints": constraints,
        "objective": {
            "coefficients": objective,
            "sense": config["objective"]["sense"],
            "unit": "objective units",
            "offset": config["objective"]["offset"],
        },
    })


def solve_declarative_selection(public_problem: Any, limits: Any,
                                configuration: Any) -> dict[str, Any]:
    public = validate_public_input(public_problem)
    config = validate_configuration(configuration)
    if len(public["text"].encode()) > limits["max_input_bytes"]:
        raise DeclarativeSkillError("input_limit")
    model = compile_selection_model(public["text"], config)
    if len(model["variables"]) > limits["max_variables"] \
            or len(model["constraints"]) > limits["max_constraints"]:
        raise DeclarativeSkillError("model_limit")
    result = execute(
        {"op": "solve", "model": model},
        wall_seconds=limits["wall_seconds"],
        limits={
            "solve_seconds": min(20, max(1, limits["wall_seconds"] - 2)),
            "total_seconds": min(110, limits["wall_seconds"]),
            "node_limit": 100_000,
            "max_queries": 1,
        },
    )
    return {
        "status": result.get("status", "unknown"),
        "objective": result.get("objective"),
        "certificate": "trusted_declarative_milp",
        "compiler_version": VERSION,
    }


__all__ = [
    "CONFIG_SCHEMA", "CONFIG_SCHEMA_V2", "CONFIG_SCHEMA_V3", "DeclarativeSkillError", "VERSION",
    "compile_selection_model",
    "parse_selection_text", "solve_declarative_selection", "validate_configuration",
]
