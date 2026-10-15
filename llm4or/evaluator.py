"""Post-inference scoring. Never imported by the inference runner or teacher."""
import math

from .schema import digest, interface, model
from .solver import execute


def evaluate(candidate, reference, solver=execute):
    candidate, reference = model(candidate), model(reference)
    result = {"reference_hash": digest(reference), "candidate_hash": digest(candidate),
              "objective_match_proxy": None, "formulation_check": "unknown"}
    c = solver({"op": "solve", "model": candidate})
    r = solver({"op": "solve", "model": reference})
    result["candidate_status"], result["reference_status"] = c["status"], r["status"]
    if c["status"] == r["status"] == "optimal" and candidate["objective"]["unit"] == reference["objective"]["unit"]:
        result["objective_match_proxy"] = math.isclose(c["objective"], r["objective"], rel_tol=1e-6, abs_tol=1e-6)
    comparison = solver({"op": "compare", "left": candidate, "right": reference})
    result["comparison"] = comparison
    if comparison["status"] != "compared":
        result["formulation_check"] = "unsupported"
        return result
    statuses = [comparison[k]["status"] for k in ("left_to_right", "right_to_left")]
    if "witness" in statuses or comparison["preference"]["status"] == "strict_reversal":
        result["formulation_check"] = "different"
    elif all(s == "contained_within_tolerance" for s in statuses):
        # Sufficient, conservative objective check: no unsupported equivalence claim
        # for affine objectives on a lower-dimensional feasible set.
        if candidate["objective"] == reference["objective"] and interface(candidate) == interface(reference):
            result["formulation_check"] = "same_within_tolerance_exact_objective"
        else:
            result["formulation_check"] = "same_feasible_set_objective_unresolved"
    result["scope"] = "relative_to_audited_reference_not_certified_natural_language_truth"
    return result
