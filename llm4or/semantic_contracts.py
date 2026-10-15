"""Deterministic semantic contracts for a small, high-confidence OR grammar.

Contracts are derived from public text and the model's declared business
interface.  They never use benchmark answers.  A contract can repair an
existing target, veto a later edit, or abstain when the interface is
insufficient; it cannot invent unrelated variables or silently widen scope.
"""
from copy import deepcopy
import re

from .benchmark_inputs import payload_sha256, validate_public_input
from .milp_schema import model
from .schema import digest


COUNT_NOUNS = {"pill", "container", "chair", "order", "car", "vehicle", "worker", "machine"}


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _count_tokens(text):
    out=set()
    for token in _tokens(text):
        out.add(token[:-1] if token.endswith("s") and token[:-1] in COUNT_NOUNS else token)
    return out & COUNT_NOUNS


def _number(value):
    return int(value) if float(value).is_integer() else float(value)


def _count_domain_contracts(problem, candidate):
    text=problem["text"]
    questions=re.findall(r"\bhow many\s+([^?]+)\?", text, flags=re.I)
    if not questions:
        return []
    question_tokens=set().union(*(_count_tokens(q) for q in questions))
    if not question_tokens:
        return []
    contracts=[]
    for variable in candidate["variables"]:
        meaning=variable["meaning"]
        mtokens=_count_tokens(meaning)
        # Require the interface itself to declare a count and to share an
        # indivisible noun with the question.  This excludes gallons, weight,
        # money, and other divisible quantities even when phrased "how many".
        shared=mtokens & question_tokens
        if meaning.lower().startswith("number of ") and shared:
            contracts.append({
                "kind":"domain", "target":variable["id"], "domain":"integer",
                "source":"how_many_indivisible_count", "quote":questions[0].strip(),
            })
    return contracts


def _ratio_contracts(problem, candidate):
    text=problem["text"]
    pattern=re.compile(
        r"(?:minimum|at least)\s+(?:of\s+)?(?P<pct>\d+(?:\.\d+)?)%\s+of\s+"
        r"(?P<total>[^.]{1,120}?)\s+(?:in|into|on)\s+(?P<part>[^.,]{1,120}?)(?=\s+and\s+|[.,]|$)",
        flags=re.I,
    )
    contracts=[]
    for match in pattern.finditer(text):
        fraction=float(match.group("pct"))/100.0
        part_tokens=_tokens(match.group("part"))-{"the","her","his","their","company"}
        variables=candidate["variables"]
        scores=[]
        for variable in variables:
            tokens=_tokens(variable["meaning"])-{"the","her","his","their","company","investment"}
            scores.append((len(tokens & part_tokens), variable["id"]))
        best=max(scores, default=(0,""))[0]
        winners=[vid for score,vid in scores if score==best and score>0]
        units={v["unit"] for v in variables}
        if len(winners)!=1 or len(units)!=1:
            continue
        part=winners[0]
        total=[v["id"] for v in variables]
        coefficients={vid:-fraction for vid in total}
        coefficients[part]+=1.0
        contracts.append({
            "kind":"row", "target_role":"minimum_fraction_of_total",
            "part":part, "total":sorted(total), "fraction":fraction,
            "row":{"coefficients":{k:_number(v) for k,v in sorted(coefficients.items())},
                   "rhs":0,"sense":"ge"},
            "source":"percentage_of_total", "quote":match.group(0).strip(" .,"),
        })
    return contracts


def _flow_contracts(problem, candidate):
    text=problem["text"]
    observations={}
    for match in re.finditer(
        r"At location\s+(?P<node>\d+),\s+there are currently\s+(?P<stock>\d+(?:\.\d+)?)\s+"
        r"cars present,\s+but\s+(?P<need>\d+(?:\.\d+)?)\s+cars are needed\. ?",
        text, flags=re.I,
    ):
        observations[match.group("node")]=(float(match.group("stock")),float(match.group("need")),match.group(0).strip())
    if len(observations)<2:
        return []
    arcs={}
    for variable in candidate["variables"]:
        match=re.fullmatch(r"Number of cars moved from location\s+(\d+)\s+to location\s+(\d+)",
                           variable["meaning"],flags=re.I)
        if not match:
            return []
        arcs[variable["id"]]=match.groups()
    if not arcs:
        return []
    contracts=[]
    for node,(stock,need,quote) in sorted(observations.items(),key=lambda x:int(x[0])):
        coefficients={}
        for vid,(origin,destination) in arcs.items():
            if destination==node:coefficients[vid]=1
            elif origin==node:coefficients[vid]=-1
        if not coefficients:
            continue
        contracts.append({
            "kind":"row", "target_role":"stock_flow_requirement", "node":node,
            "row":{"coefficients":dict(sorted(coefficients.items())),
                   "rhs":_number(need-stock),"sense":"ge"},
            "source":"initial_plus_inflow_minus_outflow", "quote":quote,
        })
    return contracts


def derive_contracts(problem, candidate):
    """Return deterministic contracts, or an empty set when grammar is unknown."""
    p=validate_public_input(problem);m=model(candidate)
    contracts=[]
    contracts.extend(_count_domain_contracts(p,m))
    contracts.extend(_ratio_contracts(p,m))
    contracts.extend(_flow_contracts(p,m))
    out={"schema":"semantic-contracts-v1","input_sha256":payload_sha256(p),
         "model_interface_sha256":digest({"variables":m["variables"]}),"contracts":contracts}
    out["contracts_sha256"]=digest(out)
    return out


def _same_row(actual, expected, tolerance=1e-9):
    if actual["sense"]!=expected["sense"] or abs(float(actual["rhs"])-float(expected["rhs"]))>tolerance:
        return False
    if set(actual["coefficients"])!=set(expected["coefficients"]):
        return False
    return all(abs(float(actual["coefficients"][k])-float(expected["coefficients"][k]))<=tolerance
               for k in expected["coefficients"])


def _row_target(contract, candidate):
    expected=contract["row"]
    support=set(expected["coefficients"])
    matches=[row for row in candidate["constraints"] if set(row["coefficients"])==support]
    if contract["target_role"]=="stock_flow_requirement":
        named=[row for row in matches if row["id"].lower()=="demand_"+contract["node"]]
        if len(named)==1:return named[0]
    if contract["target_role"]=="minimum_fraction_of_total":
        named=[row for row in matches if "pct" in row["id"].lower() or "percent" in row["id"].lower()]
        if len(named)==1:return named[0]
    return matches[0] if len(matches)==1 else None


def check_contracts(problem, candidate, contracts=None):
    """Check contract truth independently of any teacher/candidate direction."""
    p=validate_public_input(problem);m=model(candidate);bundle=contracts or derive_contracts(p,m)
    results=[]
    variables={v["id"]:v for v in m["variables"]}
    for contract in bundle["contracts"]:
        if contract["kind"]=="domain":
            actual=variables.get(contract["target"])
            passed=actual is not None and actual["domain"]==contract["domain"]
            results.append({"kind":"domain","target":contract["target"],"passed":passed})
        else:
            target=_row_target(contract,m)
            passed=target is not None and _same_row(target,contract["row"])
            results.append({"kind":"row","target":target["id"] if target else None,
                            "role":contract["target_role"],"passed":passed})
    return {"status":"passed" if all(r["passed"] for r in results) else "failed",
            "checked":len(results),"results":results,"contracts_sha256":bundle["contracts_sha256"]}


def synthesize_contract_repairs(problem, candidate, contracts=None):
    """Replace only uniquely aligned rows/domains; report insufficient interfaces."""
    p=validate_public_input(problem);m=model(candidate);bundle=contracts or derive_contracts(p,m)
    repaired=deepcopy(m);edits=[];unresolved=[]
    variables={v["id"]:v for v in repaired["variables"]}
    for contract in bundle["contracts"]:
        if contract["kind"]=="domain":
            target=variables.get(contract["target"])
            if target is None:
                unresolved.append({"kind":"domain","reason":"target_missing","target":contract["target"]});continue
            if target["domain"]!=contract["domain"]:
                edits.append({"kind":"domain","target":target["id"],"before":target["domain"],"after":contract["domain"]})
                target["domain"]=contract["domain"]
        else:
            target=_row_target(contract,repaired)
            if target is None:
                unresolved.append({"kind":"row","reason":"unique_target_not_found","role":contract["target_role"]});continue
            expected=contract["row"]
            if not _same_row(target,expected):
                before={k:deepcopy(target[k]) for k in ("coefficients","rhs","sense")}
                target.update(deepcopy(expected));edits.append({"kind":"row","target":target["id"],"before":before,"after":deepcopy(expected)})
    repaired=model(repaired)
    return repaired,{"schema":"semantic-contract-repair-v1","contracts_sha256":bundle["contracts_sha256"],
                     "edits":edits,"unresolved":unresolved,"check":check_contracts(p,repaired,bundle)}


def apply_contracts_transactionally(problem, candidate, solver, contracts=None):
    """Apply contracts only when the complete repaired model remains solvable.

    A local clause can be correct while the model interface lacks variables
    needed to realize it.  In that case the contract is retained as a
    diagnostic and the original model is returned unchanged.
    """
    original=model(candidate);repaired,report=synthesize_contract_repairs(problem,original,contracts)
    if not report["edits"]:
        return original,{**report,"status":"already_compliant","accepted":False}
    state=solver({"op":"solve","model":repaired})
    if state.get("status")!="optimal":
        return original,{**report,"status":"interface_insufficient","accepted":False,
                         "solve_status":state.get("status")}
    return repaired,{**report,"status":"accepted","accepted":True,"solve_status":"optimal"}
