# Fresh common-protocol estimand audit

## Decision

A reproducible larger-size RCPSP/VRPTW cohort exists, but the experiment is not
ready to freeze or dispatch.  The cohort can support a prospective
size-generalization and mechanism comparison.  With only 38 identities, it
cannot by itself support a broad cross-method superiority claim except for a
very large paired effect.

This audit is metadata-only. It does not display problem text or reference
values, execute gold programs, read request or response bodies, or call a model,
solver, native evaluator or VM.

## Cohort reconstruction

The source is the pinned Text2Opt-Bench revision
`1dac06be656c41d827ef20987cf8af0b48d382a2`.  The prior public preparation kept
canonical small-tier records with at most 96 variables and 192 constraints.
Applying the outcome-blind complement rule to RCPSP and VRPTW yields 38 larger
records:

| Family | Records | Variables | Constraints | Public prompt tokens with data |
|---|---:|---:|---:|---:|
| RCPSP | 13 | 98--181 | 159--311 | 2,900--3,771 |
| VRPTW | 25 | 109--419 | 172--742 | 942--1,534 |

All 38 IDs, source-file hashes, public-text hashes and normalized-text hashes
are unique.  Public-text hash overlap with the existing 183-record prepared
cohort is zero.  Before writing this audit, none of the 38 IDs occurred in
`experiments/`, `results/`, `docs/`, `data/manifests/` or
`data/prepared_benchmarks/`.  All 38 source records have a finite reference
objective and solver status 2; metadata variable and constraint counts match
the corresponding source dictionaries.  No reference value was printed or
copied.

The canonical metadata projection SHA-256 is
`806191d6693ff6f5f50cf2c16b478e0c8c43fb93eea0be936f279befa1d3789c`.
This supports file-level novelty and endpoint readiness.  It does not prove
that no human ever saw an outcome, unseen-family transfer, or independent
template-level sampling.

## Primary estimand

The primary comparison should be **answer-blind common-evidence,
method-native-budget formulation accuracy**.

Every method receives the same content-addressed atomic facts: the public
natural-language description and public structured instance data.  Each method
may render those facts through its own prospectively audited adapter, but no
adapter may add an evaluator value or method-specific fact.  The common
backbone is AntChat DeepSeek-V4-Flash.

Success requires that the output safely compile, reach the declared optimal
solver state and match the frozen objective using relative tolerance `1e-5`
and absolute tolerance `1e-6`.  Parser, schema, compilation, resource, solve,
projection or exhausted transport failures count as incorrect.  Only a global
endpoint outage detected before outcomes are opened may reschedule an entire
affected block under a predeclared rule.

The primary table must report all 38 identities, family-specific results,
paired corrections and regressions versus Base, an exact paired test,
safe-adapter/resource coverage, physical requests, retries and token accounting.

This estimand equalizes information and backbone. It does not equalize compute,
because method-native schedules differ.

## Required separate views

Three views must remain separate:

1. **Equal-budget sensitivity.** Apply the same frozen physical-request and
   token ceiling to every method. This normalizes compute but is not an
   author-native reproduction.
2. **Author-native reproduction.** Preserve official input representation,
   feedback and rounds. This tests reproducibility but cannot form an
   unconditional leaderboard because information and compute differ.
3. **BIND answer-bearing final.** Report official repair after round one as an
   upper-information row outside the answer-blind primary comparison.

OptiTrust remains artifact-unavailable and receives no numerical row unless a
verified author- or venue-linked runnable package appears.

## Rows required in the prospective table

The primary experiment requires Base, strongest matched static knowledge, the
full Benchmark-Grounded Proof-Carrying Knowledge Compilation method, its
claim-critical ablations, BIND first round and CoE safe-adapter. Unsafe
no-verifier or no-resource arms may be scored offline but cannot be promoted or
execute unrestricted generated code.

The current method cannot yet enter the table: RCPSP/VRPTW typed skills, router
and promotion artifacts do not exist.  BIND and CoE have local official-code
reproductions, but their fresh common-fact serializers and candidate-specific
resource admission are not frozen.  These are experiment-construction gaps,
not evidence that any method succeeds or fails on the 38 records.

## Power boundary of 38 identities

For a one-sided exact McNemar/sign test at alpha .05, the power of 38 paired
identities is:

| Discordance `r` | `q=.65` | `q=.70` | `q=.75` | `q=.80` |
|---:|---:|---:|---:|---:|
| .20 | .104 | .164 | .245 | .350 |
| .30 | .173 | .276 | .407 | .558 |
| .40 | .239 | .381 | .549 | .718 |
| .50 | .296 | .469 | .657 | .822 |

Here `q` is the probability that the current method wins conditional on a
discordant pair.  Five corrections and zero regressions give the first nominal
one-sided value below .05, but the design remains poorly powered for moderate
effects.  The 38-record experiment should therefore be framed as
size-generalization confirmation and a mechanism panel.  A definitive
cross-method leaderboard needs a larger independent cohort or replication
across additional source lineages.

## Remaining freeze blockers

The cohort identity and evaluator checks pass.  The experiment is still
missing:

- a content-addressed common atomic-fact packet;
- frozen current-method RCPSP/VRPTW skills and router;
- frozen component-ablation artifacts;
- fresh BIND and CoE serializers with fact-equivalence audits;
- native-budget and equal-budget ceilings;
- an outcome-blind custody receipt; and
- compile-time nonzero and serialized-byte resource admission.

Until these objects exist, no plan, authorization or dispatch namespace should
be created. The machine-readable audit is
`experiments/fresh_common_protocol_estimand_audit_20261015.json`.
