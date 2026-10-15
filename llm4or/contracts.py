"""Machine-readable output contracts; semantic cross-field checks stay in schema.py.

Schemas describe the RESPONSE, never a request envelope to copy. They are used
locally and in prompts; provider-side strict JSON Schema support is not assumed.
"""
from copy import deepcopy
from jsonschema import Draft202012Validator

from .schema import Invalid, model

NUMBER = {"type": "number", "minimum": -1e12, "maximum": 1e12}
ID = {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*$", "maxLength": 64}
TEXT = {"type": "string", "minLength": 1, "maxLength": 500}
COEFFICIENTS = {"type": "object", "minProperties": 1, "maxProperties": 16,
                "propertyNames": ID, "additionalProperties": NUMBER}


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


ROW_SCHEMA = obj({"id": ID, "coefficients": COEFFICIENTS,
                  "sense": {"enum": ["le", "ge", "eq"]}, "rhs": NUMBER})
LP_SCHEMA = obj({
    "schema": {"const": "lp-v1"},
    "variables": {"type": "array", "minItems": 1, "maxItems": 16,
                  "items": obj({"id": ID, "meaning": TEXT, "unit": TEXT,
                                "domain": {"const": "continuous"},
                                "lower": {"anyOf": [NUMBER, {"type": "null"}]},
                                "upper": {"anyOf": [NUMBER, {"type": "null"}]}})},
    "constraints": {"type": "array", "maxItems": 64, "items": ROW_SCHEMA},
    "objective": obj({"coefficients": COEFFICIENTS, "sense": {"enum": ["min", "max"]},
                      "unit": TEXT, "offset": NUMBER})})
LP_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"


def claim(kind, properties):
    return obj({"id": ID, "model": {"enum": ["initial", "teacher"]},
                "kind": {"const": kind}, **properties})


CLAIM_SCHEMA = {"oneOf": [
    claim("declared_bound", {"variable": ID, "side": {"enum": ["lower", "upper"]},
                             "expected": {"anyOf": [NUMBER, {"type": "null"}]}}),
    claim("row_coefficient", {"row": ID, "variable": ID, "expected": NUMBER}),
    claim("row_rhs", {"row": ID, "expected": NUMBER}),
    claim("row_sense", {"row": ID, "expected": {"enum": ["le", "ge", "eq"]}}),
    claim("entails", {"coefficients": COEFFICIENTS, "sense": {"enum": ["le", "ge"]},
                      "rhs": NUMBER, "expected": {"type": "boolean"}}),
]}
TEACHER_SCHEMA = obj({
    "schema": {"const": "teacher-v2"},
    "status": {"enum": ["repair", "no_witness", "unresolved"]},
    "model_hashes": obj({"initial": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                         "teacher": {"type": "string", "pattern": "^[a-f0-9]{64}$"}}),
    "quote": {"type": "string", "minLength": 1, "maxLength": 20000},
    "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
    "interpretation": {"type": "string", "minLength": 1, "maxLength": 2000},
    "claims": {"type": "array", "maxItems": 8, "items": CLAIM_SCHEMA},
    "target_rows": {"type": "array", "maxItems": 4, "uniqueItems": True, "items": ID},
    "positive_examples": {"type": "array", "maxItems": 8, "items": COEFFICIENTS},
})
TEACHER_SCHEMA["$schema"] = LP_SCHEMA["$schema"]


def validate(value, contract):
    errors = list(Draft202012Validator(contract).iter_errors(value))
    if errors:
        # Do not echo untrusted response contents into generic error messages.
        path = "/".join(str(p) for p in errors[0].absolute_path) or "root"
        raise Invalid("output_contract_violation:" + path + ":" + errors[0].validator)
    if contract is LP_SCHEMA:
        return model(value)
    return deepcopy(value)
