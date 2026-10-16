"""Prospective RetailOpt-190 short-decision experiment controller."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import platform
from typing import Any, Mapping

from .formal_gateway import RequestUnavailable, VERSION as GATEWAY_VERSION, wire_body
from .formal_provider import BASE_URL, MODEL, check_profile_metadata
from .formulationbench_same_knowledge import (
    PREPARATION_PYTHON,
    _runtime_metadata,
    authorization,
    ledger_summary,
    publish_new,
    publish_private_requests,
)
from .gateway import Stopped
from .nlequiv_skill_route import PersistentRateGate, rate_gate_summary
from .retailopt190_knowledge import (
    CARD_BY_ID,
    library_payload,
    library_sha256,
    parse_decision,
    questions,
    render_request,
    route,
)
from .run_interruption import RunInterrupted
from .schema import canonical, digest


VERSION = "retailopt190-short-decision-v2"
ARMS = ("base_short", "knowledge_short")
CAPACITY_PLAN_PATH = "experiments/retailopt190_short_capacity_plan_v2_20261017.json"
CAPACITY_AUTH_PATH = "experiments/retailopt190_short_capacity_authorization_v2_20261017.json"
CAPACITY_AUDIT_PATH = "experiments/retailopt190_short_capacity_audit_v2_20261017.json"
CAPACITY_RESULT_PATH = "experiments/retailopt190_short_capacity_result_v2_20261017.json"
CAPACITY_REQUEST_ROOT = "results/private/retailopt190_short_capacity_requests_v2_20261017"
CAPACITY_RUN_DIRECTORY = "results/private/retailopt190_short_capacity_v2_20261017"
FULL_PLAN_PATH = "experiments/retailopt190_short_full_plan_v2_20261017.json"
FULL_AUTH_PATH = "experiments/retailopt190_short_full_authorization_v2_20261017.json"
FULL_AUDIT_PATH = "experiments/retailopt190_short_full_audit_v2_20261017.json"
FULL_EXECUTION_PATH = "experiments/retailopt190_short_full_execution_v2_20261017.json"
FULL_REQUEST_ROOT = "results/private/retailopt190_short_full_requests_v2_20261017"
FULL_RUN_DIRECTORY = "results/private/retailopt190_short_full_v2_20261017"


class RetailExperimentError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bytes(value: Any) -> bytes:
    return (canonical(value) + "\n").encode()


def _file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def response_schema(selected_skill_ids: list[str]) -> dict[str, Any]:
    qs = questions(selected_skill_ids)
    properties = {
        question.question_id: {"type": "string", "enum": list(question.choices)}
        for question in qs
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema", "answers"],
        "properties": {
            "schema": {"const": "llm4or-retailopt190-short-decision-v1"},
            "answers": {
                "type": "object",
                "additionalProperties": False,
                "required": [question.question_id for question in qs],
                "properties": properties,
            },
        },
    }


def make_payload(view: Mapping[str, Any], cell_id: str, selected_skill_ids: list[str]) -> dict[str, Any]:
    return {
        "version": VERSION,
        "instruction": view["instructions"],
        "view": dict(view),
        "context": {
            "cell_id": cell_id,
            "arm": view["arm"],
            "opaque_archetype_id": view["opaque_archetype_id"],
            "selected_skill_ids": selected_skill_ids,
        },
        "output_contract": {
            "kind": "exact_short_semantic_decision",
            "all_questions_required": True,
            "code_or_explanation_forbidden": True,
        },
        "response_schema": response_schema(selected_skill_ids),
    }


def _strict_response(text: str, selected_skill_ids: list[str]) -> dict[str, str]:
    def pairs(rows):
        value = {}
        for key, child in rows:
            if key in value:
                raise RetailExperimentError("duplicate_response_key")
            value[key] = child
        return value

    def constant(_value):
        raise RetailExperimentError("nonfinite_response")

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except RetailExperimentError:
        raise
    except (TypeError, ValueError, UnicodeError) as exc:
        raise RetailExperimentError("invalid_response_json") from exc
    return parse_decision(value, selected_skill_ids)


def _sanitize_prompt(text: str, source_id: str, opaque: str) -> str:
    if text.count(source_id) != 1:
        raise RetailExperimentError("source_id_occurrence")
    return text.replace(source_id, f"scenario_{opaque[:16]}")


def build_full_material(source_root: str | Path, ledger_path: str | Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    source_root = Path(source_root)
    ledger_raw = Path(ledger_path).read_bytes()
    ledger = json.loads(ledger_raw)
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in ledger["records"]:
        groups.setdefault(record["archetype"], []).append(record)
    if len(groups) != 38 or any(sorted(row["variant"] for row in rows) != list(range(5)) for rows in groups.values()):
        raise RetailExperimentError("archetype_grid")
    entries: dict[str, bytes] = {}
    cells = {}
    public_inputs = {}
    private_archetypes = []
    for archetype, rows in sorted(groups.items()):
        ordered = sorted(rows, key=lambda row: row["variant"])
        representative = ordered[0]
        routes = []
        for row in ordered:
            data = json.loads((source_root / "scenarios/data" / f"{row['source_id']}.json").read_text())
            routes.append(route(data))
        if len(set(routes)) != 1:
            raise RetailExperimentError("variant_route_drift")
        selected = list(routes[0])
        opaque = _sha(f"{ledger['source']['commit']}\0{archetype}".encode())
        prompt = (source_root / "scenarios/prompts" / f"{representative['source_id']}.scenario.txt").read_text()
        prompt = _sanitize_prompt(prompt, representative["source_id"], opaque)
        private_archetypes.append(
            {
                "opaque_archetype_id": opaque,
                "source_archetype": archetype,
                "source_records": [
                    {"opaque_id": row["opaque_id"], "source_id": row["source_id"], "variant": row["variant"]}
                    for row in ordered
                ],
                "selected_skill_ids": selected,
            }
        )
        for arm in ARMS:
            view = render_request(
                opaque_archetype_id=opaque,
                public_prompt=prompt,
                selected_skill_ids=selected,
                arm=arm,
            )
            cell_id = _sha(f"{opaque}\0{arm}".encode())
            payload = make_payload(view, cell_id, selected)
            raw = _bytes(payload)
            evidence_bytes = len(_bytes(view["evidence"])) if view["evidence"] else 0
            entries[f"requests/{cell_id}.json"] = raw
            cells[cell_id] = {
                "opaque_archetype_id": opaque,
                "arm": arm,
                "selected_skill_ids": selected,
                "route_card_count": len(selected),
                "question_count": len(questions(selected)),
                "request_sha256": _sha(raw),
                "request_bytes": len(raw),
                "evidence_bytes": evidence_bytes,
            }
            public_inputs[cell_id] = digest(payload)
    private_ledger = {
        "schema": VERSION + "-private-archetype-ledger",
        "source_commit": ledger["source"]["commit"],
        "source_custody_ledger_sha256": _sha(ledger_raw),
        "archetypes": private_archetypes,
    }
    entries["private/archetype_ledger.json"] = _bytes(private_ledger)
    return {
        "cells": dict(sorted(cells.items())),
        "public_inputs": dict(sorted(public_inputs.items())),
        "entries_sha256": digest({path: _sha(raw) for path, raw in sorted(entries.items())}),
        "max_request_bytes": max(row["request_bytes"] for row in cells.values()),
        "max_wire_bytes": max(
            len(canonical(wire_body(json.loads(raw), 512)).encode())
            for path, raw in entries.items() if path.startswith("requests/")
        ),
        "max_evidence_bytes": max(row["evidence_bytes"] for row in cells.values()),
        "private_archetype_ledger_sha256": _sha(entries["private/archetype_ledger.json"]),
    }, dict(sorted(entries.items()))


def build_capacity_material(maximum_task_bytes: int) -> tuple[dict[str, Any], dict[str, bytes]]:
    selected = ["retail.core.flow.v1", "retail.substitution.v1", "retail.moq_fixed.v1"]
    entries = {}; cells = {}; public_inputs = {}
    synthetic_task = "[SCENARIO]\nscenario_synthetic\n[BUSINESS DESCRIPTION]\n" + "x" * maximum_task_bytes
    opaque = "f" * 64
    for arm in ARMS:
        view = render_request(opaque_archetype_id=opaque, public_prompt=synthetic_task, selected_skill_ids=selected, arm=arm)
        cell_id = _sha(f"capacity\0{arm}".encode())
        payload = make_payload(view, cell_id, selected); raw = _bytes(payload)
        entries[f"requests/{cell_id}.json"] = raw
        cells[cell_id] = {"opaque_archetype_id": opaque, "arm": arm, "selected_skill_ids": selected, "route_card_count": 3, "question_count": len(questions(selected)), "request_sha256": _sha(raw), "request_bytes": len(raw), "evidence_bytes": len(_bytes(view["evidence"])) if view["evidence"] else 0}
        public_inputs[cell_id] = digest(payload)
    return {
        "cells": dict(sorted(cells.items())),
        "public_inputs": dict(sorted(public_inputs.items())),
        "entries_sha256": digest({path: _sha(raw) for path, raw in sorted(entries.items())}),
        "max_request_bytes": max(len(raw) for raw in entries.values()),
        "max_wire_bytes": max(len(canonical(wire_body(json.loads(raw), 512)).encode()) for raw in entries.values()),
    }, dict(sorted(entries.items()))


def _common_plan(root: Path, material: Mapping[str, Any], *, capacity: bool) -> dict[str, Any]:
    check_profile_metadata()
    # The gateway admits against the exact serialized provider envelope rather
    # than the inner payload.  Binding the maximum wire size prevents a valid
    # maximum-envelope request from being rejected before transport.
    reserve = material["max_wire_bytes"] + 8_192 + 512
    cells = 2 if capacity else 76
    attempts = cells * 3
    code_paths = [
        "llm4or/retailopt190_experiment.py",
        "llm4or/retailopt190_knowledge.py",
        "llm4or/formal_gateway.py",
        "llm4or/formal_provider.py",
        "llm4or/openai_httpx_worker.py",
        "llm4or/schema.py",
        "scripts/openai_httpx_transport_worker.py",
    ]
    if capacity:
        code_paths += ["scripts/freeze_retailopt190_short_capacity.py", "scripts/run_retailopt190_short_capacity.py"]
    else:
        code_paths += ["scripts/freeze_retailopt190_short_full.py", "scripts/run_retailopt190_short_full.py"]
    return {
        "kind": "fresh_common_external",
        "endpoint": BASE_URL,
        "model": MODEL,
        "runtime_version": VERSION,
        "gateway_version": GATEWAY_VERSION,
        "replicates": [0],
        "public_inputs": material["public_inputs"],
        "cells": material["cells"],
        "token_cap": reserve + 1,
        "trajectory_token_caps": [reserve + 1],
        "limits": {
            "max_requests": attempts,
            "max_total_reserved_or_reported_tokens": attempts * reserve,
            "max_completion_tokens": 512,
            "max_input_bytes": max(32_768, material["max_wire_bytes"] + 4_096),
            "max_output_bytes": 16_384,
            "token_overhead_reserve": 8_192,
            "request_seconds": 150,
            "max_run_seconds": 3_600 if capacity else 21_600,
            "minimum_free_disk_bytes": 5_000_000_000,
        },
        "resilience": {"max_attempts_per_request": 3, "backoff_seconds": [2, 5], "circuit_breaker_consecutive_failures": 8, "retryable_local_errors": ["invalid_json_response"], "max_concurrent_requests": 5},
        "transport": {"kind": "openai_httpx_single_attempt_v1", "python": str(PREPARATION_PYTHON), "python_sha256": _file_sha(PREPARATION_PYTHON), "worker": "scripts/openai_httpx_transport_worker.py"},
        "runtime": {"controller_python": platform.python_version(), "controller_machine": platform.machine(), "transport_runtime": _runtime_metadata()},
        "frozen_files": {path: _file_sha(root / path) for path in code_paths},
        "skill_library_sha256": library_sha256(),
        "private_request_bundle_sha256": material["entries_sha256"],
    }


def build_capacity_plan(root: str | Path, maximum_task_bytes: int) -> tuple[dict[str, Any], dict[str, bytes]]:
    root = Path(root).resolve(); material, entries = build_capacity_material(maximum_task_bytes)
    plan = _common_plan(root, material, capacity=True)
    plan.update({
        "schema": VERSION + "-capacity-plan",
        "status": "frozen_ready_for_synthetic_capacity",
        "authorization_schema": VERSION + "-capacity-authorization",
        "authorization_path": CAPACITY_AUTH_PATH,
        "external_method": {"name": "RetailOptShortDecisionCapacity", "paper_label": "retail-short-capacity", "scope_stage": "retailcapacity", "max_calls": 1},
        "matrix": {"synthetic_cells": 2, "logical_requests": 2},
        "run_directory": CAPACITY_RUN_DIRECTORY,
        "private_request_root": CAPACITY_REQUEST_ROOT,
        "output": {"public_result": CAPACITY_RESULT_PATH, "public_audit": CAPACITY_AUDIT_PATH},
        "capacity_gate": {"terminal_cells": 2, "completed": 2, "method_failure": 0, "infrastructure_unavailable": 0, "logical_slots": 2, "maximum_completion_tokens": 512, "restart_new_items": 0},
        "privacy": {"benchmark_bodies": False, "benchmark_labels": False, "evaluator_opened": False, "credentials_read_during_freeze": False},
        "claim_boundary": "Synthetic maximum-envelope short-decision capacity only; no benchmark accuracy.",
    })
    return plan, entries


def build_full_plan(root: str | Path, source_root: str | Path, ledger_path: str | Path, capacity_result: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
    if capacity_result.get("capacity_gate", {}).get("passed") is not True:
        raise RetailExperimentError("capacity_not_passed")
    root = Path(root).resolve(); material, entries = build_full_material(source_root, ledger_path)
    plan = _common_plan(root, material, capacity=False)
    plan.update({
        "schema": VERSION + "-full-plan",
        "status": "frozen_ready_for_prospective_execution",
        "authorization_schema": VERSION + "-full-authorization",
        "authorization_path": FULL_AUTH_PATH,
        "external_method": {"name": "RetailOptShortDecision", "paper_label": "benchmark-grounded-proof-carrying-knowledge", "scope_stage": "retailfull", "max_calls": 1},
        "source": {"commit": "d809c6bbeb42cb99b0564c41bfb8f331f0156b9d", "records": 190, "archetypes": 38, "variants_per_archetype": 5},
        "population": {"archetypes": 38, "variants": 190, "arms": list(ARMS), "logical_requests": 76, "solver_evaluations": 380},
        "matrix": {"inference_cells": 76, "logical_requests": 76},
        "run_directory": FULL_RUN_DIRECTORY,
        "private_request_root": FULL_REQUEST_ROOT,
        "private_archetype_ledger_sha256": material["private_archetype_ledger_sha256"],
        "output": {"public_execution": FULL_EXECUTION_PATH},
        "capacity_gate": {"plan_sha256": capacity_result["plan_sha256"], "result_sha256": digest(capacity_result), "passed": True},
        "rate_limit_policy": {"max_logical_starts": 40, "window_seconds": 60, "safety_seconds": 1.0, "observed_provider_limit": 60},
        "evidence_budget": {"maximum_cards": 3, "maximum_evidence_bytes": material["max_evidence_bytes"], "decision_completion_tokens": 512, "reported_separately": True},
        "matched_design": {"same_model": True, "same_public_task": True, "same_question_set": True, "same_output_contract": True, "same_compiler": True, "same_solver": True, "only_difference": "selected obligation and counterexample evidence present only in knowledge_short"},
        "endpoint": {"primary": "relative_objective_error_strictly_below_0.01", "execution_and_status_reported_separately": True, "full_denominator": 190},
        "statistical_gate": {
            "primary_unit": "archetype_fully_correct_on_all_five_variants",
            "test": "one_sided_exact_mcnemar",
            "alpha": 0.05,
            "minimum_instance_accuracy_gain": 0.05,
            "minimum_archetype_corrections": 6,
            "maximum_archetype_regressions": 2,
            "correction_regression_ratio": 2.0,
            "minimum_inference_terminal_fraction_per_arm": 0.99,
            "missing_invalid_or_solver_failure": "incorrect",
        },
        "privacy": {"reference_values_available_to_inference": False, "request_bodies_public": False, "response_bodies_public": False, "evaluator_opened_during_freeze": False},
        "claim_boundary": {"direct_modeling_accuracy": True, "single_benchmark": True, "benchmark_specific_authored_knowledge": True, "automatic_skill_acquisition": False, "universal_or_superiority": False},
    })
    return plan, entries


def material_audit(plan: Mapping[str, Any], entries: Mapping[str, bytes], *, capacity: bool) -> dict[str, Any]:
    cells = plan["cells"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in cells.values(): grouped.setdefault(row["opaque_archetype_id"], []).append(row)
    checks = {
        "request_bundle_bound": digest({path: _sha(raw) for path, raw in sorted(entries.items())}) == plan["private_request_bundle_sha256"],
        "two_arms": all({row["arm"] for row in rows} == set(ARMS) for rows in grouped.values()),
        "same_route_and_questions": all(len({(tuple(row["selected_skill_ids"]), row["question_count"]) for row in rows}) == 1 for rows in grouped.values()),
        "base_has_zero_evidence": all(row["evidence_bytes"] == 0 for row in cells.values() if row["arm"] == "base_short"),
        "knowledge_has_evidence": all(row["evidence_bytes"] > 0 for row in cells.values() if row["arm"] == "knowledge_short"),
        "card_budget": max(row["route_card_count"] for row in cells.values()) <= 3,
        "completion_budget": plan["limits"]["max_completion_tokens"] == 512,
        "concurrency_five": plan["resilience"]["max_concurrent_requests"] == 5,
    }
    if capacity:
        checks.update({"synthetic_only": len(grouped) == 1 and next(iter(grouped)) == "f" * 64, "two_cells": len(cells) == 2})
    else:
        checks.update({"thirty_eight_archetypes": len(grouped) == 38, "seventy_six_cells": len(cells) == 76, "private_mapping_present": "private/archetype_ledger.json" in entries})
    return {"schema": plan["schema"] + "-audit", "status": "passed" if all(checks.values()) else "failed", "plan_sha256": digest(plan), "checks": checks, "execution": {"api_calls": 0, "model_calls": 0, "solver_calls": 0, "credentials_read": False}, "claim_boundary": plan["claim_boundary"]}


def load_request(root: str | Path, plan: Mapping[str, Any], cell_id: str) -> dict[str, Any]:
    raw = (Path(root) / plan["private_request_root"] / "requests" / f"{cell_id}.json").read_bytes()
    if _sha(raw) != plan["cells"][cell_id]["request_sha256"]:
        raise RetailExperimentError("request_drift")
    value = json.loads(raw)
    if digest(value) != plan["public_inputs"][cell_id]:
        raise RetailExperimentError("request_binding")
    return value


def _cell_path(directory: Path, cell_id: str) -> Path:
    return directory / "cells" / f"{cell_id}.json"


def run_plan(root: str | Path, plan: Mapping[str, Any], directory: str | Path, gateway: Any, *, workers: int = 5) -> dict[str, Any]:
    root, directory = Path(root), Path(directory)
    if workers != 5:
        raise RetailExperimentError("concurrency")
    plan_hash = digest(plan); rate_gate = PersistentRateGate(directory, plan) if "rate_limit_policy" in plan else None

    def one(cell_id: str):
        path = _cell_path(directory, cell_id)
        if path.exists():
            value = json.loads(path.read_text())
            if value.get("plan_sha256") != plan_hash or value.get("cell_id") != cell_id:
                raise RetailExperimentError("checkpoint_binding")
            return value, False
        descriptor = plan["cells"][cell_id]; payload = load_request(root, plan, cell_id)
        scope = f"{plan['external_method']['scope_stage']}:{plan['external_method']['name']}:0:{cell_id}"
        gateway.register(scope, 1, plan["token_cap"]); gateway.work_started(scope)
        try:
            if rate_gate is not None: rate_gate.admit()
            response = gateway.request(scope, payload, plan_hash, 0, 0)
            answers = _strict_response(response["text"], descriptor["selected_skill_ids"])
            record = {"answers": answers, "decision_sha256": digest(answers), "completion_tokens": response["completion_tokens"]}
            status, error = "completed", None; gateway.work_finished(scope, "complete", None)
        except RequestUnavailable as exc:
            record, status, error = None, "infrastructure_unavailable", str(exc).split(":", 1)[-1][:160]; gateway.work_finished(scope, "unavailable", error)
        except RunInterrupted:
            raise
        except Stopped as exc:
            halt = gateway.halt_reason()
            if halt: raise RunInterrupted("global_halt:" + halt) from exc
            record, status, error = None, "method_failure", str(exc)[:160]; gateway.work_finished(scope, "complete", error)
        except Exception as exc:
            record, status, error = None, "method_failure", type(exc).__name__; gateway.work_finished(scope, "complete", error)
        cell = {"schema": VERSION + "-private-cell", "plan_sha256": plan_hash, "cell_id": cell_id, "status": status, "error": error, "record": record}
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700); publish_new(path, cell)
        return cell, True

    rows = []; new_items = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(one, cell_id) for cell_id in sorted(plan["cells"])]):
            value, created = future.result(); rows.append(value); new_items += int(created)
    result = {"terminal": len(rows), "new_items": new_items, "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())), "gateway": gateway.summary()}
    if rate_gate is not None: result["rate_limit"] = rate_gate_summary(directory, plan["rate_limit_policy"])
    return result


def score_capacity(plan: Mapping[str, Any], directory: str | Path, *, restart_new_items: int) -> dict[str, Any]:
    directory, plan_hash = Path(directory), digest(plan); rows = []
    for cell_id in sorted(plan["cells"]):
        row = json.loads(_cell_path(directory, cell_id).read_text())
        if row.get("plan_sha256") != plan_hash: raise RetailExperimentError("checkpoint_plan")
        rows.append(row)
    counts = Counter(row["status"] for row in rows); ledger = ledger_summary(directory)
    observed = {"terminal_cells": len(rows), "completed": counts["completed"], "method_failure": counts["method_failure"], "infrastructure_unavailable": counts["infrastructure_unavailable"], "logical_slots": ledger["logical_slots"], "maximum_completion_tokens": ledger["maximum_completion_tokens"], "restart_new_items": restart_new_items}
    checks = {key: observed[key] <= expected if key == "maximum_completion_tokens" else observed[key] == expected for key, expected in plan["capacity_gate"].items()}; checks["no_halt"] = ledger["halt"] is None
    return {"schema": VERSION + "-capacity-result", "status": "complete", "plan_sha256": plan_hash, "capacity_gate": {**observed, "passed": all(checks.values()), "checks": checks}, "ledger": ledger, "claim_boundary": plan["claim_boundary"]}


def full_execution(plan: Mapping[str, Any], directory: str | Path, *, restart_new_items: int) -> dict[str, Any]:
    directory = Path(directory); counts = Counter()
    for cell_id in plan["cells"]:
        row = json.loads(_cell_path(directory, cell_id).read_text()); counts[row["status"]] += 1
    result = {"schema": VERSION + "-full-execution", "status": "terminal" if sum(counts.values()) == 76 else "incomplete", "plan_sha256": digest(plan), "cells": {"terminal": sum(counts.values()), **{key: counts[key] for key in ("completed", "method_failure", "infrastructure_unavailable")}}, "ledger": ledger_summary(directory), "restart_new_items": restart_new_items, "evaluator_opened": False, "claim_boundary": "Inference execution only; reference objectives unopened by the runner."}
    result["rate_limit"] = rate_gate_summary(directory, plan["rate_limit_policy"])
    return result


__all__ = [
    "ARMS", "CAPACITY_AUDIT_PATH", "CAPACITY_AUTH_PATH", "CAPACITY_PLAN_PATH",
    "CAPACITY_REQUEST_ROOT", "CAPACITY_RESULT_PATH", "FULL_AUDIT_PATH",
    "FULL_AUTH_PATH", "FULL_EXECUTION_PATH", "FULL_PLAN_PATH", "FULL_REQUEST_ROOT",
    "VERSION", "build_capacity_plan", "build_full_material", "build_full_plan",
    "full_execution", "library_payload", "load_request", "make_payload",
    "material_audit", "run_plan", "score_capacity",
]
