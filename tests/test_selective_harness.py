import unittest

from llm4or.selective_harness import wrap_solve_result


def public(text="unrecognized free-form case"):
    return {"id": "case", "text": text, "profile": "description_parameters_v1",
            "parameters": [], "instances": []}


class SelectiveHarnessTests(unittest.TestCase):
    def test_abstention_preserves_opaque_backend_result(self):
        backend = {"method": "BIND", "status": "optimal", "objective": 7.0,
                   "opaque": {"trace": [1, 2, 3]}}
        wrapped = wrap_solve_result(public(), backend)
        self.assertFalse(wrapped["adopted"])
        self.assertTrue(wrapped["fallback_identity"])
        self.assertEqual(wrapped["result"], backend)
        self.assertIsNot(wrapped["result"], backend)

    def test_optimal_compiler_result_is_adopted(self):
        compiled = {"status": "optimal", "objective": 3.0, "certificate": {"kind": "fixture"}}
        wrapped = wrap_solve_result(
            public("Transportation Costs (Source x Destination):"),
            {"method": "CoE", "status": "error"},
            detector=lambda _: "transportation",
            compiler=lambda _: compiled,
        )
        self.assertTrue(wrapped["adopted"])
        self.assertFalse(wrapped["fallback_identity"])
        self.assertEqual(wrapped["result"], compiled)


if __name__ == "__main__":
    unittest.main()
