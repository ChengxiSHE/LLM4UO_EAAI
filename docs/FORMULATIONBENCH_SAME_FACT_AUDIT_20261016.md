# FormulationBench Flat-K/PCK-K same-fact audit

**Status:** complete 89-pair same-fact verification passed; provider capacity
and prospective execution gates remain open.

Each answer-blind inference record was compiled into a canonical typed fact
graph. The compiler treats problem attributes, parameter declarations,
assumptions, definitions, variables, objectives, constraints and the official
parameter map as typed semantic units. Object order is canonicalized;
assumptions and constraints are treated as order-independent multisets;
nested map direction, index order inside a fact, variable domains, integrality,
bounds and quantifier scope are preserved. Every unit receives a SHA-256
content identity, and the graph identity commits to the complete fact
multiset.

Flat-K and PCK-K receive the same six generic checks with byte-identical text:
parameter compatibility, forward feasibility, backward feasibility,
integrality and bounds, index and quantifier coverage, and objective
preservation. Flat-K lists all facts in one canonical inventory. PCK-K places
each fact exactly once under its typed obligation. The verifier recomputes each
fact hash from the serialized body, reconstructs each multiset and guidance
hash, and rejects additions, removals, mutations, duplicates, missing
obligations or unknown evaluator fields.

The complete fixed inference population produced:

| Quantity | Result |
|---|---:|
| verified pairs | 89 / 89 |
| semantic facts | 4,935 |
| facts per pair | 33–214 |
| unique graph identities | 89 |
| fact-multiset mismatches | 0 |
| guidance variants | 1 |
| guidance mismatches | 0 |
| Flat-K serialized bytes | 9,999–61,190 |
| PCK-K serialized bytes | 10,054–61,245 |

The machine-readable audit is
`experiments/formulationbench_same_fact_audit_20261016.json`, SHA-256
`c70c0ead7bdfcccaf69ecba3398c1b702ef5700f73942c2ac4bfc362b3f4e760`.
It contains only aggregate counts and hashes. It does not contain a task body,
fact body, code, data value, pair label, solution, proof, request, response or
credential.

This closes the operational same-knowledge requirement: both arms receive the
same semantic fact multiset and the same generic checks. It does not show that
PCK-K improves model behavior. The next gate must establish that the isolated
transport can reliably accept the observed input-size envelope and return the
strict short response before any 89-pair plan is frozen.
