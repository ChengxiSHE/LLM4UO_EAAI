import copy
import unittest

from llm4or.semantic_contracts import (
    apply_contracts_transactionally, check_contracts, derive_contracts,
    synthesize_contract_repairs,
)
from llm4or.semantic_contracts_v2 import derive_contracts as derive_contracts_v2


def problem(text):
    return {"id":"synthetic","text":text,"profile":"description_parameters_v1",
            "parameters":[],"instances":[]}


def variable(identifier, meaning, unit="items", domain="continuous"):
    return {"id":identifier,"meaning":meaning,"unit":unit,"domain":domain,"lower":0,"upper":None}


def base_model(variables, constraints):
    return {"schema":"milp-v1","variables":variables,"constraints":constraints,
            "objective":{"sense":"min","coefficients":{v["id"]:1 for v in variables},"offset":0,"unit":"cost"}}


class SemanticContractTests(unittest.TestCase):
    def test_percentage_of_total_contract_rejects_shortcut(self):
        p=problem("Invest a minimum of 40% of her investment into her younger sister's company, and keep the rest flexible.")
        variables=[variable("younger","Investment in younger sister's company","dollars"),
                   variable("elder","Investment in elder sister's company","dollars")]
        correct=base_model(variables,[{"id":"min_pct","coefficients":{"elder":-0.4,"younger":0.6},"sense":"ge","rhs":0}])
        shortcut=copy.deepcopy(correct);shortcut["constraints"][0]["coefficients"]["younger"]=1
        contracts=derive_contracts(p,correct)
        self.assertEqual(len(contracts["contracts"]),1)
        self.assertEqual(check_contracts(p,correct,contracts)["status"],"passed")
        self.assertEqual(check_contracts(p,shortcut,contracts)["status"],"failed")

    def test_how_many_indivisible_nouns_repairs_all_matching_counts(self):
        p=problem("Two pills are available. How many pills of each should the patient take?")
        m=base_model([variable("p1","Number of Pill 1"),variable("p2","Number of Pill 2")],[])
        repaired,report=synthesize_contract_repairs(p,m)
        self.assertEqual(report["check"]["status"],"passed")
        self.assertEqual({v["domain"] for v in repaired["variables"]},{"integer"})
        self.assertEqual(len(report["edits"]),2)

    def test_divisible_quantity_abstains(self):
        p=problem("How many gallons of fuel should be blended?")
        m=base_model([variable("fuel","Number of gallons of fuel","gallons")],[])
        self.assertEqual(derive_contracts(p,m)["contracts"],[])

    def test_stock_flow_contract_uses_initial_inventory_offset(self):
        p=problem("At location 1, there are currently 12 cars present, but 15 cars are needed. "
                  "At location 2, there are currently 20 cars present, but 17 cars are needed.")
        variables=[variable("x12","Number of cars moved from location 1 to location 2","cars")]
        m=base_model(variables,[
            {"id":"demand_1","coefficients":{"x12":-1},"sense":"ge","rhs":15},
            {"id":"demand_2","coefficients":{"x12":1},"sense":"ge","rhs":17},
        ])
        repaired,report=synthesize_contract_repairs(p,m)
        rows={r["id"]:r for r in repaired["constraints"]}
        self.assertEqual(rows["demand_1"]["rhs"],3)
        self.assertEqual(rows["demand_2"]["rhs"],-3)
        self.assertEqual(report["check"]["status"],"passed")

    def test_transaction_rolls_back_when_interface_cannot_realize_contract(self):
        p=problem("At location 1, there are currently 12 cars present, but 15 cars are needed. "
                  "At location 2, there are currently 20 cars present, but 17 cars are needed.")
        variables=[variable("x12","Number of cars moved from location 1 to location 2","cars")]
        m=base_model(variables,[
            {"id":"demand_1","coefficients":{"x12":-1},"sense":"ge","rhs":15},
            {"id":"demand_2","coefficients":{"x12":1},"sense":"ge","rhs":17},
        ])
        def infeasible(_):return {"status":"infeasible"}
        retained,report=apply_contracts_transactionally(p,m,infeasible)
        self.assertEqual(retained,m)
        self.assertEqual(report["status"],"interface_insufficient")

    def test_v2_explicit_discrete_counts_are_integer(self):
        cases=[("reams","Number of reams of graph paper"),
               ("packages","Number of packages of adhesive"),
               ("cans","Number of cans of paint"),
               ("processes","Number of processes to run"),
               ("experiments","Number of experiments to conduct"),
               ("days","Number of days to operate")]
        for noun,meaning in cases:
            with self.subTest(noun=noun):
                p=problem(f"How many {noun} should the company use?")
                contracts=derive_contracts_v2(p,base_model([variable("x",meaning,noun)],[]))
                self.assertEqual([(x["source"],x["target"]) for x in contracts["contracts"]],
                                 [("how_many_explicit_discrete_count","x")])

    def test_v2_packaged_count_requires_question_and_declared_count(self):
        mentioned=problem("The factory stores packages. How much material should it use?")
        not_count=base_model([variable("x","Material shipped in packages","packages")],[])
        self.assertEqual(derive_contracts_v2(mentioned,not_count)["contracts"],[])
        question=problem("How many packages should the factory ship?")
        self.assertEqual(derive_contracts_v2(question,not_count)["contracts"],[])

    def test_v2_divisible_measurements_still_abstain(self):
        for noun in ("gallons","kilograms","hours","dollars","hectares"):
            with self.subTest(noun=noun):
                p=problem(f"How many {noun} should be allocated?")
                m=base_model([variable("x",f"Number of {noun}",noun)],[])
                self.assertEqual(derive_contracts_v2(p,m)["contracts"],[])


if __name__=="__main__":unittest.main()
