import json
from pathlib import Path
import tempfile
import unittest

from llm4or import fresh_common38_optitrust_style_compact as compact
from llm4or.formal_gateway import FormalGateway, RequestUnavailable
from llm4or.fresh_common38_optitrust_style_compact_audit import build_audit_from, publish_or_check
from llm4or.schema import canonical


ROOT = Path(__file__).resolve().parents[1]


class FakeGateway:
    def __init__(self): self.started=[]; self.finished=[]
    def work_started(self, scope): self.started.append(scope)
    def work_finished(self, scope, status, error=None): self.finished.append((scope,status,error))
    def summary(self):
        return {"physical_attempts":380,"logical_requests":380,"retry_attempts":0,
                "failed_physical_attempts":0,"reserved_or_reported_tokens":7600,
                "logical_tokens":7600,"halt":None}


def recursive_keys(value):
    if isinstance(value,dict):
        for key,item in value.items(): yield key; yield from recursive_keys(item)
    elif isinstance(value,list):
        for item in value: yield from recursive_keys(item)


class FreshCommon38CompactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.plan=compact.build_plan(ROOT)

    def test_plan_binds_38_ten_slots_three_attempts_five_workers_and_resource_limits(self):
        self.assertEqual(len(self.plan["bindings"]),38)
        method=self.plan["external_method"]
        self.assertEqual(method["name"],"OptiTrustStyleCompact")
        self.assertEqual(method["max_calls"],10)
        self.assertEqual(len(method["stage_slots"]),10)
        self.assertEqual(self.plan["matrix"]["logical_requests"],380)
        self.assertEqual(self.plan["limits"]["max_requests"],1140)
        self.assertEqual(self.plan["resilience"]["max_attempts_per_request"],3)
        self.assertEqual(self.plan["resilience"]["max_concurrent_requests"],5)
        self.assertEqual(self.plan["resource_limits"]["serialized_bytes"],196608)

    def test_controller_resumes_and_retains_independent_failures(self):
        unavailable=self.plan["bindings"][0]["id"]; calls=[]
        def runner(public,gateway,scope,replicate,token_cap,**kwargs):
            calls.append(scope); self.assertEqual(kwargs["resource_limits"],self.plan["resource_limits"])
            if scope.endswith(unavailable): raise RequestUnavailable("request_unavailable:synthetic")
            return {"status":"complete","author_accept":False,"consensus":{"status":"no_majority","votes":2},"views":[]}
        with tempfile.TemporaryDirectory() as directory:
            first=compact.run_plan(ROOT,self.plan,Path(directory),FakeGateway(),runner=runner,workers=5)
            second=compact.run_plan(ROOT,self.plan,Path(directory),FakeGateway(),runner=runner,workers=5)
        self.assertEqual(first["terminal"],38); self.assertEqual(first["status_counts"]["infrastructure_unavailable"],1)
        self.assertEqual(second["new_items"],0); self.assertEqual(len(calls),38)

    def test_scoring_is_full_denominator_and_body_free(self):
        cells=[]
        for index,row in enumerate(self.plan["bindings"]):
            record={"status":"complete","author_accept":index<9,"consensus":{"status":"selected","votes":3},
                    "views":[{"status":"optimal","objective":1,"model_sha256":"a"*64}]}
            cells.append({"id":row["id"],"family":row["family"],"status":"completed","record":record})
        result=compact.score_cells(self.plan,cells,FakeGateway().summary())
        self.assertEqual(result["aggregate"]["correct"],9); self.assertEqual(result["aggregate"]["planned"],38)
        prohibited={"request","response","text","code","objective","point","optimum","reference","api_key","components","formulation","views","candidate"}
        self.assertTrue(prohibited.isdisjoint(set(recursive_keys(result))))
        self.assertNotIn("a"*64,json.dumps(result,sort_keys=True))

    def test_offline_audit_reconstructs_380_slots_and_restart(self):
        candidate={"schema":"milp-v1","variables":[{"id":"x","meaning":"fixed","unit":"unit","domain":"binary","lower":0,"upper":0}],
                   "constraints":[],"objective":{"coefficients":{},"sense":"min","unit":"unit","offset":0}}
        from llm4or.schema import digest
        def responder(payload,_body):
            stage=payload["context"]["stage"]
            if stage in {"decomposition","decomposition_reflection"}: text=json.dumps({"components":"bounded"})
            elif stage in {"formulation_outline","formulation_reflection"}: text=json.dumps({"formulation":"bounded"})
            elif stage=="canonical_candidate": text=json.dumps(candidate)
            else: text=json.dumps({"schema":"optitrust-review-v1","candidate_sha256":digest(candidate),"verdict":"accept","edits":[]})
            return {"text":text,"prompt_tokens":10,"completion_tokens":10,"total_tokens":20,"finish_reason":"stop"}
        solver=lambda operation,**kwargs:{"status":"optimal","objective":0}
        with tempfile.TemporaryDirectory() as temporary:
            temporary=Path(temporary); directory=temporary/"offline"; plan_path=temporary/"plan.json"; result_path=temporary/"result.json"; audit_path=temporary/"audit.json"
            plan_path.write_text(canonical(self.plan)+"\n")
            gateway=FormalGateway(ROOT,self.plan,offline=True,directory=directory,responder=responder)
            first=compact.run_plan(ROOT,self.plan,directory,gateway,solver=solver,workers=5)
            second=compact.run_plan(ROOT,self.plan,directory,gateway,solver=solver,workers=5)
            self.assertEqual(first["terminal"],38); self.assertEqual(second["new_items"],0)
            result=compact.score_cells(self.plan,compact.load_cells(self.plan,directory),compact.ledger_summary(directory)); result_path.write_text(canonical(result)+"\n")
            audit=build_audit_from(ROOT,self.plan,plan_path,directory,result_path,expected_offline=True)
            self.assertEqual(audit["checks"]["ledger"]["logical_slots"],380)
            publish_or_check(audit_path,audit,check=False); publish_or_check(audit_path,audit,check=True)

    def test_entrypoints_exist_and_are_frozen(self):
        scripts={"scripts/freeze_fresh_common38_optitrust_style_compact.py","scripts/run_fresh_common38_optitrust_style_compact.py","scripts/score_fresh_common38_optitrust_style_compact.py","scripts/audit_fresh_common38_optitrust_style_compact.py"}
        self.assertTrue(all((ROOT/path).is_file() for path in scripts)); self.assertTrue(scripts.issubset(self.plan["frozen_files"]))


if __name__=="__main__": unittest.main()
