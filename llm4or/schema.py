"""Strict, bounded JSON interface. Coefficients are keyed by business variable ID."""
import hashlib
import json
import math
import re

MAX_BYTES = 100_000
MAX_VARS = 16
MAX_ROWS = 64


class Invalid(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def loads(text):
    if not isinstance(text, str) or len(text.encode()) > MAX_BYTES:
        raise Invalid("JSON exceeds size limit")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Invalid("duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise Invalid("nonfinite JSON constant")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError) as exc:
        raise Invalid("invalid JSON") from exc


def keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise Invalid("unexpected or missing fields")


def number(value):
    if type(value) not in (float, int) or abs(value) > 1e12 or not math.isfinite(value):
        raise Invalid("finite bounded number required")
    return value


def string(value, maximum=500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise Invalid("bounded nonempty text required")
    return value


def identifier(value):
    string(value, 64)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value):
        raise Invalid("invalid identifier")
    return value


def model(value):
    """Validate and detach a model; no coercion, expression parsing or code execution."""
    if isinstance(value, str):
        value = loads(value)
    if len(canonical(value).encode()) > MAX_BYTES:
        raise Invalid("model exceeds size limit")
    keys(value, {"schema", "variables", "constraints", "objective"})
    if value["schema"] != "lp-v1":
        raise Invalid("unsupported schema")
    vs = value["variables"]
    if not isinstance(vs, list) or not 1 <= len(vs) <= MAX_VARS:
        raise Invalid("variable count")
    ids = []
    for var in vs:
        keys(var, {"id", "meaning", "unit", "domain", "lower", "upper"})
        ids.append(identifier(var["id"]))
        string(var["meaning"])
        string(var["unit"])
        if var["domain"] != "continuous":
            raise Invalid("unsupported domain: only continuous LP")
        for side in ("lower", "upper"):
            if var[side] is not None:
                number(var[side])
        if var["lower"] is not None and var["upper"] is not None and var["lower"] > var["upper"]:
            raise Invalid("contradictory variable bounds")
    if len(set(ids)) != len(ids):
        raise Invalid("duplicate variable ID")

    def coefficients(coefs):
        keys(coefs, ids)  # Every variable is explicit, including zero coefficients.
        for v in coefs.values():
            number(v)

    rows = value["constraints"]
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise Invalid("constraint count")
    row_ids = []
    for row in rows:
        keys(row, {"id", "coefficients", "sense", "rhs"})
        row_ids.append(identifier(row["id"]))
        coefficients(row["coefficients"])
        if row["sense"] not in {"le", "ge", "eq"}:
            raise Invalid("constraint sense")
        number(row["rhs"])
    if len(set(row_ids)) != len(row_ids):
        raise Invalid("duplicate constraint ID")
    obj = value["objective"]
    keys(obj, {"coefficients", "sense", "unit", "offset"})
    coefficients(obj["coefficients"])
    number(obj["offset"])
    string(obj["unit"])
    if obj["sense"] not in {"min", "max"}:
        raise Invalid("objective sense")
    return loads(canonical(value))


def interface(value):
    return sorted(({k: v[k] for k in ("id", "meaning", "unit", "domain")}
                   for v in value["variables"]), key=lambda v: v["id"])


def public_problem(problem_id, record, text_field="document"):
    """Deliberately project only text. Never send annotations or reference variables."""
    identifier(problem_id)
    if text_field not in {"document", "question", "description"}:
        raise Invalid("unapproved text field")
    text = string(record[text_field], 20_000)
    return {"id": problem_id, "text": text}


def validate_public(value):
    keys(value, {"id", "text"})
    identifier(value["id"])
    string(value["text"], 20_000)
    return loads(canonical(value))
