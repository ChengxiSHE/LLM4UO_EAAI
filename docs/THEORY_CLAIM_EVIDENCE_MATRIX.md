# Theory-to-evidence matrix for proof-carrying knowledge compilation

Status: paper-facing synthesis, 2026-10-14. This document connects the formal
framework to the evidence that currently exists. It is deliberately shorter
than the complete [theory note](PROOF_CARRYING_SKILL_EVOLUTION_THEORY.md) and
does not replace any experiment-specific closure.

## One-sentence argument

We formulate benchmark-specific knowledge engineering as **proof-carrying
skill evolution**: development failures induce typed candidate programs,
counterexamples eliminate invalid candidates, a trusted compiler checks the
survivor, a public-input router deploys it selectively, and an independently
frozen benchmark endpoint decides whether the new library version is promoted.

This framing makes the contribution a reproducible acquisition and deployment
procedure. It does not describe an agent that is merely told to improve a
score, and it does not claim unrestricted recursive self-improvement.

## Terminology ledger

| Canonical term | Definition | Terms not used as synonyms |
|---|---|---|
| skill | A tuple `k=(g,e,t,v,r,p)` containing a guard, typed evidence extractor, transformation, verifier, resource checker and provenance | prompt, prose hint |
| skill library | A versioned set of mutually routable skills plus an unchanged fallback | memory, context window |
| skill evolution | A frozen candidate-generation, verification and promotion step from one library version to the next | autonomous self-improvement |
| proof-carrying compilation | A skill emits an executable candidate together with checkable semantic and resource obligations | proof of natural-language understanding |
| selective router | A public-input decision rule that returns exactly one pinned skill or abstains | evaluator-guided selector |
| benchmark endpoint accuracy | Full-denominator correctness under the benchmark's fixed status/objective rule | universal formulation equivalence |
| confirmation | Evaluation after the skill, comparator, router and endpoint have been frozen | development replay |

## Formal decomposition

For benchmark family `b`, let `H_b` be a declared finite skill grammar and
`D_b` a declared finite verification domain. A trusted oracle `O_b` rejects a
candidate `h` when it finds `x in D_b` such that `h(x) != O_b(x)`. Every
counterexample is retained. The admitted skill is then checked by the unchanged
compiler and its exact resource accounting.

For deployment, let `A(x)` be router acceptance, `B(x)` the frozen previous
library output and `K(x)` the candidate skill output. The routed system is

```text
R(x) = K(x), if A(x)=1; otherwise B(x).
```

For binary benchmark correctness, its paired effect is exactly

```text
Acc(R)-Acc(B)
  = P(A, B wrong, K right) - P(A, B right, K wrong).
```

The first term is correction headroom; the second is regression risk. This
identity is why coverage, compilation rate or verifier acceptance cannot serve
as the paper's primary effectiveness endpoint.

## Claims, obligations and current evidence

| Claim | Executable obligation | Current evidence | Status and boundary |
|---|---|---|---|
| Finite construction terminates | `H_b` is finite and every failed iteration eliminates at least the current candidate | The count-family grammar contains 64 candidates and retains the first counterexample for every rejected candidate | Established for the declared finite grammar, not for arbitrary programs |
| A promoted rule is extensionally correct on its finite verification domain | Enumerate all `D_b` and compare with an independent oracle | Count-family verification covered 20,977 assignments; independent review performed 930,790 candidate-assignment checks | Established only on `D_b`, conditional on the oracle |
| A rejected finite-grammar proposal admits an auditable minimum-repair certificate | Bind the failed candidate and verifier sources, verify every member of `H_b`, and report all passing candidates at the minimum declared distance | The answer-free v3 count certificate verified all 64 hypotheses; all six distance-one neighbors failed and one distance-two repair was uniquely minimum | Exact within the frozen grammar and verifier; it does not prove grammar completeness or model discovery |
| Compact typed knowledge has a finite-sample complexity interpretation | Freeze a prefix code and candidate family before evaluation labels; report serialized skill length and independent group count | Formal Occam bound is now specified; current authored-development grammars do not satisfy the untouched-data premise | Theoretical design obligation, not a current empirical guarantee |
| An accepted compiled output is correct for its typed contract | Guard soundness, complete evidence extraction, semantics-preserving compilation, exact backend result and correct projection all hold | The TSP skill binds the missing edge and XOR obligation, compiles them into a directed MTZ MILP, and independently checks the returned tour and objective | Conditional compositional guarantee; public-language faithfulness remains a premise |
| Resource limits are respected | Exact counts for rows, columns, nonzeros, bytes and backend limits all pass before execution | Count and TSP compilers fail closed on exceeded limits; the scalable TSP backend was replay-equivalent on all 180 sealed development and promotion rows | Declared-limit guarantee, not a runtime guarantee |
| Fallback is behavior preserving | Outside the accepted region, return the prior output byte-for-byte | Selective harness replay records fallback identity; TSP abstentions remain on the full denominator | Structural guarantee outside adoption, not a universal non-regression theorem |
| A skill provides benchmark value | Positive paired endpoint effect on a frozen full denominator, with regressions and failures retained | TSP size-13--19 confirmation: static `54/140`, skill `100/140`, 46 corrections, 0 regressions, `+32.86` percentage points | Confirmed same-source size transfer; item-level `2^-46` is nominal because templates share lineage |
| The method instantiates across benchmark sources | Independently construct and confirm at least two benchmark-specific skills under the same acquisition and promotion protocol | TSP confirmation improves `54/140` to `100/140`; OR-Debug confirmation improves `828/2845` to `2752/2845`, with zero regressions in both | Supported across two benchmark sources and task types; this is methodological replication, not one skill transferring unchanged across sources |
| A mixed router preserves frozen family behavior | Freeze at least two confirmed skills, route a mixed public-only set and account for route errors, failures and abstention | The frozen 2,985-record TSP/OR-Debug composition routed all 140 TSP and 2,845 OR-Debug records uniquely; every compact mixed output exactly equalled its frozen direct-family output, with zero failures or mismatches | Established as retrospective compositional identity for these public envelopes; it is not a learned-router result or fresh accuracy confirmation |
| An authored proof-carrying skill can add value beyond a static expert library | Compare the skill with an equal-information, equal-capability frozen static control | TSP uses a strong canonical static controller; the typed constraint skill adds positive confirmation gains | Supported for the authored TSP skill; it is not evidence of automatic proposal generation |
| Automatic construction adds value beyond flat feedback | Match source candidates, atomic evidence, grammar, model, budgets and verifier; vary only the feedback organization and retain every assigned outcome | The first bounded AntChat proposer produced a typed candidate that passed 20,977 semantic checks but failed the resource obligation; no matched interaction-aware control has run | Current evidence is a negative construction trace, not a positive automatic-acquisition result |
| Repeated library evolution controls unsafe promotion | Allocate prespecified `alpha_t`, use fresh independent groups, freeze each candidate before outcomes, and archive every decision | OR-Debug used an alpha-allocated 37-group promotion gate before one-shot 100-group confirmation; the gate passed and confirmation retained zero regressions | One realized risk-controlled transition; the anytime theorem still requires fresh groups and valid dependence units for every future generation |
| Search over several candidate libraries controls selection risk | Freeze a prefix-coded candidate family before promotion and allocate candidate budget as `alpha * a_t * 2^-ell(L)` | The rule is derived from Kraft-weighted union control; no current promotion run used this multi-candidate allocation | Prospective protocol guarantee only; outcome-dependent codes or candidate sets invalidate it |
| Repeated updates have a cumulative regression budget | Keep the target distribution and endpoint fixed, bound each promoted transition's population regression mass, and telescope the bounds | TSP and OR-Debug each have zero observed regressions for one transition, but they are different benchmark targets | No current repeated-generation empirical guarantee; zero observations are not population bounds |

The authoritative TSP evidence is the
[confirmation closure](../results/tsp_constraint_confirmation_root_closure_20261014.json).
Its public confirmation result is `54/140` versus `100/140`; all 40 skill
abstentions remain incorrect in the denominator, and scoring made no new model
or candidate-solver calls.

## Relationship to existing results and baselines

The earlier V9 and typed BinPacking studies show that trusted compilation can
improve benchmark endpoint accuracy, but they should not be relabelled as
automatic skill evolution. V9 improves its coupled Base from `200/400` to
`259/400`; typed BinPacking improves from `37/160` to `158/160`. The latter also
has explicit semantic counterexamples, so its positive endpoint result does not
license a broad semantic-safety theorem. These studies motivate the verifier
and abstention layers; the TSP study is the cleaner instantiation of the full
construction-to-confirmation sequence.

The fixed external comparison must remain a separate empirical axis:

| External method | Local evidence | Permitted interpretation |
|---|---|---|
| BIND | Official-prompt local reproduction; first round `31/40`, official answer-bearing final `40/40` on the fixed common-40 cohort | Strong local comparator, but the final round uses answer feedback and is not answer-blind |
| CoE | Official-code adaptation was rerun, but 25 and 29 completed outputs in the two snapshots fell outside the fixed safe adapter | Evidence about the disclosed adaptation; not evidence that native CoE is intrinsically weak |
| OptiTrust | The pinned arXiv v1 source archive contains no verified runnable implementation, training data or checkpoint | Official reproduction unavailable; do not substitute the paper's reported score |

These rows are documented in the
[fixed common-40 report](EXTERNAL_FIXED_COMMON40_RESULTS.md) and the
[compatibility audit](METHOD_BASELINE_COMPATIBILITY_AUDIT.md). They support
reproducibility and positioning, but the different information, feedback and
execution contracts prevent an unconditional leaderboard claim.

## Paper-ready method paragraph

We represent a modeling skill as a typed, proof-carrying program rather than a
retrieved natural-language hint. Each skill specifies a public-input
applicability guard, a typed evidence extractor, a formulation transformation,
semantic and resource verifiers, and provenance. Candidate skills are selected
from a declared finite grammar by counterexample-guided elimination on
development data. The surviving candidate is compiled through a trusted
backend and deployed only when exactly one public-input guard matches;
otherwise, the system returns the frozen previous-library output unchanged.
Library updates are promoted only after full-denominator paired evaluation on a
frozen benchmark endpoint. This separation gives bounded guarantees for finite
construction, declared contracts and fallback identity, while leaving
natural-language faithfulness, routing under distribution shift and endpoint
improvement as empirical questions.

## Paper-ready results and discussion paragraph

Two sources now instantiate the procedure.  In OPT-Engine TSP, a strong static
controller solved 54 of 140 frozen size-13--19 confirmation instances, whereas
the proof-carrying constraint skill solved 100, yielding 46 paired corrections,
no regressions and +32.86 percentage points.  In OR-Debug-Bench, a generic
solver/IIS repair control scored `828/2845` (29.10%) on one-shot confirmation,
whereas the frozen typed repair library scored `2752/2845` (96.73%), yielding
1,924 corrections, no regressions and +67.63 points.  Sixty-five of 100 held-out
structural groups improved and none declined (`p=2.71e-20` by the prespecified
group sign test).  All 93 OR-Debug abstentions remained wrong in the denominator.
Together, the studies support replication of the acquisition methodology across
construction and repair tasks.  A subsequent public-only composition replay
routed all 2,985 frozen confirmation records to the expected family and reproduced
all 2,985 direct outputs exactly.  This establishes behavior preservation for the
frozen mixed interfaces, without recomputing accuracy.  The studies do not show
that one learned skill transfers unchanged across sources, that the authored rules
were synthesized automatically, or that benchmark templates form independent
item-level samples.

## Main-text allocation

- **Main Methods:** skill tuple, finite counterexample-guided construction,
  proof-carrying compiler, selective router and promotion rule.
- **Main Results:** TSP and OR-Debug confirmation effects, full denominators,
  corrections/regressions, and exact mixed-router output preservation.
- **Main Discussion:** conditional nature of the guarantees, retrospective
  composition boundary, the negative first proposer and the unresolved matched
  feedback comparison.
- **Supplementary Information:** complete counterexample ledger, compiler
  accounting, backend-equivalence replay, artifact hashes, external-adapter
  limitations and nominal inference details.

## Theory-derived experimental panel

The framework now fixes six arms for the next independent-source study: Base,
strong static library, evolved library without verification, evolved library
without complexity control, full evolved library, and full library without
selective routing. The primary comparison remains full evolved versus strong
static. The two unsafe ablations are evaluated offline and cannot be deployed.
Every arm must report full-denominator accuracy, paired corrections/regressions,
coverage, ambiguity, abstention, serialized skill size and total construction
and execution cost. This panel is a preregistered consequence of the theory,
not a post-result explanation.

## Research decision

The theoretical framework is now a five-part methodology rather than a loose
analogy: finite program synthesis, proof-carrying compilation, complexity-aware
knowledge selection, selective routing, and risk-controlled version promotion.
The promotion theory now couples the description code to family-wise error
allocation and converts per-transition regression limits into a cumulative
degradation budget on one fixed target. These are prospective protocol
guarantees, not retroactive empirical claims for the current authored skills.
The second-source OR-Debug promotion and confirmation close the largest prior
evidence gap and distinguish the contribution from ordinary prompt or harness
tuning.  The frozen mixed TSP/OR-Debug public-only router now preserves every
direct output on the 2,985-record retrospective composition set. The first
bounded automatic proposer failed its verifier gate, while exhaustive repair
proved a unique two-field interaction within the grammar. The strongest
remaining gap is causal: interaction-aware separating-witness feedback must be
compared with flat feedback under matched evidence, model, budget and verifier.
The current results support benchmark-grounded proof-carrying knowledge compilation
and frozen-interface composition; they do not support unrestricted RSI,
learned routing under distribution shift or fully autonomous knowledge
acquisition.

The authoritative composition artifact is the hardened
[public metadata-only mixed identity audit](../results/mixed_skill_confirmation_public_audit_v3_20261015.json)
(SHA256 `3c9b8700639cfe5599fc76b18cca4318b14d4b0865fb5bd343f5c0d26fead08f`).
It records 2,985 exact matches, zero route or source mismatches, zero terminal
failures, and zero missing, duplicate, invalid or unexpected records.  Its
inherited endpoint counts are descriptive consequences of output identity, not
newly scored observations.  The first audit remains immutable as historical
evidence; v2 adds fail-closed accounting for malformed rows and source identity.
