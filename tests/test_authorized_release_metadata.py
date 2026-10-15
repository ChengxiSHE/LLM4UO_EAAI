import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "experiments" / "author_release_decision_packet_20261015.json"


class AuthorizedReleaseMetadataTests(unittest.TestCase):
    def test_root_licenses_notice_and_citation_are_present(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", license_text)
        self.assertIn("Version 2.0, January 2004", license_text)

        data_license = (ROOT / "LICENSE-DATA").read_text(encoding="utf-8")
        self.assertIn("CC BY 4.0", data_license)
        self.assertIn("author-owned aggregate", data_license)
        self.assertIn("does not cover", data_license)

        notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        for required in (
            "Copyright 2026 Chengxi She",
            "solver-in-the-loop",
            "CoE",
            "Gurobi",
            "benchmark",
        ):
            self.assertIn(required, notice)

        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        for required in (
            "cff-version: 1.2.0",
            'family-names: "She"',
            'given-names: "Chengxi"',
            'affiliation: "School of Management & Engineering, Nanjing University"',
            'email: "522023150104@smail.nju.edu.cn"',
            'license: "Apache-2.0"',
            'repository-code: "https://github.com/ChengxiSHE/LLM4UO_EAAI"',
        ):
            self.assertIn(required, citation)
        self.assertNotIn("orcid:", citation.lower())

    def test_zenodo_metadata_is_honest_and_doi_free(self):
        metadata = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["upload_type"], "software")
        self.assertEqual(metadata["access_right"], "open")
        self.assertEqual(metadata["license"], "Apache-2.0")
        self.assertEqual(metadata["creators"][0]["name"], "She, Chengxi")
        self.assertEqual(
            metadata["creators"][0]["affiliation"],
            "School of Management & Engineering, Nanjing University",
        )
        self.assertNotIn("orcid", metadata["creators"][0])
        self.assertNotIn("doi", metadata)

    def test_all_author_decisions_are_approved_without_invented_metadata(self):
        packet = json.loads(PACKET.read_text(encoding="utf-8"))
        self.assertEqual(packet["status"], "author_approved_ready_for_verified_publication")
        self.assertTrue(all(item["approved"] for item in packet["author_decisions"]))
        self.assertEqual(
            {item["id"] for item in packet["author_decisions"]},
            {f"D{index}" for index in range(1, 9)},
        )
        for item in packet["author_decisions"]:
            self.assertIn("approval_source", item)
        author = packet["verified_author_metadata"]
        self.assertEqual(author["name"], "Chengxi She")
        self.assertEqual(author["target_venue"], "undecided")
        self.assertEqual(author["funding"], "not_declared")
        self.assertEqual(author["orcid"], "omitted_unverified")
        self.assertFalse(packet["execution"]["doi_reserved"])
        self.assertFalse(packet["execution"]["repository_published"])

        disclosures = "\n".join(packet["ready_to_paste"].values())
        self.assertNotIn("[PUBLIC REPOSITORY]", disclosures)
        self.assertNotIn("[APPROVED SOFTWARE LICENSE]", disclosures)
        self.assertNotIn("[ARCHIVAL DOI]", disclosures)
        self.assertIn("DOI will be added after archival deposit", disclosures)

    def test_authorized_release_audit_binds_required_metadata(self):
        audit = json.loads(
            (ROOT / "experiments" / "authorized_release_audit_20261016.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["status"], "authorized_metadata_complete_publication_pending")
        self.assertTrue(audit["all_required_paths_tracked"])
        self.assertTrue(audit["all_required_hashes_match"])
        self.assertTrue(audit["decisions"]["all_d1_d8_approved"])
        self.assertFalse(audit["execution"]["repository_published"])
        self.assertFalse(audit["execution"]["doi_minted"])


if __name__ == "__main__":
    unittest.main()
