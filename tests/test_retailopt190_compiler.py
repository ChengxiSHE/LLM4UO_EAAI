import copy
import unittest

from llm4or.retailopt190_compiler import RetailCompileError, validate_data


def data():
    return {
        "name": "opaque",
        "description": "public description",
        "periods": 2,
        "products": ["p"],
        "locations": ["l"],
        "shelf_life": {"p": 2},
        "lead_time": {"p": 0},
        "demand_curve": {"p": [1, 2]},
        "demand_share": {"l": 1.0},
        "production_cap": {"p": [3, 3]},
        "cold_capacity": {"l": 4},
        "cold_usage": {"p": 1},
        "labor_cap": {"l": [5, 5]},
        "labor_usage": {"p": 0},
        "return_rate": {"p": 0},
        "costs": {"purchasing": {"p": 1}, "inventory": {"p": 1}, "waste": {"p": 1}, "lost_sales": {"p": 5}, "fixed_order": 0, "transshipment": 0},
        "constraints": {"moq": 0, "pack_size": 1, "budget_per_period": None, "waste_limit_pct": None},
        "network": {"sub_edges": [], "trans_edges": []},
    }


class RetailOptCompilerTests(unittest.TestCase):
    def test_minimal_data_validates(self):
        validate_data(data())

    def test_unknown_key_and_bad_entities_fail_closed(self):
        value = data(); value["unknown"] = 1
        with self.assertRaisesRegex(RetailCompileError, "data_keys"):
            validate_data(value)
        value = data(); value["products"] = ["p", "p"]
        with self.assertRaisesRegex(RetailCompileError, "entity_identity"):
            validate_data(value)

    def test_nonmapping_component_fails_closed(self):
        value = data(); value["network"] = []
        with self.assertRaisesRegex(RetailCompileError, "network"):
            validate_data(value)


if __name__ == "__main__":
    unittest.main()
