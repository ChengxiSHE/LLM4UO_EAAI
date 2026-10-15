import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from llm4or.evaluator import evaluate
from llm4or.fixtures import box, scenario, triangle
from llm4or.gates import paired_evolution_gate, repair_gate, teacher_packet
from llm4or.gateway import Gateway, Limits, MockReply, Stopped
from llm4or.pipeline import run_problem
from llm4or.schema import Invalid, canonical, loads, model, public_problem
from llm4or.solver import compare, execute, solve


def local_solver(op):
    if op["op"] == "solve":
        return solve(model(op["model"]))
    return compare(model(op["left"]), model(op["right"]))


class SchemaTests(unittest.TestCase):
    def test_roundtrip(self):
        self.assertEqual(model(canonical(triangle())), triangle())

    def test_rejects_code(self):
        with self.assertRaises(Invalid):
            model("import os")

    def test_duplicate_json_keys(self):
        with self.assertRaises(Invalid):
            loads('{"a":1,"a":2}')

    def test_nonfinite(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.assertRaises(Invalid):
                loads(value)

    def test_extra_field(self):
        m = box(); m["program"] = "print(1)"
        with self.assertRaises(Invalid):
            model(m)

    def test_domain(self):
        m = box(); m["variables"][0]["domain"] = "integer"
        with self.assertRaises(Invalid):
            model(m)

    def test_missing_coefficient(self):
        m = box(); del m["objective"]["coefficients"]["y"]
        with self.assertRaises(Invalid):
            model(m)

    def test_duplicate_id(self):
        m = box(); m["variables"][1]["id"] = "x"
        with self.assertRaises(Invalid):
            model(m)

    def test_boolean_coefficient(self):
        m = box(); m["objective"]["coefficients"]["x"] = True
        with self.assertRaises(Invalid):
            model(m)

    def test_huge_integer_rejected_without_overflow(self):
        m = box(); m["objective"]["coefficients"]["x"] = 10**1000
        with self.assertRaises(Invalid):
            model(m)

    def test_size_limit(self):
        m = box(); m["variables"] *= 100
        with self.assertRaises(Invalid):
            model(m)

    def test_label_projection(self):
        p = public_problem("q1", {"document": "Question only", "answer": "GOLD_SENTINEL",
                                  "correct_program": "GOLD_SENTINEL", "vars": ["GOLD_SENTINEL"]})
        self.assertEqual(p, {"id": "q1", "text": "Question only"})


class SolverTests(unittest.TestCase):
    def test_omission_equal_optimum(self):
        self.assertEqual(solve(box())["objective"], solve(triangle())["objective"])
        result = compare(box(), triangle())
        self.assertEqual(result["left_to_right"]["status"], "witness")
        self.assertEqual(result["right_to_left"]["status"], "contained_within_tolerance")

    def test_reverse_overconstraint(self):
        result = compare(triangle(), box())
        self.assertEqual(result["right_to_left"]["status"], "witness")

    def test_scaled_and_reordered(self):
        m = triangle(); m["variables"].reverse()
        m["constraints"][0]["coefficients"] = {"y": 7, "x": 7}
        m["constraints"][0]["rhs"] = 7
        r = compare(m, triangle())
        self.assertTrue(all(r[k]["status"] == "contained_within_tolerance" for k in ("left_to_right", "right_to_left")))

    def test_equality(self):
        m = triangle(); m["constraints"][0]["sense"] = "eq"
        self.assertEqual(compare(triangle(), m)["left_to_right"]["status"], "witness")

    def test_infeasible_is_unknown(self):
        m = triangle(); m["constraints"][0]["rhs"] = -1
        self.assertEqual(compare(m, triangle())["left_to_right"]["status"], "unknown")

    def test_unbounded_is_not_equivalence(self):
        m = box()
        for v in m["variables"]: v["upper"] = None
        self.assertEqual(solve(m)["status"], "unbounded")
        self.assertEqual(compare(m, m)["left_to_right"]["status"], "unknown")

    def test_unit_mismatch(self):
        m = box(); m["objective"]["unit"] = "yuan"
        self.assertEqual(compare(box(), m)["status"], "unsupported")

    def test_business_mapping_mismatch(self):
        m = box(); m["variables"][0]["meaning"] = "different decision"
        self.assertEqual(compare(box(), m)["status"], "unsupported")

    def test_preference_reversal(self):
        a, b = triangle(), triangle()
        a["objective"]["coefficients"] = {"x": 2, "y": 1}
        b["objective"]["coefficients"] = {"x": 1, "y": 2}
        self.assertEqual(compare(a, b)["preference"]["status"], "strict_reversal")

    def test_tie_not_equivalence(self):
        m = box(); m["objective"]["coefficients"] = {"x": 0, "y": 0}
        self.assertEqual(compare(m, box())["preference"]["status"], "no_strict_reversal_not_equivalence")

    def test_wall_timeout(self):
        self.assertEqual(execute({"op": "solve", "model": box()}, wall_seconds=0.001)["reason"], "wall_timeout")

    def test_worker(self):
        self.assertEqual(execute({"op": "solve", "model": triangle()})["status"], "optimal")

    def test_worker_rejects_code(self):
        self.assertEqual(execute({"op": "eval", "code": "print(1)"})["status"], "invalid_input")

    def test_evaluation_proxy_is_separate(self):
        r = evaluate(box(), triangle(), solver=local_solver)
        self.assertTrue(r["objective_match_proxy"])
        self.assertEqual(r["formulation_check"], "different")


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def gateway(self, **overrides):
        return Gateway(self.tmp.name, Limits(**overrides))

    def call(self, g, key="one", reply=None):
        return g.request(key, "p1", "test", {"input": "public"}, reply or MockReply("{}"))

    def test_cached_resume(self):
        self.call(self.gateway())
        self.call(self.gateway())
        self.assertEqual(self.gateway().summary()["attempts_including_failures"], 1)

    def test_counter_survives_failure(self):
        g = self.gateway(requests=1)
        with self.assertRaises(Stopped): self.call(g, reply=MockReply("{}", fail=True))
        with self.assertRaisesRegex(Stopped, "request_limit"): self.call(g, key="retry1")
        self.assertEqual(g.summary()["failed"], 1)

    def test_timeout_counted(self):
        g = self.gateway(request_seconds=0.03)
        with self.assertRaisesRegex(Stopped, "timeout"): self.call(g, reply=MockReply("{}", delay=1))
        self.assertEqual(g.summary()["attempts_including_failures"], 1)

    def test_input_limit(self):
        g = self.gateway(input_bytes=1)
        with self.assertRaisesRegex(Stopped, "input_byte_limit"): self.call(g)
        self.assertEqual(g.summary()["attempts_including_failures"], 0)

    def test_output_limit(self):
        g = self.gateway(output_bytes=1)
        with self.assertRaisesRegex(Stopped, "output_byte_limit"): self.call(g)
        self.assertEqual(g.summary()["failed"], 1)

    def test_completion_limit(self):
        g = self.gateway(completion_tokens=2)
        with self.assertRaisesRegex(Stopped, "completion_token_limit"):
            self.call(g, reply=MockReply("{}", completion_tokens=3))

    def test_reservation_is_fail_closed(self):
        g = self.gateway(); self.call(g)
        with sqlite3.connect(g.db) as con:
            con.execute("UPDATE attempts SET status='reserved', response=NULL")
        with self.assertRaisesRegex(Stopped, "reserved"): self.call(self.gateway())
        self.assertEqual(g.summary()["reserved_outcome_unknown"], 1)

    def test_cannot_reset_config(self):
        self.gateway()
        with self.assertRaisesRegex(Stopped, "configuration changed"): self.gateway(requests=100)

    def test_content_collision(self):
        g = self.gateway(); self.call(g)
        with self.assertRaisesRegex(Stopped, "different content"): self.call(g, reply=MockReply("different"))

    def test_cache_integrity(self):
        g = self.gateway(); self.call(g)
        with sqlite3.connect(g.db) as con:
            con.execute("UPDATE attempts SET response='{}'")
        with self.assertRaisesRegex(Stopped, "integrity"): self.call(g)

    def test_concurrency_lock(self):
        g = self.gateway()
        with g._lock():
            with self.assertRaisesRegex(Stopped, "active"): self.call(g)

    def test_per_problem_limit(self):
        g = self.gateway(per_problem=1); self.call(g)
        with self.assertRaisesRegex(Stopped, "request_limit"): self.call(g, key="second")

    def test_run_deadline_survives_restart(self):
        g = self.gateway()
        with sqlite3.connect(g.db) as con:
            con.execute("UPDATE metadata SET started=0")
        with self.assertRaisesRegex(Stopped, "run_wall_limit"): self.call(self.gateway())

    def test_live_transport_refused(self):
        with self.assertRaisesRegex(Stopped, "only offline"):
            self.gateway().request("k", "p", "phase", {}, object())


class PipelineTests(unittest.TestCase):
    def run_case(self, name):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        g = Gateway(tmp.name)
        p, replies, ref = scenario(name)
        return run_problem(p, g, replies, solver=local_solver), g, p, replies, ref

    def test_correction_and_independent_evaluation(self):
        r, g, _, _, ref = self.run_case("correction")
        self.assertEqual(r["repair_gate"]["status"], "accepted_relative_to_evidence")
        self.assertEqual(evaluate(r["semantic_final"], ref, solver=local_solver)["formulation_check"], "same_within_tolerance_exact_objective")
        self.assertEqual(g.summary()["attempts_including_failures"], 5)

    def test_harmful_repair_rolled_back(self):
        r, *_ = self.run_case("overconstraint")
        self.assertEqual(r["repair_gate"]["reason"], "protected_example_regression")
        self.assertEqual(r["semantic_final"], r["initial"])

    def test_unresolved_no_repair_call(self):
        r, g, *_ = self.run_case("unresolved")
        self.assertEqual(r["repair_gate"]["reason"], "teacher_unresolved")
        self.assertEqual(g.summary()["attempts_including_failures"], 4)

    def test_malformed_preserves_failure(self):
        r, g, *_ = self.run_case("malformed")
        self.assertEqual(r["status"], "initial_failed")
        self.assertEqual(g.summary()["attempts_including_failures"], 1)

    def test_restart_no_new_calls(self):
        r, g, p, replies, _ = self.run_case("correction")
        restarted = Gateway(g.directory)
        second = run_problem(p, restarted, replies, solver=local_solver)
        self.assertEqual(second["semantic_final"], r["semantic_final"])
        self.assertEqual(restarted.summary()["attempts_including_failures"], 5)

    def test_whole_record_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, replies, _ = scenario()
            p["answer"] = "GOLD_SENTINEL"
            with self.assertRaises(Invalid): run_problem(p, Gateway(tmp), replies)

    def test_no_labels_in_any_phase(self):
        r, g, p, replies, ref = self.run_case("correction")
        evaluate(r["semantic_final"], ref, solver=local_solver)
        with sqlite3.connect(g.db) as con:
            for (body,) in con.execute("SELECT request FROM attempts"):
                payload = json.loads(body)
                self.assertEqual(set(payload["problem"]), {"id", "text"})
                self.assertNotIn("reference_hash", body)
                self.assertNotIn("GOLD_SENTINEL", body)

    def test_reference_sentinel_never_reaches_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, replies, _ = scenario()
            upstream = {"document": p["text"], "answer": "GOLD_SENTINEL",
                        "correct_program": "GOLD_SENTINEL", "success_rate": "GOLD_SENTINEL"}
            g = Gateway(tmp)
            run_problem(public_problem(p["id"], upstream), g, replies, solver=local_solver)
            with sqlite3.connect(g.db) as con:
                self.assertNotIn("GOLD_SENTINEL", "".join(row[0] for row in con.execute("SELECT request FROM attempts")))

    def test_provenance_tampering(self):
        p, replies, _ = scenario()
        raw = loads(replies["teacher_feedback"].text); raw["quote"] = "invented quotation"
        with self.assertRaises(Invalid): teacher_packet(raw, p, box(), triangle(), compare(box(), triangle()))

    def test_gate_write_scope_and_immutables(self):
        p, replies, _ = scenario()
        packet = teacher_packet(loads(replies["teacher_feedback"].text), p, box(), triangle(), compare(box(), triangle()))
        m = triangle(); m["constraints"].append({"id": "extra", "coefficients": {"x": 0, "y": 1}, "sense": "le", "rhs": 0})
        self.assertEqual(repair_gate(box(), m, triangle(), packet, local_solver)["reason"], "write_scope_violation")
        m = triangle(); m["objective"]["sense"] = "min"
        self.assertEqual(repair_gate(box(), m, triangle(), packet, local_solver)["reason"], "immutable_interface_bounds_or_objective")

    def test_gate_unknown_rejects(self):
        p, replies, _ = scenario()
        packet = teacher_packet(loads(replies["teacher_feedback"].text), p, box(), triangle(), compare(box(), triangle()))
        r = repair_gate(box(), triangle(), triangle(), packet, lambda op: {"status": "unknown"})
        self.assertEqual(r["status"], "rejected")

    def test_budget_exhaustion_retains_initial(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, replies, _ = scenario(); g = Gateway(tmp, Limits(requests=1))
            r = run_problem(p, g, replies, solver=local_solver)
            self.assertEqual(r["status"], "completed_with_errors")
            self.assertEqual(r["semantic_final"], box())

    def test_evolution_statistic(self):
        self.assertFalse(paired_evolution_gate([(True, True)]*10, 1)["accept"])
        self.assertTrue(paired_evolution_gate([(False, True)]*6, 1)["accept"])
        self.assertFalse(paired_evolution_gate([(True, False)]*6, 1)["accept"])

    def test_teacher_claim_can_be_wrong_despite_gate_acceptance(self):
        # Demonstrates a limitation, not a desired efficacy outcome: exact text
        # provenance alone cannot certify the teacher's mathematical interpretation.
        p, replies, ref = scenario()
        wrong_teacher = triangle(); wrong_teacher["constraints"][0]["rhs"] = 0.5
        packet_raw = loads(replies["teacher_feedback"].text)
        packet_raw["positive_examples"] = [{"x": 0, "y": 0.5}]
        evidence = compare(box(), wrong_teacher)
        packet = teacher_packet(packet_raw, p, box(), wrong_teacher, evidence)
        gate = repair_gate(box(), wrong_teacher, wrong_teacher, packet, local_solver)
        self.assertEqual(gate["status"], "accepted_relative_to_evidence")
        self.assertEqual(evaluate(gate["retained_model"], ref, solver=local_solver)["formulation_check"], "different")

    def test_empty_protected_examples_refused(self):
        p, replies, _ = scenario()
        raw = loads(replies["teacher_feedback"].text); raw["positive_examples"] = []
        with self.assertRaises(Invalid): teacher_packet(raw, p, box(), triangle(), compare(box(), triangle()))

    def test_solver_unknown_in_full_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, replies, _ = scenario(); g = Gateway(tmp)
            r = run_problem(p, g, replies, solver=lambda op: {"status": "unknown", "reason": "timeout"})
            self.assertEqual(r["status"], "completed_with_errors")
            self.assertEqual(r["semantic_final"], r["initial"])


if __name__ == "__main__":
    unittest.main()
