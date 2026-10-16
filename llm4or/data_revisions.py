"""Apply narrowly reviewed input-metadata revisions; never edit source values."""
from copy import deepcopy

from .benchmark_inputs import payload_sha256, validate_public_input, BASE_PROFILE
from .schema import Invalid, keys


def revise_parameter_shapes(payload, review):
    payload = validate_public_input(payload)
    keys(review, {"problem_id", "before_sha256", "status", "edits"})
    if (review["status"] != "reviewed_metadata_only" or review["problem_id"] != payload["id"]
            or review["before_sha256"] != payload_sha256(payload) or payload["profile"] != BASE_PROFILE):
        raise Invalid("revision provenance/profile mismatch")
    if not isinstance(review["edits"], list) or not review["edits"]:
        raise Invalid("empty revision")
    revised = deepcopy(payload)
    parameters = {p["symbol"]: p for p in revised["parameters"]}
    touched = set()
    for edit in review["edits"]:
        keys(edit, {"parameter", "before", "after", "rationale", "evidence"})
        symbol = edit["parameter"]
        if symbol not in parameters or symbol in touched or not edit["rationale"] or not edit["evidence"]:
            raise Invalid("invalid/duplicate parameter revision")
        if parameters[symbol]["shape"] != edit["before"] or edit["before"] == edit["after"]:
            raise Invalid("revision precondition failed")
        parameters[symbol]["shape"] = deepcopy(edit["after"])
        touched.add(symbol)
    # No general JSON patch, expression evaluation, or value/answer modification.
    return validate_public_input(revised)
