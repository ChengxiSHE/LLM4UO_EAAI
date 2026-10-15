import json
from pathlib import Path
import unittest

from llm4or.coe_official_adapter import CoEPromptSource
from llm4or.coe_runtime import run_coe_forward
from llm4or.schema import canonical


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "data/raw/xzymustbexzy__Chain-of-Experts_20261003"


class Gateway:
    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []
        self.registered = None

    def register(self, scope, calls, tokens):
        self.registered = (scope, calls, tokens)

    def request(self, scope, payload, prefix, replicate, slot):
        self.requests.append((scope, payload, prefix, replicate, slot))
        return {"text": canonical({"text": self.answers.pop(0)}), "total_tokens": 1}

    def scope_usage(self, scope):
        return {"logical_requests": len(self.requests), "logical_tokens": len(self.requests)}


class RawJsonGateway(Gateway):
    def request(self, scope, payload, prefix, replicate, slot):
        self.requests.append((scope, payload, prefix, replicate, slot))
        answer = self.answers.pop(0)
        return {"text": answer, "total_tokens": 1}


@unittest.skipUnless((UPSTREAM / ".git").is_dir(), "ignored upstream CoE checkout unavailable")
class CoERuntimeTests(unittest.TestCase):
    def test_reference_is_loaded_after_reducer_and_generated_code_is_translated(self):
        prompts = CoEPromptSource.load(UPSTREAM, "current")
        code = '''```python
from gurobipy import *
def demo(cap):
    m = Model()
    x = m.addVar(lb=0, ub=cap, name="x")
    m.setObjective(x, GRB.MAXIMIZE)
    m.optimize()
    return m.objVal
```'''
        gateway = Gateway(["Modeling Expert", "modeling comment", code])
        load_counts = []
        def reference():
            load_counts.append(len(gateway.requests))
            return [{"input": {"cap": 3}, "output": [3]}]
        public = {"id": "demo", "profile": "description_parameters_v1", "text": "maximize x",
                  "parameters": [], "instances": []}
        result = run_coe_forward(
            public, {"description": "maximize x", "code_example": "def demo(cap): pass"},
            "demo", gateway, "coedev:CoE:17:demo", 17, 1000, prompts, reference,
            max_collaborations=1,
        )
        self.assertEqual(gateway.registered[1], 3)
        self.assertEqual(load_counts, [3])
        self.assertTrue(result["author_accept"])
        self.assertTrue(result["adapter_supported"])
        self.assertEqual(result["steps"][0]["expert_key"], "modeling_expert")

    def test_json_object_transport_falls_back_to_verbatim_official_response(self):
        prompts = CoEPromptSource.load(UPSTREAM, "current")
        code = '''```python
from gurobipy import *
def demo(cap):
    m = Model()
    x = m.addVar(lb=0, ub=cap, name="x")
    m.setObjective(x, GRB.MAXIMIZE)
    m.optimize()
    return m.objVal
```'''
        gateway = RawJsonGateway([
            json.dumps({"selected_expert": "Modeling Expert"}),
            json.dumps({"analysis": "model x"}),
            json.dumps({"text": code}),
        ])
        public = {"id": "demo", "profile": "description_parameters_v1", "text": "maximize x",
                  "parameters": [], "instances": []}
        result = run_coe_forward(
            public, {"description": "maximize x", "code_example": "def demo(cap): pass"},
            "demo", gateway, "coedev:CoE:17:demo", 17, 1000, prompts,
            lambda: [{"input": {"cap": 3}, "output": [3]}], max_collaborations=1,
        )
        self.assertEqual(result["steps"][0]["expert_key"], "modeling_expert")
        self.assertTrue(result["author_accept"])


if __name__ == "__main__":
    unittest.main()
