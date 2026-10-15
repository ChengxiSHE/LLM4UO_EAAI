"""Label-free benchmark input projections; not a solver or a live runner.

Only explicit source fields are copied. Reference values, structured modeling
annotations and source code never enter the default description/parameter view.
The optional scaffold profile is a different, explicitly named information regime.
"""
import hashlib
import json
import math

from .schema import Invalid, canonical, identifier, keys, string

MAX_INPUT_BYTES = 1_000_000
BASE_PROFILE = "description_parameters_v1"
SCAFFOLD_PROFILE = "description_parameters_scaffold_v1"


def _detach(value):
    try:
        encoded = canonical(value)
    except (ValueError, TypeError, RecursionError) as exc:
        raise Invalid("invalid JSON input") from exc
    if len(encoded.encode()) > MAX_INPUT_BYTES:
        raise Invalid("input size limit")
    return json.loads(encoded)


def _data(value, depth=0):
    if depth > 12:
        raise Invalid("parameter nesting limit")
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, list):
        for child in value:
            _data(child, depth + 1)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for child in value.values():
            _data(child, depth + 1)
        return
    raise Invalid("unsupported parameter value")


def validate_public_input(payload):
    # Validate a detached bounded JSON object, including all nested key sets.
    payload = _detach(payload)
    if not isinstance(payload, dict):
        raise Invalid("input object required")
    profile = payload.get("profile")
    expected = {"id", "profile", "text", "parameters", "instances"}
    if profile == SCAFFOLD_PROFILE:
        expected.add("scaffold")
    elif profile != BASE_PROFILE:
        raise Invalid("unknown input information profile")
    keys(payload, expected)
    identifier(payload["id"])
    string(payload["text"], MAX_INPUT_BYTES)
    if not isinstance(payload["parameters"], list) or len(payload["parameters"]) > 1000:
        raise Invalid("parameter definitions")
    symbols = []
    for parameter in payload["parameters"]:
        keys(parameter, {"symbol", "definition", "shape"})
        identifier(parameter["symbol"])
        symbols.append(parameter["symbol"])
        string(parameter["definition"], 10000)
        dims = parameter["shape"]
        if not isinstance(dims, list) or len(dims) > 10:
            raise Invalid("parameter shape")
        if any(not ((type(d) is int and d >= 0) or (isinstance(d, str) and d.strip())) for d in dims):
            raise Invalid("parameter dimension")
    if len(symbols) != len(set(symbols)):
        raise Invalid("duplicate parameter symbol")
    if not isinstance(payload["instances"], list) or len(payload["instances"]) > 1000:
        raise Invalid("instances")
    instance_ids = []
    for instance in payload["instances"]:
        keys(instance, {"id", "input"})
        identifier(instance["id"])
        instance_ids.append(instance["id"])
        keys(instance["input"], symbols)
        _data(instance["input"])
    if len(instance_ids) != len(set(instance_ids)):
        raise Invalid("duplicate instance ID")
    if profile == SCAFFOLD_PROFILE:
        string(payload["scaffold"], 100000)
    return payload


def flat_input(problem_id, row, question_field):
    if question_field not in {"en_question", "question", "description", "document", "Question"}:
        raise Invalid("unapproved question field")
    return validate_public_input({"id": problem_id, "profile": BASE_PROFILE,
                                  "text": row[question_field], "parameters": [], "instances": []})


def complexor_input(problem_id, specification, samples, *, profile=BASE_PROFILE, scaffold=None):
    if not isinstance(samples, list) or not samples:
        raise Invalid("ComplexOR requires nonempty parameter instances")
    if not isinstance(specification, dict) or not isinstance(specification.get("parameters"), list):
        raise Invalid("ComplexOR parameter specification required")
    if any(not isinstance(s, dict) or "input" not in s for s in samples):
        raise Invalid("ComplexOR sample input required")
    # Deliberately exclude background/constraints/objective and all unlisted keys.
    parameters = [{key: p[key] for key in ("symbol", "definition", "shape")}
                  for p in specification["parameters"]]
    payload = {"id": problem_id, "profile": profile, "text": specification["description"],
               "parameters": parameters,
               "instances": [{"id": f"instance_{i:04d}", "input": sample["input"]}
                             for i, sample in enumerate(samples)]}
    if profile == SCAFFOLD_PROFILE:
        payload["scaffold"] = scaffold  # inert text only, never executed by this adapter
    elif scaffold is not None:
        raise Invalid("scaffold forbidden in description/parameter profile")
    return validate_public_input(payload)


def array_shape(value):
    if not isinstance(value, list):
        return []
    shapes = [array_shape(v) for v in value]
    if not shapes:
        return [0]
    return [len(value)] + (shapes[0] if all(s == shapes[0] for s in shapes) else ["ragged"])


def input_shape_issues(payload):
    """Detect contradictions without correcting data or dropping source problems.

    Shape expressions are never eval'd. Unresolvable shapes remain unknown.
    This is an input-consistency audit, not a mathematical eligibility classifier.
    """
    payload = validate_public_input(payload)
    issues = []
    for instance in payload["instances"]:
        inputs = instance["input"]
        for parameter in payload["parameters"]:
            resolved = [inputs.get(d, d) if isinstance(d, str) else d for d in parameter["shape"]]
            actual = array_shape(inputs[parameter["symbol"]])
            if not all(type(d) is int and d >= 0 for d in resolved):
                code = "unresolved_shape_expression"
            elif actual != resolved:
                code = "declared_actual_shape_mismatch"
            else:
                continue
            issues.append({"instance_id": instance["id"], "parameter": parameter["symbol"],
                           "code": code, "declared_shape": parameter["shape"],
                           "resolved_shape": resolved, "actual_shape": actual})
    return issues


def payload_sha256(payload):
    return hashlib.sha256(canonical(validate_public_input(payload)).encode()).hexdigest()
