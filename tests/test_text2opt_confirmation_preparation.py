import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "freeze_text2opt_confirmation_run", ROOT / "scripts/freeze_text2opt_confirmation_run.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Text2OptConfirmationPreparationTests(unittest.TestCase):
    def test_selection_is_complete_public_and_outcome_free(self):
        rows, categories = MODULE.build_selection()
        self.assertEqual(len(rows), 431)
        self.assertEqual(len(categories), 7)
        self.assertEqual(len({row["problem_id"] for row in rows}), 431)
        for row in rows:
            self.assertEqual(
                set(row),
                {"problem_id", "category", "input_sha256", "source_file", "source_file_sha256"},
            )
            self.assertNotIn("objective", row)
            self.assertNotIn("gurobi_result", row)


if __name__ == "__main__":
    unittest.main()
