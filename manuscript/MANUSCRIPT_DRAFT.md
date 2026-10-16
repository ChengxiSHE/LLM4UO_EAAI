# Benchmark-Grounded Proof-Carrying Knowledge Compilation for Reliable Optimization Modeling

**Status:** evidence-grounded manuscript draft, 16 October 2026. Results in this
document are restricted to terminal artifacts bound by the project evidence
manifest. The eight-pair matched-feedback engineering canary is complete and
negative; the fresh RCPSP/VRPTW common-protocol comparison, bounded finite
component censuses and a bounded active-acquisition census are complete. The
history-free public release, independent public integrity review and controlled
endpoint recomputation are complete. Natural-language fact acquisition, broader source replication, an
archival DOI, and submission-specific formatting remain incomplete. Figures 1 and 2 have
passed publication-size render and visual QA.
A claim-level audit is maintained in
[`MANUSCRIPT_EVIDENCE_AUDIT.md`](MANUSCRIPT_EVIDENCE_AUDIT.md).

## Abstract

Language models can generate executable optimization programs, yet a program
that parses and solves may still encode the wrong feasible region, objective,
or relation between quantities. Repeated prompting provides limited protection
against such errors because free-form guidance is difficult to verify, route,
version, and retire. We study **Benchmark-Grounded Proof-Carrying Knowledge
Compilation**, an optimization-modeling methodology that represents reusable
knowledge as typed programs with explicit applicability, evidence extraction,
transformation, semantic verification, resource admission, and provenance
contracts. In the two successful studies, benchmark-specific skills are
authored inside this protocol; automatic proposal is evaluated separately as a
negative diagnostic. We formalize construction as proof-constrained structural
risk minimization over a versioned library: candidate skills are induced from
benchmark development failures, checked by an immutable verifier and compiler,
deployed only through a public-input router that abstains on ambiguity, and
promoted according to a frozen endpoint on held-out groups. On a frozen
traveling-salesperson-problem (TSP) confirmation set, a canonical directed-MTZ
controller solves 54 of 140 instances,
whereas the typed constraint skill solves 100, yielding 46 paired corrections,
no regressions, and a 32.86 percentage-point gain. On OR-Debug-Bench, a generic
fresh-IIS static repair control solves 828 of 2,845 instances and the typed
repair library solves 2,752 under the frozen source-corrected endpoint,
yielding 1,924 corrections, no regressions, and a 67.63 point gain. The
unmodified released-label endpoint gives 2,236 of 2,845. Sixty-five of 100
held-out structural groups improve and none decline
($p=2.71\times10^{-20}$, prespecified group sign test). A fail-closed
router subsequently reproduces all 2,985 direct-family outputs exactly. On a
fresh common cohort of 38 larger RCPSP/VRPTW instances, proof-carrying
compilation is correct on 30, compared with 13 for answer-blind BIND and 4 for
CoE-safe; the one-call Base is correct on none. The paired current-versus-BIND
comparison contains 18 corrections and one regression (Holm-adjusted
$p=7.63\times10^{-5}$). This fixed-cohort comparison uses unequal native
inference budgets, does not equalize authored construction cost or provider
tokens, includes answer-bearing feedback only in the separately reported BIND
final row, and covers two families from one source lineage. A bounded automatic
proposer passes 20,977 semantic assignments but
fails an exact resource obligation. In a subsequent eight-pair engineering
canary, fact-equivalent flat and verifier-partitioned feedback both admit all
eight proposals, with zero discordant pairs; the prespecified progression gate
therefore fails. In a separate exact census over the 10 extensionally distinct
classes induced by the frozen semantic grammar, balanced verifier-selected
witnesses identify 10/10 classes within three queries, versus 6/10 for a
fixed-order separating-witness control. In a separate complete library census,
proof-constrained description length selects a fully correct router library in
64/64 calibration episodes, versus 1/64 for a proof-only frozen-hash selector,
with 132 routing-decision corrections and no regressions. These results support auditable,
benchmark-specific skill
engineering with conditional guarantees; they do not establish universal
semantic correctness or natural-language fact discovery.

## 1. Introduction

Natural-language optimization systems must cross two distinct boundaries.
They must first infer the intended variables, relations, domains, and objective
from a public problem description, and must then encode that interpretation in
an executable model. A solver certifies neither boundary. It can optimize a
malformed model, and a numerically plausible objective may hide a missing
constraint or an incorrectly bound parameter. Consequently, parse success,
compiler acceptance, solver status, and objective agreement are useful
diagnostics but insufficient substitutes for final benchmark formulation
accuracy.

Existing systems improve language-to-optimization modeling through structured
grounding, multi-agent collaboration, iterative repair, and synthetic
verification. BIND separates template reasoning from instance binding and uses
evaluation feedback to repair generated code [@gao2026bind]. Chain-of-Experts
(CoE) delegates terminology, modeling, programming, and review to specialized
agents [@xiao2024chainofexperts]. OptiTrust proposes verifiable synthetic data
as a route toward trustworthy modeling agents [@lima2025optitrust]. These
methods motivate stronger reasoning and verification, but they leave an
optimization-modeling systems question: how should reusable benchmark-derived knowledge be
represented, checked, selectively deployed, and promoted without allowing the
same proposer to redefine its own correctness boundary?

We address this question by treating modeling knowledge as a versioned program
artifact rather than retrieved prose. A skill carries an applicability guard,
a typed evidence extractor, a formulation transformation, semantic and
resource checks, and provenance. Development failures define candidate
obligations and counterexamples. A trusted compiler admits only artifacts that
satisfy their declared checks. A public-only router chooses exactly one pinned
skill or returns the previous system unchanged. Finally, a frozen benchmark
endpoint, rather than verifier acceptance alone, determines whether the new
library version is empirically useful.

This process can be viewed as proof-constrained structural risk minimization
over a versioned skill library. The learned object contains both the skill set
and its router; its empirical endpoint error is balanced against a prefix-code
description cost and declared execution cost, while semantic and resource
obligations remain hard constraints. Under exactly-one routing, the utility of
the whole library decomposes into routed corrections minus routed regressions,
so adding a narrow rule is valuable only when its accepted region improves the
frozen endpoint.

This design separates proposal from certification. A skill may be proposed by
a human, a language model, or finite search; proposer autonomy is an
experimental factor rather than a correctness premise. The verifier, endpoint,
resource policy, and accepted lineage remain outside the state that the
proposer may edit. The resulting process is a bounded form of artifact
evolution, not weight-level or unrestricted recursive self-improvement.

Our contributions are:

1. We formulate benchmark-derived optimization knowledge as proof-carrying
   typed skills and cast construction as proof-constrained structural risk
   minimization over a versioned skill-and-router library.
2. We state bounded guarantees for finite construction, correctness on an
   enumerated verification domain, minimum repair within a frozen grammar,
   declared resource compliance, conditional accepted-path correctness,
   unchanged fallback, modular multi-skill utility, library-level complexity,
   and sequential promotion risk.
3. We demonstrate prospective endpoint gains over a frozen canonical TSP
   controller and a frozen fresh-IIS OR-Debug repair control, followed by exact
   retrospective composition behind one public-only router.
4. We audit local BIND and CoE reproductions under disclosed safe-execution
   adapters and retain OptiTrust as artifact-unavailable because the inspected
   author source does not provide a verified runnable implementation.
5. We report a negative language-model construction trace, an exact
   minimum-repair certificate, and a prospective eight-pair feedback canary
   with zero paired discordance. A separate complete finite census then shows
   that balanced active witnesses identify all 10 extensional semantic classes
   within three queries, versus 6/10 for a fixed-order control. This supports
   bounded automatic acquisition inside the frozen grammar while ruling out a
   natural-language fact-discovery claim.
6. We rerun Base, BIND and CoE on a fresh RCPSP/VRPTW cohort shared with the
   current method, and we enumerate bounded component populations showing an
   exact semantic-admission effect, an exact resource-admission effect and an
   exact selective-routing effect. A separate complete shadow-guard library
   census identifies a bounded complexity-control effect while retaining the
   negative language-model acquisition result and explicit finite-population
   boundaries.

## 2. Related work

### 2.1 Language-to-optimization modeling

Language-to-optimization systems differ in what information they receive, what
they emit, and how their outputs are judged. BIND receives structured instance
data and can use answer-bearing evaluation feedback after its initial response
[@gao2026bind]. CoE coordinates multiple specialist prompts before reducing
their comments into a program [@xiao2024chainofexperts]. OptiTrust emphasizes
the generation of verifiable synthetic supervision [@lima2025optitrust]. We
compare these systems through their disclosed interfaces and locally runnable
artifacts. Published scores provide literature context but are not inserted as
local empirical rows.

### 2.2 Program synthesis and counterexamples

Our finite skill grammars draw on syntax-guided synthesis and sketch-based
program construction [@solarlezama2008sketching; @alur2013sygus]. Candidate
fields delimit a search space, and verifier counterexamples remove inconsistent
members. We do not claim a new general synthesis algorithm: each grammar and
oracle is an authored component, and the associated soundness statement is
restricted to its declared finite domain.

### 2.3 Proof-carrying and validated compilation

Proof-carrying code separates an untrusted producer from a trusted checker
[@necula1997proofcarrying], while translation validation checks a concrete
translation rather than trusting a compiler implementation wholesale
[@pnueli1998translation]. Our skills follow the same separation at the
artifact level. Their certificates concern declared semantic and resource
obligations; they do not prove that arbitrary natural language has been
interpreted faithfully.

### 2.4 Selective prediction and controlled updates

A fail-closed router creates a risk--coverage trade-off related to selective
prediction [@elyaniv2010selective]. Compact, prefix-coded skills motivate an
Occam-style complexity interpretation [@blumer1987occam], and risk-controlled
promotion is related to high-confidence policy improvement
[@thomas2015hcpi]. Generalized binary search provides a useful language for
separating witnesses in finite spaces [@nowak2011gbs], but logarithmic query
bounds require additional splitting assumptions and are not claimed for the
language-model proposer used here.

### 2.5 Skill libraries and skill evolution

Recent work makes clear that reusable agent knowledge should be evaluated as
an evolving library rather than as an unversioned prompt. SkillOpt treats a
single textual skill as trainable external state and accepts bounded edits only
after held-out improvement [@yang2026skillopt]. SkillOps introduces typed skill
contracts and library-level maintenance [@pu2026skillops], while SkillSpec
separates consensus-gated content updates from representation specialization
[@chen2026skillspec]. SkillForge verifies and refines skills through
reinforcement-learning interaction [@yang2026skillforge], and Skill-V uses
versioned falsifiable contracts, outcome-grounded revision and
applicability-aware filtering [@ma2026skillv]. HASP further shows that skills
can be executable programs with activation checks and direct intervention in
an agent loop [@liu2026hasp]. SkillsBench supplies matched paired evidence that
curated skills can materially change task success and that skill efficacy must
be measured under deterministic endpoints [@li2026skillsbench].

Table 1 compares the objects and decision signals emphasized in the primary
sources. It is a scope map rather than an assertion that an unlisted mechanism
is absent from a system.

| System | Retained or updated object | Disclosed update or acceptance signal | Scope relevant to this paper |
|---|---|---|---|
| SkillOpt | One natural-language skill document | Held-out score improvement after bounded textual edits | Reproducible text-space skill optimization |
| SkillOps | Typed skill contracts and a hierarchical ecosystem graph | Library-health diagnostics over utility, compatibility, risk and validation | Method-agnostic library maintenance |
| SkillSpec | Complete textual skills plus flat, graph or hybrid organization | Consensus across paired evaluations, followed by representation specialization | Separates knowledge retention from organization |
| SkillForge | An interaction-grounded skill bank used by an RL agent | Environment evidence and explicit skill use during training | Continuous verified skill refinement in interactive environments |
| Skill-V | Versioned falsifiable contracts with applicability conditions | Rubric--outcome agreement, protected constraints and historical non-regression | Outcome-grounded revision and applicability filtering |
| HASP | Executable program functions with activation checks | Teacher-reviewed validation and controlled evolution | Direct intervention in an agent loop |
| This work | Typed optimization transformations with public guards, semantic obligations, exact resource obligations and provenance | Immutable verifier admission followed by grouped full-denominator formulation-accuracy promotion | Solver-facing optimization modeling with exact fallback outside unique coverage |

SkillsBench is complementary to these construction systems: it supplies a
paired no-skill/curated-skill evaluation protocol with deterministic verifiers,
rather than another library-update rule [@li2026skillsbench].

These concurrent systems rule out a broad novelty claim for versioning,
validation-gated updates, typed contracts, applicability filtering, or
executable skills by themselves. Our narrower contribution is specific to
optimization modeling: a skill carries mechanically checked formulation
semantics and exact resource obligations, deployment uses a frozen solver-facing
benchmark endpoint and an exact previous-library fallback, and promotion
reports full-denominator formulation accuracy with lineage-separated paired
corrections and regressions. We therefore use "proof-carrying" only for the
declared optimization contracts checked by our implementation; we do not claim
the first verifiable or self-evolving skill library in general.

## 3. Problem setting

Let a benchmark family $b$ provide public inputs $x\in\mathcal X_b$, a
frozen endpoint $Q_b(x,y)\in\{0,1\}$ applied to input $x$ and output $y$, and
lineage-separated development, promotion, and confirmation groups. Endpoint
correctness may require solver
status, feasibility, objective agreement, or a benchmark-specific repair
judgment. Endpoints from different families are not assumed to be numerically
interchangeable.

Let $B(x)$ denote the output of a frozen previous library and $K(x)$ the
output of a candidate skill. A public-only acceptance decision $A(x)$
produces

\[
R(x)=\begin{cases}
K(x), & A(x)=1,\\
B(x), & A(x)=0.
\end{cases}
\]

The paired endpoint effect satisfies the exact identity

\[
\operatorname{Acc}(R)-\operatorname{Acc}(B)
=\Pr(A,B\text{ wrong},K\text{ correct})
-\Pr(A,B\text{ correct},K\text{ wrong}).
\]

We therefore report full-denominator accuracy, paired corrections and
regressions, coverage, ambiguity, abstention, method failure, and
infrastructure unavailability. Verification and compilation rates are
mechanism measures rather than replacements for endpoint accuracy.

Evaluation follows a custody boundary. Candidate skills, controls, routers,
and endpoints are frozen before confirmation outcomes are opened. Routers see
public inputs only. Evaluator-only references may score a durably recorded
output but may not select, repair, or route it. Unsupported and unavailable
records remain in the denominator, and related templates are grouped for
promotion and inference.

## 4. Benchmark-Grounded Proof-Carrying Knowledge Compilation

### 4.1 Typed skill and library state

We represent a skill as

\[
k=(g,e,t,v,r,p),
\]

where $g$ is a public-input guard, $e$ extracts typed evidence, $t$
constructs or transforms a formulation, $v$ checks semantic obligations,
$r$ performs exact resource admission, and $p$ records provenance. A
library version is

\[
L_t=(K_t,\rho_t,V,E,\text{ledger}_t),
\]

where $K_t$ is a content-addressed skill set, $\rho_t$ is a public-only
router, $V$ is the immutable verifier, $E$ is the frozen endpoint, and the
ledger contains accepted and rejected ancestry. A proposed transition
$L_t\rightarrow L_{t+1}$ occurs only after verification and independent
promotion; otherwise the state remains $L_t$.

### 4.2 Finite counterexample-guided construction

For each benchmark family, we declare a finite candidate language $H_b$, a
finite verification domain $D_b$, and an independently implemented contract
oracle $O_b$. Candidates are checked in a frozen order. When
$h(x)\neq O_b(x)$ for $x\in D_b$, the first counterexample is retained and
the candidate is eliminated. Semantic and resource violations are hard
constraints. Among surviving candidates, the construction objective favors
paired corrections, penalizes regressions, serialized description length, and
execution cost:

\[
h^*\in\arg\max_h
\left[\operatorname{corr}(h)-\lambda_r\operatorname{regr}(h)
-\lambda_l\ell(h)-\lambda_c C(h)\right]
\quad\text{s.t.}\quad V(h)=1.
\]

This objective prevents a longer prompt or more attempts from being treated as
knowledge by default. The selected skill is frozen before promotion.

For automatic acquisition, the statistical unit is a rejected typed proposal
paired with its frozen grammar, verifier, budget, parent lineage and custody
state. For fact-equivalent flat and separating-witness feedback policies, let
$Y_i(0)$ and $Y_i(1)$ denote admission success within the common budget. On a
predeclared finite proposal population, the acquisition effect is exactly
$n^{-1}\sum_i[Y_i(1)-Y_i(0)]$. Sequential revisions sharing a parent require
lineage-level analysis; per-instance formulation outputs and free-text rules
outside the common grammar are different objects and cannot inflate $n$.

At library level, the learned object includes both skills and router. For the
admissible successor set $\mathscr L_t$, we select

\[
L^*\in\arg\min_{L\in\mathscr L_t}
\left[\widehat R_{\mathrm{dev}}(L)+\lambda_l\ell(L)+\lambda_c C(L)\right],
\]

subject to every newly admitted skill passing the unchanged verifier. Here
$\ell(L)$ encodes the router and typed skills, so a collection of
identity-specific patches is not free. This proof-constrained library
selection objective describes the methodology; the present successful TSP and
OR-Debug skills are authored candidates rather than evidence that automatic
search finds its optimum.

To isolate description length at the correct library-selection unit, we freeze
a common pool containing all 64 libraries induced by six optional shadow
guards on top of the verified exactly-one router. Each optional branch can fit
calibration data that omit its public witness but fails that witness in the
full 69-envelope routing endpoint. The 64 episodes enumerate every calibration
subset. Both selectors receive the same proof-admitted pool; the treatment
uses a label-independent prefix code and the control uses only a frozen content
hash. The six-bit membership header declares the deterministic rule payloads,
making the code self-delimiting and prefix-free before episode labels are
consulted.

### 4.3 Proof-carrying compilation

For a source contract $C$, transformed model $T_k(C)$, and projection
$\pi$, the semantic obligation is

\[
g_k(C)\Rightarrow \pi(\operatorname{Sol}(T_k(C)))=
\operatorname{Sol}(C),
\]

with objective preservation required for optimization. Semantic checks and
resource checks remain separate. The compiler counts variables, rows,
nonzeros, serialized bytes, and backend-specific limits before execution.
Parsing, extraction, ambiguity, compilation, solving, or projection failure
causes abstention or a declared terminal failure; it cannot silently weaken the
contract.

### 4.4 Selective routing and exact fallback

The router returns one pinned skill only when exactly one guard matches the
public input. Zero or multiple matches invoke the frozen fallback. Current
guards are deterministic and benchmark-specific. We make no claim about
learned routing or paraphrase robustness under distribution shift.

For a fixed benchmark family, or a prespecified mixture in which each family
uses its own frozen endpoint, let $A_j$ be the pairwise-disjoint events that
the router uniquely selects skill $j$, let $q_0$ be the previous-library
endpoint, and let $q_j$ be the selected-skill endpoint. Then library-level
gain is

\[
\operatorname{Acc}(R)-\operatorname{Acc}(R_t)
=\sum_{j=1}^m\left[
\Pr(A_j,q_0=0,q_j=1)-\Pr(A_j,q_0=1,q_j=0)
\right].
\]

Thus reusable knowledge has value only through routed corrections net of
routed regressions. This modular identity applies to exactly-one routing under
a fixed evaluation mixture; it does not certify a post hoc change in family
weights or interacting compositions that apply several skills to one
formulation.

### 4.5 Risk-controlled promotion

Promotion evaluates frozen paired outcomes on lineage-separated groups. Each
generation receives a prespecified error budget $\alpha_t$, with
$\sum_t\alpha_t\leq\alpha$. A promoted version must show a positive lower
confidence bound on paired gain and satisfy an upper bound on regression mass.
Every accepted and rejected transition records its parent, candidate,
verifier, endpoint, plan, evidence, and rollback hashes.

When a generation compares several frozen candidate libraries, we allocate its
budget by a prefix code: candidate $L$ receives
$\alpha a_t2^{-\ell_t(L)}$, where $\sum_ta_t\leq1$ and the code satisfies
Kraft's inequality. A union bound then controls false promotion over both
candidates and generations. Under one fixed target distribution, per-transition
regression bounds also telescope, so a sequence with regression budgets
$\bar\epsilon_t$ can lose at most $\sum_t\bar\epsilon_t$ accuracy relative to
its initial library on that target. Neither result applies when candidate codes,
family weights, or endpoints are changed after promotion outcomes are opened.

### 4.6 Worked example

Consider a synthetic four-node TSP with edge costs
$c_{AB}=1,c_{AC}=2,c_{AD}=4,c_{BC}=4,c_{BD}=2,c_{CD}=1$. The public task also
forbids edge $AB$ and requires exactly one of $AC$ and $CD$. The canonical TSP
controller selects the cost-6 cycle $A$--$B$--$D$--$C$--$A$, which violates
both added relations. The typed extractor instead emits `forbidden={A,B}` and
`xor_edges=[{A,C},{C,D}]`. For directed arc variables, the trusted compiler
defines $u_{ij}=x_{ij}+x_{ji}$ and adds
$u_{AB}=0$ and $u_{AC}+u_{CD}=1$ to the canonical tour model. The resulting
cost-12 cycle $A$--$C$--$B$--$D$--$A$ is the only feasible cycle up to reversal.

This example separates the framework's checks. Extraction asserts what the
public relation means; compilation proves only that the typed relation is
encoded; resource admission checks the emitted model; the solver optimizes that
model; and the frozen endpoint judges the projected cycle. A lower cost from
the canonical controller is not evidence of correctness because it optimized a
different feasible region. The example is synthetic and contributes no row to
the reported accuracy. Its full enumeration and certificate boundary appear in
[`WORKED_EXAMPLE.md`](WORKED_EXAMPLE.md).

### 4.7 Reproducible construction and promotion protocol

Algorithm 1 makes the separation between proposal, verification, and empirical
promotion explicit. The proposer may be a language model, a multi-agent
generator, a human author, or an enumerator; changing it does not change the
admission boundary.

```text
Algorithm 1  Benchmark-grounded proof-carrying knowledge compilation
Input: previous library L_t; benchmark family b; development groups S_dev;
       promotion groups S_prom; confirmation groups S_conf;
       frozen candidate language H_b, verifier V, endpoint E;
       generation error budget alpha_t.
Output: L_t or one admitted successor L_(t+1), plus an immutable ledger.

1: Freeze H_b, V, E, resource limits, public-only router interface,
   denominators, group identities, costs, and the promotion rule.
2: Convert development failures into typed obligations without evaluator-only
   answers, item identifiers, or confirmation outcomes.
3: Ask the untrusted proposer for candidates in H_b, or enumerate H_b in the
   declared order.
4: For every candidate h:
      a. validate its schema and public applicability guard;
      b. search the declared domain for a semantic counterexample;
      c. compile h and check exact resource limits;
      d. retain the candidate hash, decision, and first rejecting witness.
5: Select a surviving compact candidate under the frozen correction,
   regression, description-length, and execution-cost objective.
6: Freeze a public-only guard. If zero or multiple skills match, abstain to the
   exact previous-library output.
7: Evaluate the frozen successor and L_t as paired policies on S_prom. Count
   every abstention, method failure, and infrastructure failure in the declared
   denominator.
8: If the alpha_t promotion gate fails, retain L_t and archive the rejection.
9: Otherwise append the content-addressed successor and its rollback target,
   then evaluate it once on S_conf without further adaptation.
10: Return the selected library version and the complete accepted/rejected
    lineage.
```

The finite-verification claims apply to steps 3--5, fallback identity to step
6, and risk-controlled promotion to steps 7--9. Benchmark accuracy is an
empirical result of steps 7 and 9 rather than a consequence of verifier
acceptance. Full split construction, information boundaries, endpoint rules,
request accounting, and release limitations are specified in
[`SUPPLEMENTARY_REPRODUCIBILITY.md`](SUPPLEMENTARY_REPRODUCIBILITY.md).

## 5. Theoretical properties and boundaries

**Finite termination.** If $H_b$ is finite and each failed iteration removes
at least its current candidate, construction terminates after at most
$|H_b|$ candidate decisions.

**Enumerated-domain soundness.** If the verifier checks every $x\in D_b$ and
accepts only when $h(x)=O_b(x)$, the accepted skill is extensionally correct
on $D_b$. The claim does not extend beyond $D_b$, protect against errors in
$O_b$, or prove source-language faithfulness.

**Minimum repair within a frozen grammar.** Exhaustive evaluation under a
declared distance identifies every passing candidate at minimum distance from
a rejected proposal. The certificate establishes minimum repair only within
the grammar and verifier.

**Balanced-witness contraction.** If every reachable non-singleton version
space admits a witness whose largest outcome cell is at most a fixed fraction
$\beta<1$, and acquisition always chooses such a witness, the surviving class
shrinks as $\beta^m$. This conditional logarithmic teaching bound is not
established for the current proposer; the matched feedback study tests its
operational premise.

**Conditional accepted-path correctness.** An accepted output is correct for
its typed contract if the guard is sound, extraction recovers every
correctness-relevant field, compilation preserves feasible solutions and the
objective, the backend returns an exact optimum, and projection is correct.
The conclusion is deliberately conditional because no downstream solver can
repair a mistaken source interpretation.

**Resource safety.** If exact accounting is complete for the declared limits,
an admitted model satisfies those limits. This property does not guarantee a
runtime or a solver outcome.

**Conservative library extension.** If a successor invokes a new skill only
under exactly-one new-guard acceptance and otherwise returns the stored
previous-library output, behavior is unchanged outside unique new coverage,
including ambiguity. Accuracy inside the new coverage region remains an
empirical paired comparison.

**Modular library utility.** Under exactly-one routing and a fixed evaluation
mixture, the accuracy change of a multi-skill library is the sum, across
disjoint selected-skill events, of correction probability minus regression
probability. The identity turns per-skill evidence into a library-level
accounting rule but provides no guarantee after reweighting families or for
interacting multi-skill rewrites.

**Matched acquisition effect.** On a proposal population frozen before
outcomes, the paired admission effect of separating-witness versus flat
feedback equals $(n_{01}-n_{10})/n$. This finite-population identity does not
require independence. Statistical testing, power and transfer to future
proposals require independent proposal states or valid parent-lineage clusters
and prespecified task-family weights.

**Anytime promotion control.** If every generation uses fresh valid groups,
the candidate is frozen before outcomes are opened, and its confidence
procedure fails with probability at most $\alpha_t$, then a union bound limits
the probability that any promoted version violates its stated promotion
condition to $\sum_t\alpha_t$. This result does not protect against a wrong
evaluator or dependent pseudo-replicates.

**Complexity-weighted selection and cumulative regression.** If every
generation freezes a prefix-coded candidate family before evaluation and gives
candidate $L$ budget $\alpha a_t2^{-\ell_t(L)}$, Kraft's inequality and a union
bound control any false promotion by $\alpha$. On one unchanged target,
transition-wise population regression bounds telescope into a cumulative
degradation budget. These are protocol guarantees rather than current empirical
findings: the present authored libraries do not operationalize prefix-code
allocation, and the TSP and OR-Debug transitions use different target families.

These statements combine established tools from synthesis, proof-carrying
artifacts, selective prediction, complexity control, and safe policy updates.
Our proposed contribution is their executable composition for
benchmark-grounded optimization-modeling skills, rather than any one theorem
in isolation. Formal definitions, proof sketches and assumption boundaries are
provided in [`SUPPLEMENTARY_THEORY.md`](SUPPLEMENTARY_THEORY.md).

## 6. Experimental design

### 6.1 TSP confirmation

The first study uses a frozen OPT-Engine TSP constraint split. Skill
construction uses development records of sizes 4--8; promotion uses sizes
9--12; confirmation contains 140 records of sizes 13--19. The strong static
controller and typed constraint skill share the scalable backend and endpoint.
The typed skill extracts one forbidden edge and an exclusive-or obligation over
two present edges, then compiles these relations with the exactly-once tour and
minimum-cost objective. All abstentions remain in the denominator.

### 6.2 OR-Debug-Bench replication

The second study constructs a typed repair library for corrupted LP/MIP models.
The comparator is a generic fresh-IIS repair policy under the same public
bundle, six-operation repair language, patcher, solver, and endpoint. A
37-group promotion gate precedes a one-shot confirmation over 2,845 records in
100 structural groups. Ambiguous cases are retained as abstentions.

### 6.3 Mixed routing

The composition study interleaves the frozen 140 TSP and 2,845 OR-Debug public
confirmation envelopes. Success requires exactly one expected route, no
execution failure, and byte-equivalent compact output relative to the pinned
direct-family execution. This retrospective replay tests composition identity,
not a new accuracy estimate.

### 6.4 External reproduction panel

The fixed external panel uses 40 RCPSP/VRPTW identities, pinned method sources,
and the `gpt-6-luna` backbone at high reasoning effort. BIND is reported
separately for its answer-blind first round and its
answer-bearing final repair. CoE paper and current snapshots retain
safe-adapter failures in the denominator. OptiTrust is marked
artifact-unavailable because the inspected author source archive contains no
verified runnable package. Unequal prompts, feedback, rounds, and execution
coverage preclude an unconditional leaderboard.

### 6.5 Automatic-construction diagnostic

The diagnostic freezes a 64-candidate count grammar, 20,977 semantic
assignments, exact resource obligations, and an answer-free repair procedure.
One bounded AntChat DeepSeek-V4-Flash request proposes a typed candidate. The
response is evaluated without adapting the grammar or verifier. Exhaustive
enumeration then computes the minimum passing repair to characterize the
failure, not to relabel the proposer as successful.

A metadata-only provenance inventory finds five current DCP skill-proposal
identities, but four are free-text or sequential revisions and only this one
belongs to the common typed grammar. The 229 packing trajectories are
per-instance formulations, and inspected legacy VERA identities use
incompatible opened protocols. Exact paired power analysis therefore treats
eight future typed pairs as an engineering pilot only; under the illustrative
$r=.30,q=.70$ alternative, 138 independent pairs are required for 80% power
and 186 for 90% at one-sided alpha .05.

We therefore froze an engineering canary over eight rejected members of the
same typed grammar: the historical model proposal and seven deterministic
synthetic rejected seeds selected before treatment outcomes. Each proposal was
paired across flat cumulative facts and the same facts augmented with
verifier-derived version-space partition counts. Both arms used the same six
authored atomic facts, three rounds, response schema, model, token reservation,
and one-send request policy. The prespecified progression gate required at
least two separating-witness-only admissions, zero flat-only admissions, and
no global safety failure. This canary tests feedback organization after the
facts are known; it does not test automatic discovery of those facts.

We therefore add a separate outcome-blind active-acquisition census. Removing
the resource-policy axis leaves 32 semantic candidates. Their behavior on the
complete 20,977-query verification domain induces 10 extensionally distinct
classes. For every hidden class, both policies begin with the same 10-class
version space and observe only selected query labels. The treatment chooses a
separating query that minimizes the largest remaining partition; the control
chooses the first separating query in a frozen canonical order. No arm receives
an authored fact sentence, target identity, benchmark endpoint outcome, or
resource-policy label. The prespecified budget is three queries per target.

## 7. Results

### 7.1 A typed TSP skill improves prospective endpoint accuracy

The frozen canonical directed-MTZ controller is correct on 54 of 140
confirmation records
(38.57%), whereas the proof-carrying constraint skill is correct on 100
(71.43%). The paired difference is 46 corrections, zero regressions, and
+32.86 percentage points. Gains are positive at every tested size from 13 to
19. The skill abstains on 40 records, all of which remain incorrect in the
full denominator. These results establish same-source size transfer over the
frozen static controller; the shared template lineage prevents interpreting
the 140 rows as independent item-level samples.

### 7.2 The methodology replicates on OR-Debug-Bench

On confirmation, the generic static policy is correct on 828 of 2,845 records
(29.10%), and the typed repair library is correct on 2,752 (96.73%) under the
frozen source-corrected endpoint. The library yields 1,924 corrections, zero
regressions, and +67.63 percentage points. Under the unmodified released repair
identities, the same frozen outputs are correct on 2,236 of 2,845 records
(78.59%), with 1,408 corrections, zero regressions, and 609 both-wrong records.
The 516-record difference is confined to type-B LP records whose released
repair assigns an integer category despite the declared LP domain; the
development-frozen corrected rule uses a continuous category. Sixty-five of
100 held-out structural groups improve, 35 tie, and none decline under the
corrected-primary endpoint; the prespecified structural-group sign test gives
$p=2.71\times10^{-20}$. The complete aggregate ledger contains 100 groups of
size 1--126; the 516 endpoint disagreements span 20 groups, are all type B,
and leave the static-policy score unchanged. All 93 abstentions remain
incorrect. This study
replicates the acquisition, verification, routing, and promotion methodology
on a second benchmark source and task type. It does not show that one unchanged
skill transfers between TSP construction and model repair.

| Confirmation study | Frozen control | Proof-carrying skill/library | Corrections | Regressions | Absolute gain |
|---|---:|---:|---:|---:|---:|
| TSP, sizes 13--19 | 54/140 (38.57%) | 100/140 (71.43%) | 46 | 0 | +32.86 pp |
| OR-Debug, 100 groups | 828/2,845 (29.10%) | 2,752/2,845 (96.73%) | 1,924 | 0 | +67.63 pp |
| OR-Debug, released-label sensitivity | 828/2,845 (29.10%) | 2,236/2,845 (78.59%) | 1,408 | 0 | +49.49 pp |

### 7.3 Public-only routing preserves direct-family behavior

The mixed router uniquely selects the expected family for all 2,985 frozen
records. Every compact mixed output equals the corresponding direct-family
output, with zero route mismatches, source mismatches, execution failures,
missing outputs, duplicates, invalid rows, or unexpected rows. The result
establishes exact behavior preservation for the frozen envelopes. The endpoint
accuracies reported above are inherited descriptively and were not rescored as
a new confirmation study.

### 7.4 External reproductions expose information and execution boundaries

On the fixed common-40 cohort, BIND is correct on 31 records in its
answer-blind first round and 40 after official answer-bearing feedback. The
paper and current CoE snapshots are author-exact on 3 and 1 records,
respectively, under the fixed safe adapter. Author-exact requires the scalar
returned by the official `solve_problem` contract to equal the single expected
scalar exactly. The adapter interprets only a bounded supported subset and
fails closed instead of importing generated modules. However, 25 and 29
completed CoE outputs fall outside that adapter, so these rows characterize the
disclosed adaptation rather than unrestricted native CoE. All method and
adapter failures remain in the planned denominator, while infrastructure
unavailability is reported separately. The inspected OptiTrust arXiv v1 source
contains no verified runnable implementation, training data, checkpoint, or
inference script. We therefore report artifact unavailability instead of
importing a published score.

| Method row | Correct / planned | Availability record | Information or execution boundary |
|---|---:|---|---|
| BIND, first round | 31/40 | 40 complete; 0 infrastructure unavailable | Answer-blind; official structured interface |
| BIND, final | 40/40 | 40 complete; 0 infrastructure unavailable | Uses official answer-bearing repair feedback |
| CoE, paper snapshot | 3/40 | 38 complete; 1 method failure; 1 infrastructure unavailable | Safe adapter; 25 completed outputs unsupported |
| CoE, current snapshot | 1/40 | 37 complete; 1 method failure; 2 infrastructure unavailable | Safe adapter; 29 completed outputs unsupported |
| OptiTrust | Artifact unavailable | Not executed | No verified runnable author package in audited source |

These rows cannot be ranked directly against the TSP and OR-Debug results:
the populations, prompts, feedback budgets, rounds, and endpoints differ. The
current method also has no row in this retrospective common-40 panel; inserting
its TSP or OR-Debug score would conflate benchmark sources and endpoints.

### 7.5 Fresh common-protocol comparison

We next froze 38 larger RCPSP/VRPTW identities that had no overlap with the
earlier prepared text cohort and supplied the same public problem and
structured facts to all model-facing rows. Every failure remains in the
38-instance denominator. The primary rows use AntChat DeepSeek-V4-Flash and
each method's prespecified native trajectory; an answer-blind at-most-one-call
sensitivity view is reported separately. The authored proof-carrying compiler
uses no external model call at inference and is scored by the same frozen
solver-facing objective endpoint.

| Method | Correct / 38 | RCPSP / 13 | VRPTW / 25 | Maximum external calls per item |
|---|---:|---:|---:|---:|
| Proof-carrying compilation | 30 | 12 | 18 | 0 |
| Base | 0 | 0 | 0 | 1 |
| BIND, round 1 | 13 | 13 | 0 | 1 |
| BIND, final | 13 | 13 | 0 | 3 |
| CoE-safe | 4 | 2 | 2 | 11 |

Against Base, the current method has 30 paired corrections and no regression.
Against BIND round 1 and final it has 18 corrections and one regression; against
CoE-safe it has 26 corrections and no regression. Four prespecified one-sided
exact conditional McNemar/sign tests remain significant after Holm correction
(adjusted $p=3.73\times10^{-9}$, $7.63\times10^{-5}$,
$7.63\times10^{-5}$ and $4.47\times10^{-8}$, respectively). BIND's
answer-bearing continuation makes zero corrections and zero regressions over
its first round on this cohort. The Base row includes 29 explicit unsupported
outputs, four incorrect objectives, two method failures and three
infrastructure-unavailable records; its zero score therefore is not created by
excluding failed cells. CoE-safe completes 37 method cells with one method
failure and no infrastructure-unavailable cell.

Under the answer-blind ceiling of at most one external call per item, the valid
terminal rows are the current method, BIND round 1 and Base. This view controls
the call ceiling, not library-construction cost or provider-token consumption.
CoE has no valid official one-call terminal artifact, and BIND final can use
answer-bearing feedback, so neither is inserted into that sensitivity view.
The cohort supplies fixed-endpoint size-generalization and compatibility
evidence; its size and two-family lineage do not establish unrestricted
benchmark superiority.

### 7.6 Bounded component censuses

The component analysis uses the experimental unit appropriate to each
mechanism. For admission, we enumerate all 64 members of the frozen typed-count
grammar. We measure the semantic and resource gates independently rather than
reusing the deployment verifier's fail-fast trace. All four cells are present:
47 candidates fail both gates, 11 fail semantics only, five fail resources
only, and one passes both. Full admission accepts that one candidate and makes
no unsafe admission. Removing the semantic gate admits 12 candidates and
creates 11 unsafe admissions; removing the exact resource gate admits six and
creates five. Thus, within this complete finite grammar, the semantic and
resource gates prevent 11 and five unsafe admissions, respectively, without
rejecting the one safe candidate.

For routing, a frozen 69-envelope grammar contains 43 zero-match, 24
unique-match and two multiple-match cases spanning missing-key, renamed-key,
additive, partial cross-family, unrelated and new-family shifts. Exactly-one
routing with fallback is correct on 69/69. A forced-first/default policy is
correct on 24/69, so selective fallback yields 45 corrections and no
regression. A policy that falls back on zero matches but forces ambiguous
multiple matches reaches 67/69. These are complete deterministic censuses of
declared finite populations, so sampling $p$-values and Holm correction are not
used.

The library-selection census adds the remaining bounded component contrast.
Across all 64 calibration subsets of the six-shadow-guard grammar,
proof-constrained MDL selects the branch-free, fully correct library in 64/64
episodes. The proof-only frozen-hash selector does so in 1/64. The paired table
contains 63 MDL-only fully correct selections, zero control-only, one both and
zero neither. Over the $64\times69=4{,}416$ routing decisions, MDL is correct
on all 4,416, whereas the control is correct on 4,284, yielding 132 corrections
and no regressions. This is an exact causal contrast over the complete authored
shadow-guard grammar. It does not estimate behavior under a natural proposer
distribution or measure the description length of the successful TSP/OR
libraries.

### 7.7 Bounded active acquisition succeeds; natural-language acquisition remains unsupported

The automatic proposer returns a valid member of the frozen count grammar and
passes all 20,977 semantic assignments. It nevertheless retains a broad
declared-length domain that violates the exact compiler resource limit and
omits the zero-tail exception. The candidate is rejected. Exhaustive
verification shows that all six distance-one repairs fail. Changing only the
bound strategy reveals a zero-tail semantic counterexample, whereas changing
only the zero-tail policy retains the resource failure. Their joint change is
the unique passing distance-two repair. This certificate demonstrates an
interaction between semantic and resource fields inside the frozen grammar;
the repair is attributable to enumeration and verification, not to the model.

The matched engineering canary subsequently issued 44 physical requests for
48 logical cells; four later cells were skipped after an earlier acceptance.
All 44 provider responses were structurally valid typed candidates, accounting
for 42,797 prompt, 4,723 completion, and 47,520 total tokens. Both feedback
arms eventually admitted every proposal: seven of eight pairs first passed in
round 3 in both arms, and one pair passed in round 1 in both arms. Thus the
paired table is 0 separating-witness-only, 0 flat-only, 8 both, and 0 neither.
The prespecified engineering gate fails. The result shows that the six authored
facts are sufficient for repair by the final round, but supplies no evidence
that the partition annotation improves acquisition or sample efficiency. We
retain the authored-skill fallback and do not open the planned 138-pair
confirmation for this intervention.

The finite active-acquisition census supplies the complementary positive
result. The 32 semantic candidates collapse to 10 extensionally distinct
classes on the complete query domain. Balanced witness selection identifies
10/10 hidden classes within three queries, using 26 queries in total, a mean of
2.6 and a worst case of 3. The canonical-first control identifies 6/10 within
the same budget, using 30 queries in total, a mean of 3.0 and a worst case of
4. The paired budget table is 4 balanced-only, 0 control-only, 6 both and 0
neither. These are exact complete-population quantities, so no sampling
$p$-value is attached. The result establishes automatic acquisition of an
extensional behavior class within the frozen grammar. It does not identify the
resource-policy axis, discover natural-language facts, estimate language-model
proposer efficacy, score benchmark accuracy, or promote a library.

## 8. Discussion

The two prospective studies support a common methodological conclusion:
benchmark-specific optimization knowledge can be made reusable and empirically
valuable when represented as a typed artifact with explicit proof obligations,
selective routing, and independent endpoint promotion. The TSP study isolates
a relational constraint absent from a strong canonical controller, while the
OR-Debug study applies the same methodology to typed repair operations. Their
different endpoints and skill contents prevent a pooled effect estimate, but
their agreement supports methodological replication across construction and
repair settings.

The evaluated pipelines combine several mechanisms, and the end-to-end
benchmark comparisons alone do not identify their individual causal necessity.
The finite component censuses add bounded evidence: exact semantic admission
prevents 11 unsafe admissions and exact resource admission prevents five in the
complete 64-member count grammar, while exactly-one routing corrects 45
forced-policy errors in the 69-envelope routing grammar. In the complete
six-shadow-guard library grammar, label-independent description length adds 63
fully correct selections and 132 correct routing decisions without a
regression relative to a proof-only frozen-hash selector. Typed evidence
makes the correctness-relevant quantities and relations explicit; trusted
compilation rejects semantic or resource violations before execution; and
selective routing limits adoption to a declared region while preserving the
prior output elsewhere. The paired accuracy identity shows why none of these
mechanisms alone guarantees improvement: useful coverage must create more
corrections than regressions. The zero-regression observations support
dominance only on the evaluated cohorts and do not establish a
distribution-free guarantee.

The framework complements rather than replaces existing generation methods.
BIND shows that answer-bearing iterative feedback can be highly effective, but
its final result answers a different information-budget question from
answer-blind modeling. CoE illustrates both the appeal of specialized agents
and the practical difficulty of safely executing unconstrained generated
programs. A generator such as BIND, CoE, or a future OptiTrust implementation
could propose candidates for the proof-carrying layer when its outputs can be
translated into the typed contract. Compatibility alone does not guarantee
admission or endpoint gain.

The automatic-construction studies localize the remaining causal question.
The first language-model proposal uses the correct finite vocabulary and
satisfies every semantic assignment, yet misses a resource-sensitive
interaction. The matched canary then compares flat and partition-annotated
feedback under identical atomic evidence, model, grammar, schema, output
ceiling, request budget, and verifier. It finds no discordance: both arms
repair every proposal on the same round. Partition counts alone therefore do
not justify a larger confirmation. The subsequent exact census intervenes
earlier by selecting correctness-relevant assignment labels: a balanced
version-space policy improves budgeted class recovery over a fixed query
order. This validates the finite teaching mechanism under an authored grammar,
oracle and domain, while leaving the harder problem of deriving semantic axes
and facts from natural-language benchmark failures open. Any such proposer
remains outside the verifier and promotion boundary.

The method is related to bounded verifier-mediated improvement, but the term
should be read narrowly. The system updates external skill artifacts and a
content-addressed lineage. It does not rewrite model weights, the verifier, the
endpoint, or the resource policy. The current evidence therefore supports
auditable proof-carrying knowledge compilation for optimization modeling, not
general priority for skill evolution or unrestricted recursive
self-improvement.

## 9. Limitations and threats to validity

First, every formal guarantee is conditional on an authored grammar, oracle,
and verifier. An omitted semantic axis can make an incorrect skill appear
sound on its finite domain. The current claims therefore concern declared
contracts rather than arbitrary optimization prose.

Second, compilation correctness cannot establish source-language faithfulness.
If a public relation is misread before it enters the typed representation, the
downstream proof concerns the wrong contract. Independent formulation review
and shifted-language evaluation remain necessary.

Third, the TSP confirmation remains within one source and perturbation family,
and its rows share template lineage. The OR-Debug analysis addresses dependence
through 100 prespecified public-shape groups, but that key is not proven to
capture every shared source-model or generation-template lineage. Its group
sign test is therefore conditional on the stated grouping and does not
establish transfer to unrelated industrial models. The mixed router uses
frozen known envelopes and is not a test of learned routing under distribution
shift.

Fourth, the successful TSP and OR-Debug skills are authored under the proposed
methodology. The first bounded model proposer fails its resource gate, and the
eight-pair matched canary yields zero discordant pairs between flat and
partition-annotated feedback. A separate exact census does support automatic
identification of all 10 extensional behavior classes induced by the authored
semantic grammar within three balanced queries, versus 6/10 under the fixed
query order. This is a bounded acquisition result under a complete authored
grammar, oracle and domain; it does not discover the grammar, resource-policy
axis or natural-language facts. The canary facts were authored and identical
across arms, so the language-model canary likewise does not measure automatic
fact discovery; its small deterministic synthetic population is an engineering
diagnostic rather than a powered efficacy sample. A repository-wide metadata
inventory does not supply substitute observations:
only one of five prior DCP proposal identities belongs to the frozen typed
grammar, while per-instance formulations and legacy opened lineages are
nonexchangeable. The prespecified gate prevents expanding this ineffective
feedback intervention; any replacement acquisition treatment requires a new
outcome-blind design and independent units.

Fifth, the external comparison is not a uniform leaderboard. The fresh
common-38 study now supplies matched Base, BIND, CoE-safe and current-method
rows on identical public packets and the same endpoint, but their native
trajectories consume different numbers of model calls. BIND final additionally
receives answer-bearing feedback, CoE remains limited by the safe adapter, and
OptiTrust lacks a verified runnable artifact. The separate at-most-one-call
view controls only the inference-call ceiling and does not equalize authored
library-construction cost or provider tokens. The 38 identities cover two
families from one source lineage; the paired results can establish a large
effect on this frozen cohort, not broad moderate-effect leaderboard
superiority or transfer to unrelated optimization families.

The endpoint panel alone cannot identify every component contribution. Semantic and
resource admission act on candidate proposals, description length acts on
library selection, and selective routing acts on public deployment envelopes.
Their valid units are therefore proposals, library-selection
episodes, and shifted or ambiguous envelopes, respectively. We prespecify four
paired contrasts against the full method and control their familywise error by
Holm's procedure. At the conservative planning threshold $0.05/4$, the
38-identity endpoint panel has only 3.1--60.0% power over the displayed
discordance scenarios, and seven corrections with zero regressions are needed
for a raw one-sided exact $p<0.0125$. These analyses motivate separate frozen
proposal and routing cohorts; under the illustrative $r=.30,q=.70$ alternative,
80% and 90% power require 205 and 263 valid units. Historical metadata cannot
supply them: only one current proposal lies in the common frozen typed grammar,
the two successful family libraries are not repeated selections from one
candidate pool, and all 2,985 mixed records occupy known unique routes. The new
finite censuses avoid pseudoreplication by making narrower population claims:
the semantic and resource effects are exact for the complete 64-member
typed-count grammar, and the routing effect is exact for the complete
69-envelope shift and ambiguity grammar. The complexity effect is exact for all
64 calibration subsets of the authored six-shadow-guard library grammar. These
results do not estimate a proposer-distribution average, natural library
evolution or unrestricted shift robustness.

Finally, all 70 paths in the current evidence manifest are tracked and
hash-verified, and restricted task-text and repair-bearing sources have been
replaced by metadata-only projections. Credential-free Layer A, the exact
offline-analysis stack, the local solver boundary, the provider transport
preflight, and clean figure reconstruction now have separate executable audits.
A one-commit, zero-parent candidate reproduced Layer A with no restricted or
private paths, showing that the contaminated ancestry can be removed
mechanically. The author has since approved scoped Apache-2.0 software and CC BY
4.0 aggregate-data licensing, the NOTICE and third-party exclusions, the
availability and AI-use disclosures, and publication of a history-free
candidate. One shared exclusive durable publisher now serves the nine
source-hash-bound historical adapters. A final release audit also replaced a
private provider-preflight dependency with a body-free public surface that binds
only the endpoint, model, concurrency, CA identity and TLS construction. The
corrected history-free candidate is publicly frozen as `v1.0.0`; an
unauthenticated recursive clone acquired the main repository and pinned
submodule, passed full object checks, 91 release tests and six deterministic
reconstruction/preflight commands, and remained clean. All 11 release-asset
server digests match their local sources. Gurobi remains a separate commercial
dependency, and no archival DOI is claimed. These archival conditions do not
change the closed numerical results.

The current implementation now exposes one canonical answer-free skill
manifest per family and a parent-linked library manifest binding the router,
verifier closure, endpoints, rollback target, and accepted and rejected
ancestry. A strict validator, exclusive durable publisher, and manifest-driven
reconstructor recover all 2,985 direct-versus-mixed output identities from the
single library hash. Its operational semantic envelope is 17,728 bits. Because
these authored policies and their encoding were frozen after development
outcomes were known, that measurement is an artifact description rather than a
retrospective generalization bound. The finite shadow-guard census identifies
the selection mechanism only in its declared grammar; the TSP/OR accuracy gains
do not identify a complexity effect in natural library construction.

## 10. Conclusion

Benchmark-Grounded Proof-Carrying Knowledge Compilation converts reusable
optimization-modeling knowledge into versioned typed programs with explicit
verification, selective routing, and endpoint-tested promotion. Frozen TSP and
OR-Debug studies show large full-denominator gains over strong static controls,
and the fresh common-38 comparison retains a large advantage over Base, BIND
and CoE-safe on two larger optimization families under unequal native inference
budgets, non-equalized authored construction cost, and one source lineage. A public-only mixed router
preserves all direct-family outputs, while finite component censuses isolate
bounded semantic-admission, resource-admission and selective-routing effects. External
reproductions, a negative automatic proposer, a zero-discordance matched
feedback canary, a positive finite active-acquisition census, and an
exact finite complexity-control census delimit the current evidence: the methodology
supports auditable benchmark-specific skill engineering and bounded acquisition
inside an authored grammar, but does not support universal semantic correctness
or autonomous natural-language knowledge discovery. Natural-language grammar
and fact acquisition, natural library-selection replication, and a second
fresh source lineage remain valuable extensions. The latter is required before
claiming broad benchmark superiority, but is not needed for the bounded
common-38 claim reported here.

The public `v1.0.0` package is an integrity/audit release: it reconstructs
aggregate arithmetic, evidence bindings and body-free output identities, but
does not redistribute restricted task bodies or evaluator-only answers and
therefore cannot itself rescore every central endpoint. A separate frozen,
hash-bound controlled-review protocol permits independent endpoint
recomputation under restricted-data custody; a fresh-context reviewer
reproduced all three central endpoint families exactly. This separation preserves the
release boundary rather than treating aggregate integrity as end-to-end public
benchmark reproduction.

## Data and code availability

First-party code, typed skill and library manifests, public-only routing and
verification code, aggregate evidence, figure Source Data and deterministic
reconstruction commands are publicly available in the history-free `v1.0.0`
release at <https://github.com/ChengxiSHE/LLM4UO_EAAI> under Apache-2.0, with
explicitly marked author-owned aggregate Source Data and documentation under CC
BY 4.0. The exact release bundle and five-layer audit sidecars are attached to
the GitHub Release; an archival DOI will be added after external deposit and is
not yet claimed. The solver-in-the-loop dataset remains an external pinned
submodule under its upstream terms, and Gurobi 13.0.1 requires a separate user
installation and license. Provider replay requires a user-supplied account and
credential; credential-free evidence reconstruction does not. Private request
and response bodies, credentials, evaluator-only answers and restricted
upstream task text are excluded from release.
The public package therefore supports integrity reconstruction rather than
public rescoring from those excluded materials. Conference artifact reviewers
may recompute the TSP, OR-Debug and common-38 endpoints through the frozen
controlled-review protocol, which verifies exact input/code hashes and emits
only an aggregate attestation
([protocol](../docs/CONTROLLED_ENDPOINT_REVIEW_PROTOCOL_20261016.md)).
The completed aggregate audit is available separately
([audit](../docs/CONTROLLED_ENDPOINT_REVIEW_AUDIT_20261016.md)).

## AI-use disclosure

Language models were used in the explicitly identified candidate-generation
experiments, in software-development assistance and in manuscript drafting.
Candidate knowledge, code changes, numerical results and prose were not
accepted solely on model output. Human authors defined the research questions
and frozen evaluation contracts, reviewed the outputs, and verified the
reported evidence through deterministic checks, independent endpoint scoring,
source and citation audits, and reproducible reconstruction. The human authors
remain accountable for all claims, analyses, citations and released artifacts.

