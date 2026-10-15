from pathlib import Path
import unittest

from llm4or.gurobi_cli_solver import DEFAULT_BINARY, execute, model_to_lp


MODEL = {
    "schema": "milp-v1",
    "variables": [
        {"id": "x", "meaning": "units", "unit": "1", "domain": "integer", "lower": 0, "upper": 3},
        {"id": "y", "meaning": "switch", "unit": "1", "domain": "binary", "lower": None, "upper": None},
    ],
    "constraints": [
        {"id": "cap", "coefficients": {"x": 1, "y": 1}, "sense": "le", "rhs": 3},
    ],
    "objective": {"coefficients": {"x": 2, "y": 1}, "sense": "max", "unit": "1", "offset": 5},
}


class GurobiCliSolverTests(unittest.TestCase):
    def test_lp_export_is_declarative_and_preserves_domains(self):
        text = model_to_lp(MODEL)
        self.assertIn("Maximize", text)
        self.assertIn("cap: + 1 x + 1 y <= 3", text)
        self.assertIn("Generals\n x", text)
        self.assertIn("Binaries\n y", text)
        self.assertNotIn("import", text)

    @unittest.skipUnless(Path(DEFAULT_BINARY).is_file(), "Gurobi CLI not installed")
    def test_live_cli_solution_is_independently_rechecked(self):
        result = execute({"op": "solve", "model": MODEL}, time_limit=5, wall_seconds=10)
        self.assertEqual(result["status"], "optimal")
        self.assertAlmostEqual(result["objective"], 11.0)
        self.assertTrue(result["point_check"]["feasible"])


if __name__ == "__main__":
    unittest.main()
