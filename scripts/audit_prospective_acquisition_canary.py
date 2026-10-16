#!/usr/bin/env python3
"""Independent offline audit for the prospective acquisition canary."""

import base64
from collections import Counter
from pathlib import Path

from llm4or import antchat_object_pilot_contract as contract
from llm4or.schema import canonical, digest
from scripts import freeze_prospective_acquisition_canary as freezer
from scripts import run_prospective_acquisition_canary as runner


ROOT = Path(__file__).resolve().parents[1]
VERSION = "prospective-acquisition-canary-audit-v1"


class ProspectiveAcquisitionAuditError(ValueError):
    """Fail-closed independent-audit error."""


def require(ok, code):
    if not ok:
        raise ProspectiveAcquisitionAuditError(code)


def evaluate_gate(pairs):
    """Evaluate the fixed engineering gate over exactly eight paired units."""

    require(type(pairs) is list and len(pairs) == 8 and
            len({row.get("unit_id") for row in pairs}) == 8, "gate_denominator")
    counts = Counter()
    global_failure = False
    for row in pairs:
        require(type(row) is dict and
                type(row.get("flat_success")) is bool and
                type(row.get("treatment_success")) is bool and
                type(row.get("global_safety_failure")) is bool,
                "gate_pair")
        flat = row["flat_success"]
        treatment = row["treatment_success"]
        label = ("both" if flat and treatment else
                 "flat_only" if flat else
                 "treatment_only" if treatment else "neither")
        counts[label] += 1
        global_failure = global_failure or row["global_safety_failure"]
    ordered = {key: counts[key] for key in
               ("treatment_only", "flat_only", "both", "neither")}
    return {
        "passed": (ordered["treatment_only"] >= 2 and
                   ordered["flat_only"] == 0 and not global_failure),
        "counts": ordered,
        "minimum_treatment_only": 2,
        "maximum_flat_only": 0,
        "requires_no_global_safety_failure": True,
        "global_safety_failure_observed": global_failure,
    }


def _load_frozen_without_dispatch_expiry(root):
    root = Path(root).resolve()
    plan = runner.read_json(runner._safe_path(root, freezer.PLAN))
    bundle = runner.read_json(runner._safe_path(root, freezer.BUNDLE))
    require(plan.get("schema") == freezer.VERSION, "plan_schema")
    require(digest(bundle) == plan.get("private_bundle_sha256"), "bundle_digest")
    expected = freezer.build_plan(root, bundle, plan.get("created_at_unix"))
    require(canonical(plan) == canonical(expected), "plan_binding")
    return root, plan, bundle


def _verify_provider_cell(plan, bundle, public_cases, directories, cell, terminal):
    envelope_path = runner._cell_path(directories, "envelopes", cell["cell_id"])
    require(envelope_path.exists(), "envelope_missing")
    saved = runner.read_json(envelope_path)
    candidate_path = runner._cell_path(directories, "candidates", cell["cell_id"])
    if saved.get("schema") == runner.VERSION + "-transport-failure":
        require(saved == {
            "schema": runner.VERSION + "-transport-failure",
            "plan_sha256": digest(plan),
            "cell_id": cell["cell_id"],
            "error": saved.get("error"),
            "global_halt": saved.get("global_halt"),
        } and type(saved.get("error")) is str and
                type(saved.get("global_halt")) is bool, "transport_record")
        expected_status = ("global_safety_failure" if saved["global_halt"] else
                           "infrastructure_unavailable")
        require(terminal["status"] == expected_status and
                terminal["reason"] == saved["error"] and
                terminal["usage"] is None and terminal["response_sha256"] is None and
                not candidate_path.exists(), "transport_terminal")
        return {"provider_complete": False, "typed_response": False,
                "verification_passed": False}

    require(saved.get("schema") == runner.VERSION + "-provider-envelope" and
            saved.get("plan_sha256") == digest(plan) and
            saved.get("cell_id") == cell["cell_id"] and
            type(saved.get("envelope_base64")) is str, "provider_record")
    try:
        raw = base64.b64decode(saved["envelope_base64"], validate=True)
    except (TypeError, ValueError) as exc:
        raise ProspectiveAcquisitionAuditError("provider_envelope_base64") from exc
    require(runner.sha(raw) == saved.get("envelope_sha256"), "provider_envelope_hash")
    parsed = contract.parse_envelope(raw, "B")
    require(terminal["usage"] == parsed["usage"] and
            terminal["response_sha256"] == parsed["raw_sha256"],
            "provider_terminal_metadata")
    if parsed["status"] != "complete":
        expected_status = ("global_safety_failure" if parsed["global_halt"] else
                           "infrastructure_unavailable")
        require(terminal["status"] == expected_status and
                terminal["reason"] == parsed["error"] and
                not candidate_path.exists(), "provider_failure_terminal")
        return {"provider_complete": False, "typed_response": False,
                "verification_passed": False}

    status, reason, candidate_record = runner._candidate_outcome(
        parsed["raw"], public_cases
    )
    require(terminal["status"] == status and terminal["reason"] == reason,
            "candidate_terminal")
    if candidate_record is None:
        require(not candidate_path.exists(), "candidate_unexpected")
        return {"provider_complete": True, "typed_response": False,
                "verification_passed": False}
    saved_candidate = runner.read_json(candidate_path)
    expected_candidate = {
        "schema": runner.VERSION + "-private-candidate",
        "plan_sha256": digest(plan),
        "cell_id": cell["cell_id"],
        **candidate_record,
    }
    require(canonical(saved_candidate) == canonical(expected_candidate),
            "candidate_recomputation")
    return {"provider_complete": True, "typed_response": True,
            "verification_passed": candidate_record["verification"]["passed"]}


def _arm_summary(cells):
    require(len(cells) == 3 and sorted(row["round"] for row in cells) == [1, 2, 3],
            "arm_rounds")
    accepted = [row["round"] for row in cells if row["status"] == "accepted_candidate"]
    require(len(accepted) <= 1, "multiple_arm_acceptance")
    if accepted:
        require(all(row["status"] == "skipped_after_success"
                    for row in cells if row["round"] > accepted[0]),
                "skip_after_acceptance")
    return {
        "success": bool(accepted),
        "accepted_round": accepted[0] if accepted else None,
        "logical_cells": 3,
        "status_counts": dict(sorted(Counter(row["status"] for row in cells).items())),
    }


def build_audit(root=ROOT):
    """Recompute all identities, per-cell outcomes, accounting, and the gate."""

    root, plan, bundle = _load_frozen_without_dispatch_expiry(root)
    directories = runner._directories(root, plan)
    report = runner._load_terminal_report(root, plan, directories)
    require(report is not None, "terminal_report_missing")
    public_cases = freezer._inputs(root)[1]
    plan_by_id = {row["cell_id"]: row for row in plan["cells"]}
    terminals = {}
    recomputed = Counter()
    for cell_id, cell in plan_by_id.items():
        terminal = runner._bound_terminal(
            plan, cell,
            runner.read_json(runner._cell_path(directories, "cells", cell_id)),
        )
        terminals[cell_id] = terminal
        reservation_path = runner._cell_path(directories, "reservations", cell_id)
        envelope_path = runner._cell_path(directories, "envelopes", cell_id)
        candidate_path = runner._cell_path(directories, "candidates", cell_id)
        if terminal["physical_send_completed"]:
            require(reservation_path.exists(), "reservation_missing")
            require(canonical(runner.read_json(reservation_path)) ==
                    canonical(runner.reservation_for(plan, cell)), "reservation_binding")
            evidence = _verify_provider_cell(
                plan, bundle, public_cases, directories, cell, terminal
            )
            recomputed["physical_sends"] += 1
            recomputed["provider_complete"] += evidence["provider_complete"]
            recomputed["typed_responses"] += evidence["typed_response"]
            recomputed["verification_passed"] += evidence["verification_passed"]
        elif terminal["reason"] == "orphaned_reservation_no_replay":
            require(reservation_path.exists() and not envelope_path.exists() and
                    not candidate_path.exists(), "orphan_evidence")
            require(canonical(runner.read_json(reservation_path)) ==
                    canonical(runner.reservation_for(plan, cell)), "orphan_reservation")
            recomputed["orphaned_reservations"] += 1
        else:
            require(not reservation_path.exists() and not envelope_path.exists() and
                    not candidate_path.exists(), "nondispatch_evidence")

    require(len(list(directories["cells"].glob("*.json"))) == 48, "extra_terminals")
    require({path.stem for path in directories["reservations"].glob("*.json")} ==
            {cell_id for cell_id, value in terminals.items()
             if value["physical_send_completed"] or
             value["reason"] == "orphaned_reservation_no_replay"},
            "reservation_inventory")
    require({path.stem for path in directories["envelopes"].glob("*.json")} ==
            {cell_id for cell_id, value in terminals.items()
             if value["physical_send_completed"]}, "envelope_inventory")

    paired = []
    gate_rows = []
    global_failure = any(row["status"] == "global_safety_failure"
                         for row in terminals.values())
    for unit in bundle["units"]:
        arms = {}
        for arm in ("flat", "separating_witness"):
            rows = sorted(
                [value for value in terminals.values()
                 if value["unit_id"] == unit["unit_id"] and value["arm"] == arm],
                key=lambda row: row["round"],
            )
            arms[arm] = _arm_summary(rows)
        paired.append({
            "unit_id": unit["unit_id"],
            "source_provenance": unit["provenance"],
            "denominator_included": True,
            "flat": arms["flat"],
            "separating_witness": arms["separating_witness"],
        })
        gate_rows.append({
            "unit_id": unit["unit_id"],
            "flat_success": arms["flat"]["success"],
            "treatment_success": arms["separating_witness"]["success"],
            "global_safety_failure": global_failure,
        })
    gate = evaluate_gate(gate_rows)
    require(sum(gate["counts"].values()) == 8, "paired_count")
    audit = {
        "schema": VERSION,
        "status": "passed" if not gate["global_safety_failure_observed"] else
                  "global_safety_failure",
        "approved_program": plan["approved_program"],
        "plan_sha256": digest(plan),
        "private_bundle_sha256": digest(bundle),
        "terminal_result_sha256": digest(report),
        "model": plan["model"],
        "paired_units": paired,
        "paired_counts": gate["counts"],
        "engineering_gate": {key: value for key, value in gate.items()
                             if key != "counts"},
        "progression_decision": (
            "eligible_to_prepare_stage2_preregistration_not_authorized_to_dispatch"
            if gate["passed"] else "retain_authored_skill_fallback_no_stage2"
        ),
        "accounting": report["accounting"],
        "recomputed_evidence_counts": dict(sorted(recomputed.items())),
        "verification": {
            "source_hashes_match": True,
            "private_bundle_recomputed": True,
            "paired_fact_equivalence_recomputed": True,
            "request_identity_recomputed": True,
            "provider_envelopes_reparsed": True,
            "typed_responses_reverified": True,
            "accounting_recomputed": True,
            "full_eight_pair_denominator": True,
        },
        "claim_boundary": {
            "engineering_canary_only": True,
            "automatic_acquisition_efficacy_claimed": False,
            "confirmatory_effect_claimed": False,
            "benchmark_accuracy_claimed": False,
            "library_promotion_performed": False,
        },
    }
    require(canonical(report["accounting"]) ==
            canonical(runner._build_report(
                plan, list(terminals.values()), directories
            )["accounting"]), "accounting_recomputation")
    return audit


def publish(root=ROOT):
    root = Path(root).resolve()
    path = runner._safe_path(root, freezer.AUDIT)
    require(not path.exists(), "audit_output_exists")
    require(path.parent.is_dir(), "audit_parent")
    audit = build_audit(root)
    runner.write_new_json(path, audit)
    return audit


if __name__ == "__main__":
    print(canonical(publish()))
