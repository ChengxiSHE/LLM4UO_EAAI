from pathlib import Path
import unittest

from llm4or.fresh_common38 import build_private_bundle
from llm4or.schema import digest
from llm4or import structured_or_skills as skills


ROOT = Path(__file__).resolve().parents[1]


class StructuredOrSkillsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = build_private_bundle(ROOT)["records"]

    def test_every_packet_has_exactly_one_typed_route(self):
        counts = {"rcpsp": 0, "vrptw": 0}
        for row in self.rows:
            route = skills.route_packet(row["public_payload"])
            self.assertEqual(route, row["family"])
            counts[route] += 1
        self.assertEqual(counts, {"rcpsp": 13, "vrptw": 25})

    def test_every_packet_compiles_with_exact_source_counts_and_caps(self):
        for row in self.rows:
            admitted = skills.compile_and_admit(row["public_payload"])
            model = admitted["model"]
            metrics = admitted["metrics"]
            self.assertEqual(admitted["route"], row["family"])
            self.assertEqual(metrics["variables"], row["non_outcome_metadata"]["num_vars"])
            self.assertEqual(metrics["constraints"], row["non_outcome_metadata"]["num_constraints"])
            self.assertTrue(all(metrics[key] <= skills.RESOURCE_CAPS[key]
                                for key in skills.RESOURCE_CAPS))
            self.assertEqual(admitted["model_sha256"], digest(model))

    def test_models_are_referentially_closed_and_deterministic(self):
        for row in self.rows:
            first = skills.compile_and_admit(row["public_payload"])
            second = skills.compile_and_admit(row["public_payload"])
            self.assertEqual(first["model_sha256"], second["model_sha256"])
            variables = [item["id"] for item in first["model"]["variables"]]
            constraints = [item["id"] for item in first["model"]["constraints"]]
            self.assertEqual(len(variables), len(set(variables)))
            self.assertEqual(len(constraints), len(set(constraints)))
            known = set(variables)
            self.assertLessEqual(set(first["model"]["objective"]["coefficients"]), known)
            for constraint in first["model"]["constraints"]:
                self.assertLessEqual(set(constraint["coefficients"]), known)

    def test_unknown_or_ambiguous_schema_fails_closed(self):
        base = self.rows[0]["public_payload"]
        data = base["instances"][0]["input"]["instance_data"]
        with self.assertRaisesRegex(ValueError, "typed_route_zero"):
            skills.route_instance({"unrelated": 1})
        ambiguous = dict(data)
        ambiguous.update({
            "n_customers": 1, "n_vehicles": 1, "vehicle_capacity": 1,
            "vehicle_fixed_cost": 1.0, "depot_coordinates": [0, 0],
            "customer_coordinates": [[1, 1]], "customer_demands": [1],
            "time_windows": [[0, 10], [0, 5]], "service_times": [1],
        })
        with self.assertRaisesRegex(ValueError, "typed_route_multiple"):
            skills.route_instance(ambiguous)

    def test_shape_and_semantic_mutations_fail_before_model_emission(self):
        rcpsp = next(row for row in self.rows if row["family"] == "rcpsp")
        bad = skills.copy_packet(rcpsp["public_payload"])
        bad["instances"][0]["input"]["instance_data"]["mode_costs"][0].pop()
        with self.assertRaisesRegex(ValueError, "rcpsp_mode_costs"):
            skills.compile_and_admit(bad)

        vrptw = next(row for row in self.rows if row["family"] == "vrptw")
        bad = skills.copy_packet(vrptw["public_payload"])
        bad["instances"][0]["input"]["instance_data"]["time_windows"][1] = [8, 7]
        with self.assertRaisesRegex(ValueError, "vrptw_time_windows"):
            skills.compile_and_admit(bad)

    def test_packet_contract_is_single_instance_data_parameter(self):
        bad = skills.copy_packet(self.rows[0]["public_payload"])
        bad["parameters"][0]["symbol"] = "other"
        with self.assertRaisesRegex(ValueError, "packet_contract"):
            skills.compile_and_admit(bad)


if __name__ == "__main__":
    unittest.main()
