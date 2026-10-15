#!/usr/bin/env python3
"""Export the confirmed human-seeded V9 compiler as typed generation-zero skills."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.schema import digest
from llm4or.verified_skill_library import skill_sha256, validate_skill_package


OUTPUT = ROOT / "experiments/v9_generation_zero_skill_library.json"
COMPILER = ROOT / "llm4or/text2opt_template_compiler.py"
DEVELOPMENT = ROOT / "results/v9_template_development_evaluation.json"


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


DESIGNS = {
    "transportation": {
        "required_all": ["cost matrix", "source\\dest"],
        "contract": "Linear transportation with explicit source supplies, destination demands, and a rectangular cost matrix.",
        "invariants": ["cost matrix dimensions match sources and destinations", "all flows are nonnegative"],
        "test": ("scale_cost", "multiply every unit cost by a positive scalar", "optimal objective scales by that scalar"),
    },
    "jssp": {
        "required_all": ["number of jobs:", "machine assignments", "processing times"],
        "contract": "Job-shop scheduling with one ordered operation per listed job step and unary machine capacity.",
        "invariants": ["machine and processing-time rows have equal shapes", "every operation is scheduled exactly once"],
        "test": ("permute_jobs", "permute complete job rows", "optimal makespan is unchanged"),
    },
    "disaster_response": {
        "required_all": ["risk costs (depot x unit)", "fleet parameters:", "penalty costs per unit shortage"],
        "contract": "Multi-day disaster-response allocation with fleet, depot, demand, shortage, risk, and transport relations.",
        "invariants": ["all depot-unit-day tensors agree", "shortage and delivery jointly cover demand"],
        "test": ("permute_days", "permute complete day-indexed data blocks", "total optimal objective is unchanged"),
    },
    "modified_facility_location": {
        "required_all": ["facility capacities", "customer demands", "transport rate"],
        "contract": "Capacitated facility location with opening, assignment, demand, capacity, fixed-cost, and distance-rate terms.",
        "invariants": ["each customer is assigned exactly once", "assigned demand respects opened-facility capacity"],
        "test": ("permute_customers", "permute all customer-indexed rows and columns", "optimal objective is unchanged"),
    },
    "vrptw": {
        "required_all": ["customer time windows", "vehicle capacity", "fixed", "cost per vehicle"],
        "contract": "Capacitated vehicle routing with customer time windows, service times, depot returns, fixed vehicle cost, and travel cost.",
        "invariants": ["each customer is served exactly once", "every selected route respects capacity and time windows"],
        "test": ("permute_customers", "consistently relabel customer-indexed data", "optimal objective is unchanged"),
    },
    "rcpsp": {
        "required_all": ["execution mode durations", "resource requirements per mode", "precedence dependencies"],
        "contract": "Multi-mode resource-constrained project scheduling with renewable capacities and precedence lags.",
        "invariants": ["one execution mode is selected per activity", "selected modes respect resources and precedence"],
        "test": ("permute_resources", "consistently permute resource columns and capacities", "optimal makespan is unchanged"),
    },
}


def main():
    compiler_sha256 = file_sha256(COMPILER)
    development_sha256 = file_sha256(DEVELOPMENT)
    registry = {f"text2opt.{family}.v9": compiler_sha256 for family in DESIGNS}
    packages = []
    for family, design in DESIGNS.items():
        implementation_id = f"text2opt.{family}.v9"
        test_id, transform, expectation = design["test"]
        proposal = {
            "family": family, "recognizer_required_all": design["required_all"],
            "implementation_id": implementation_id, "semantic_contract": design["contract"],
            "invariants": design["invariants"], "metamorphic_test": design["test"],
        }
        package = {
            "schema": "verified-typed-skill-v1",
            "skill_id": "text2opt_" + family,
            "version": 1,
            "parent_sha256": None,
            "family": family,
            "recognizer": {"kind": "casefolded_literal_v1",
                           "required_all": design["required_all"],
                           "required_any": [], "forbidden_any": []},
            "implementation": {"id": implementation_id, "sha256": compiler_sha256},
            "contracts": {"input_schema": "public-problem-v1",
                          "output_schema": "trusted-solve-result-v1",
                          "semantic_contract": design["contract"]},
            "invariants": design["invariants"],
            "metamorphic_tests": [{"id": test_id, "transform": transform,
                                    "expectation": expectation}],
            "limits": {"max_input_bytes": 1_000_000, "max_variables": 20_000,
                       "max_constraints": 50_000, "wall_seconds": 30},
            "fallback": "unchanged_backend",
            "provenance": {"proposer": "human_seed_v9",
                           "development_manifest_sha256": development_sha256,
                           "proposal_sha256": digest(proposal)},
        }
        packages.append(validate_skill_package(package, registry))
    packages.sort(key=lambda item: item["skill_id"])
    package_hashes = {item["skill_id"]: skill_sha256(item, registry) for item in packages}
    manifest = {
        "schema": "verified-skill-library-manifest-v1",
        "version": "v9-generation-zero-v1",
        "role": "human_seeded_generation_zero_not_automatic_rsi",
        "compiler_source": "llm4or/text2opt_template_compiler.py",
        "compiler_source_sha256": compiler_sha256,
        "development_evidence": "results/v9_template_development_evaluation.json",
        "development_evidence_sha256": development_sha256,
        "trusted_implementations": registry,
        "packages": packages,
        "package_sha256": package_hashes,
        "claim_boundary": "This export binds the confirmed static V9 implementation. It is not an automatically induced generation.",
    }
    manifest["library_sha256"] = digest(manifest)
    OUTPUT.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "skills": len(packages),
                      "library_sha256": manifest["library_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
