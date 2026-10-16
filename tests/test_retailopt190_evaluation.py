import unittest

from llm4or.retailopt190_evaluation import aggregate_evaluation, one_sided_exact_mcnemar


class RetailOptEvaluationTests(unittest.TestCase):
    def test_exact_tail(self):
        self.assertEqual(one_sided_exact_mcnemar(0, 0), 1.0)
        self.assertAlmostEqual(one_sided_exact_mcnemar(6, 0), 1 / 64)
        self.assertAlmostEqual(one_sided_exact_mcnemar(5, 1), 7 / 64)

    def test_aggregate_pairs_instances_and_archetypes(self):
        rows=[]
        for a in range(2):
            for v in range(5):
                iid=f"i{a}-{v}"
                rows.append({"arm":"base_short","opaque_archetype_id":f"a{a}","opaque_instance_id":iid,"terminal":"complete","solver_status":"OPTIMAL","correct":a==1})
                rows.append({"arm":"knowledge_short","opaque_archetype_id":f"a{a}","opaque_instance_id":iid,"terminal":"complete","solver_status":"OPTIMAL","correct":True})
        result=aggregate_evaluation(rows,inference_completed={"base_short":2,"knowledge_short":2},expected_instances_per_arm=10,expected_archetypes=2)
        self.assertEqual(result["paired_instances"],{"corrections":5,"regressions":0})
        self.assertEqual(result["paired_archetypes"]["corrections"],1)
        self.assertFalse(result["confirmation_gate"]["passed"])


if __name__ == "__main__": unittest.main()
