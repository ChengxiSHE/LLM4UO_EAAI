"""Versioned extensions to the frozen v5 semantic-contract grammar.

The v1 module remains byte-for-byte stable because it is bound into the v5
evaluation and blind-audit protocols.  This module adds only a narrow lexical
class for explicitly requested, inherently discrete quantities.  It still
requires a ``how many`` question and a matching ``Number of ...`` business
variable, and it abstains for unlisted measurement quantities.
"""
import re

from .benchmark_inputs import payload_sha256, validate_public_input
from .milp_schema import model
from .schema import digest
from .semantic_contracts import (
    apply_contracts_transactionally, check_contracts, derive_contracts as derive_contracts_v1,
    synthesize_contract_repairs,
)


EXPLICIT_DISCRETE_NOUNS = {
    "bag", "bottle", "can", "day", "experiment", "package", "process", "ream", "taco",
}


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _discrete_tokens(text):
    out=set()
    for token in _tokens(text):
        if token.endswith("es") and token[:-2] in EXPLICIT_DISCRETE_NOUNS:
            singular=token[:-2]
        elif token.endswith("s") and token[:-1] in EXPLICIT_DISCRETE_NOUNS:
            singular=token[:-1]
        else:
            singular=token
        if singular in EXPLICIT_DISCRETE_NOUNS:
            out.add(singular)
    return out


def _explicit_discrete_count_contracts(problem, candidate):
    questions=re.findall(r"\bhow many\s+([^?]+)\?",problem["text"],flags=re.I)
    if not questions:
        return []
    question_tokens=set().union(*(_discrete_tokens(question) for question in questions))
    if not question_tokens:
        return []
    contracts=[]
    for variable in candidate["variables"]:
        meaning=variable["meaning"]
        shared=_discrete_tokens(meaning)&question_tokens
        if meaning.lower().startswith("number of ") and shared:
            contracts.append({
                "kind":"domain","target":variable["id"],"domain":"integer",
                "source":"how_many_explicit_discrete_count","quote":questions[0].strip(),
            })
    return contracts


def derive_contracts(problem, candidate):
    """Return v2 contracts while preserving all v1 contract behavior."""
    p=validate_public_input(problem);m=model(candidate)
    prior=derive_contracts_v1(p,m)
    contracts=list(prior["contracts"])
    targets={item["target"] for item in contracts if item["kind"]=="domain"}
    contracts.extend(item for item in _explicit_discrete_count_contracts(p,m) if item["target"] not in targets)
    out={"schema":"semantic-contracts-v2","input_sha256":payload_sha256(p),
         "model_interface_sha256":digest({"variables":m["variables"]}),"contracts":contracts}
    out["contracts_sha256"]=digest(out)
    return out


__all__=["apply_contracts_transactionally","check_contracts","derive_contracts",
         "synthesize_contract_repairs","EXPLICIT_DISCRETE_NOUNS"]
