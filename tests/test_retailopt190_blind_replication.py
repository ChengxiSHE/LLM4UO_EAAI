import json
import unittest

from llm4or.formal_gateway import validate_fresh_external_payload
from llm4or.retailopt190_blind_replication import VERSION
from llm4or.retailopt190_experiment import make_payload
from llm4or.retailopt190_knowledge import render_request
from llm4or.schema import digest


class RetailOptBlindTests(unittest.TestCase):
    def _payload(self,arm):
        selected=['retail.core.flow.v1']; cell='a'*64
        value=make_payload(render_request(opaque_archetype_id='b'*64,public_prompt='task',selected_skill_ids=selected,arm=arm),cell,selected)
        value['version']=VERSION;value['view'].pop('arm');value['view']['schema']='llm4or-retailopt190-short-decision-request-v2'
        value['context']={'opaque_archetype_id':'b'*64,'selected_skill_ids':selected}
        return value

    def test_pair_differs_only_in_evidence(self):
        base=self._payload('base_short');knowledge=self._payload('knowledge_short')
        knowledge['view']['evidence']=[]
        self.assertEqual(base,knowledge)

    def test_gateway_accepts_label_blind_contract(self):
        cell='a'*64;payload=self._payload('base_short');selected=['retail.core.flow.v1']
        plan={'kind':'fresh_common_external','replicates':[0],'runtime_version':VERSION,'token_cap':10000,
              'external_method':{'name':'RetailOptShortDecisionBlind','scope_stage':'retailblind','max_calls':1},
              'public_inputs':{cell:digest(payload)},'cells':{cell:{'arm':'base_short','opaque_archetype_id':'b'*64,'selected_skill_ids':selected}}}
        validate_fresh_external_payload(plan,f'retailblind:RetailOptShortDecisionBlind:0:{cell}',payload,0,0)
        changed=json.loads(json.dumps(payload));changed['view']['arm']='base_short'
        with self.assertRaisesRegex(Exception,'payload_changed'):validate_fresh_external_payload(plan,f'retailblind:RetailOptShortDecisionBlind:0:{cell}',changed,0,0)


if __name__=='__main__':unittest.main()
