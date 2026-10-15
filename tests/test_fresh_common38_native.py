import json
from pathlib import Path
import tempfile
import unittest

from llm4or import fresh_common38_native as native


ROOT = Path(__file__).resolve().parents[1]


class FreshCommon38NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = native.build_plan(ROOT)

    def test_plan_binds_all_models_without_bodies(self):
        self.assertEqual(len(self.plan["bindings"]), 38)
        self.assertEqual(sum(row["family"] == "rcpsp" for row in self.plan["bindings"]), 13)
        self.assertEqual(sum(row["family"] == "vrptw" for row in self.plan["bindings"]), 25)
        self.assertEqual(self.plan["solver"]["threads"], 1)
        self.assertEqual(self.plan["solver"]["time_limit_seconds"], 20)
        text = json.dumps(self.plan, sort_keys=True)
        for prohibited in ('"public_payload"', '"instance_data"', '"text"',
                           '"objective"', '"point"', '"reference"'):
            self.assertNotIn(prohibited, text)

    def test_fake_run_is_checkpointed_and_resumable(self):
        calls = []
        def solver(operation, **kwargs):
            calls.append(operation["model"]["schema"])
            point = {row["id"]: 0.0 for row in operation["model"]["variables"]}
            return {"status": "limit", "objective": None, "point": point,
                    "point_check": None, "reason": "test_limit", "wall_seconds": 0.01,
                    "backend": "fake"}
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            first = native.run_plan(ROOT, self.plan, out, solver=solver)
            self.assertEqual(first["terminal"], 38)
            self.assertEqual(first["new_solver_calls"], 38)
            second = native.run_plan(ROOT, self.plan, out, solver=solver)
            self.assertEqual(second["terminal"], 38)
            self.assertEqual(second["new_solver_calls"], 0)
            self.assertEqual(len(calls), 38)

    def test_aggregate_scoring_does_not_publish_values(self):
        cells = []
        references = {}
        for index, row in enumerate(self.plan["bindings"]):
            objective = float(index + 1)
            cells.append({"id": row["id"], "family": row["family"],
                          "model_sha256": row["model_sha256"], "status": "optimal",
                          "objective": objective, "point": {}, "reason": None,
                          "backend": "fake", "wall_seconds": 0.1})
            references[row["id"]] = {"solver_status": 2, "optimum": objective}
        result = native.score_cells(self.plan, cells, references)
        self.assertEqual(result["aggregate"]["correct"], 38)
        self.assertEqual(result["aggregate"]["planned"], 38)
        rendered = json.dumps(result, sort_keys=True)
        self.assertNotIn('"optimum"', rendered)
        self.assertNotIn('"objective"', rendered)
        self.assertNotIn('"point"', rendered)


if __name__ == "__main__":
    unittest.main()
