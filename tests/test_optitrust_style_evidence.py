import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text())


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class OptiTrustStyleEvidenceTests(unittest.TestCase):
    def test_indexed_closure_separates_transport_recovery_from_method_failure(self):
        value = load("experiments/optitrust_indexed_closure_20261016.json")
        self.assertEqual(value["status"], "closed_with_boundary_no_common38_dispatch")
        self.assertTrue(value["conclusion"]["infrastructure_closed"])
        self.assertFalse(value["conclusion"]["method_feasibility_passed"])
        self.assertFalse(value["conclusion"]["full_common38_dispatched"])
        self.assertEqual(value["conclusion"]["capacity_gate_passed_version"], "v4")
        self.assertEqual(
            value["aggregate_new_indexed_execution"],
            {
                "common38_accuracy_scored": False,
                "logical_requests": 52,
                "new_solver_calls": 0,
                "physical_attempts": 59,
                "reference_answers_loaded": False,
                "retry_attempts": 7,
            },
        )
        self.assertEqual(
            [item["passed"] for item in value["feasibility_sequence"]],
            [False, False],
        )
        self.assertEqual(
            [item["infrastructure_unavailable"] for item in value["feasibility_sequence"]],
            [0, 0],
        )
        self.assertEqual(
            [item["selected_consensus_cells"] for item in value["feasibility_sequence"]],
            [0, 0],
        )

    def test_synthesis_marks_zero_scoreable_outcomes_as_not_estimable(self):
        value = load("experiments/fresh_common38_optitrust_style_synthesis_20261016.json")
        self.assertEqual(value["status"], "complete_unscoreable_adapter_capacity_failure")
        self.assertEqual(value["method"], "OptiTrust-style-safe-sidecar")
        self.assertEqual(value["cohort"], {"planned": 38, "scoreable": 0})
        self.assertEqual(value["outcomes"]["infrastructure_unavailable"], 38)
        self.assertEqual(value["failure_localization"]["terminal_slot_distribution"], {
            "5": 35,
            "6": 1,
            "9": 2,
        })
        self.assertEqual(value["paired_against_current"]["status"], "not_estimable")
        self.assertNotIn("accuracy", value["paired_against_current"])
        self.assertNotIn("p_value", json.dumps(value["paired_against_current"]))
        self.assertFalse(value["claim_boundary"]["official_optitrust_reproduction"])
        self.assertFalse(value["claim_boundary"]["method_accuracy_estimated"])

    def test_external_ledger_keeps_official_and_paper_based_rows_separate(self):
        ledger = load("experiments/external_baseline_evidence_ledger_20261014.json")
        official = ledger["baselines"]["optitrust"]
        sensitivity = ledger["baselines"]["optitrust_style_safe_sidecar_v1"]
        self.assertEqual(
            official["official_reproduction_status"],
            "not_yet_reproducible_from_verified_artifact",
        )
        self.assertEqual(sensitivity["classification"], "paper_based_sensitivity")
        self.assertEqual(sensitivity["scoreable_outcomes"], 0)
        self.assertEqual(sensitivity["infrastructure_unavailable"], 38)
        self.assertFalse(sensitivity["official_reproduction"])
        self.assertEqual(
            sensitivity["synthesis_sha256"],
            sha256(sensitivity["synthesis"]),
        )

    def test_manifest_binds_result_audit_synthesis_and_boundary(self):
        manifest = load("experiments/paper_evidence_manifest_20261015.json")
        entry = manifest["headline_evidence"]["optitrust_style_safe_sidecar_v1"]
        for path_key, hash_key in (
            ("result", "result_sha256"),
            ("audit", "audit_sha256"),
            ("synthesis", "synthesis_sha256"),
        ):
            self.assertEqual(entry[hash_key], sha256(entry[path_key]))
        self.assertEqual(entry["assertions"]["cohort.scoreable"], 0)
        self.assertEqual(
            entry["assertions"]["paired_against_current.status"],
            "not_estimable",
        )
        self.assertIn("not an accuracy estimate", entry["boundary"])

    def test_manifest_and_manuscript_bind_the_indexed_negative_preflight(self):
        manifest = load("experiments/paper_evidence_manifest_20261015.json")
        entry = manifest["headline_evidence"]["optitrust_style_indexed_closure"]
        for path_key, hash_key in (
            ("artifact", "sha256"),
            ("human_report", "human_report_sha256"),
        ):
            self.assertEqual(entry[hash_key], sha256(entry[path_key]))
        self.assertTrue(entry["assertions"]["conclusion.infrastructure_closed"])
        self.assertFalse(entry["assertions"]["conclusion.method_feasibility_passed"])
        self.assertFalse(entry["assertions"]["conclusion.full_common38_dispatched"])
        self.assertFalse(
            entry["assertions"]["aggregate_new_indexed_execution.common38_accuracy_scored"]
        )

        manuscript = (ROOT / "manuscript/MANUSCRIPT_DRAFT.md").read_text()
        supplement = (ROOT / "manuscript/SUPPLEMENTARY_REPRODUCIBILITY.md").read_text()
        evidence = (ROOT / "manuscript/MANUSCRIPT_EVIDENCE_AUDIT.md").read_text()
        for text in (manuscript, supplement, evidence):
            self.assertIn("OptiTrust-style indexed adapter", text)
            self.assertIn("method gate", text)
            self.assertIn("no accuracy", text)

    def test_goal_and_paper_preserve_the_official_artifact_boundary(self):
        goal = load("experiments/goal_completion_audit_20261015.json")
        g06 = next(item for item in goal["requirements"] if item["id"] == "G06")
        self.assertEqual(g06["status"], "external_unavailable")
        self.assertIn("paper-based sensitivity", g06["supported_claim"])
        self.assertIn("zero scoreable", g06["supported_claim"])
        manuscript = (ROOT / "manuscript/MANUSCRIPT_DRAFT.md").read_text()
        evidence = (ROOT / "manuscript/MANUSCRIPT_EVIDENCE_AUDIT.md").read_text()
        roadmap = (ROOT / "docs/TOP_CONFERENCE_METHOD_ROADMAP.md").read_text()
        for text in (manuscript, evidence, roadmap):
            self.assertIn("OptiTrust-style-safe-sidecar", text)
            self.assertIn("not an accuracy estimate", text)


if __name__ == "__main__":
    unittest.main()
