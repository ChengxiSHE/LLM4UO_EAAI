"""Repair checks are relative to evidence, not a natural-language truth oracle."""
import math

from .schema import Invalid, digest, keys, model, number, string
from .solver import TOL, execute, matrices


def teacher_packet(raw, problem, initial, teacher, evidence):
    keys(raw, {"status", "quote", "start", "end", "explanation", "target_rows", "positive_examples"})
    if raw["status"] not in {"repair", "unresolved"}:
        raise Invalid("teacher status")
    string(raw["explanation"], 2000)
    if type(raw["start"]) is not int or type(raw["end"]) is not int:
        raise Invalid("quote offsets")
    start, end = raw["start"], raw["end"]
    if not 0 <= start < end <= len(problem["text"]) or problem["text"][start:end] != raw["quote"]:
        raise Invalid("quote provenance mismatch")
    rows = raw["target_rows"]
    examples = raw["positive_examples"]
    if not isinstance(rows, list) or len(rows) > 4 or len(set(rows)) != len(rows):
        raise Invalid("repair scope too broad")
    if not isinstance(examples, list) or len(examples) > 8:
        raise Invalid("too many examples")
    known = {r["id"] for r in teacher["constraints"]}
    if any(not isinstance(r, str) or r not in known for r in rows):
        raise Invalid("unknown teacher row")
    if raw["status"] == "repair":
        # S0/S1 v1: only a witnessed omission/restriction on explicit rows.
        # Bound/objective edits and evidence-free repairs are not permitted.
        witnessed = {evidence.get(k, {}).get("violated_row", "").split(":")[0]
                     for k in ("left_to_right", "right_to_left")
                     if evidence.get(k, {}).get("status") == "witness"}
        if not rows or not set(rows) <= witnessed:
            raise Invalid("no executable witness supporting target scope")
        if not examples:
            raise Invalid("repair requires at least one protected example")
    order, a, b, _ = matrices(teacher)
    for point in examples:
        keys(point, order)
        x = [number(point[v]) for v in order]
        if any(sum(c * z for c, z in zip(row, x)) - bound > TOL for row, bound in zip(a, b)):
            raise Invalid("positive example contradicts teacher model")
    return {**raw, "initial_hash": digest(initial), "teacher_hash": digest(teacher),
            "evidence_hash": digest(evidence), "provenance_status": "exact_quote_not_entailment"}


def repair_gate(initial, proposal, teacher, packet, solver=execute):
    def reject(reason, **extra):
        return {"status": "rejected", "reason": reason, "retained_model": initial, **extra}

    if packet["status"] != "repair":
        return reject("teacher_unresolved")
    if digest(initial) != packet["initial_hash"] or digest(teacher) != packet["teacher_hash"]:
        return reject("stale_evidence")
    try:
        proposal = model(proposal)
    except (ValueError, TypeError):
        return reject("invalid_proposal")
    if digest(proposal) == digest(initial):
        return reject("no_change")
    if proposal["variables"] != initial["variables"] or proposal["objective"] != initial["objective"]:
        return reject("immutable_interface_bounds_or_objective")
    old = {r["id"]: r for r in initial["constraints"]}
    new = {r["id"]: r for r in proposal["constraints"]}
    changed = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
    if not set(changed) <= set(packet["target_rows"]):
        return reject("write_scope_violation", changed_rows=changed)
    # Untargeted constraints are byte-equivalent after JSON normalization.
    order, a, b, _ = matrices(proposal)
    for point in packet["positive_examples"]:
        x = [point[v] for v in order]
        if any(sum(c * z for c, z in zip(row, x)) - bound > TOL for row, bound in zip(a, b)):
            return reject("protected_example_regression", point=point)
    state = solver({"op": "solve", "model": proposal})
    if state["status"] != "optimal":
        return reject("proposal_solver_not_optimal", solve=state)
    # Require selected teacher clauses, without forcing full teacher agreement.
    target = model({**teacher, "constraints": [r for r in teacher["constraints"] if r["id"] in packet["target_rows"]]})
    checks = solver({"op": "compare", "left": proposal, "right": target})
    if checks.get("left_to_right", {}).get("status") != "contained_within_tolerance":
        return reject("target_clause_not_certified", check=checks)
    return {"status": "accepted_relative_to_evidence", "retained_model": proposal,
            "changed_rows": changed, "check": checks,
            "warning": "teacher interpretation and positive examples are not independently certified truth"}


def paired_evolution_gate(pairs, generation, delta=0.05):
    """Pure statistical test only. Caller must enforce fresh families and frozen candidates."""
    if type(generation) is not int or generation < 1 or not 0 < delta < 1 or not pairs:
        raise ValueError("invalid gate inputs")
    if any(len(p) != 2 or any(type(x) is not bool for x in p) for p in pairs):
        raise ValueError("one incumbent/candidate binary pair per independent family")
    plus = sum(not old and new for old, new in pairs)
    minus = sum(old and not new for old, new in pairs)
    m = plus + minus
    pvalue = sum(math.comb(m, j) for j in range(plus, m + 1)) / 2**m if m else 1.0
    threshold = delta / (generation * (generation + 1))
    return {"n_plus": plus, "n_minus": minus, "pvalue": pvalue,
            "threshold": threshold, "accept": pvalue <= threshold,
            "assumptions_enforced_by_this_function": False}
