# Theory-to-implementation conformance audit

Status: behaviorally conformant; artifact conformance partial, 2026-10-15. The
machine-readable source is
[`theory_implementation_conformance_audit_20261015.json`](../experiments/theory_implementation_conformance_audit_20261015.json).

## Decision

The theoretical skill and library definitions describe the behavior of the
current TSP, OR-Debug and mixed-routing implementation, but they are not yet the
literal shape of one canonical released artifact. The six skill roles

\[
k=(g,e,t,v,r,p)
\]

are present for both families. The library roles

\[
L_t=(K_t,\rho_t,V,E,\operatorname{ledger}_t)
\]

are also present across code, plans, result closures and the mixed executor.
What is missing is one content-addressed skill manifest per family and one
parent-linked library manifest that binds those distributed pieces together.

This distinction matters for the paper. The current evidence supports the
behavioral method claims and the frozen accuracy results. It does not yet show
that a clean clone can reconstruct an exact library version from one manifest,
or that the serialized library length used in the theoretical complexity term
is already an operational measurement.

## TSP skill

| Role | Current implementation | Assessment |
| --- | --- | --- |
| Guard $g$ | The scalable extractor accepts the frozen size and relation envelope; failures invoke the static path | Present and fail closed |
| Extractor $e$ | Public graph, missing edge, exactly-one relation, tour objective, unit and quoted evidence are re-extracted | Present |
| Transformation $t$ | The typed contract is compiled to the constrained graph and directed-MTZ backend | Present |
| Verifier $v$ | Candidate bytes are rebound to a fresh extraction; returned tours and objectives are independently decoded | Present, distributed across compiler and backend |
| Resource checker $r$ | Input, candidate, graph and backend limits fail closed | Present, distributed across modules |
| Provenance $p$ | Version strings, question hashes, code pins and the root closure exist | Present, but not one canonical skill manifest |

The authoritative endpoint evidence remains the frozen TSP confirmation root
closure. This audit does not recompute its accuracy or alter its claim boundary.

## OR-Debug skill library

| Role | Current implementation | Assessment |
| --- | --- | --- |
| Guard $g$ | Exactly one public error type and LP/MIP source class must match | Present and fail closed |
| Extractor $e$ | Public problem text, public MPS structure and fresh IIS evidence become typed fields | Present |
| Transformation $t$ | A finite six-operation repair DSL changes the MPS | Present |
| Verifier $v$ | Exactly one executable candidate must remain; the hidden endpoint checks the frozen result | Present, split between public and evaluator layers |
| Resource checker $r$ | MPS, solver, time and thread limits are enforced by runner/backend code | Present, not embedded in each proposal object |
| Provenance $p$ | Skill IDs, schema, source declaration, source hashes, plan hashes and result hashes exist | Present, with ancestry distributed across artifacts |

This is sufficient for the bounded behavioral claim that the frozen typed
repair policy was evaluated under a pinned execution boundary. It is not yet a
self-contained proof-carrying package that another process can load by a single
skill hash.

## Library state

The mixed executor already pins the TSP and OR-Debug code closure and uses an
explicit exactly-one public router. The 2,985-record audit establishes exact
output identity with the two direct family runs. Therefore the implemented
composition behaves like the theoretical library on the frozen cohort.

The following artifact-level gaps remain:

1. $K_t$ is implicit in pinned code paths rather than a canonical array of
   skill-manifest hashes.
2. $V$ is distributed across family modules and has no single verifier-closure
   identity.
3. $E$ exists in sealed family results but is not directly bound by a library
   manifest.
4. accepted and rejected evidence exists, but not as one parent-linked version
   ledger with an explicit rollback target.
5. the theory's description length $\ell(L)$ has no canonical serialized
   library object from which it can be measured.

## Consequence for the methodology

The theory is not merely decorative: all required behaviors already exist and
are exercised in the reported experiments. The remaining discrepancy is an
artifact-design and reproducibility problem. Closing it would strengthen three
claims without changing the underlying method:

- an exact library version can be named by one hash;
- every admitted skill carries its executable obligations and provenance; and
- complexity control refers to the serialized skill-and-router artifact rather
  than an informal source-code count.

It would not establish automatic acquisition, natural-language faithfulness,
distribution-free non-regression or a new accuracy result.

## Closure contract

A future implementation should introduce an answer-free skill manifest binding
the six roles by interface, version, file hash and declared limits. A library
manifest should bind the skill manifests, router, verifier closure, endpoint
identities, parent version, rollback target, promotion decision and ledger
references. Reconstruction must reproduce the existing direct-family and
mixed-output hashes before the new artifact can replace the distributed
representation.

This audit is read-only with respect to the method and results. It made no API,
model, solver, native-evaluator or VM call and read no request body, response
body, evaluator-only answer or credential.
