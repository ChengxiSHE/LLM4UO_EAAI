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
