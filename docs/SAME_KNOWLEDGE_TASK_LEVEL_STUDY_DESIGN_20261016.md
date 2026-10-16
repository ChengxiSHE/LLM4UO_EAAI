# Same-knowledge task-level study design

**Status:** design complete; FormulationBench is fixed as the replacement
source and is eligible in principle, but custody, serialization and capacity
gates remain open. No request, model, solver, or native call is authorized by
this document.

## Question

Does a proof-carrying representation improve final formulation accuracy or
failure containment when the semantic knowledge itself is held fixed?

The existing TSP and OR-Debug controls do not answer this question because
they omit knowledge supplied to the successful systems. Their accuracy gains
remain valid complete-system results.

## Frozen comparison

For a new benchmark source or family whose outcomes have not been opened,
construct one canonical, answer-free set of atomic modeling facts before any
endpoint evaluation. A deterministic serializer creates two views:

1. **Flat-knowledge control:** the complete atomic facts are inserted as
   ordinary guidance under a fixed schema.
2. **Proof-carrying treatment:** the same atomic facts are encoded as typed
   guards, evidence fields, transformations, semantic obligations, resource
   obligations, and provenance.

Both arms receive the same public input, fact content, base model, maximum
calls, completion ceiling, solver contract, and endpoint. The serializer must
emit a machine-checkable atom-identity ledger proving that no arm receives an
extra semantic fact. Prompt surface form is allowed to differ because that is
the intervention; token counts must be reported and bounded.

The primary contrast is treatment versus flat knowledge. A no-knowledge Base
may be included only as a secondary anchor and cannot identify the
representation effect.

## Outcomes

The primary endpoint is full-denominator formulation accuracy. Secondary
outcomes are paired corrections and regressions, valid compilation, semantic
rejection, resource rejection, unique routing, abstention, method failure,
infrastructure unavailability, solver status, model calls, provider tokens,
and wall time.

The treatment passes only if it has a positive prespecified paired accuracy
effect, the allowed regression ceiling is met, and the result persists at the
family or source-lineage unit. Improved validation rate alone is insufficient.

## Custody and independence

- Candidate facts, serializers, prompts, router, verifier, resource policy,
  endpoint, denominator, inference unit, and success rule are frozen before
  outcomes are opened.
- Development data may determine the canonical facts. Promotion and
  confirmation groups must be disjoint by the strongest available source-model
  or template lineage, not only by item identifier.
- The existing TSP, OR-Debug, common-38, exposed DCP, and historical Text2Opt
  outcomes cannot be relabeled as confirmation for this study.
- No benchmark is eligible until it has a rights-safe public-input route, a
  scoreable endpoint, a reference-access contract, and a resource contract.

## Routing extension

Routing is tested separately on a frozen mixed-envelope challenge derived
without endpoint labels. The same skill set is used in both arms. The treatment
uses exactly-one selection with fallback; the control uses the prespecified
alternative router. This contrast measures deployment selection, not knowledge
content or formulation generation.

## Current candidate source and why no experiment is launched now

The incomplete MIPLIB-NL release remains rejected and its 220 exact instances
cannot be selected post audit. FormulationBench now supplies the replacement
source at commit `6f37a71e6251b11599ef42869e4268882985a8a7` and tree
`793db197693fac5446fe1bd39aaf178fea437822`. Its explicit MIT license,
path-separated descriptions/formulations/solutions/proofs and exact 89-pair
denominator make it eligible in principle. A body-free tree census agrees with
the official aggregate contract: 20 problems, 109 formulations, 89 pair maps
and 63 positive proofs. No pair identity has been joined to its label or proof.

For this source, the G09 operational endpoint is full-denominator pair-validity
accuracy rather than formulation generation. Flat-K and PCK-K receive the same
canonical formulation facts; only serialization into typed proof obligations
changes. This isolates representation/admission and complements, rather than
replaces, the TSP and OR-Debug formulation-accuracy results.

No experiment is launched because the source has not yet passed full
materialization, answer-blind custody, same-fact serializer and short-output
capacity gates. Labels, solutions, Lean proofs and pair-level proof-presence
metadata remain evaluator-only.

The 219 DCP confirmation block still cannot be opened after its development
gate failed, and the successful TSP, OR-Debug, and common-38 outcomes are
already known. Reusing any of those sets would create a post hoc result rather
than resolve the blind-review concern.
