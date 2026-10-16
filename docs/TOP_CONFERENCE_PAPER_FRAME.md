# Top-conference paper frame

## Authoritative current frame — 2026-10-16 post-review revision

This document is the sole current framing document. Historical plans remain in
Git history and project handoff records; they do not define the present claim.

### Research question

Can benchmark-specific optimization-modeling knowledge be compiled into
versioned, typed artifacts that improve final formulation accuracy while making
their applicability, verification, resource use, routing, fallback, and
promotion decisions auditable?

### Method object

The paper-facing method is **Benchmark-Grounded Proof-Carrying Knowledge
Compilation**. Its object is a versioned library
`L_t=(K_t,rho_t,V,E,ledger_t)`:

- `K_t` contains content-addressed skills with an applicability guard, typed
  evidence extractor, formulation transformation, semantic checks, resource
  checks, and provenance;
- `rho_t` is a public-input router that selects exactly one skill or returns
  the prior system unchanged;
- `V` is the trusted verification and compilation boundary;
- `E` is the frozen benchmark endpoint;
- `ledger_t` binds accepted, rejected, parent, and rollback lineage.

The proposer may be a person, finite search, or a language model. The current
successful TSP and OR-Debug libraries were authored from development failures.
The outer Codex goal loop is research administration and is not part of the
method.

### Evidence hierarchy

1. **System-level benchmark evidence.** On frozen confirmation cohorts, the
   complete authored pipelines improve final formulation accuracy over named
   controls. These are the headline empirical results.
2. **Deployment invariants.** The public-only router reconstructs all 2,985
   direct-family outputs exactly and fails closed outside unique coverage.
3. **Exhaustive contract tests.** Finite authored populations test semantic
   admission, resource admission, routing, active witness selection, and
   description-length selection. These establish behavior of the declared
   contracts, not causal attribution for the benchmark gains.
4. **External implementation comparisons.** Base, BIND, and CoE-safe are rerun
   on a common frozen cohort under disclosed unequal information and execution
   regimes. OptiTrust has no verified runnable official artifact in the audited
   source; the separately labeled indexed reimplementation fails its method
   gate and has no accuracy row.
5. **Prospective theory.** Sequential risk budgets and complexity-weighted
   promotion are conditional protocol guarantees. They were not implemented by
   the completed TSP or OR-Debug studies.

### Headline results

| Study | Control | Complete authored method | Corrections / regressions | Interpretation |
|---|---:|---:|---:|---|
| TSP, sizes 13--19 | 54/140 | 100/140 | 46 / 0 | Same-source held-out-size system result |
| OR-Debug, released labels (primary) | 828/2,845 | 2,236/2,845 | 1,408 / 0 | Public benchmark-label system result |
| OR-Debug, source-corrected sensitivity | 828/2,845 | 2,752/2,845 | 1,924 / 0 | Prespecified semantic sensitivity; not the primary headline |
| Fresh common-38 | Base 0; BIND round 1/final 13/13; CoE-safe 4 | 30/38 | 30/0, 18/1, 18/1, 26/0 | Frozen implementation comparison under unequal regimes |
| Mixed router | 2,985 direct outputs | 2,985 exact identities | 0 mismatches | Retrospective preservation, not a new accuracy score |

The TSP and OR-Debug results demonstrate improved benchmark formulation
accuracy for the complete systems. Because the controls do not receive the
same semantic knowledge in another representation, these experiments do not
show that proof-carrying representation, verification, routing, or promotion
caused the gains.

### Main contributions

1. An optimization-specific artifact model for benchmark knowledge, including
   formulation semantics, exact resource obligations, selective routing,
   provenance, rollback, and frozen solver-facing endpoints.
2. A set of conditional guarantees whose assumptions and trust boundaries are
   explicit, plus exact implementation checks for fallback and content-addressed
   reconstruction.
3. Two full-denominator benchmark case studies with large formulation-accuracy
   gains, explicit abstentions, released-label sensitivity, and zero observed
   paired regressions.
4. A common-cohort implementation comparison with locally rerun Base, BIND,
   and CoE-safe rows and preserved information, budget, adapter, and licensing
   boundaries.
5. Exhaustive finite contract tests and a negative language-model acquisition
   trace that distinguish what has been implemented, measured, and left
   prospective.
6. A history-free public release, aggregate reconstruction command, controlled
   endpoint-review protocol, scoped licensing, and claim-level evidence map.

### Claims that are not supported

The manuscript must not claim:

- that the architecture's individual mechanisms caused the TSP or OR-Debug
  gains relative to a same-knowledge alternative;
- equal-budget or broad algorithmic superiority from common-38;
- transfer of one unchanged skill across benchmark sources;
- independent item-level sampling for template-related benchmark rows;
- natural-language fact or grammar discovery;
- unrestricted recursive self-improvement;
- that the source-corrected OR-Debug labels are publicly adjudicated or more
  authoritative than the released labels;
- that exhaustive authored finite populations estimate natural proposal or
  deployment distributions.

### Current scientific gap

The strongest remaining scientific experiment is a prospectively frozen,
task-level **same-knowledge comparison**. It must hold semantic knowledge,
public inputs, endpoint, and resource budget fixed while varying how that
knowledge is represented, admitted, or deployed. Already opened TSP,
OR-Debug, and common-38 outcomes cannot serve as a new confirmation set. Until
this gap is closed, the paper is a rigorous systems case study rather than a
causal validation of every architectural component.

MIPLIB-NL was rejected after its current release failed whole-source
materialization, with no bundle or experiment dispatched. FormulationBench is
now fixed as the replacement source before any task, pair label, solution or
Lean proof body is opened. Its 89 reformulation pairs support a full-denominator
same-fact comparison between flat and proof-obligation serialization. This is
a prospective G09 mechanism study of representation and admission; it does not
replace the existing formulation-generation accuracy endpoints, and it remains
non-dispatchable until custody, serializer and short-output capacity gates pass.

### Reproducibility state

The immutable public release is `v1.1.1`, commit
`ed663fcdf8336f77c466652a516d5bc2c567f93a`. Its history-free recursive clone
passed 81 Layer-A tests and three deterministic checks. The submission overlay
adds manuscript-only evidence and does not mutate that release. The public
aggregate claim table is rebuilt by:

```bash
python3 scripts/build_reviewer_claim_table.py --check
```

The full evidence route and controlled-access boundary are in
[`manuscript/REVIEWER_EVIDENCE_INDEX.md`](../manuscript/REVIEWER_EVIDENCE_INDEX.md).
An external archival DOI remains unavailable and is not claimed.

### Submission posture

Three mutually blind reviews converged on a major-revision decision. The
system-level accuracy case is supported; mechanism attribution, closest-method
novelty, and breadth remain the main scientific risks. The current manuscript
must lead with the bounded system result, treat finite censuses as contract
tests, make released OR-Debug labels primary, and keep the same-knowledge study
as an open gate rather than implying it has already been completed.
