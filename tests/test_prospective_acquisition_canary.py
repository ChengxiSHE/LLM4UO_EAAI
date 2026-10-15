import json
from pathlib import Path
import unittest

from llm4or import prospective_acquisition_canary as canary
from llm4or.schema import canonical
from llm4or.typed_count_skill import verify_candidate


ROOT = Path(__file__).resolve().parents[1]


class ProspectiveAcquisitionCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = json.loads(
            (ROOT / "results/dcp_typed_count_repair_input_20261014.json").read_text()
        )
        preview = json.loads(
            (ROOT / "results/dcp_count_public_binding_preview_20261014.json").read_text()
        )
        cls.model_proposal = source["candidate"]
        cls.public_cases = sorted(
            [
                row["instance"]
                for row in preview["rows"]
                if row["contract_kind_for_analysis_only"] == "partial_fixed_tail"
            ],
            key=lambda row: (row["n"], row["m"]),
        )

    def test_selects_one_model_and_seven_unique_rejected_synthetic_units(self):
        units = canary.select_units(self.model_proposal, self.public_cases)

        self.assertEqual(len(units), 8)
        self.assertEqual(
            [row["provenance"] for row in units].count("historical_model_generated"),
            1,
        )
        self.assertEqual(
            [row["provenance"] for row in units].count("deterministic_synthetic_seed"),
            7,
        )
        self.assertEqual(len({row["unit_id"] for row in units}), 8)
        self.assertEqual(len({row["source_candidate_sha256"] for row in units}), 8)
        self.assertTrue(all(row["initial_version_space_size"] == 64 for row in units))
        self.assertTrue(
            all(
                not verify_candidate(row["source_candidate"], self.public_cases)["passed"]
                for row in units
            )
        )
        self.assertEqual(
            canonical(units),
            canonical(canary.select_units(self.model_proposal, self.public_cases)),
        )

    def test_teacher_trace_contracts_the_frozen_version_space_from_64_to_1(self):
        facts = canary.build_fact_ledger()
        trace = canary.build_teacher_trace(facts)

        self.assertEqual(len(facts), 6)
        self.assertEqual(len({row["fact_id"] for row in facts}), 6)
        self.assertEqual(len(trace), 6)
        self.assertEqual([row["before_candidates"] for row in trace], [64, 32, 16, 8, 4, 2])
        self.assertEqual([row["retained_candidates"] for row in trace], [32, 16, 8, 4, 2, 1])
        self.assertEqual([row["eliminated_candidates"] for row in trace], [32, 16, 8, 4, 2, 1])
        self.assertEqual(trace[-1]["retained_candidates"], 1)
        self.assertEqual({row["fact_id"] for row in facts}, {row["fact_id"] for row in trace})

    def test_paired_payloads_have_identical_facts_and_no_winner_or_answer_fields(self):
        unit = canary.select_units(self.model_proposal, self.public_cases)[0]
        facts = canary.build_fact_ledger()
        trace = canary.build_teacher_trace(facts)
        prohibited = (
            "authored_candidate",
            "selected_candidate",
            "winner",
            "minimum_repair",
            "benchmark_answer",
            "solved_vector",
            "reference_answer",
        )

        for round_number in (1, 2, 3):
            flat = canary.build_payload(unit, "flat", round_number, facts, trace)
            treatment = canary.build_payload(
                unit, "separating_witness", round_number, facts, trace
            )
            self.assertEqual(flat["revealed_facts"], treatment["revealed_facts"])
            self.assertEqual(len(flat["revealed_facts"]), 2 * round_number)
            self.assertNotIn("separation_structure", flat)
            self.assertIn("separation_structure", treatment)
            self.assertEqual(
                [row["fact_id"] for row in treatment["separation_structure"]],
                [row["fact_id"] for row in treatment["revealed_facts"]],
            )
            flat_text = canonical(flat).casefold()
            treatment_text = canonical(treatment).casefold()
            for token in prohibited:
                self.assertNotIn(token, flat_text)
                self.assertNotIn(token, treatment_text)

    def test_payload_and_teacher_fail_closed_on_mutation(self):
        unit = canary.select_units(self.model_proposal, self.public_cases)[0]
        facts = canary.build_fact_ledger()
        trace = canary.build_teacher_trace(facts)
        with self.assertRaises(ValueError):
            canary.build_payload(unit, "other", 1, facts, trace)
        with self.assertRaises(ValueError):
            canary.build_payload(unit, "flat", 0, facts, trace)
        with self.assertRaises(ValueError):
            canary.build_payload(unit, "flat", 4, facts, trace)
        changed = json.loads(json.dumps(facts))
        changed[0]["statement"] += " mutation"
        with self.assertRaises(ValueError):
            canary.build_payload(unit, "flat", 1, changed, trace)
        changed_trace = json.loads(json.dumps(trace))
        changed_trace[0]["retained_candidates"] -= 1
        with self.assertRaises(ValueError):
            canary.build_payload(unit, "flat", 1, facts, changed_trace)

    def test_response_schema_is_exact_finite_grammar(self):
        schema = canary.response_schema()
        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(len(schema["required"]), 8)
        self.assertEqual(schema["properties"]["schema"]["const"], "typed-partial-count-skill-v1")
        self.assertEqual(
            schema["properties"]["resource_policy"]["enum"],
            ["compiler_exact", "estimate_only"],
        )


if __name__ == "__main__":
    unittest.main()
