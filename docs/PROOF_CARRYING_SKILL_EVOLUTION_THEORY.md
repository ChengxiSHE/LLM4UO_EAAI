# Benchmark-Grounded Proof-Carrying Knowledge Compilation

Status: theoretical framework with closed count, TSP and OR-Debug
instantiations, 2026-10-14. The framework organizes the method and its proof obligations. It
does not turn conditional compilation guarantees or same-source confirmation
into an unbounded theorem, cross-source transfer, or autonomous recursive
self-improvement.

For the concise paper-facing mapping from each claim to its executable
obligation, evidence and boundary, see
[THEORY_CLAIM_EVIDENCE_MATRIX.md](THEORY_CLAIM_EVIDENCE_MATRIX.md).

## Central thesis

The knowledge library should be treated as a versioned collection of small
programs with explicit contracts, rather than as retrieved prose. A skill is

`k = (g, e, t, v, r, p)`,

where `g` is a public-input applicability guard, `e` extracts typed evidence,
`t` constructs or transforms a formulation, `v` checks semantic obligations,
`r` checks exact resource limits, and `p` records provenance. An untrusted
proposer may suggest `k`; only the trusted checker can admit it. The benchmark
endpoint, rather than checker acceptance, determines empirical usefulness.

This yields a concise paper story: **knowledge compilation as proof-carrying program
synthesis under benchmark feedback**. The system converts development failures
into typed hypotheses, eliminates hypotheses with counterexamples, compiles the
survivor through a trusted backend, routes it selectively from public evidence,
and promotes a library version only after an independent endpoint test.

The framework is therefore more than a name for a collection of benchmark
patches. It defines what may enter the library, what evidence an entry must
carry, how library complexity is controlled, and which observations may cause
a version update. The model may propose knowledge, but it cannot certify or
promote its own proposal.

At library level, write

```text
L_t = (K_t, rho_t, V, E, ledger_t),
```

where `K_t` is the content-addressed set of skill programs, `rho_t` is the
public-only router, `V` is the immutable verifier, `E` is the frozen benchmark
endpoint, and `ledger_t` contains accepted and rejected lineage. A proposed
skill induces a transition `L_t -> L_(t+1)` only if its proof obligations pass
and the independent promotion rule accepts it. Otherwise the state remains
`L_t`. The verifier and endpoint are outside the state that the proposer may
edit. This is the precise sense in which the system evolves its knowledge
library while keeping its safety boundary fixed.

## Four-layer framework

### 1. Contract language

Each benchmark family has a finite typed language `H_b`. Its fields expose every
fact that can affect correctness: applicability, variable roles, counted scope,
relation semantics, exceptional branches, output binding, and resource policy.
The language is intentionally incomplete. Unsupported or ambiguous public
tasks must yield abstention instead of silently extending the semantics.

The contract language separates three questions that free-text guidance mixes:

1. Does the public task satisfy the skill guard?
2. Does the emitted model preserve the declared source contract?
3. Can the current compiler and solver safely execute it?

### 2. Counterexample-guided construction

Let `D_b` be a declared finite verification domain and `O_b` an independently
implemented contract oracle. Starting from `H_b`, evaluate candidates in a
fixed order. If `h(x) != O_b(x)` for some `x in D_b`, retain the first hashed
counterexample and eliminate `h`. Candidates must also pass the unchanged
schema/compiler and exact resource guards. This is a finite SyGuS/CEGIS
instance; the grammar and oracle are part of the authored method and must be
reported as such.

**Proposition 1 — finite termination.** If `H_b` is finite and every failed
iteration removes at least its current candidate, construction terminates after
at most `|H_b|` candidate decisions.

**Proposition 2 — bounded extensional soundness.** If the verifier enumerates
all `D_b` and accepts `h` only when `h(x)=O_b(x)` for every `x`, then accepted
`h` is extensionally correct on `D_b`. This says nothing about inputs outside
`D_b`, mistakes in `O_b`, or whether the public language was interpreted
faithfully.

### 2.1 Knowledge construction as constrained program learning

The construction step can be stated as a constrained learning problem instead
of an informal sequence of prompt edits. For development records `S_dev`, a
candidate skill `h`, description length `L(h)`, execution cost `C(h)`, and
verified-contract violations `V(h)`, select only from a frozen typed grammar:

```text
h* in argmax_h [corrections(h) - lambda_r regressions(h)
                - lambda_l L(h) - lambda_c C(h)]
subject to V(h)=0 and every declared resource bound passing.
```

The terms have operational meanings. Corrections and regressions are paired
benchmark outcomes, `L(h)` counts the serialized guard, extractor, transform
and verifier rather than English prose, and `C(h)` records model, compiler and
solver costs. Contract violations are hard constraints, not a score that can be
traded against accuracy. The chosen skill is frozen before promotion. This
turns knowledge engineering into **verified structural risk minimization**:
prefer the smallest auditable program that explains reusable failures and
survives counterexamples, rather than memorizing development identities.

For a prefix-free code over a frozen hypothesis family, description length also
has a standard finite-sample interpretation. Let `R(h)` be a Bernoulli error
risk on independent target-distribution units and `R_hat_n(h)` its empirical
risk. Allocating failure probability `delta 2^-L(h)` to each candidate and
applying Hoeffding plus a union bound gives, simultaneously for all candidates,

```text
R(h) <= R_hat_n(h)
        + sqrt((L(h) ln 2 + ln(1/delta)) / (2n)).
```

**Proposition 2a — description-length generalization bound.** Under independent
sampling, a label-independent prefix code and a hypothesis family frozen before
the evaluated labels are opened, the inequality above holds with probability at
least `1-delta`, including for a candidate selected after comparing members of
that frozen family. It does not apply to the current authored grammar on the
same development data that inspired it, to arbitrary LLM-generated programs,
or to synthetic records treated as independent merely because their item IDs
differ. In this project its legitimate role is to motivate compact typed skills
and to analyze untouched promotion or confirmation groups, not to rebrand
development fit as a theorem.

### 2.2 Exact local repair as version-space elimination

For a rejected proposer output `h_0` in a finite grammar, define Hamming
distance over the declared typed choices and let `V(h)` be the unchanged
conjunction of semantic and resource obligations. Exhaustively evaluating
`H_b` yields

```text
d* = min { d(h_0,h) : h in H_b and V(h)=pass }.
```

Returning every passing candidate at `d*` gives an exact minimum-repair
certificate within the grammar. Uniqueness is computed rather than assumed.
If each retained counterexample defines a fixed predicate, the compatible
version space is monotone nonincreasing. When a passing member exists, a learner
that never repeats a rejected member and receives an eliminating witness for
each failure can incur at most `|H_b|-1` rejections before acceptance; an empty
passing set takes `|H_b|` rejections to exhaust. These are finite-class,
verifier-relative facts; they do not establish grammar completeness,
public-language faithfulness or benchmark generalization.

### 3. Proof-carrying compilation and selective routing

For source contract `C`, transformed model `T_k(C)`, and projection `pi`, the
semantic obligation is

`g_k(C) => pi(Sol(T_k(C))) = Sol(C)`.

Optimization also requires objective preservation under `pi`. Exact compiler
statistics form a separate operational certificate: columns, rows, nonzeros,
serialized bytes, and all backend-specific limits must pass. A semantic proof
does not imply resource safety, and a compiled model does not imply semantic
correctness.

The router sees only public input. It returns one pinned skill when exactly one
guard matches; zero or multiple matches abstain to the frozen fallback. For the
current deterministic template router, this gives a checkable recognition
contract but no paraphrase robustness claim. A later learned router is a new
component and must be calibrated and tested separately.

**Proposition 3 — conditional resource safety.** If the trusted compiler's
exact accounting is complete for its declared limits and `r` admits a model,
then the emitted model satisfies those declared limits. The proposition is
conditional on the accounting implementation and does not predict runtime.

**Proposition 4 — accepted-path compositional correctness.** Let `x` be a
public task. Assume (i) the guard accepts only tasks satisfying contract `C`,
(ii) evidence extraction recovers every correctness-relevant field of `C`,
(iii) the compiler preserves feasible solutions and objectives under `pi`,
(iv) the backend returns an exact optimum of the compiled model, and (v) the
projector returns `pi` of that optimum. Then an accepted output is optimal for
`C`. The proof composes the five implications. This is useful because each
premise has a separate executable obligation; it is deliberately conditional
because source-language faithfulness is premise (i)--(ii), rather than
something a MILP solver can prove.

### 4. Endpoint-tested library evolution

Let `A(x)` denote router acceptance, `B(x)` the frozen previous-library output,
and `K(x)` the new skill output. Outside `A`, return the exact coupled `B(x)`.
For binary endpoint correctness,

`Acc(new)-Acc(old) = P(A, B wrong, K right) - P(A, B right, K wrong)`.

The identity explains why coverage alone is insufficient. Every promotion must
report corrections, regressions, abstentions, infrastructure failures, costs,
and family-level effects on a frozen full denominator. Adaptive construction
uses development data; promotion and confirmation require lineage-separated
units or an explicitly dependence-aware analysis. Multiple candidate policies
need a prespecified correction or sequential testing budget.

The trusted verifier may guarantee bounded semantic and resource properties,
but benchmark gain remains empirical because routing, extraction, numerical
solving, output projection, and source-language interpretation can still fail.

**Corollary — conservative extension under dominance.** If the router returns
the previous library byte-for-byte outside `A`, and the admitted skill is never
wrong on an accepted task where the previous library is right, then endpoint
accuracy cannot decrease. The empirical counterpart is the regression term in
the identity above. Zero observed regressions supports dominance only on the
evaluated cohort; it is not a distribution-free proof of future dominance.

### 4.1 Risk-controlled, versioned library updates

Let the paired outcome of a proposed update be one of correction, regression,
unchanged-correct or unchanged-wrong on each independent evaluation group. A
promotion rule should require both a positive lower confidence bound on
`P(correction)-P(regression)` and an upper confidence bound on the regression
mass. If generation `t` receives a prespecified error budget `alpha_t` with
`sum_t alpha_t <= alpha`, exact one-sided tests or confidence bounds can be used
without pretending that repeated adaptive trials constitute one fixed test.

**Proposition 5 — anytime risk-controlled promotion.** Assume every generation
uses fresh evaluation groups drawn from the declared target distribution, the
candidate and router are frozen before their outcomes are opened, and the
generation-specific confidence procedure has error at most `alpha_t`. Then,
by a union bound, the probability that any promoted version violates its stated
promotion condition is at most `sum_t alpha_t <= alpha`. This controls erroneous
promotion decisions under the assumptions; it does not guarantee that a useful
candidate will be found, protect against a wrong evaluator, or convert dependent
synthetic templates into independent samples.

The library is stored as a content-addressed chain. A new version contains the
parent hash, added or replaced skill hashes, retained counterexamples, verifier
version, promotion plan, and rollback target. Exact guard overlap is prohibited;
zero or multiple matches cause abstention. These rules yield three engineering
invariants: rejected candidates cannot become ancestors, fallback outputs are
unchanged outside the accepted region, and rollback reconstructs a prior library
exactly. Monotone population accuracy remains a statistical claim, not an
engineering invariant.

## Construction algorithm

The paper can present the complete methodology as the following six-stage
procedure, which we call **benchmark-grounded proof-carrying knowledge compilation**:

1. **Freeze the endpoint and custody split.** Define full-denominator accuracy,
   independent grouping, development, promotion and confirmation before skill
   construction.
2. **Cluster typed failure obligations.** Convert development failures into
   public-input contract fields, never evaluator answers or item identifiers.
3. **Synthesize a compact skill.** Search a declared grammar under the
   constrained objective above; retain the first counterexample for every
   rejected candidate.
4. **Compile a proof-carrying artifact.** Emit an inert typed transformation,
   semantic obligations, resource certificate, provenance and exact fallback.
5. **Calibrate selective routing.** Freeze public-only guards; report coverage,
   ambiguity, abstention and route errors rather than optimizing accuracy alone.
6. **Promote and confirm.** Apply the alpha-spent paired gate on untouched
   groups, append an accepted version to the content-addressed library, and run
   one final confirmation without further adaptation.

This procedure makes the knowledge-evolution process itself reproducible. An
LLM can implement the proposer in stage 3, a human can author a candidate, or a
finite synthesizer can enumerate it; all three use the same admission and
evaluation boundary. Autonomy is therefore an experimental factor rather than
part of the correctness claim.

## Current count-family instantiation

The partial-count contract uses a six-axis, 64-candidate grammar. Exactly one
candidate survived the declared finite oracle and exact compiler checks. The
main verifier covered 20,977 assignments; independent review performed 930,790
candidate-assignment checks. This is the construction-layer instance of
Propositions 1 and 2.

The first AntChat proposer emitted a structurally invalid free-form candidate.
One counterexample-conditioned typed revision then made one bounded request
(2,307 reported tokens, zero retries). The returned member passed all 20,977
semantic assignment checks but failed the exact compiler resource obligation:
it retained the broad declared-length domains and reached the indicator limit
on the largest public case. It also omitted the zero-tail exception. Thus the
automatic revision did **not** recover the authored skill and is retained as a
negative construction result, not an accuracy gain.

An offline repair certificate subsequently evaluated all 64 hypotheses without
using the authored candidate object for selection. None of the six
distance-one neighbors passed. Changing only the bound strategy exposed a
zero-tail semantic counterexample; changing only the zero-tail policy retained
the resource failure. Their joint change was the unique minimum passing repair
at distance two. The authoritative v3 report
`results/dcp_typed_count_repair_certificate_v3_20261014.json` has SHA-256
`43af5c30bc8bc69f0c60a990f133fe842e9cfee149119bbcf37b08159730d911`.
It consumes an answer-free fixed projection, pins the complete ten-file local
verifier closure before its first verifier import, checks the actually loaded
closure, and verifies file identities again after computation. The earlier v1
and v2 reports remain historical and are superseded.
This is concrete evidence for verifier-mediated version-space elimination and
interaction-aware feedback. It is not evidence that the language model
autonomously found the repair, nor an untreated-arm estimate of a causal
feedback effect.

The expanded library adds complete-count and truth-equivalence contracts and a
strict public-only router. On the frozen 15 exposed development tasks it routes
15/15. In a matched local comparison, `static_broad` compiles 14/15 while
`verified_typed` compiles 15/15. The two policies emit byte-identical proposals
for all 10 non-partial tasks; their only differences are the five partial tasks.
Four partial proposals compile under both policies, while the broad `n=40,m=12`
model fails the exact indicator limit and the typed model compiles. This isolates
a local resource-capacity mechanism.

These facts first established **local compilation headroom**. A frozen paired
numeric stage retained the same15-case denominator and globally reused
byte-identical queries. It made19 physical solver calls for20 reserved exact
queries: static produced14 selected solutions plus one resource rejection,
while verified typed produced15 selected solutions. There were no unknown solve
jobs and independent arithmetic checks passed for all29 selected role outputs.

The evaluator-native endpoint has now judged the18 unique identity-output
candidates and projected them back to all30 roles. Static broad is correct on
13/15 tasks (86.67%): one proposal is an invalid solution and the frozen large
partial-count case is resource-rejected. Verified typed is correct on15/15
(100%). The paired result is two confirmed corrections, zero regressions and
zero missing judgments, a +13.33 percentage-point exposed-development gain.
This supports the proposed resource-and-semantics mechanism and reaches claim
level3 on this exposed development cohort. It does not establish statistical
significance, independent confirmation, transfer or a general natural-language
router: only two pairs are discordant and the router recognizes the exposed
templates exactly.

## TSP constraint instantiation: from headroom audit to prospective transfer

The TSP study instantiates the same framework at a larger endpoint scale. A
strong authored canonical controller was frozen first. Under the official
OPT-Engine rule `|prediction-reference| <= 0.002|reference|`, it scores 48/50
on exposed canonical development: every one of the 48 complete public pair
tables is correct and two truncated source rows remain failures. This is a
useful negative result for the method: an automatic update on that partition
would have no answerable-row headroom, so the framework redirects construction
instead of manufacturing a gain against a weak comparator.

Before inspecting constraint-development text, a single-variant split was
frozen by metadata and size: 100 development rows at sizes 4--8, 80 promotion
rows at sizes 9--12, and 140 confirmation rows at sizes 13--19.
The strong static control scores 48/100 on development. Public abstention texts
expose a repeated formal obligation: one unordered edge is unavailable and
exactly one of two other unordered edges must occur in the Hamiltonian cycle.
The acquired skill is the typed program

`k_tsp = (complete-minus-one graph, forbidden edge, xor(edge_1,edge_2),`
`exactly-once tour, return, minimize)`.

Its compiler re-extracts all weights and quoted obligation spans from the same
public text, requires a unique absent pair, binds two distinct present XOR
edges, and rejects weakened or ambiguous language. Its exact dynamic program
adds an XOR-count bit to the Held--Karp state and never creates the forbidden
edge. Conditional on faithful extraction, the recurrence is exact: each state
stores the least-cost path for a visited set, last node, and XOR count in
`{0,1}`; transitions that would exceed one are discarded, and closure accepts
only count one. Induction on the visited-set size gives optimality for the
typed graph. This is a standard finite-state extension of Held--Karp, not a new
TSP algorithm or a proof of natural-language faithfulness.

The cascade returns the unchanged static controller outside the new guard. On
the 100 exposed development rows it scores 98/100 versus 48/100: 50
corrections, zero regressions, and a +50 percentage-point difference
(`p=2^-50` by the one-sided exact sign test). The two remaining failures are
the same truncated public sources. The aggregate static score was known before
the final skill implementation, but no per-item reference value or per-item
correctness label was method-visible; grammar construction used public
abstention text. The result is therefore development evidence, not an untouched
promotion result.

The skill and comparator were then frozen before the 80 promotion texts were
exported. On prospective same-source size transfer, the static control scores
32/80 (40%) and the skill 64/80 (80%), with 32 corrections, zero regressions,
and `p=2^-32 = 2.3283064365386963e-10`. Accuracy differences are positive at
each size 9, 10, 11, and 12. This is claim-level benchmark evidence for a
benchmark-specific reusable skill and a prospective size-transfer result. It
is still within the same OPT-Engine perturbation source and generator family.

Before the confirmation public projection was exported, both arms were moved
to one directed MTZ exact backend. On all 180 already sealed development and
promotion rows, 162 solved objectives were identical to the original dynamic
program and 18 abstentions were preserved. A separately versioned scalable
frontend then reproduced route, status, adoption and objective behavior on all
180 rows with zero mismatches. This makes the backend change a measured
equivalence step instead of a new method variant.

The frozen size-13--19 confirmation contains 140 rows. The scalable static
control scores 54/140 (38.57%); the skill cascade scores 100/140 (71.43%). The
paired gain is 46 corrections, zero regressions and +32.86 percentage points,
with positive gains at every size from 13 through 19. The nominal one-sided
sign-test value is `2^-46 = 1.4210854715202004e-14`. All 40 skill abstentions
remain in the denominator, and scoring made no new candidate solver or model
calls. This is a sealed, prospective size-confirmation result for the frozen
skill. Independent artifact review passed with no required fixes; root closure
is `results/tsp_constraint_confirmation_root_closure_20261014.json` (SHA256
`0a0aef6aad14e720f537c3201b5cc585b0177c0a05150a18d0300f3e498c437d`).

The confirmation is still within the same OPT-Engine source and perturbation
generator. Shared templates and source lineage make the item-level sign-test
value nominal rather than proof of 140 independent experimental units. It does
not establish cross-source generalization, an independently evolved second
family, or mixed-task routing.

This instantiation also clarifies what is and is not automated. The split,
typed grammar, evidence obligations, compiler, and repair of parser surface
forms are authored engineering driven by benchmark public data. The result
supports **benchmark-grounded proof-carrying skill engineering**. It does not
yet support the stronger claim that an LLM autonomously synthesized the skill
from failures. A future synthesis component must propose within the same typed
grammar and be compared with this authored upper bound.

## OR-Debug-Bench instantiation: cross-source repair knowledge

The pinned OR-Debug-Bench source supplies the planned independent instantiation.
Its 4,962 LP/MIP repair records are grouped into 999 development, 1,118 promotion
and 2,845 confirmation records with no structural-group overlap. Development
has established an inert six-operation repair DSL and a trusted MPS patcher.
All 999 original development models are infeasible and all 999 reference-patched
models solve to optimality. The audit also found that the released Type-B rule
incorrectly restores integer domains for 188 records declared as LP; a frozen
source-corrected continuous-domain policy recovers all 188 recorded objectives.

This source is theoretically useful because it separates three kinds of
knowledge that a prose prompt usually conflates: **diagnostic knowledge**
(which public inconsistency is present), **transformational knowledge** (which
typed edit repairs it), and **certification knowledge** (which unchanged fields,
solver status and objective obligations must hold). A proof-carrying repair is
accepted only when all three agree. Feasibility alone is not the endpoint,
because deleting constraints can repair infeasibility while destroying the
intended formulation.

The constrained-learning experiment is now complete.  A generic solver/IIS
static control was frozen first.  Under the same public bundle, repair DSL,
patcher, solver and hidden scorer, development-derived typed skills were then
frozen before any promotion content was exported.  Development accuracy was
`266/999` (26.63%) for static and `958/999` (95.90%) for evolved.  This large
development difference is descriptive because the rules were authored there.

On the untouched promotion split, static scored `327/1118` (29.25%) and evolved
`1080/1118` (96.60%), yielding 753 corrections, zero regressions and +67.35
percentage points.  Twenty-eight of 37 structural groups improved, nine tied
and none declined.  The prespecified group sign test was `p=3.73e-9`; the
zero-regression group upper bound was 11.17%, so the frozen promotion gate
passed.

The skill, comparator, public-only execution boundary and evaluator then
remained unchanged for one-shot confirmation.  Static scored `828/2845`
(29.10%) and evolved `2752/2845` (96.73%): 1,924 corrections, zero regressions
and +67.63 percentage points.  Ninety-three ambiguous Type-A instances were
explicit abstentions and remained wrong in the denominator.  Sixty-five of 100
structural groups improved, 35 tied and none declined (`p=2.71e-20`); the
one-sided 95% zero-regression group upper bound is 2.95%.

This is the second complete benchmark-source instantiation of the framework.
It demonstrates that the library transition can preserve its endpoint gain
across held-out structural groups after promotion.  It does not prove that
items are independent, that the released benchmark is semantically flawless,
or that an LLM autonomously discovered the typed rules.  The 188 released
Type-B LP domain errors are reported separately through both released and
source-corrected endpoints.  The next compositional test is a frozen mixed
public-only router over the confirmed TSP construction skill and OR-Debug
repair library.

## Relationship to RSI and established theory

The method can be described as a **bounded verifier-mediated improvement loop**:
the current library produces failures, failures propose a finite update, and a
fixed verifier plus an external benchmark gate decides whether the update becomes
the next version. It resembles one restricted component of recursive
self-improvement, but it does not let the system rewrite its verifier, evaluator,
resource policy, or promotion rule. Calling it unrestricted RSI would overstate
both autonomy and guarantees.

The framework combines established ideas from syntax-guided synthesis/CEGIS,
proof-carrying artifacts, selective prediction with abstention, and statistical
policy selection. Compact prefix-coded skills add an Occam/MDL interpretation,
and alpha-spent promotion supplies a sequential testing interpretation. Those
ingredients are not claimed as new. The prospective
contribution is their benchmark-grounded composition for LLM-to-optimization
modeling: typed reusable knowledge, auditable evolution, conditional guarantees,
and endpoint-tested routing under one common interface.

## Falsifiable paper claims

The paper can support progressively stronger claims only when the corresponding
evidence exists:

1. **Mechanism:** typed construction rejects invalid skills and emits a bounded
   verified survivor. Current count evidence supports this claim locally.
2. **Operational value:** verified skills improve compile/solve coverage over a
   matched broad static library. Compilation headroom is observed; solve and
   native evidence are still pending.
3. **Benchmark value:** the library improves final modeling accuracy over Base
   and the strong static control on frozen full-denominator evaluation.
4. **Transfer:** independently constructed skills improve at least two benchmark
   families or sources under their own endpoints.
5. **Routing:** a public-only frozen router preserves those gains on a mixed
   benchmark set with measured abstention and route errors.

Failure at a later level does not erase a valid earlier mechanism result, but it
does narrow the paper's contribution. A top-conference effectiveness claim needs
at least level 3, and the intended general method story needs levels 4 and 5.

## Theory-derived hypotheses and ablations

The framework commits the paper to predictions that can fail:

| Hypothesis | Comparison | Required observation |
|---|---|---|
| Compact typed skills generalize better than memorizing patches | Full method versus equal-budget construction without description-length/identity restrictions | The unrestricted arm may fit development better, but the compact arm must have lower promotion error or equal error at lower complexity |
| Proof obligations prevent destructive apparent repairs | Evolved library with versus without the trusted checker | The unchecked arm may have higher coverage, but must not have lower false-adoption/collateral-change rate for the theory to be supported |
| Evolution adds information beyond a static expert library | Evolved versus frozen equal-interface static control | Positive paired full-denominator gain on untouched promotion and confirmation, with all regressions retained |
| Selective routing creates a risk--coverage tradeoff | Exact guard, successively relaxed guards, and no-abstention routing | Coverage, regression mass and ambiguity must be reported together; accuracy alone is insufficient |
| Knowledge composes across sources | Per-source skills versus the same skills behind one public-only mixed router | Mixed routing preserves most per-source gains without evaluator-visible routing or cross-source guard collisions |
| Sequential gating prevents favorable repeated testing | Frozen alpha-spent gate versus retrospective best-generation selection | Report every rejected generation; only the prespecified gate may support a promotion claim |

The minimal experimental panel is therefore: Base, strong static library,
evolved library without verifier, evolved library without complexity control,
full evolved library, and full library with routing disabled. Each arm must use
the same model, public inputs, request ceiling, DSL, compiler and solver where
the comparison permits it. Primary metrics are full-denominator endpoint
accuracy, paired corrections and regressions, group-level uncertainty, coverage,
ambiguity, abstention, serialized skill length, physical requests, tokens and
solver cost. These requirements prevent the theoretical story from being
validated by a larger prompt or additional attempts alone.
