import unittest

from llm4or.benchmark_independence import IndependenceAuditError, audit_overlap, normalized


class BenchmarkIndependenceTests(unittest.TestCase):
    def test_exact_and_template_overlap_are_measured_without_identities(self):
        candidates = [("candidate-secret", "Ship 12 crates from one depot to two stores quickly")]
        references = [
            ("reference-secret", "legacy", "Ship 99 crates from one depot to two stores quickly"),
            ("other-secret", "text2opt", "Schedule workers across a weekly planning horizon"),
        ]
        result = audit_overlap(candidates, references)
        self.assertEqual(result["lexical"]["exact_normalized_matches"], 0)
        self.assertEqual(result["numeric_template"]["exact_normalized_matches"], 1)
        rendered = str(result)
        self.assertNotIn("candidate-secret", rendered)
        self.assertNotIn("reference-secret", rendered)

    def test_disjoint_text_has_zero_or_low_overlap(self):
        result = audit_overlap(
            [("c", "perishable inventory expires after three periods")],
            [("r", "legacy", "assign aircraft to routes under capacity")],
        )
        self.assertEqual(result["lexical"]["exact_normalized_matches"], 0)
        self.assertLess(result["lexical"]["maximum_shingle_jaccard"]["max"], 0.8)

    def test_bad_inputs_fail_closed(self):
        with self.assertRaisesRegex(IndependenceAuditError, "empty_corpus"):
            audit_overlap([], [("r", "legacy", "some valid reference text")])
        with self.assertRaisesRegex(IndependenceAuditError, "duplicate_candidate_identity"):
            audit_overlap([("x", "first text"), ("x", "second text")], [("r", "legacy", "reference text")])
        with self.assertRaisesRegex(IndependenceAuditError, "empty_text"):
            normalized("", template=False)


if __name__ == "__main__":
    unittest.main()
