import copy
import unittest

from llm4or.benchmark_inputs import (BASE_PROFILE, SCAFFOLD_PROFILE, complexor_input,
                                     flat_input, input_shape_issues, validate_public_input)
from llm4or.schema import Invalid, canonical


class BenchmarkInputTests(unittest.TestCase):
    def fixture(self):
        spec = {"description": "Choose quantities for N products.",
                "parameters": [{"symbol": "N", "definition": "Product count", "shape": []},
                               {"symbol": "Demand", "definition": "Demand per product", "shape": ["N"]}],
                "constraints": ["GOLD_SENTINEL"], "objective": "GOLD_SENTINEL",
                "background": "GOLD_SENTINEL"}
        samples = [{"input": {"N": 2, "Demand": [3, 4]}, "output": "GOLD_SENTINEL"}]
        return spec, samples

    def test_hidden_field_noninterference(self):
        spec, samples = self.fixture()
        before = complexor_input("complexor_test", spec, samples)
        spec["constraints"] = ["DIFFERENT_GOLD"]
        spec["objective"] = "DIFFERENT_GOLD"
        spec["parameters"][0]["answer"] = "GOLD_SENTINEL"
        samples[0]["output"] = {"answer": "DIFFERENT_GOLD"}
        samples[0]["reference_program"] = "GOLD_SENTINEL"
        self.assertEqual(before, complexor_input("complexor_test", spec, samples))
        self.assertNotIn("GOLD_SENTINEL", canonical(before))

    def test_all_flat_labels_excluded(self):
        for field in ("en_question", "question", "description", "document", "Question"):
            row = {field: "Question text", "en_answer": "GOLD_SENTINEL", "results": "GOLD_SENTINEL",
                   "original_answer": "GOLD_SENTINEL", "orginal_answer": "GOLD_SENTINEL",
                   "correct_program": "GOLD_SENTINEL", "type": "GOLD_SENTINEL"}
            self.assertNotIn("GOLD_SENTINEL", canonical(flat_input("q1", row, field)))

    def test_outputs_cannot_be_reintroduced(self):
        spec, samples = self.fixture()
        p = complexor_input("q1", spec, samples)
        for mutate in (lambda x: x.update(answer=1),
                       lambda x: x["instances"][0].update(output=1),
                       lambda x: x["parameters"][0].update(answer=1),
                       lambda x: x["instances"][0]["input"].update(answer=1)):
            candidate = copy.deepcopy(p); mutate(candidate)
            with self.assertRaises(Invalid): validate_public_input(candidate)

    def test_no_silent_parameter_key_loss(self):
        spec, samples = self.fixture()
        samples[0]["input"]["extra"] = 1
        with self.assertRaises(Invalid): complexor_input("q1", spec, samples)

    def test_missing_parameter_refused(self):
        spec, samples = self.fixture(); del samples[0]["input"]["Demand"]
        with self.assertRaises(Invalid): complexor_input("q1", spec, samples)

    def test_scaffold_explicit_and_inert(self):
        spec, samples = self.fixture()
        source = 'raise RuntimeError("must never execute")'
        with self.assertRaises(Invalid): complexor_input("q1", spec, samples, scaffold=source)
        p = complexor_input("q1", spec, samples, profile=SCAFFOLD_PROFILE, scaffold=source)
        self.assertEqual(p["scaffold"], source)
        p["profile"] = BASE_PROFILE
        with self.assertRaises(Invalid): validate_public_input(p)

    def test_shape_mismatch_retained_and_reported(self):
        spec, samples = self.fixture(); samples[0]["input"]["Demand"].append(5)
        p = complexor_input("q1", spec, samples)
        self.assertEqual(p["instances"][0]["input"]["Demand"], [3, 4, 5])
        self.assertEqual(input_shape_issues(p)[0]["code"], "declared_actual_shape_mismatch")

    def test_shape_expression_never_executed(self):
        spec, samples = self.fixture(); spec["parameters"][1]["shape"] = ["__import__('os').abort()"]
        p = complexor_input("q1", spec, samples)
        self.assertEqual(input_shape_issues(p)[0]["code"], "unresolved_shape_expression")

    def test_multiple_instances_preserved_without_outputs(self):
        spec, samples = self.fixture(); samples.append({"input": {"N": 1, "Demand": [9]}, "output": "GOLD_SENTINEL"})
        p = complexor_input("q1", spec, samples)
        self.assertEqual(len(p["instances"]), 2)
        self.assertEqual(input_shape_issues(p), [])
        self.assertNotIn("GOLD_SENTINEL", canonical(p))

    def test_detached_from_upstream(self):
        spec, samples = self.fixture(); p = complexor_input("q1", spec, samples)
        samples[0]["input"]["Demand"][0] = 99
        self.assertEqual(p["instances"][0]["input"]["Demand"][0], 3)

    def test_nonfinite_and_deep_values_refused(self):
        spec, samples = self.fixture(); samples[0]["input"]["N"] = float("nan")
        with self.assertRaises(Invalid): complexor_input("q1", spec, samples)
        nested = 1
        for _ in range(14): nested = [nested]
        samples[0]["input"]["N"] = nested
        with self.assertRaises(Invalid): complexor_input("q1", spec, samples)

    def test_parameter_duplicates_refused(self):
        spec, samples = self.fixture(); spec["parameters"].append(spec["parameters"][0])
        with self.assertRaises(Invalid): complexor_input("q1", spec, samples)

    def test_empty_complexor_samples_refused(self):
        spec, _ = self.fixture()
        with self.assertRaises(Invalid): complexor_input("q1", spec, [])


if __name__ == "__main__":
    unittest.main()
