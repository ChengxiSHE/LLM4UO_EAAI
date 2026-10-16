import json
from pathlib import Path
import tempfile
import unittest

from llm4or.nlequiv_skill_route import (
    ARMS, PersistentRateGate, RoutedSkillError, build_views, fact_inventory,
    parse_decision, rate_gate_summary, selected_skills, skill_manifest,
)


def pair():
    formulation = {
        "constraints": [{"description": "positive range", "formulation": "x >= 0", "code": {}}],
        "keywords": ["log transform"], "notes": {"solver_modeling": "synthetic"},
        "objective": {"description": "minimize", "formulation": "x", "code": {}},
        "parameters": {}, "parametrized_description": "Use log and reciprocal transforms.",
        "variables": {"x": {"description": "positive", "type": "continuous"}},
    }
    return {"schema": "llm4or-nlequiv-inference-pair-v1", "opaque_id": "a" * 64,
            "source_commit": "b" * 40, "source_tree": "c" * 40,
            "formulation_a": formulation, "formulation_b": json.loads(json.dumps(formulation))}


class RoutedSkillTests(unittest.TestCase):
    def test_three_views_have_identical_fact_multisets(self):
        value = pair(); expected = sorted(row["fact_sha256"] for row in fact_inventory(value))
        views = build_views(value)
        self.assertEqual(set(views), set(ARMS))
        for arm, view in views.items():
            facts = view.get("facts") or [row for obligation in view["obligations"] for row in obligation["facts"]]
            self.assertEqual(sorted(row["fact_sha256"] for row in facts), expected, arm)

    def test_router_selects_only_triggered_generic_cards(self):
        selected = selected_skills(pair())
        self.assertEqual(selected[0], "universal_equivalence")
        self.assertIn("exp_log", selected)
        self.assertIn("reciprocal", selected)
        self.assertNotIn("softplus", selected)

    def test_decision_contract_is_two_fields_only(self):
        self.assertTrue(parse_decision('{"equivalent":true,"schema":"llm4or-equivalence-decision-v1"}'))
        for text in ('{"equivalent":true}', '{"equivalent":1,"schema":"llm4or-equivalence-decision-v1"}', '{"equivalent":true,"schema":"llm4or-equivalence-decision-v1","why":"x"}'):
            with self.assertRaises(RoutedSkillError): parse_decision(text)

    def test_skill_manifest_declares_authored_boundary(self):
        manifest = skill_manifest()
        self.assertEqual(manifest["status"], "frozen_before_nlequiv_inference_or_labels")
        self.assertEqual(manifest["router"]["fallback"], "universal_equivalence")
        self.assertIn("not automatically acquired", manifest["claim_boundary"])

    def test_persistent_rate_gate_enforces_rolling_window(self):
        now = [0.0]; sleeps = []
        def clock(): return now[0]
        def sleeper(seconds): sleeps.append(seconds); now[0] += seconds
        plan = {"rate_limit_policy": {"max_logical_starts": 2, "window_seconds": 10, "safety_seconds": 0.5, "observed_provider_limit": 3}}
        with tempfile.TemporaryDirectory() as temporary:
            gate = PersistentRateGate(Path(temporary), plan, clock=clock, sleeper=sleeper)
            gate.admit(); gate.admit(); gate.admit()
            self.assertEqual(len(sleeps), 1)
            self.assertGreaterEqual(now[0], 10.5)
            summary = rate_gate_summary(temporary, plan["rate_limit_policy"])
            self.assertEqual(summary["logical_starts"], 3)
            self.assertTrue(summary["within_policy"])


if __name__ == "__main__": unittest.main()
