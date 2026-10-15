# Content-addressed skill and library manifest design

Status: design complete; not implemented or authorized for reconstruction,
2026-10-15. The machine-readable design is
[`content_addressed_library_manifest_design_20261015.json`](../experiments/content_addressed_library_manifest_design_20261015.json).

## Decision

Use two levels of canonical manifests:

1. one **skill manifest** binds the six roles
   $k=(g,e,t,v,r,p)$; and
2. one **library manifest** binds
   $L_t=(K_t,\rho_t,V,E,\operatorname{ledger}_t)$, its parent and its rollback
   target.

This design is preferable to a monolithic bundle because it preserves the
current family boundaries and avoids copying unlicensed or separately licensed
upstream code. It is preferable to an event ledger alone because a ledger does
not provide one deterministic loadable object for execution, rollback and
complexity accounting.

The manifests contain hashes, interfaces, typed semantic payloads and bounded
aggregate evidence. They must not contain benchmark text, reference solutions,
evaluator-only answers, model traffic, credentials or restricted repair
identities.

## Canonical identity

Manifest bodies use UTF-8 compact JSON with sorted object keys, duplicate-key
rejection and no non-finite numbers. The content identity is

\[
\operatorname{sha256}(\operatorname{canonical}(M\setminus
\{\texttt{content\_sha256}\})).
\]

Repository references must be relative POSIX paths with no absolute path,
`..`, symlink or root escape. Publication requires exclusive terminal creation,
file and directory durability, no replacement of an existing terminal object,
and an explicit policy for abandoned reservations.

The current `llm4or.schema` serializer supplies a compatible starting
convention. It is not yet the manifest validator or safe publisher.

## Skill manifest

Each skill manifest binds:

| Theory role | Manifest role | Required content |
| --- | --- | --- |
| $g$ | `guard` | public fields, applicability predicates, ambiguity and abstention behavior |
| $e$ | `extractor` | typed output schema, evidence-binding rules and implementation closure |
| $t$ | `transform` | typed transformation or repair DSL, projection and backend interface |
| $v$ | `semantic_verifier` | oracle/checker interface, declared domain and fail-closed outcomes |
| $r$ | `resource_checker` | exact input/model/backend limits and failure policy |
| $p$ | `provenance` | authorship mode, parent proposal, construction split, verifier and decision hashes |

Every executable role names its interface, semantic version and ordered
first-party path/hash closure. The manifest additionally declares the exact
fallback target and the claim boundary.

A canonical `semantic_payload` records the typed guard, grammar or DSL,
transformation obligations, resource policy and fallback semantics. This field
is necessary because a short path or hash cannot legitimately stand in for all
learned knowledge when description length is measured.

## Library manifest

The library manifest binds the sorted skill-manifest hashes, the public router,
the verifier closure, frozen endpoint identities, the promotion decision and
accepted and rejected ledger references. A successor binds both its parent and
rollback library hashes. Failed promotion creates a rejected ledger event and
does not create a successor version.

The router section states exactly-one matching, overlap handling, zero-match
fallback and its implementation closure. Endpoint sections store identities
and aggregate evidence references without copying evaluator-only answers.

This makes the library version a real reconstructable artifact rather than a
name for a collection of distributed files.

## Operational description length

For the theoretical complexity term, define

\[
\ell(L)=8\,|\operatorname{encode}(S_1,\ldots,S_m,\rho)|,
\]

where `encode` is a frozen prefix-free envelope over the canonical semantic
payloads of every skill and the router. It includes guard predicates, typed
fields, grammar or DSL alternatives, transformations, semantic/resource
policies and fallback rules.

It excludes paths, reconstruction hashes, timestamps, machine metadata,
benchmark identities, evaluation outcomes and request/response bodies. A
semantic payload cannot be replaced by an external pointer: referenced
first-party declarative bytes are included in the encoding. External solver or
upstream benchmark code remains a disclosed execution dependency rather than
learned knowledge.

This definition supplies a nontrivial, auditable object for the Occam/MDL term.
It becomes a valid empirical complexity intervention only when the encoding and
hypothesis family are frozen before the evaluated outcomes. It cannot be
applied retroactively to prove that the current authored libraries generalized
because they were compact.

## Compatibility with other methods

BIND, CoE, OptiTrust, a language model, a human or finite enumeration can all
act as producers. They propose the semantic payload; the same manifest
validator, semantic verifier, resource admission and promotion endpoint decide
whether it enters the library. Byte-identical artifacts under identical
versions must receive identical admission decisions.

This establishes interface compatibility. It does not guarantee that an
external method emits a translatable artifact, passes verification or improves
benchmark accuracy.

## Reconstruction gate

A future implementation is acceptable only if it:

1. validates field allowlists, canonical bytes, paths and closure hashes before
   importing executable modules;
2. preserves separately licensed upstream acquisition boundaries;
3. verifies the parent and rollback identities;
4. reconstructs the current TSP and OR-Debug policies from the manifests; and
5. reproduces the sealed direct-family and 2,985-record mixed hashes without
   changing the endpoint or opening restricted bodies.

Manifest availability alone does not close automatic acquisition, component
causality or clean-clone release. Those remain separate empirical and release
requirements.

This design made no API, model, solver, native-evaluator or VM call, changed no
runtime behavior and read no benchmark body, model traffic, evaluator-only
answer or credential.
