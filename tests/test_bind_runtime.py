import json
from pathlib import Path
import re
import tempfile
import unittest

from llm4or.bind_official_adapter import BindPromptSource, BindSourceError
from llm4or.bind_runtime import (
    bind_reference_projection, public_bind_projection, run_bind_instance_data,
)


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "data/raw/text2opt_bench_20261003"

PUBLIC = {
    "id": "bind_case",
    "profile": "description_parameters_v1",
    "text": "Choose a nonnegative integer quantity no greater than the supplied capacity.",
    "parameters": [],
    "instances": [],
}

PROBLEM = {
    "meta": {
        "problem_type": "toy allocation", "goal": "MAXIMIZE",
        "num_vars": 1, "num_constraints": 0,
    },
    "instance_data": {"cap": 3, "profit": 1},
    "LLM_description": "Choose x to maximize profit.",
    "LLM_description_template": "Choose x no greater than {CAP} and maximize {PROFIT} times x.",
    "gurobi_result": {"solver_status": 2, "theoretical_optimum": 3},
}


class FakeGateway:
    def __init__(self):
        self.calls = []
        self.registered = None

    def register(self, scope, calls, tokens):
        self.registered = (scope, calls, tokens)

    def request(self, scope, payload, prefix, replicate, slot):
        instruction = payload["instruction"]
        match = re.search(r'INSTANCE_DATA_PATH = r"([^"]+)"', instruction)
        self.assertion(match is not None, "virtual data path absent")
        path = match.group(1)
        if slot == 0:
            body = f'''```python
import json
from gurobipy import *
INSTANCE_DATA_PATH = r"{path}"
def solve_problem():
    with open(INSTANCE_DATA_PATH, "r") as f:
        d = json.load(f)
    m = Model()
    x = m.addVar(lb=0, ub=1, vtype=GRB.INTEGER, name="x")
    m.setObjective(d["profit"] * x, GRB.MAXIMIZE)
    m.optimize()
    return m
```'''
        else:
            body = f'''```python
import json
from gurobipy import *
INSTANCE_DATA_PATH = r"{path}"
def solve_problem():
    with open(INSTANCE_DATA_PATH, "r") as f:
        d = json.load(f)
    m = Model()
    x = m.addVar(lb=0, ub=d["cap"], vtype=GRB.INTEGER, name="x")
    m.setObjective(d["profit"] * x, GRB.MAXIMIZE)
    m.optimize()
    return m
```'''
        self.calls.append({"slot": slot, "payload": payload, "durably_saved": True})
        return {"text": json.dumps({"code": body}), "total_tokens": 100 + slot}

    @staticmethod
    def assertion(condition, message):
        if not condition:
            raise AssertionError(message)

    def scope_usage(self, _scope):
        return {"logical_requests": len(self.calls), "logical_tokens": 201}


class BindRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not UPSTREAM.exists():
            raise unittest.SkipTest("pinned Text2Opt source fixture absent")
        cls.source = BindPromptSource.load(UPSTREAM)

    def test_hash_bound_prompt_source_and_public_projection(self):
        projected = public_bind_projection(PROBLEM)
        self.assertNotIn("gurobi_result", projected)
        self.assertNotIn("num_vars", projected["meta"])
        prompt = self.source.initial_prompt(projected, "/virtual/data.json")
        self.assertIn('`d["cap"]`', prompt)
        self.assertIn('INSTANCE_DATA_PATH = r"/virtual/data.json"', prompt)
        self.assertNotIn("theoretical_optimum", prompt)
        self.assertEqual(bind_reference_projection(PROBLEM), {
            "optimum": 3, "solver_status": 2, "num_vars": 1, "num_constraints": 0,
        })

    def test_source_hash_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "main/evaluation"
            path.mkdir(parents=True)
            (path / "agentic_offload.py").write_text("AGENTIC_SYSTEM_PROMPT='changed'")
            (path / "run_eval.py").write_text("changed")
            with self.assertRaisesRegex(BindSourceError, "source_changed"):
                BindPromptSource.load(root)

    def test_two_round_oracle_repair_loads_reference_only_after_saved_response(self):
        gateway = FakeGateway()
        events = []

        def load_reference():
            self.assertEqual(len(gateway.calls), 1)
            self.assertTrue(gateway.calls[0]["durably_saved"])
            events.append("reference_loaded")
            return bind_reference_projection(PROBLEM)

        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            result = run_bind_instance_data(
                PUBLIC, PROBLEM, gateway, "binddev:BIND:17:bind_case", 17, 65536,
                self.source, load_reference, checkpoint_path=checkpoint,
            )
            self.assertEqual(json.loads(checkpoint.read_text()), result)
        self.assertEqual(events, ["reference_loaded"])
        self.assertEqual(gateway.registered, ("binddev:BIND:17:bind_case", 3, 65536))
        self.assertEqual([row["slot"] for row in gateway.calls], [0, 1])
        self.assertEqual(result["status"], "completed_success")
        self.assertEqual(result["rounds_used"], 2)
        self.assertFalse(result["rounds"][0]["objective_matches"])
        self.assertTrue(result["rounds"][1]["objective_matches"])
        second_prompt = gateway.calls[1]["payload"]["instruction"]
        self.assertIn("Expected objective   : 3", second_prompt)
        self.assertIn("Official BIND assistant message", second_prompt)
        self.assertNotIn("theoretical_optimum", gateway.calls[0]["payload"]["instruction"])
        self.assertEqual(
            gateway.calls[0]["payload"]["context"]["transport_adapter"],
            "stateless_transcript_flattening",
        )
        self.assertEqual(
            result["prompt_transport"],
            "official_messages_flattened_for_stateless_codex_cli",
        )

    def test_antchat_transport_label_is_explicit_without_changing_default(self):
        gateway = FakeGateway()
        result = run_bind_instance_data(
            PUBLIC, PROBLEM, gateway, "freshbind:BIND:0:bind_case", 0, 65536,
            self.source, lambda: bind_reference_projection(PROBLEM),
            transport_adapter="stateless_antchat_chat_completions",
        )
        self.assertEqual(
            gateway.calls[0]["payload"]["context"]["transport_adapter"],
            "stateless_antchat_chat_completions",
        )
        self.assertEqual(
            result["prompt_transport"],
            "official_messages_flattened_for_stateless_antchat_chat_completions",
        )


if __name__ == "__main__":
    unittest.main()
