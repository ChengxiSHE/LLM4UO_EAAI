"""Post-inference MILP evaluation. Never imported by a teacher or live runner.

Numerical objective/status matching is a proxy, distinct from formulation
comparison. Unknown, unsupported and ambiguous cases stay in the denominator.
"""
import math
import re

from .schema import Invalid, digest, identifier, keys, number, string
from .milp_schema import model
from .milp_solver import execute, check_point

REL_TOL = 1e-6
ABS_TOL = 1e-6
DEFINITIVE = {"optimal", "infeasible", "unbounded"}


def _base(input_status):
    if not isinstance(input_status, str) or input_status not in {"ready", "unresolved_input_semantics"}:
        raise Invalid("unknown input audit status")
    return {"input_status": input_status, "benchmark_success": None,
            "objective_match_proxy": None, "status_match_proxy": None,
            "formulation_check": "not_checked", "denominator_included": True,
            "scope": "relative_to_reference_not_certified_natural_language_truth"}


def _grade(candidate, reference):
    cs, rs = candidate["status"], reference["status"]
    out = {"benchmark_success": None, "objective_match_proxy": None, "status_match_proxy": None}
    if rs not in DEFINITIVE:
        return {**out, "grade_reason": "reference_not_certified"}
    if cs == "invalid_input":
        return {**out, "benchmark_success": False, "grade_reason": "invalid_candidate"}
    if cs not in DEFINITIVE:
        return {**out, "grade_reason": "candidate_not_certified"}
    out["status_match_proxy"] = cs == rs
    if cs != rs:
        return {**out, "benchmark_success": False, "grade_reason": "status_mismatch"}
    if rs in {"infeasible", "unbounded"}:
        return {**out, "benchmark_success": True, "grade_reason": "matching_status_only_not_formulation_proof"}
    if (candidate["objective_sense"], candidate["objective_unit"]) != (reference["objective_sense"], reference["objective_unit"]):
        return {**out, "grade_reason": "objective_interface_unsupported"}
    cv, rv = candidate.get("objective"), reference.get("objective")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (cv, rv)):
        return {**out, "grade_reason": "missing_finite_certified_objective"}
    match = math.isclose(cv, rv, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return {**out, "benchmark_success": match, "objective_match_proxy": match,
            "grade_reason": "objective_match" if match else "objective_mismatch",
            "objective_tolerances": {"relative": REL_TOL, "absolute": ABS_TOL}}


def _same_objective(left, right):
    a, b = left["objective"], right["objective"]
    return (all(a[k] == b[k] for k in ("sense", "unit", "offset"))
            and all(a["coefficients"].get(k, 0) == b["coefficients"].get(k, 0)
                    for k in a["coefficients"].keys() | b["coefficients"].keys()))


def evaluate(candidate, reference, *, solver=execute, input_status="ready", compare_formulation=True):
    out = _base(input_status)
    if input_status != "ready":
        return {**out, "grade_reason": "input_ambiguity", "candidate_status": "not_run", "reference_status": "not_run"}
    try:
        reference = model(reference)
    except Invalid:
        return {**out, "grade_reason": "invalid_reference", "reference_status": "invalid_input", "candidate_status": "not_run"}
    out["reference_hash"] = digest(reference)
    r = solver({"op": "solve", "model": reference})
    try:
        candidate = model(candidate)
        out["candidate_hash"] = digest(candidate)
        c = solver({"op": "solve", "model": candidate})
    except Invalid:
        c = {"status": "invalid_input"}
        candidate = None
    out.update(candidate_status=c["status"], reference_status=r["status"], candidate_solve=c, reference_solve=r)
    out.update(_grade(c, r))
    if candidate is not None and c.get("point") is not None:
        # Cross-feasibility is diagnostic; a single feasible point never proves
        # equality of the feasible sets or correct natural-language semantics.
        out["candidate_point_in_reference"] = check_point(reference, c["point"])
    if candidate is None or not compare_formulation:
        return out
    comparison = solver({"op": "compare", "left": candidate, "right": reference})
    out["comparison"] = comparison
    if comparison["status"] != "compared":
        out["formulation_check"] = "unsupported" if comparison["status"] == "unsupported" else "unknown"
        return out
    statuses = [comparison[k]["status"] for k in ("left_to_right", "right_to_left")]
    if "witness" in statuses or comparison["preference"]["status"] == "strict_reversal":
        out["formulation_check"] = "different"
    elif all(s == "contained_within_tolerance" for s in statuses):
        out["formulation_check"] = ("same_within_tolerance_exact_objective" if _same_objective(candidate, reference)
                                    else "same_feasible_set_objective_unresolved")
    else:
        out["formulation_check"] = "unknown"
    return out


def validate_reference_label(reference):
    keys(reference, {"schema", "status", "objective", "objective_sense", "objective_unit", "provenance"})
    if (reference["schema"] != "optimization-reference-v1" or not isinstance(reference["status"], str)
            or reference["status"] not in DEFINITIVE):
        raise Invalid("unsupported reference schema/status")
    if not isinstance(reference["objective_sense"], str) or reference["objective_sense"] not in {"min", "max"}:
        raise Invalid("reference objective direction")
    string(reference["objective_unit"])
    if reference["status"] == "optimal":
        number(reference["objective"])
    elif reference["objective"] is not None:
        raise Invalid("non-optimal reference must not contain an objective")
    p = reference["provenance"]
    keys(p, {"source_sha256", "review_status", "review_note"})
    if not isinstance(p["source_sha256"], str) or not re.fullmatch("[a-f0-9]{64}", p["source_sha256"]):
        raise Invalid("reference provenance hash")
    if not isinstance(p["review_status"], str) or p["review_status"] not in {"audited", "unreviewed"}:
        raise Invalid("reference audit status")
    string(p["review_note"], 4000)
    return reference


def evaluate_against_label(candidate, reference_label, *, solver=execute, input_status="ready"):
    """For datasets with scalar/status references, after an explicit label audit.

    No parser guesses numbers from free text, translates arbitrary status strings,
    or treats the upstream existence of a label as an independent audit.
    """
    out = _base(input_status)
    if input_status != "ready":
        return {**out, "grade_reason": "input_ambiguity", "candidate_status": "not_run"}
    try:
        label = validate_reference_label(reference_label)
    except Invalid:
        return {**out, "grade_reason": "invalid_reference_label", "candidate_status": "not_run"}
    out["reference_hash"] = digest(label)
    if label["provenance"]["review_status"] != "audited":
        return {**out, "grade_reason": "reference_not_audited", "candidate_status": "not_run"}
    try:
        candidate = model(candidate)
        out["candidate_hash"] = digest(candidate)
        c = solver({"op": "solve", "model": candidate})
    except Invalid:
        c = {"status": "invalid_input"}
    return {**out, **_grade(c, label), "candidate_status": c["status"], "reference_status": label["status"],
            "candidate_solve": c, "formulation_check": "unavailable_scalar_or_status_reference"}


def summarize(results):
    total = len(results)
    if any(r.get("denominator_included") is not True for r in results):
        raise Invalid("all planned problem outcomes must stay in the denominator")
    correct = sum(r["benchmark_success"] is True for r in results)
    incorrect = sum(r["benchmark_success"] is False for r in results)
    unknown = total - correct - incorrect
    return {"total_planned": total, "correct_proxy": correct, "incorrect_proxy": incorrect, "unresolved": unknown,
            "success_rate_full_denominator": correct / total if total else None,
            "determinate_fraction": (correct + incorrect) / total if total else None,
            "scope": "protocol_proxy_not_semantic_correctness"}


def evaluate_batch(planned, candidates, references, *, solver=execute):
    """One retained outcome per predeclared problem, including missing outputs.

    planned comes from the separately audited evaluation manifest, with each
    entry containing exactly id and input_status. Reference packages contain
    kind ('model' or 'label') and value and stay exclusively in this evaluator.
    This function neither chooses a split nor certifies its independence.
    """
    if not isinstance(planned, list) or not isinstance(candidates, dict) or not isinstance(references, dict):
        raise Invalid("batch objects required")
    ids = []
    for entry in planned:
        keys(entry, {"id", "input_status"}); identifier(entry["id"])
        _base(entry["input_status"]); ids.append(entry["id"])
    if len(ids) != len(set(ids)):
        raise Invalid("duplicate planned problem")
    if not set(candidates) <= set(ids) or not set(references) <= set(ids):
        raise Invalid("unplanned candidate/reference")
    results = []
    for entry in planned:
        pid, input_status = entry["id"], entry["input_status"]
        if input_status != "ready":
            result = {**_base(input_status), "grade_reason": "input_ambiguity", "candidate_status": "not_run"}
        elif pid not in references:
            result = {**_base(input_status), "grade_reason": "missing_reference", "candidate_status": "not_run"}
        else:
            package = references[pid]
            keys(package, {"kind", "value"})
            if package["kind"] == "model":
                result = evaluate(candidates.get(pid), package["value"], solver=solver)
            elif package["kind"] == "label":
                result = evaluate_against_label(candidates.get(pid), package["value"], solver=solver)
            else:
                raise Invalid("unknown reference kind")
        results.append({"problem_id": pid, **result})
    return {"results": results, "summary": summarize(results),
            "split_independence_certified_by_this_function": False}
