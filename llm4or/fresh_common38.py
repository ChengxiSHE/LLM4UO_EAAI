"""Common-evidence packets for the fresh larger RCPSP/VRPTW cohort.

The upstream JSON files contain evaluator fields, but this module projects only
the distributed natural-language description, structured instance data, and
non-outcome size/type metadata.  It neither solves nor dispatches model calls.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from .benchmark_inputs import BASE_PROFILE, input_shape_issues, validate_public_input
from .gateway import Stopped
from .schema import canonical, digest, loads
from .text2opt_template_compiler_v10 import compile_template_problem


VERSION = "fresh-common38-packets-v1"
SOURCE_REVISION = "1dac06be656c41d827ef20987cf8af0b48d382a2"
FAMILIES = ("rcpsp", "vrptw")
MAX_VARIABLES = 96
MAX_CONSTRAINTS = 192
RESOURCE_CAPS = {
    "variables": 2000,
    "constraints": 10000,
    "nonzeros": 100000,
    "serialized_bytes": 4000000,
}
SOURCE_RELATIVE = "data/raw/text2opt_bench_20261003"
OLD_PREPARED = "data/prepared_benchmarks/text2opt_template_confirmation_v1.json"
ESTIMAND_AUDIT = "experiments/fresh_common_protocol_estimand_audit_20261015.json"


class FreshCommon38Error(ValueError):
    """Fail-closed packet construction error."""


def require(ok, code):
    if not ok:
        raise FreshCommon38Error(code)


def sha(raw):
    require(type(raw) is bytes, "sha_bytes")
    return hashlib.sha256(raw).hexdigest()


def _read(path, maximum=16 * 1024 * 1024):
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= maximum, "source_file")
        blocks = []
        left = maximum + 1
        while left:
            block = os.read(fd, min(left, 1_048_576))
            if not block:
                break
            blocks.append(block)
            left -= len(block)
        raw = b"".join(blocks)
        require(len(raw) == info.st_size and len(raw) <= maximum, "source_stability")
        return raw
    finally:
        os.close(fd)


def _json(path):
    raw = _read(path)
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise FreshCommon38Error("source_json") from exc
    require(type(value) is dict, "source_object")
    return value, raw


def _normalized(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def _source_root(root):
    root = Path(root).resolve()
    source = (root / SOURCE_RELATIVE).resolve()
    require(root in source.parents and source.is_dir(), "source_root")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    require(revision == SOURCE_REVISION, "source_revision")
    return root, source


def _payload(problem_id, text, instance_data):
    return validate_public_input({
        "id": problem_id,
        "profile": BASE_PROFILE,
        "text": text,
        "parameters": [{
            "symbol": "instance_data",
            "definition": "Public structured instance data exactly as distributed.",
            "shape": [],
        }],
        "instances": [{
            "id": "instance_0000",
            "input": {"instance_data": instance_data},
        }],
    })


def build_private_bundle(root):
    """Project the exact 38 public packets without using evaluator outcomes."""

    root, source = _source_root(root)
    old, _ = _json(root / OLD_PREPARED)
    old_rows = old.get("confirmation")
    require(type(old_rows) is list and len(old_rows) == 183, "prior_prepared")
    old_hashes = {sha(_normalized(row["public"]["text"]).encode("utf-8"))
                  for row in old_rows}
    rows = []
    for family in FAMILIES:
        directory = source / f"synthetic_dataset/Template/basic_template/{family}/small"
        files = sorted(directory.glob("*.json"))
        require(len(files) == 50, "source_family_size")
        for path in files:
            value, raw = _json(path)
            text = value.get("LLM_description")
            instance_data = value.get("instance_data")
            meta = value.get("meta")
            require(type(text) is str and text.strip() and type(instance_data) is dict and
                    type(meta) is dict, "public_projection_fields")
            num_vars = meta.get("num_vars")
            num_constraints = meta.get("num_constraints")
            require(type(num_vars) is int and type(num_constraints) is int,
                    "capacity_metadata")
            if num_vars <= MAX_VARIABLES and num_constraints <= MAX_CONSTRAINTS:
                continue
            problem_id = f"text2opt_{family}_{path.stem}"
            public = _payload(problem_id, text, instance_data)
            require(input_shape_issues(public) == [], "packet_shape")
            normalized_sha = sha(_normalized(text).encode("utf-8"))
            rows.append({
                "schema": VERSION + "-record",
                "id": problem_id,
                "family": family,
                "source_file": str(path.relative_to(source)),
                "source_file_sha256": sha(raw),
                "public_payload": public,
                "public_payload_sha256": digest(public),
                "public_text_sha256": sha(text.encode("utf-8")),
                "normalized_public_text_sha256": normalized_sha,
                "instance_data_sha256": digest(instance_data),
                "non_outcome_metadata": {
                    "problem_type": meta.get("problem_type"),
                    "optimization_type": meta.get("optimization_type"),
                    "num_vars": num_vars,
                    "num_constraints": num_constraints,
                    "prompt_tokens_with_data": meta.get("prompt_tokens_with_data"),
                    "prompt_tokens_without_data": meta.get("prompt_tokens_without_data"),
                },
                "overlaps_prepared_183": normalized_sha in old_hashes,
            })
    rows.sort(key=lambda row: row["id"])
    require(len(rows) == 38 and
            Counter(row["family"] for row in rows) == {"rcpsp": 13, "vrptw": 25},
            "cohort_size")
    for key in ("id", "source_file_sha256", "public_payload_sha256",
                "public_text_sha256", "normalized_public_text_sha256"):
        require(len({row[key] for row in rows}) == 38, "unique_" + key)
    require(not any(row["overlaps_prepared_183"] for row in rows), "prior_overlap")
    return {
        "schema": VERSION + "-private-bundle",
        "source_revision": SOURCE_REVISION,
        "selection_rule": "family in {rcpsp,vrptw} and (num_vars > 96 or num_constraints > 192)",
        "selection_uses_outcomes": False,
        "records": rows,
        "claim_boundary": {
            "source_files_contain_reference_fields": True,
            "reference_values_used_or_copied": False,
            "source_variables_or_constraints_used_or_copied": False,
            "common_information_for_every_method": True,
            "private_body_bearing_bundle": True,
        },
    }


def _failure_code(exc):
    value = str(exc)
    if value.startswith("template_parse_missing:"):
        return "template_parse_missing"
    if value == "unsupported_or_ambiguous_text2opt_template_family":
        return value
    if value == "vrptw_route_enumeration_capacity":
        return value
    return "unexpected_static_compiler_failure"


def _static_readiness(bundle):
    compiled = []
    failures = Counter()
    family = {name: {"planned": 0, "compiled": 0, "failed": 0}
              for name in FAMILIES}
    for row in bundle["records"]:
        family[row["family"]]["planned"] += 1
        try:
            model = compile_template_problem(row["public_payload"])
        except (ValueError, Stopped) as exc:
            failures[_failure_code(exc)] += 1
            family[row["family"]]["failed"] += 1
            continue
        variables = len(model["variables"])
        constraints = len(model["constraints"])
        nonzeros = sum(len(item["coefficients"]) for item in model["constraints"])
        serialized_bytes = len(canonical(model).encode("utf-8"))
        metrics = {
            "variables": variables,
            "constraints": constraints,
            "nonzeros": nonzeros,
            "serialized_bytes": serialized_bytes,
        }
        require(all(metrics[key] <= RESOURCE_CAPS[key] for key in RESOURCE_CAPS),
                "static_resource_cap")
        compiled.append({
            "id": row["id"],
            "model_sha256": digest(model),
            "metrics": metrics,
            "source_counts_match": (
                variables == row["non_outcome_metadata"]["num_vars"] and
                constraints == row["non_outcome_metadata"]["num_constraints"]
            ),
        })
        family[row["family"]]["compiled"] += 1
    require(len(compiled) + sum(failures.values()) == 38, "readiness_denominator")
    maximum = {key: max(row["metrics"][key] for row in compiled)
               for key in RESOURCE_CAPS}
    return {
        "compiler": "text2opt-template-compiler-v10",
        "planned_denominator": 38,
        "compiled": len(compiled),
        "failed": sum(failures.values()),
        "source_count_exact_matches": sum(row["source_counts_match"] for row in compiled),
        "failure_codes": dict(sorted(failures.items())),
        "families": family,
        "maximum_compiled_resources": maximum,
        "resource_caps": dict(RESOURCE_CAPS),
        "compiled_bindings": compiled,
        "solver_calls": 0,
    }


def build_public_manifest(root, bundle):
    """Build a body-free, content-addressed readiness record."""

    root = Path(root).resolve()
    expected = build_private_bundle(root)
    require(type(bundle) is dict and canonical(bundle) == canonical(expected),
            "bundle_identity")
    estimand_raw = _read(root / ESTIMAND_AUDIT)
    bindings = [{
        "id": row["id"],
        "family": row["family"],
        "source_file_sha256": row["source_file_sha256"],
        "public_payload_sha256": row["public_payload_sha256"],
        "public_text_sha256": row["public_text_sha256"],
        "instance_data_sha256": row["instance_data_sha256"],
    } for row in bundle["records"]]
    return {
        "schema": VERSION + "-public-readiness",
        "status": "common_packets_ready_method_dispatch_not_ready",
        "source_revision": SOURCE_REVISION,
        "estimand_audit_sha256": sha(estimand_raw),
        "private_bundle_sha256": digest(bundle),
        "cohort": {
            "records": 38,
            "rcpsp": 13,
            "vrptw": 25,
            "unique_ids": 38,
            "unique_source_files": 38,
            "unique_public_payloads": 38,
            "overlap_with_prepared_183": 0,
        },
        "packet_contract": {
            "profile": BASE_PROFILE,
            "natural_language_description": True,
            "structured_instance_data": True,
            "same_payload_hash_for_every_method": True,
            "reference_values_present": False,
            "source_model_annotations_present": False,
        },
        "packet_bindings": bindings,
        "static_compiler_readiness": _static_readiness(bundle),
        "decision": {
            "common_atomic_fact_packet_ready": True,
            "current_method_skills_ready": False,
            "external_serializers_ready": False,
            "native_and_equal_budget_caps_ready": False,
            "outcome_blind_custody_ready": False,
            "ready_to_dispatch": False,
        },
        "execution": {
            "api_calls": 0,
            "model_calls": 0,
            "solver_calls": 0,
            "native_or_vm_calls": 0,
        },
        "claim_boundary": {
            "packet_readiness_only": True,
            "benchmark_accuracy_computed": False,
            "method_superiority_claimed": False,
            "static_compile_failure_is_incorrect_in_future_denominator": True,
        },
    }


def _write_new(path, value):
    path = Path(path)
    require(path.parent.is_dir() and not path.exists() and not path.is_symlink(),
            "output_exists_or_parent")
    raw = canonical(value).encode("utf-8")
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL |
             getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            require(written > 0, "output_write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def publish_values(private_path, public_path, bundle, manifest):
    require(type(bundle) is dict and type(manifest) is dict, "publish_values")
    private_path, public_path = Path(private_path), Path(public_path)
    require(not private_path.exists() and not public_path.exists(), "output_exists")
    _write_new(private_path, bundle)
    _write_new(public_path, manifest)


__all__ = [
    "FAMILIES", "VERSION", "build_private_bundle", "build_public_manifest",
    "publish_values",
]
