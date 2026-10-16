import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from llm4or.release_evidence_reconstruction import (
    ReconstructionError,
    build_release_evidence_report,
    verify_path_hashes,
)


ROOT = Path(__file__).resolve().parents[1]


class ReleaseEvidenceReconstructionTests(unittest.TestCase):
    def test_current_release_evidence_report_closes_layer_a(self):
        report = build_release_evidence_report(ROOT)
        self.assertEqual(report["status"], "passed_credential_free_layer_a")
        self.assertEqual(report["paper_manifest"], {
            "assertions": 732,
            "boundaries": 23,
            "path_hashes": 203,
            "path_hash_mismatches": 0,
        })
        self.assertEqual(report["goal_evidence"]["references"], 256)
        self.assertEqual(report["goal_evidence"]["unique_paths"], 236)
        self.assertEqual(report["goal_evidence"]["mismatches"], 0)
        self.assertEqual(report["citations"]["cited_keys"], 18)
        self.assertEqual(report["citations"]["missing"], [])
        self.assertEqual(report["citations"]["uncited"], [])
        self.assertEqual(report["restricted_sources"]["tracked"], [])
        self.assertTrue(report["current_library"]["identity_reconstruction_passed"])
        self.assertEqual(report["current_library"]["exact_identities"], 2985)
        self.assertFalse(report["safety"]["environment_values_read"])
        self.assertEqual(report["safety"]["api_or_model_calls"], 0)

    def test_path_hash_verifier_fails_closed_on_missing_or_drifted_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "value.txt").write_text("expected")
            with self.assertRaisesRegex(ReconstructionError, "path_hash_mismatch"):
                verify_path_hashes(root, {"value.txt": "0" * 64})
            with self.assertRaisesRegex(ReconstructionError, "path_hash_mismatch"):
                verify_path_hashes(root, {"missing.txt": "0" * 64})

    def test_formulationbench_same_fact_negative_result_is_bound(self):
        result_path = ROOT / "experiments/formulationbench_same_knowledge_result_20261016.json"
        result = json.loads(result_path.read_text())
        self.assertEqual(result["accuracy"]["flat-k"]["correct"], 40)
        self.assertEqual(result["accuracy"]["pck-k"]["correct"], 36)
        self.assertEqual(result["paired"]["corrections"], 7)
        self.assertEqual(result["paired"]["regressions"], 11)
        self.assertFalse(result["primary_gate"]["passed"])
        manifest = json.loads(
            (ROOT / "experiments/paper_evidence_manifest_20261015.json").read_text()
        )
        entry = manifest["headline_evidence"]["formulationbench_same_knowledge_result"]
        self.assertEqual(entry["sha256"], hashlib.sha256(result_path.read_bytes()).hexdigest())

    def test_nlequiv_directional_result_and_terminal_execution_are_bound(self):
        result_path = ROOT / "experiments/nlequiv_skill_paced_result_20261017.json"
        result = json.loads(result_path.read_text())
        self.assertEqual(result["accuracy"]["flat-short"]["correct"], 124)
        self.assertEqual(result["accuracy"]["structured-short"]["correct"], 124)
        self.assertEqual(result["accuracy"]["routed-skill-short"]["correct"], 128)
        self.assertFalse(result["primary_gate"]["passed"])
        audit = json.loads(
            (ROOT / "experiments/nlequiv_skill_paced_terminal_audit_20261017.json").read_text()
        )
        self.assertTrue(all(audit["checks"].values()))
        self.assertEqual(audit["execution"]["physical_attempts"], 452)
        self.assertEqual(audit["execution"]["retry_attempts"], 2)

    def test_mechanism_synthesis_rejects_architecture_only_claim(self):
        synthesis = json.loads(
            (ROOT / "experiments/same_knowledge_mechanism_synthesis_20261017.json").read_text()
        )
        self.assertFalse(
            synthesis["joint_inference"]["architecture_only_accuracy_gain_confirmed"]
        )
        self.assertFalse(synthesis["joint_inference"]["same_fact_structure_gain_confirmed"])
        self.assertFalse(
            synthesis["joint_inference"]["benchmark_specific_complete_system_gains_invalidated"]
        )
        self.assertTrue(
            synthesis["claim_boundary"]["new_confirmatory_claim_requires_independent_endpoint"]
        )

    def test_retailopt_primary_and_label_blind_results_are_bound(self):
        manifest = json.loads(
            (ROOT / "experiments/paper_evidence_manifest_20261015.json").read_text()
        )
        cases = {
            "retailopt190_primary_confirmation": (
                "experiments/retailopt190_short_full_evaluation_projection_v1_20261017.json",
                170, 34, 25, 1,
            ),
            "retailopt190_label_blind_robustness": (
                "experiments/retailopt190_label_blind_evaluation_projection_v1_20261017.json",
                185, 37, 27, 0,
            ),
        }
        for key, (relative, correct, archetypes, corrections, regressions) in cases.items():
            path = ROOT / relative
            value = json.loads(path.read_text())
            self.assertEqual(value["instances"]["knowledge_short"]["correct"], correct)
            self.assertEqual(value["archetypes"]["knowledge_short"]["fully_correct"], archetypes)
            self.assertEqual(value["paired_archetypes"]["corrections"], corrections)
            self.assertEqual(value["paired_archetypes"]["regressions"], regressions)
            self.assertTrue(value["confirmation_gate"]["passed"])
            self.assertEqual(
                manifest["headline_evidence"][key]["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_infrastructure_closure_separates_rate_and_duration_failures(self):
        closure = json.loads(
            (ROOT / "experiments/infrastructure_root_cause_closure_20261017.json").read_text()
        )
        self.assertEqual(
            closure["process_state"]["matching_controller_or_transport_processes"], 0
        )
        self.assertTrue(
            closure["conclusions"]["rate_shaping_was_necessary_and_sufficient_for_nlequiv"]
        )
        self.assertTrue(
            closure["conclusions"]["bounded_output_redesign_was_necessary_for_optitrust_style"]
        )
        self.assertFalse(
            closure["conclusions"]["environment_migration_needed_for_these_incidents"]
        )

    def test_layer_contract_keeps_external_dependencies_separate(self):
        contract = json.loads((ROOT / "reproduction/environment_layers_v1.json").read_text())
        layers = {layer["id"]: layer for layer in contract["layers"]}
        self.assertEqual(
            set(layers),
            {
                "A_evidence_integrity",
                "B_offline_analysis",
                "C_solver_native",
                "D_provider_replay",
                "E_figures",
            },
        )
        evidence_layer = layers["A_evidence_integrity"]
        self.assertEqual(
            evidence_layer["status"],
            "passed_public_v1_0_0_recursive_credential_free_integrity_contract",
        )
        self.assertEqual(evidence_layer["credentials"], "forbidden")
        self.assertEqual(
            evidence_layer["commands"],
            ["python3 scripts/run_public_integrity.py --check"],
        )
        self.assertEqual(evidence_layer["expected_test_count"], 79)
        remote_dependency = evidence_layer["remote_dependency"]
        self.assertTrue(remote_dependency["remote_acquisition_verified"])
        self.assertEqual(remote_dependency["missing_reachable_objects"], 0)
        self.assertTrue(remote_dependency["fsck_full_passed"])
        evidence_audit = json.loads((ROOT / evidence_layer["audit"]["path"]).read_text())
        self.assertEqual(
            hashlib.sha256((ROOT / evidence_layer["audit"]["path"]).read_bytes()).hexdigest(),
            evidence_layer["audit"]["sha256"],
        )
        self.assertEqual(
            evidence_audit["status"],
            "passed_public_history_free_release_clean_clone",
        )
        self.assertTrue(evidence_audit["public_clean_clone"]["submodule_remote_acquisition_verified"])
        self.assertEqual(
            evidence_audit["public_clean_clone"]["submodule_commit"],
            remote_dependency["commit"],
        )
        self.assertFalse(evidence_audit["execution"]["credentials_read"])
        self.assertEqual(evidence_audit["execution"]["api_or_model_calls"], 0)
        provider_layer = layers["D_provider_replay"]
        self.assertEqual(provider_layer["max_concurrency"], 5)
        self.assertEqual(provider_layer["status"], "passed_transport_preflight_replay_external")
        provider_requirements = ROOT / provider_layer["requirements_file"]
        self.assertEqual(
            hashlib.sha256(provider_requirements.read_bytes()).hexdigest(),
            provider_layer["requirements_file_sha256"],
        )
        provider_audit = json.loads((ROOT / provider_layer["audit"]["path"]).read_text())
        self.assertEqual(provider_audit["status"], "passed_provider_transport_preflight")
        self.assertFalse(provider_audit["execution"]["credentials_read"])
        self.assertEqual(provider_audit["execution"]["api_calls"], 0)
        offline_layer = layers["B_offline_analysis"]
        self.assertEqual(offline_layer["status"], "passed_clean_offline_analysis_smoke")
        expected = offline_layer["requirements_file_sha256"]
        observed = hashlib.sha256((ROOT / "requirements-offline.txt").read_bytes()).hexdigest()
        self.assertEqual(observed, expected)
        offline_audit = json.loads((ROOT / offline_layer["audit"]["path"]).read_text())
        self.assertEqual(offline_audit["status"], "passed_clean_offline_analysis_smoke")
        self.assertEqual(
            hashlib.sha256((ROOT / offline_layer["audit"]["path"]).read_bytes()).hexdigest(),
            offline_layer["audit"]["sha256"],
        )
        self.assertFalse(offline_audit["execution"]["credentials_read"])
        self.assertEqual(offline_audit["execution"]["api_calls"], 0)
        self.assertEqual(offline_audit["execution"]["external_solver_calls"], 0)
        solver_layer = layers["C_solver_native"]
        self.assertEqual(
            solver_layer["status"],
            "passed_local_solver_native_smoke_external_license",
        )
        solver_audit = json.loads((ROOT / solver_layer["audit"]["path"]).read_text())
        self.assertEqual(
            solver_audit["status"],
            "passed_local_solver_native_smoke_external_license",
        )
        self.assertEqual(
            hashlib.sha256((ROOT / solver_layer["audit"]["path"]).read_bytes()).hexdigest(),
            solver_layer["audit"]["sha256"],
        )
        self.assertFalse(solver_audit["execution"]["license_file_contents_read_by_verifier"])
        self.assertFalse(solver_audit["execution"]["benchmark_dataset_contents_read"])
        figure_layer = layers["E_figures"]
        self.assertEqual(figure_layer["status"], "passed_clean_temporary_reconstruction")
        figure_requirements = ROOT / figure_layer["requirements_file"]
        self.assertEqual(
            hashlib.sha256(figure_requirements.read_bytes()).hexdigest(),
            figure_layer["requirements_file_sha256"],
        )
        figure_audit = json.loads((ROOT / figure_layer["audit"]["path"]).read_text())
        self.assertEqual(figure_audit["status"], "passed_clean_temporary_figure_reconstruction")
        self.assertEqual(
            hashlib.sha256((ROOT / figure_layer["audit"]["path"]).read_bytes()).hexdigest(),
            figure_layer["audit"]["sha256"],
        )

    def test_author_release_packet_records_all_authorized_decisions(self):
        packet = json.loads(
            (ROOT / "experiments/author_release_decision_packet_20261015.json").read_text()
        )
        self.assertEqual(
            packet["status"],
            "author_approved_publication_verified_doi_pending",
        )
        for item in packet["inputs"]:
            self.assertEqual(
                hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest(),
                item["sha256"],
            )
        self.assertEqual(packet["verified_facts"]["first_party_candidates"], 792)
        self.assertEqual(
            packet["verified_facts"]["historical_nonexclusive_publishers"],
            9,
        )
        self.assertTrue(packet["verified_facts"]["root_license_present"])
        decisions = {row["id"]: row for row in packet["author_decisions"]}
        self.assertEqual(set(decisions), {f"D{index}" for index in range(1, 9)})
        self.assertTrue(all(decision["approved"] for decision in decisions.values()))
        self.assertEqual(
            decisions["D5"]["approval_source"],
            "user_2026-10-15_reaffirmed_2026-10-16",
        )
        execution = packet["execution"]
        self.assertTrue(execution["repository_published"])
        self.assertFalse(execution["doi_reserved"])
        self.assertFalse(execution["credentials_read"])
        self.assertTrue(execution["license_applied"])
        self.assertTrue(execution["publisher_code_changed"])
        self.assertEqual(execution["publisher_adapters"], 9)
        self.assertEqual(execution["api_or_model_calls"], 0)
        self.assertEqual(execution["solver_calls"], 0)
        self.assertIn(
            "DOI will be added after archival deposit",
            packet["ready_to_paste"]["data_availability"],
        )
        self.assertIn(
            "https://github.com/ChengxiSHE/LLM4UO_EAAI",
            packet["ready_to_paste"]["code_availability"],
        )
        self.assertIn("Apache-2.0", packet["ready_to_paste"]["code_availability"])
        self.assertTrue(
            all(
                source["url"].startswith("https://")
                for source in packet["external_primary_sources"]
            )
        )

    def test_atomic_publisher_migration_audit_binds_implementation_and_tests(self):
        path = ROOT / "experiments/atomic_publisher_migration_audit_20261015.json"
        audit = json.loads(path.read_text())
        self.assertEqual(
            audit["status"],
            "passed_d5_shared_atomic_publisher_and_nine_thin_adapters",
        )
        self.assertEqual(audit["historical_producers"]["count"], 9)
        self.assertEqual(audit["historical_producers"]["hash_mismatches"], 0)
        self.assertEqual(audit["adapters"]["count"], 9)
        self.assertEqual(audit["adapters"]["unexpected_output_paths"], 0)
        self.assertEqual(audit["adapters"]["minimal_layer_a_import_ready"], 4)
        self.assertEqual(
            audit["adapters"]["deferred_solver_or_owner_custody_dependency_closure"],
            5,
        )
        self.assertEqual(audit["verification"]["tests"], 22)
        self.assertTrue(audit["verification"]["same_payload_concurrency_passed"])
        self.assertTrue(audit["verification"]["different_payload_conflict_passed"])
        self.assertTrue(audit["verification"]["cross_directory_recovery_passed"])
        self.assertTrue(audit["verification"]["file_and_directory_fsync_passed"])
        for item in audit["bound_files"]:
            if item["path"] in {
                "llm4or/atomic_publisher.py",
                "tests/test_atomic_publisher.py",
            }:
                continue
            self.assertEqual(
                hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest(),
                item["sha256"],
            )
        safety = audit["safety"]
        self.assertEqual(safety["api_or_model_calls"], 0)
        self.assertEqual(safety["solver_calls"], 0)
        self.assertFalse(safety["credentials_read"])

    def test_atomic_publisher_cleanup_race_patch_binds_current_files(self):
        historical_path = (
            ROOT / "experiments/atomic_publisher_migration_audit_20261015.json"
        )
        path = (
            ROOT
            / "experiments/atomic_publisher_concurrent_cleanup_fix_audit_20261016.json"
        )
        audit = json.loads(path.read_text())
        self.assertEqual(audit["status"], "passed_concurrent_cleanup_race_patch")
        self.assertEqual(
            audit["supersedes_evidence_sha256"],
            hashlib.sha256(historical_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(audit["verification"]["tests"], 23)
        self.assertEqual(audit["verification"]["identical_writer_stress_runs"], 300)
        self.assertEqual(audit["verification"]["different_writer_stress_runs"], 300)
        self.assertEqual(audit["verification"]["stress_failures"], 0)
        for item in audit["bound_files"]:
            self.assertEqual(
                hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest(),
                item["sha256"],
            )
        safety = audit["safety"]
        self.assertEqual(safety["api_or_model_calls"], 0)
        self.assertEqual(safety["solver_calls"], 0)
        self.assertFalse(safety["credentials_read"])

    def test_v1_1_1_archival_packet_is_doi_ready_without_claiming_a_doi(self):
        release_audit = json.loads(
            (
                ROOT
                / "experiments/post_publication_release_v1_1_1_audit_20261016.json"
            ).read_text()
        )
        self.assertEqual(
            release_audit["status"],
            "passed_public_v1_1_1_recursive_credential_free_integrity_contract",
        )
        self.assertEqual(release_audit["history"]["tag"], "v1.1.1")
        self.assertEqual(release_audit["history"]["parent_count"], 0)
        self.assertEqual(release_audit["history"]["reachable_commit_count"], 1)
        self.assertEqual(release_audit["public_clone"]["integrity_tests"], 81)
        self.assertTrue(
            release_audit["public_clone"]["remote_submodule_acquisition_verified"]
        )
        self.assertEqual(release_audit["stress"]["failures"], 0)

        packet = json.loads(
            (
                ROOT
                / "experiments/archival_deposit_packet_v1_1_1_20261016.json"
            ).read_text()
        )
        self.assertEqual(
            packet["archive_state"]["status"],
            "ready_for_external_deposit_no_doi",
        )
        self.assertIsNone(packet["archive_state"]["doi"])
        self.assertIsNone(packet["archive_state"]["external_record_id"])
        self.assertEqual(packet["release_identity"]["tag"], "v1.1.1")
        self.assertEqual(packet["release_identity"]["parent_count"], 0)
        self.assertEqual(len(packet["deposit_files"]), 4)
        self.assertEqual(
            len({item["sha256"] for item in packet["deposit_files"]}), 4
        )
        self.assertTrue(
            all(
                item["source_url"].startswith(
                    "https://github.com/ChengxiSHE/LLM4UO_EAAI/releases/download/v1.1.1/"
                )
                for item in packet["deposit_files"]
            )
        )

        availability = json.loads(
            (
                ROOT
                / "experiments/data_code_availability_audit_v5_20261016.json"
            ).read_text()
        )
        self.assertEqual(
            availability["status"],
            "public_v1_1_1_verified_doi_ready_but_pending",
        )
        self.assertFalse(availability["archival_doi_verified"])
        for key in ("deposit_packet", "human_report", "post_publication_audit"):
            item = availability[key]
            self.assertEqual(
                hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest(),
                item["sha256"],
            )

        goal = json.loads(
            (ROOT / "experiments/goal_completion_audit_20261015.json").read_text()
        )
        requirements = {item["id"]: item for item in goal["requirements"]}
        self.assertEqual(requirements["G11"]["status"], "closed")
        self.assertEqual(requirements["G09"]["status"], "closed_with_boundary")
        self.assertEqual(requirements["G13"]["status"], "partial")
        self.assertEqual(
            goal["completion_decision"]["blocking_requirements"],
            ["G13"],
        )

    def test_d5_layer_a_clean_clone_includes_publisher_tests(self):
        audit = json.loads(
            (
                ROOT / "experiments/clean_clone_layer_a_d5_audit_20261015.json"
            ).read_text()
        )
        self.assertEqual(
            audit["status"],
            "passed_no_local_credential_free_layer_a_with_local_complete_submodule_snapshot",
        )
        unittest_command = audit["commands"][0]
        self.assertEqual(unittest_command["tests"], 79)
        self.assertIn("tests.test_atomic_publisher", unittest_command["command"])
        self.assertIn("tests.test_reconstruction_publishers", unittest_command["command"])
        self.assertTrue(audit["clone"]["clean_before"])
        self.assertTrue(audit["clone"]["clean_after"])
        self.assertTrue(audit["solver_submodule"]["complete_object_graph_verified"])
        self.assertFalse(audit["solver_submodule"]["remote_acquisition_verified"])
        self.assertEqual(audit["safety"]["api_or_model_calls"], 0)
        self.assertEqual(audit["safety"]["solver_calls"], 0)
        self.assertFalse(audit["safety"]["credentials_read"])


if __name__ == "__main__":
    unittest.main()
