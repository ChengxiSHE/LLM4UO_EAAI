import json
import unittest

from llm4or.formal_gateway import validate_fresh_external_payload
from llm4or.retailopt190_experiment import VERSION, make_payload, response_schema
from llm4or.retailopt190_knowledge import render_request
from llm4or.schema import digest


SELECTED=["retail.core.flow.v1"]


class RetailOptExperimentTests(unittest.TestCase):
    def test_payload_and_schema_bind_exact_questions(self):
        view=render_request(opaque_archetype_id="a"*64,public_prompt="task",selected_skill_ids=SELECTED,arm="base_short")
        payload=make_payload(view,"b"*64,SELECTED)
        self.assertEqual(payload["context"]["arm"],"base_short")
        schema=response_schema(SELECTED)
        self.assertEqual(set(schema["properties"]["answers"]["required"]),{row["question_id"] for row in view["questions"]})
        self.assertEqual(payload["response_schema"],schema)

    def test_view_contains_no_reference_field(self):
        view=render_request(opaque_archetype_id="a"*64,public_prompt="task",selected_skill_ids=SELECTED,arm="knowledge_short")
        rendered=json.dumps(view,sort_keys=True)
        self.assertNotIn("reference_objective",rendered)
        self.assertNotIn("evaluator",rendered)

    def test_gateway_accepts_only_the_bound_retail_payload(self):
        cell_id="b"*64
        view=render_request(opaque_archetype_id="a"*64,public_prompt="task",selected_skill_ids=SELECTED,arm="base_short")
        payload=make_payload(view,cell_id,SELECTED)
        plan={
            "kind":"fresh_common_external","replicates":[0],"runtime_version":VERSION,
            "external_method":{"name":"RetailOptShortDecision","scope_stage":"retailfull","max_calls":1},
            "token_cap":10000,"public_inputs":{cell_id:digest(payload)},
            "cells":{cell_id:{"arm":"base_short","opaque_archetype_id":"a"*64,"selected_skill_ids":SELECTED}},
        }
        scope=f"retailfull:RetailOptShortDecision:0:{cell_id}"
        validate_fresh_external_payload(plan,scope,payload,0,0)
        changed=json.loads(json.dumps(payload));changed["view"]["arm"]="knowledge_short"
        with self.assertRaisesRegex(Exception,"payload_changed"):
            validate_fresh_external_payload(plan,scope,changed,0,0)


if __name__=="__main__":unittest.main()
