import json
import math
from pathlib import Path
import unittest

from llm4or.text2opt_template_compiler import (
    parse_disaster_response,
    parse_jssp,
    parse_rcpsp,
    parse_vrptw,
    solve_template_problem,
)


ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
EVALUATOR = ROOT / "data/next_development/text2opt_v8/evaluator.json"


class Text2OptTemplateCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.split = json.loads(SPLIT.read_text())
        cls.references = json.loads(EVALUATOR.read_text())["references"]

    def test_all_six_structured_development_families_match(self):
        rows = [row for row in self.split["development"] if row["family"] != "resource_allocation"]
        self.assertEqual(len(rows), 30)
        for row in rows:
            with self.subTest(problem_id=row["id"]):
                solved = solve_template_problem(row["public"])
                expected = self.references[row["id"]]["theoretical_optimum"]
                self.assertEqual(solved["status"], "optimal")
                self.assertTrue(math.isclose(solved["objective"], expected, rel_tol=1e-5, abs_tol=1e-6))

    def test_public_parsers_reject_missing_annex_shapes(self):
        for parser in (parse_disaster_response, parse_jssp, parse_rcpsp, parse_vrptw):
            with self.subTest(parser=parser.__name__), self.assertRaises(Exception):
                parser("No public annex is present.")

    def test_family_routing_does_not_depend_on_benchmark_id(self):
        row = next(row for row in self.split["development"] if row["family"] == "transportation")
        public = {**row["public"], "id": "neutral_public_problem"}
        solved = solve_template_problem(public)
        self.assertEqual(solved["status"], "optimal")
        self.assertTrue(math.isclose(
            solved["objective"], self.references[row["id"]]["theoretical_optimum"],
            rel_tol=1e-5, abs_tol=1e-6,
        ))


if __name__ == "__main__":
    unittest.main()
