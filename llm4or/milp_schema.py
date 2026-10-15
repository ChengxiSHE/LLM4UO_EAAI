"""Versioned sparse linear models with explicit continuous/integer/binary domains.

lp-v1 is deliberately unchanged. No expression language, inferred integrality,
implicit nonnegativity, or implicit conversion from an older experiment schema.
"""
import json

from .schema import Invalid, canonical, identifier, keys, number, string

MAX_BYTES = 4_000_000
MAX_OPERATION_BYTES = 9_000_000
MAX_VARS = 2000
MAX_ROWS = 10000
MAX_NNZ = 100000
MIN_NONZERO_COEFFICIENT = 1e-8
DOMAINS = {"continuous", "integer", "binary"}


def loads(text, max_bytes=MAX_BYTES):
    if not isinstance(text, str) or len(text.encode()) > max_bytes:
        raise Invalid("JSON size limit")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Invalid("duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise Invalid("nonfinite JSON")
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError) as exc:
        raise Invalid("invalid JSON") from exc


def model(value):
    try:
        value = loads(value if isinstance(value, str) else canonical(value))
    except (ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise Invalid("invalid model JSON") from exc
    keys(value, {"schema", "variables", "constraints", "objective"})
    if value["schema"] != "milp-v1":
        raise Invalid("expected milp-v1; no implicit schema migration")
    variables = value["variables"]
    if not isinstance(variables, list) or not 1 <= len(variables) <= MAX_VARS:
        raise Invalid("variable limit")
    ids = []
    for var in variables:
        keys(var, {"id", "meaning", "unit", "domain", "lower", "upper"})
        ids.append(identifier(var["id"]))
        string(var["meaning"]); string(var["unit"])
        if not isinstance(var["domain"], str) or var["domain"] not in DOMAINS:
            raise Invalid("unsupported variable domain")
        for side in ("lower", "upper"):
            if var[side] is not None:
                number(var[side])
        if var["lower"] is not None and var["upper"] is not None and var["lower"] > var["upper"]:
            raise Invalid("contradictory explicit bounds")
    if len(ids) != len(set(ids)):
        raise Invalid("duplicate variable ID")
    id_set = set(ids)
    nnz = 0
    def coefficients(coefs):
        nonlocal nnz
        if not isinstance(coefs, dict) or not set(coefs) <= id_set:
            raise Invalid("unknown coefficient variable")
        for val in coefs.values():
            number(val)
            if val and abs(val) < MIN_NONZERO_COEFFICIENT:
                raise Invalid("coefficient below supported numerical range")
        nnz += len(coefs)
        if nnz > MAX_NNZ:
            raise Invalid("coefficient count limit")
    rows = value["constraints"]
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise Invalid("constraint limit")
    row_ids = []
    for row in rows:
        keys(row, {"id", "coefficients", "sense", "rhs"})
        row_ids.append(identifier(row["id"]))
        coefficients(row["coefficients"])
        if not isinstance(row["sense"], str) or row["sense"] not in {"le", "ge", "eq"}:
            raise Invalid("constraint sense")
        number(row["rhs"])
    if len(row_ids) != len(set(row_ids)):
        raise Invalid("duplicate constraint ID")
    obj = value["objective"]
    keys(obj, {"coefficients", "sense", "unit", "offset"})
    coefficients(obj["coefficients"])
    number(obj["offset"]); string(obj["unit"])
    if not isinstance(obj["sense"], str) or obj["sense"] not in {"min", "max"}:
        raise Invalid("objective sense")
    return value


def effective_bounds(var):
    lower, upper = var["lower"], var["upper"]
    if var["domain"] == "binary":
        lower = max(0, lower) if lower is not None else 0
        upper = min(1, upper) if upper is not None else 1
    return lower, upper


def business_interface(value):
    # Domains are checked mathematically, not hidden as an interface mismatch.
    return sorted(({k: v[k] for k in ("id", "meaning", "unit")} for v in value["variables"]), key=lambda x: x["id"])
