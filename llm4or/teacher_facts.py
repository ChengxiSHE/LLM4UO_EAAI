"""Verify formal model facts independently of the teacher's prose interpretation."""
from copy import deepcopy
import time

from .contracts import TEACHER_SCHEMA, validate
from .gates import teacher_packet
from .schema import Invalid, digest, keys, model
from .solver import execute


def verify_claims(claims, initial, teacher, solver=execute, wall_seconds=60):
    models = {"initial": model(initial), "teacher": model(teacher)}
    reports = []
    cache = {}
    started = time.monotonic()
    if len(claims) > 8 or len({c["id"] for c in claims}) != len(claims):
        raise Invalid("claim_count_or_duplicate_ID")
    for claim in claims:
        m = models[claim["model"]]
        variables = {v["id"]: v for v in m["variables"]}
        rows = {r["id"]: r for r in m["constraints"]}
        result = {"id": claim["id"], "claim": deepcopy(claim), "model_hash": digest(m)}
        try:
            kind = claim["kind"]
            if kind == "declared_bound":
                actual = variables[claim["variable"]][claim["side"]]
                result["scope"] = "literal_variable_metadata_not_semantic_absence"
            elif kind == "row_coefficient":
                actual = rows[claim["row"]]["coefficients"][claim["variable"]]
            elif kind in {"row_rhs", "row_sense"}:
                actual = rows[claim["row"]][kind.removeprefix("row_")]
            elif kind == "entails":
                keys(claim["coefficients"], variables)
                clause = {"id": "queried_fact", **{k: claim[k] for k in ("coefficients", "sense", "rhs")}}
                cache_key = digest({"model": m, "clause": clause})
                remaining = wall_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    proof = {"status": "unknown", "reason": "fact_check_wall_limit"}
                elif cache_key in cache:
                    proof = cache[cache_key]
                else:
                    op = {"op": "entails", "model": m, "clause": clause}
                    proof = solver(op, wall_seconds=min(40, remaining)) if solver is execute else solver(op)
                    cache[cache_key] = proof
                result["proof"] = {k: v for k, v in proof.items() if k != "wall_seconds"}
                actual = True if proof["status"] == "contained_within_tolerance" else False if proof["status"] == "witness" else None
                if actual is None:
                    result.update(status="unknown", reason="implication_not_certified")
                    reports.append(result)
                    continue
            else:
                raise Invalid("unsupported_claim_kind")
            result.update(actual=actual, status="supported" if actual == claim["expected"] else "refuted")
        except KeyError:
            result.update(status="refuted", reason="claim_references_missing_symbol")
        reports.append(result)
    return reports


def _clause_key(value):
    return digest({k: value[k] for k in ("coefficients", "sense", "rhs")})


def compile_teacher_record(raw, problem, initial, teacher, evidence, solver=execute):
    """Compile only verified facts into a repair packet; never forward raw prose."""
    raw = validate(raw, TEACHER_SCHEMA)
    expected_hashes = {"initial": digest(initial), "teacher": digest(teacher)}
    if raw["model_hashes"] != expected_hashes:
        raise Invalid("stale_teacher_model_hash")
    if problem["text"][raw["start"]:raw["end"]] != raw["quote"] or raw["end"] > len(problem["text"]):
        raise Invalid("quote_provenance_mismatch")
    checked = verify_claims(raw["claims"], initial, teacher, solver)
    failures = [r for r in checked if r["status"] != "supported"]
    stop_reason = None
    if failures:
        stop_reason = "teacher_fact_refuted" if any(r["status"] == "refuted" for r in failures) else "teacher_fact_unknown"
    has_witness = (any(evidence.get(k, {}).get("status") == "witness" for k in ("left_to_right", "right_to_left"))
                   or evidence.get("preference", {}).get("status") == "strict_reversal")
    if raw["status"] == "no_witness" and has_witness:
        stop_reason = "teacher_ignored_executable_witness"
    elif raw["status"] == "no_witness" and (evidence.get("status") != "compared"
            or any(evidence.get(k, {}).get("status") != "contained_within_tolerance" for k in ("left_to_right", "right_to_left"))
            or evidence.get("preference", {}).get("status") != "no_strict_reversal_not_equivalence"):
        stop_reason = "comparison_not_certified"
    if raw["status"] != "repair" and (raw["target_rows"] or raw["positive_examples"]):
        raise Invalid("nonrepair_packet_requests_edits")
    if raw["status"] == "repair" and not stop_reason:
        # Each proposed row must be linked to opposite, verified implication
        # responses on the same actual clause. This does NOT decide which text
        # interpretation is correct; it only proves formal disagreement.
        paired = {}
        for r in checked:
            c = r["claim"]
            if c["kind"] == "entails":
                paired.setdefault(_clause_key(c), {})[c["model"]] = r["actual"]
        allowed = {k for k, v in paired.items() if set(v) == {"initial", "teacher"} and v["initial"] != v["teacher"]}
        for row_id in raw["target_rows"]:
            matching_rows = [r for m in (initial, teacher) for r in m["constraints"] if r["id"] == row_id]
            if not any(_clause_key(r) in allowed for r in matching_rows):
                stop_reason = "target_row_lacks_paired_verified_fact"
                break
        if not raw["target_rows"]:
            stop_reason = "empty_repair_scope"
    status = "repair" if raw["status"] == "repair" and stop_reason is None else "unresolved"
    legacy = {"status": status, "quote": raw["quote"], "start": raw["start"], "end": raw["end"],
              "explanation": "Formal facts were checked by the trusted kernel; textual interpretation remains unverified.",
              "target_rows": raw["target_rows"] if status == "repair" else [],
              "positive_examples": raw["positive_examples"] if status == "repair" else []}
    packet = teacher_packet(legacy, problem, initial, teacher, evidence)
    packet.update(protocol="teacher-v2", record_hash=digest(raw), verified_facts=checked,
                  fact_gate_status="blocked" if stop_reason else "passed", fact_gate_reason=stop_reason,
                  teacher_declared_status=raw["status"], interpretation_used_as_verified_fact=False)
    # The human interpretation is stored separately by the runner. Even when the
    # facts all check out, prose is not laundered into a solver-certified claim.
    return packet
