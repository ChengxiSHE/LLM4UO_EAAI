"""Answer-free canonical manifests for the frozen TSP/OR-Debug library.

The builders below serialize already frozen behavior.  They do not import the
referenced implementations, read benchmark bodies, score outputs, or authorize
execution.  Every first-party byte identity and public aggregate evidence
identity is checked by :mod:`llm4or.content_addressed_manifests`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from .content_addressed_manifests import (
    attach_content_digest,
    canonical_manifest_bytes,
    load_content_addressed_manifest,
    publish_content_addressed_manifest,
    validate_library_manifest,
    validate_skill_manifest,
)


CODE_PINS = {
    "llm4or/gurobi_cli_solver.py": "59bc10e45901908c0782767dfc70fbf3bd248af6c671d0c62b396bdfd295e126",
    "llm4or/milp_schema.py": "0900e2e5d9e4669b5067209ead0d3ab221e6b78bbdd5f5ed120670f452703556",
    "llm4or/milp_solver.py": "2a30ce4668ab04ad823f9b93adfabc291f4e76ba0f80e9614d21540d20522858",
    "llm4or/mixed_skill_execution.py": "b9928572da49960db693c55ce4fe631462ce2660cd877b9d691016c3aabfae83",
    "llm4or/mixed_skill_router.py": "950c817a60f87a8fcdbb024bab84895b4b7e547ae772f285f00bbe0977e72a83",
    "llm4or/or_debug_evolved_skill.py": "3eb6d961313b34fd57ad0d13309e716379e11b0d46dd254914de64fad85b5e93",
    "llm4or/or_debug_gurobi.py": "97691082bfe6ba48bdfdedf33f8df5abcbdb8baf44cd59c72d96f7752cb9cf8b",
    "llm4or/or_debug_iis_control.py": "7b911b667ee71272811ee5ee6980e13811703468d3f948b2ac8b16021581124e",
    "llm4or/or_debug_mps.py": "f598e37dce8d133c458258d5c87a30746bb7b66ffe25401e15b3b37b7be1ec9c",
    "llm4or/or_debug_mps_inspect.py": "389962c1aaa58fdd3b5c2aafe9ef910ae428fafd2084def1a3c6ab118cc42eaa",
    "llm4or/or_debug_public_runner.py": "60049e80ee3e2dd1c2d133cfa127461983de9a3321a49bd69f6acf41a80318be",
    "llm4or/schema.py": "82a63e82f4cf72b99f4f58be2ff5ece44ad8b8ae8c08c0aa440d8615d6d9e428",
    "llm4or/tsp_constraint_skill.py": "2bb4712061c112c155678f00d301519edaaf40be978a893585f1e86f4a1256df",
    "llm4or/tsp_constraint_skill_scalable.py": "7130d57f2f6821720e5002c4ad6841ee6cd5df7b1aca0871338b4165eec19653",
    "llm4or/tsp_graph_exact.py": "4b1f68d16e89af67370669b6812c5b5a0ca380ee5068ac2244f093987364f4b1",
    "llm4or/tsp_public_graph.py": "46f7eb934b84ae72595c8813dfaf838bbec37d31e891bef733f44c7777ffd93e",
    "llm4or/tsp_scalable_exact.py": "8bcf804cb47430fb014bee4ad8695d7cdc42699fff8dff654b9c27287317b5bc",
    "llm4or/tsp_static_controller.py": "0f1368b13891473019de4a1829649ca80b3a54d6588c9a2900d889dbd9609d63",
    "llm4or/tsp_typed_graph.py": "1703c0e79251b3663ae1d368857626e9b5ca70f327e0478d6aa53a3c4708ba2b",
}

EVIDENCE_PINS = {
    "reproduction/current_library_provenance_v1.json": "fb37602002764675743c9a08f1e09cf25a9e008f6cbd69912755a319a8619b57",
    "results/mixed_skill_confirmation_public_audit_v3_20261015.json": "3c9b8700639cfe5599fc76b18cca4318b14d4b0865fb5bd343f5c0d26fead08f",
    "results/or_debug_group_endpoint_sensitivity_audit_20261015.json": "613fd34cd25a844813c9decf22e800a4c99eba651d25b887b50d897327e33a33",
    "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json": "7f83555e8b81ff15bad510b95bf7e2617d87bb139786777407704a55e10a70ca",
    "results/tsp_constraint_confirmation_root_closure_20261014.json": "0a0aef6aad14e720f537c3201b5cc585b0177c0a05150a18d0300f3e498c437d",
}

HISTORICAL_IDENTITY_PINS = {
    "or_debug_confirmation_evaluation_plan": {
        "path": "experiments/or_debug_confirmation_evaluation_plan_20261014.json",
        "sha256": "5f20fbcd09289a37f9f38d06c71938d6a202f39a3ec5f01547f6b2a4d19bd1b7",
        "role": "verifier_plan",
    },
    "or_debug_confirmation_plan": {
        "path": "experiments/or_debug_confirmation_plan_20261014.json",
        "sha256": "1e6a75da27cf5e75fe773a12e95b97d56e827080decfe547976aa8bbf924ed79",
        "role": "construction_split",
    },
    "or_debug_promotion_plan": {
        "path": "experiments/or_debug_promotion_plan_20261014.json",
        "sha256": "72badae77d2cda495a0b2f9913d822945b1e275f0f6c0b5b304e1adb6e652059",
        "role": "promotion_decision",
    },
    "tsp_constraint_confirmation_candidate_plan": {
        "path": "experiments/tsp_constraint_confirmation_candidate_plan_20261014.json",
        "sha256": "30befe1f147928c0375f734900f9db4599597e18028607e64ba15475317717e9",
        "role": "construction_split",
    },
    "tsp_constraint_confirmation_evaluation_plan": {
        "path": "experiments/tsp_constraint_confirmation_evaluation_plan_20261014.json",
        "sha256": "86e7a399e2c3b96bf1880461066b9fb3027df3631c8b4787304111c14f79050a",
        "role": "verifier_plan",
    },
    "tsp_constraint_promotion_evaluation_plan": {
        "path": "experiments/tsp_constraint_promotion_evaluation_plan_20261014.json",
        "sha256": "76b6e210b3f5ce0a2d687b63db56f78100eaf3a60146698121ee3fca50e87274",
        "role": "endpoint_plan",
    },
    "tsp_constraint_skill_promotion_root_closure": {
        "path": "results/tsp_constraint_skill_promotion_root_closure_20261014.json",
        "sha256": "08e2afa1e961c90b8185d6a5b2bb1ef2a6a9bef18952e475c1c9adbf6b77ff8c",
        "role": "promotion_decision",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_pins(root: Path, pins: dict[str, str]) -> None:
    for path, expected in pins.items():
        if _sha256(root / path) != expected:
            raise ValueError(f"current_manifest_pin_mismatch:{path}")


def _load_historical_identities(root: Path) -> dict[str, dict[str, str]]:
    registry = json.loads(
        (root / "reproduction/current_library_provenance_v1.json").read_text()
    )
    if registry.get("schema") != "llm4or-current-library-provenance-v1":
        raise ValueError("current_manifest_provenance_schema")
    identities = registry.get("historical_identities")
    if identities != HISTORICAL_IDENTITY_PINS:
        raise ValueError("current_manifest_provenance_identity_mismatch")
    privacy = registry.get("privacy")
    if not isinstance(privacy, dict) or any(privacy.values()):
        raise ValueError("current_manifest_provenance_privacy")
    return identities


def _closure(paths: list[str]) -> list[dict[str, str]]:
    return [{"path": path, "sha256": CODE_PINS[path]} for path in paths]


def _role(interface: str, paths: list[str]) -> dict[str, Any]:
    return {
        "interface": interface,
        "semantic_version": "1.0.0",
        "implementation_closure": _closure(paths),
    }


TSP_PATHS = [
    "llm4or/schema.py",
    "llm4or/tsp_constraint_skill.py",
    "llm4or/tsp_constraint_skill_scalable.py",
    "llm4or/tsp_public_graph.py",
    "llm4or/tsp_typed_graph.py",
    "llm4or/tsp_static_controller.py",
    "llm4or/tsp_graph_exact.py",
    "llm4or/tsp_scalable_exact.py",
    "llm4or/milp_schema.py",
    "llm4or/milp_solver.py",
    "llm4or/gurobi_cli_solver.py",
]

OR_DEBUG_PATHS = [
    "llm4or/or_debug_evolved_skill.py",
    "llm4or/or_debug_mps_inspect.py",
    "llm4or/or_debug_mps.py",
    "llm4or/or_debug_iis_control.py",
    "llm4or/or_debug_public_runner.py",
    "llm4or/or_debug_gurobi.py",
]


def _tsp_skill(historical: dict[str, dict[str, str]]) -> dict[str, Any]:
    return attach_content_digest(
        {
            "schema": "llm4or.skill_manifest.v1",
            "skill_id": "tsp_constraint_xor_v2_scalable",
            "family": "tsp",
            "semantic_version": "2.0.0",
            "guard": _role("llm4or.tsp.guard.v1", ["llm4or/tsp_constraint_skill_scalable.py"]),
            "extractor": _role(
                "llm4or.tsp.extractor.v1",
                [
                    "llm4or/tsp_constraint_skill.py",
                    "llm4or/tsp_constraint_skill_scalable.py",
                    "llm4or/tsp_public_graph.py",
                    "llm4or/tsp_typed_graph.py",
                    "llm4or/tsp_static_controller.py",
                ],
            ),
            "transform": _role(
                "llm4or.tsp.directed_mtz_transform.v1",
                [
                    "llm4or/tsp_constraint_skill.py",
                    "llm4or/tsp_constraint_skill_scalable.py",
                    "llm4or/tsp_scalable_exact.py",
                ],
            ),
            "semantic_verifier": _role(
                "llm4or.tsp.semantic_verifier.v1",
                [
                    "llm4or/tsp_constraint_skill.py",
                    "llm4or/tsp_constraint_skill_scalable.py",
                    "llm4or/tsp_scalable_exact.py",
                ],
            ),
            "resource_checker": _role(
                "llm4or.tsp.resource_checker.v1",
                [
                    "llm4or/tsp_constraint_skill.py",
                    "llm4or/tsp_scalable_exact.py",
                    "llm4or/gurobi_cli_solver.py",
                ],
            ),
            "provenance": {
                "authorship_mode": "human_authored_from_public_development_failures",
                "parent_proposal_sha256": None,
                "construction_split_sha256": historical[
                    "tsp_constraint_confirmation_candidate_plan"
                ]["sha256"],
                "verifier_sha256": historical[
                    "tsp_constraint_confirmation_evaluation_plan"
                ]["sha256"],
                "decision_sha256": historical[
                    "tsp_constraint_skill_promotion_root_closure"
                ]["sha256"],
            },
            "fallback_contract": {
                "target": "frozen_tsp_static_controller",
                "zero_match": "preserve_static_output",
                "multiple_match": "preserve_static_output",
            },
            "semantic_payload": {
                "guard": {
                    "required_public_fields": ["public_text", "question_sha256", "size"],
                    "size_interval": [13, 19],
                    "match_cardinality": "exactly_one_family",
                },
                "extractor": {
                    "typed_fields": [
                        "nodes",
                        "weighted_edges",
                        "forbidden_edge",
                        "exactly_one_edge_pair",
                        "tour_objective",
                        "unit",
                        "quoted_evidence",
                    ],
                    "candidate_binding": "byte_exact_fresh_reextraction",
                },
                "transform": {
                    "backend": "directed_mtz_milp",
                    "obligations": [
                        "hamiltonian_cycle",
                        "exclude_forbidden_edge",
                        "select_exactly_one_declared_edge",
                        "minimize_declared_weight",
                    ],
                },
                "semantic_verifier": {
                    "checks": [
                        "candidate_equals_fresh_extraction",
                        "tour_decodes_over_declared_nodes",
                        "forbidden_edge_absent",
                        "exactly_one_edge_present",
                        "objective_recomputed",
                    ]
                },
                "resource_checker": {
                    "max_nodes": 19,
                    "max_source_bytes": 250000,
                    "max_edge_weight": 1000000000,
                    "max_exact_scaled_integer": 4503599627370495,
                },
                "fallback": {
                    "target": "frozen_tsp_static_controller",
                    "policy": "fail_closed_preserve_static_output",
                },
            },
            "implementation_closure": _closure(TSP_PATHS),
            "claim_boundary": [
                "Authored skill for the frozen TSP constraint grammar and size interval 13 through 19.",
                "Does not establish arbitrary natural-language equivalence, automatic acquisition or unrestricted size generalization.",
            ],
        }
    )


def _or_debug_skill(historical: dict[str, dict[str, str]]) -> dict[str, Any]:
    return attach_content_digest(
        {
            "schema": "llm4or.skill_manifest.v1",
            "skill_id": "or_debug_typed_repair_v1",
            "family": "or_debug",
            "semantic_version": "1.0.0",
            "guard": _role("llm4or.or_debug.guard.v1", ["llm4or/or_debug_evolved_skill.py"]),
            "extractor": _role(
                "llm4or.or_debug.extractor.v1",
                [
                    "llm4or/or_debug_evolved_skill.py",
                    "llm4or/or_debug_mps_inspect.py",
                    "llm4or/or_debug_gurobi.py",
                ],
            ),
            "transform": _role(
                "llm4or.or_debug.mps_patch_transform.v1",
                ["llm4or/or_debug_mps.py"],
            ),
            "semantic_verifier": _role(
                "llm4or.or_debug.semantic_verifier.v1",
                [
                    "llm4or/or_debug_evolved_skill.py",
                    "llm4or/or_debug_public_runner.py",
                    "llm4or/or_debug_gurobi.py",
                ],
            ),
            "resource_checker": _role(
                "llm4or.or_debug.resource_checker.v1",
                ["llm4or/or_debug_public_runner.py", "llm4or/or_debug_gurobi.py"],
            ),
            "provenance": {
                "authorship_mode": "controller_authored_from_public_development_evidence",
                "parent_proposal_sha256": None,
                "construction_split_sha256": historical["or_debug_confirmation_plan"][
                    "sha256"
                ],
                "verifier_sha256": historical[
                    "or_debug_confirmation_evaluation_plan"
                ]["sha256"],
                "decision_sha256": historical["or_debug_promotion_plan"]["sha256"],
            },
            "fallback_contract": {
                "target": "frozen_generic_iis_control",
                "zero_match": "preserve_control_output",
                "multiple_match": "preserve_control_output",
            },
            "semantic_payload": {
                "guard": {
                    "required_public_fields": ["model_file", "mps_sha256", "problem_nl"],
                    "error_types": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],
                    "source_classes": ["lp", "mip"],
                    "match_cardinality": "exactly_one_error_type_and_source_class",
                },
                "extractor": {
                    "typed_fields": [
                        "public_error_type",
                        "source_class",
                        "normalized_mps_structure",
                        "fresh_iis_evidence",
                    ],
                    "evidence_policy": "public_fields_plus_public_mps_plus_fresh_solver_iis",
                },
                "transform": {
                    "operations": [
                        "remove_constraint",
                        "set_coefficient",
                        "set_constraint_rhs",
                        "set_constraint_sense",
                        "set_variable_domain",
                        "set_variable_lower_bound",
                    ],
                    "execution": "inert_finite_dsl_then_mps_patch",
                },
                "semantic_verifier": {
                    "checks": [
                        "unique_public_error_type",
                        "unique_executable_candidate",
                        "source_mps_hash_matches",
                        "patched_mps_hash_recorded",
                        "frozen_endpoint_applied_after_public_execution",
                    ]
                },
                "resource_checker": {
                    "max_mps_bytes": 1000000,
                    "solver_threads": 1,
                    "solver_timeout_seconds": 15,
                    "wall_timeout_seconds": 25,
                },
                "fallback": {
                    "target": "frozen_generic_iis_control",
                    "policy": "fail_closed_preserve_control_output",
                },
            },
            "implementation_closure": _closure(OR_DEBUG_PATHS),
            "claim_boundary": [
                "Authored typed repair policy for the frozen OR-Debug error and source classes.",
                "Corrected-primary and released-primary endpoints remain separate; no unrestricted repair or automatic acquisition claim.",
            ],
        }
    )


def build_current_manifest_set(root: Path, skill_directory: Path) -> dict[str, Any]:
    """Build and validate the current two-skill genesis library in memory."""

    root = Path(root)
    _verify_pins(root, CODE_PINS)
    _verify_pins(root, EVIDENCE_PINS)
    historical = _load_historical_identities(root)
    skill_directory = PurePosixPath(Path(skill_directory).as_posix())
    if skill_directory.is_absolute() or ".." in skill_directory.parts:
        raise ValueError("current_manifest_skill_directory")
    skills = {
        "or_debug": _or_debug_skill(historical),
        "tsp": _tsp_skill(historical),
    }
    for skill in skills.values():
        validate_skill_manifest(skill, root)
    ordered = sorted(skills.values(), key=lambda item: (item["family"], item["skill_id"]))
    library = attach_content_digest(
        {
            "schema": "llm4or.library_manifest.v1",
            "library_version": "tsp-or-debug-frozen-v1",
            "parent_library_sha256": None,
            "rollback_library_sha256": None,
            "skills": [
                {
                    "family": skill["family"],
                    "skill_id": skill["skill_id"],
                    "manifest_sha256": skill["content_sha256"],
                    "path": (skill_directory / f"{skill['content_sha256']}.json").as_posix(),
                }
                for skill in ordered
            ],
            "router": {
                "interface": "llm4or.mixed_public_router.v1",
                "semantic_version": "1.0.0",
                "implementation_closure": _closure(
                    ["llm4or/mixed_skill_router.py", "llm4or/mixed_skill_execution.py"]
                ),
                "semantic_payload": {
                    "decision_rule": "exactly_one_public_guard",
                    "routes": [
                        "or_debug_typed_repair_v1",
                        "tsp_constraint_xor_v2_scalable",
                    ],
                    "zero_match": "abstain_and_preserve_family_control",
                    "multiple_match": "abstain_and_preserve_family_control",
                },
                "exact_match_policy": "exactly_one",
                "zero_match_fallback": "abstain_and_preserve_family_control",
                "multiple_match_fallback": "abstain_and_preserve_family_control",
            },
            "verifier_closure": _closure(
                [
                    "llm4or/tsp_constraint_skill.py",
                    "llm4or/tsp_constraint_skill_scalable.py",
                    "llm4or/tsp_scalable_exact.py",
                    "llm4or/or_debug_evolved_skill.py",
                    "llm4or/or_debug_public_runner.py",
                    "llm4or/or_debug_gurobi.py",
                ]
            ),
            "endpoint_identities": [
                {
                    "endpoint_id": "or_debug_corrected_primary",
                    "schema": "llm4or-release-or-debug-evaluation-projection-v1",
                    "plan_sha256": historical[
                        "or_debug_confirmation_evaluation_plan"
                    ]["sha256"],
                    "evidence_sha256": EVIDENCE_PINS[
                        "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json"
                    ],
                },
                {
                    "endpoint_id": "tsp_constraint_confirmation",
                    "schema": "tsp-constraint-confirmation-root-closure-v1",
                    "plan_sha256": historical[
                        "tsp_constraint_promotion_evaluation_plan"
                    ]["sha256"],
                    "evidence_sha256": EVIDENCE_PINS[
                        "results/tsp_constraint_confirmation_root_closure_20261014.json"
                    ],
                },
            ],
            "promotion_decision": {
                "status": "genesis",
                "decision_sha256": EVIDENCE_PINS[
                    "results/mixed_skill_confirmation_public_audit_v3_20261015.json"
                ],
            },
            "accepted_ledger_refs": [
                {
                    "path": "results/mixed_skill_confirmation_public_audit_v3_20261015.json",
                    "sha256": EVIDENCE_PINS[
                        "results/mixed_skill_confirmation_public_audit_v3_20261015.json"
                    ],
                },
                {
                    "path": "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json",
                    "sha256": EVIDENCE_PINS[
                        "results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json"
                    ],
                },
                {
                    "path": "results/tsp_constraint_confirmation_root_closure_20261014.json",
                    "sha256": EVIDENCE_PINS[
                        "results/tsp_constraint_confirmation_root_closure_20261014.json"
                    ],
                },
            ],
            "rejected_ledger_refs": [],
            "release_boundary": [
                "Only first-party implementation hashes and body-free aggregate evidence are embedded.",
                "External Gurobi and separately acquired benchmark sources remain disclosed dependencies rather than bundled code.",
            ],
            "claim_boundary": [
                "The genesis manifest names the already frozen TSP and OR-Debug behaviors; it creates no new accuracy result.",
                "Mixed identity is retrospective composition, not learned routing or unrestricted distribution-shift evidence.",
            ],
        }
    )
    validate_library_manifest(
        library,
        root,
        {skill["content_sha256"]: skill for skill in skills.values()},
    )
    return {"skills": skills, "library": library}


def publish_current_manifest_set(
    root: Path, base_directory: Path, *, check: bool
) -> dict[str, Any]:
    """Publish once, or check byte-identical materialization without replacement."""

    root = Path(root)
    base_directory = Path(base_directory)
    skill_directory = base_directory / "skills"
    library_directory = base_directory / "libraries"
    manifest_set = build_current_manifest_set(root, skill_directory)
    skills_by_digest = {
        skill["content_sha256"]: skill for skill in manifest_set["skills"].values()
    }
    skill_paths = [
        skill_directory / f"{skill['content_sha256']}.json"
        for skill in sorted(
            manifest_set["skills"].values(), key=lambda item: (item["family"], item["skill_id"])
        )
    ]
    library_path = library_directory / f"{manifest_set['library']['content_sha256']}.json"
    if check:
        for path, skill in zip(
            skill_paths,
            sorted(
                manifest_set["skills"].values(),
                key=lambda item: (item["family"], item["skill_id"]),
            ),
        ):
            loaded = load_content_addressed_manifest(path, root, kind="skill")
            if canonical_manifest_bytes(loaded) != canonical_manifest_bytes(skill):
                raise ValueError(f"current_manifest_check_mismatch:{path}")
        loaded_library = load_content_addressed_manifest(
            library_path,
            root,
            kind="library",
            skill_manifests=skills_by_digest,
        )
        if canonical_manifest_bytes(loaded_library) != canonical_manifest_bytes(
            manifest_set["library"]
        ):
            raise ValueError("current_library_manifest_check_mismatch")
    else:
        for skill in sorted(
            manifest_set["skills"].values(), key=lambda item: (item["family"], item["skill_id"])
        ):
            publish_content_addressed_manifest(
                skill, skill_directory, root, kind="skill"
            )
        publish_content_addressed_manifest(
            manifest_set["library"],
            library_directory,
            root,
            kind="library",
            skill_manifests=skills_by_digest,
        )
    return {
        "skill_paths": [path.as_posix() for path in skill_paths],
        "library_path": library_path.as_posix(),
        "skill_sha256": sorted(skills_by_digest),
        "library_sha256": manifest_set["library"]["content_sha256"],
    }
