import copy
import json
import unittest

from llm4or.retailopt190_knowledge import (
    CARDS,
    RetailKnowledgeError,
    gold_decision,
    library_payload,
    library_sha256,
    parse_decision,
    questions,
    render_request,
    route,
)


def base_data():
    return {
        "constraints": {"moq": 0, "pack_size": 1, "budget_per_period": None, "waste_limit_pct": None},
        "costs": {"fixed_order": 0},
        "labor_usage": {"p": 0},
        "lead_time": {"p": 0},
        "network": {"sub_edges": [], "trans_edges": []},
        "return_rate": {"p": 0},
    }


class RetailOptKnowledgeTests(unittest.TestCase):
    def test_library_is_body_and_answer_free(self):
        payload = library_payload()
        self.assertEqual(len(payload["cards"]), 10)
        self.assertEqual(len(library_sha256()), 64)
        rendered = json.dumps(payload["cards"], sort_keys=True)
        self.assertNotIn("reference_objective", rendered)
        self.assertNotIn("retail_f", rendered)
        self.assertNotIn("gurobipy", rendered.lower())

    def test_router_is_sparse_and_feature_complete(self):
        data = base_data()
        self.assertEqual(route(data), ("retail.core.flow.v1",))
        data["network"]["sub_edges"] = [["a", "b"]]
        data["constraints"]["moq"] = 4
        selected = route(data)
        self.assertEqual(selected, ("retail.core.flow.v1", "retail.substitution.v1", "retail.moq_fixed.v1"))
        self.assertEqual(len(questions(selected)), 12)

    def test_router_rejects_multiple_optional_features(self):
        data = base_data()
        data["constraints"]["moq"] = 4
        data["constraints"]["pack_size"] = 3
        with self.assertRaisesRegex(RetailKnowledgeError, "non_sparse_optional_route"):
            route(data)

    def test_matched_requests_differ_only_by_evidence_and_arm(self):
        selected = route(base_data())
        base = render_request(opaque_archetype_id="a" * 64, public_prompt="public task", selected_skill_ids=selected, arm="base_short")
        method = render_request(opaque_archetype_id="a" * 64, public_prompt="public task", selected_skill_ids=selected, arm="knowledge_short")
        left, right = copy.deepcopy(base), copy.deepcopy(method)
        left.pop("arm"); right.pop("arm")
        left.pop("evidence"); right.pop("evidence")
        self.assertEqual(left, right)
        self.assertEqual(base["evidence"], [])
        self.assertEqual(len(method["evidence"]), 1)

    def test_decision_parser_is_exact(self):
        selected = route(base_data())
        value = {"schema": "llm4or-retailopt190-short-decision-v1", "answers": gold_decision(selected)}
        self.assertEqual(parse_decision(value, selected), value["answers"])
        bad = copy.deepcopy(value)
        bad["answers"].pop(next(iter(bad["answers"])))
        with self.assertRaisesRegex(RetailKnowledgeError, "decision_membership"):
            parse_decision(bad, selected)
        bad = copy.deepcopy(value)
        bad["extra"] = True
        with self.assertRaisesRegex(RetailKnowledgeError, "decision_schema"):
            parse_decision(bad, selected)

    def test_every_question_has_one_admitted_answer(self):
        ids = set()
        for card in CARDS:
            for question in card.questions:
                self.assertIn(question.correct, question.choices)
                self.assertNotIn(question.question_id, ids)
                ids.add(question.question_id)


if __name__ == "__main__":
    unittest.main()
