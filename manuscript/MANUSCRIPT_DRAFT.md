# Benchmark-Grounded Proof-Carrying Knowledge Compilation for Reliable Optimization Modeling

**Status:** evidence-grounded manuscript draft, 17 October 2026. Results in this
document are restricted to terminal artifacts bound by the project evidence
manifest. The eight-pair matched-feedback engineering canary is complete and
negative; the fresh RCPSP/VRPTW common-protocol comparison, bounded finite
component censuses and a bounded active-acquisition census are complete. The
prospective FormulationBench same-fact comparison and independent NLEquiv-150
routed-skill comparison are also complete; neither passes its prespecified
mechanism gate. A subsequently frozen independent RetailOpt-190 direct-modeling
study confirms the revised short-decision, sparse-retrieval and counterexample-
witness method; a same-benchmark label-blind robustness replication is also
complete. The
history-free public release, independent public integrity review and controlled
endpoint recomputation are complete. Natural-language fact acquisition, broader source replication, an
archival DOI and submission-specific formatting remain incomplete. Figures 1
and 2 have
passed publication-size render and visual QA.
A claim-level audit is maintained in
[`MANUSCRIPT_EVIDENCE_AUDIT.md`](MANUSCRIPT_EVIDENCE_AUDIT.md).

## Abstract

An optimization program can parse and solve while encoding the wrong feasible
region, objective, or relation. We study **Benchmark-Grounded Proof-Carrying
Knowledge Compilation**, a method for turning reusable benchmark knowledge
into versioned typed programs with explicit applicability, semantic checks,
resource limits, provenance, selective routing, and frozen endpoint promotion.
The two successful libraries in this study were authored from development
failures; automatic construction is evaluated separately and is not assumed.

The primary evidence is system-level benchmark accuracy. On a frozen
traveling-salesperson-problem confirmation set, a canonical directed-MTZ
controller is correct on 54/140 instances and the complete typed-skill system
on 100/140, yielding 46 corrections, no regressions, and a 32.86 percentage-
point gain. On OR-Debug-Bench, the unmodified released-label endpoint scores a
generic fresh-IIS repair control at 828/2,845 and the complete typed-repair
system at 2,236/2,845, with 1,408 corrections, no regressions, and a 49.49-point
gain. A development-frozen source-semantic correction is reported separately
as a sensitivity and gives 2,752/2,845. A public-only router then reproduces all
2,985 frozen direct-family outputs exactly. On a fixed cohort of 38 larger
RCPSP/VRPTW instances, the authored compiler scores 30/38, versus 0/38 for Base,
13/38 for BIND round one and final, and 4/38 for CoE-safe. This is an unequal-
regime implementation comparison: construction cost, model calls, provider
tokens, feedback, and one-source-lineage breadth are not matched.

On independently frozen RetailOpt-190, the revised short-decision protocol
holds the task, typed questions, output contract, compiler and solver fixed,
while adding at most three routed obligation and counterexample cards. Base is
correct on 50/190 instances (26.32%) and the knowledge method on 170/190
(89.47%). At the prespecified five-variant archetype unit, the comparison is
10/38 versus 34/38, with 25 corrections, one regression and a one-sided exact
McNemar $p=4.02\times10^{-7}$. A post hoc label-blind robustness replication,
in which evidence is the only model-visible difference, yields 50/190 versus
185/190 and 27 archetype corrections with no regression. The latter excludes
an informative-arm-label explanation but is not a second independent test.

Secondary exhaustive tests show that the declared semantic, resource, routing,
active-witness, and description-length contracts behave as specified inside
their authored finite populations. Two prospective mechanism studies prevent a
stronger architectural claim. With 4,935 facts fixed on FormulationBench,
PCK-K scores 36/89 versus 40/89 for Flat-K ($p=0.8811$). On independent
NLEquiv-150, fact structuring ties Flat-K at 124/150, while routed generic
skills reach 128/150 versus 124/150 but do not pass the paired gate
($p=0.2617$). The evidence therefore supports auditable benchmark-specific
knowledge systems with explicit failure and fallback behavior, not an
architecture-only accuracy advantage, natural-language knowledge discovery,
or broad benchmark superiority.

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
3. We report two full-denominator system-level case studies in which complete
   authored pipelines improve final formulation accuracy over frozen TSP and
   OR-Debug controls, followed by exact retrospective composition behind one
   public-only router. These comparisons do not isolate architecture from
   knowledge content.
4. We audit local BIND and CoE reproductions under disclosed safe-execution
   adapters and retain official OptiTrust as artifact-unavailable because the
   inspected author source does not provide a verified runnable implementation.
   A separately labeled OptiTrust-style indexed adapter resolves the observed
   long-generation transport failure but fails two frozen two-family method
   gates; no common-38 run or accuracy row is therefore reported.
5. We report a negative language-model construction trace, an exact
   minimum-repair certificate, and a prospective eight-pair feedback canary
   with zero paired discordance. A separate complete finite census then shows
   that balanced active witnesses identify all 10 extensional semantic classes
   within three queries, versus 6/10 for a fixed-order control. This supports
   bounded automatic acquisition inside the frozen grammar while ruling out a
   natural-language fact-discovery claim.
6. We rerun Base, BIND and CoE on a fixed RCPSP/VRPTW cohort shared with the
   current implementation under disclosed unequal regimes. Separately, we
   exhaust finite authored populations to test semantic admission, resource
   admission, selective routing, and description-length selection as declared
   contracts, while retaining the negative language-model acquisition result
   and explicit finite-population boundaries. Two prospective studies then
   hold fact content fixed or separate structure from routed generic skills;
   neither passes its mechanism gate, bounding the contribution to complete
   benchmark-specific knowledge compilation rather than representation alone.
7. Guided by those negative controls, we freeze a revised short-decision,
   sparse-retrieval and counterexample-witness method on independent
   RetailOpt-190. It improves direct-modeling accuracy by 63.16 percentage
   points in the prospective comparison and retains the conclusion after
   removing all model-visible arm labels. This identifies the value of the
   retrieved benchmark knowledge under a shared decision interface; it does
   not identify automatic knowledge acquisition or a universal architecture
   effect.

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
The claim-level nearest-precedent map is provided in
[`CLOSEST_METHOD_CLAIM_MAP_20261016.md`](../docs/CLOSEST_METHOD_CLAIM_MAP_20261016.md);
it records shared mechanisms and the evidence still required for stronger
comparative novelty rather than inferring undocumented feature absences.

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
safe-adapter failures in the denominator. Official OptiTrust is marked
artifact-unavailable because the inspected author source archive contains no
verified runnable package. A separate paper-structure sensitivity uses five
language-conditioned reviews and strict trusted admission. Its original
full-model form is named `OptiTrust-style-safe-sidecar`; a bounded replacement
is named the OptiTrust-style indexed adapter. Neither is an official
reproduction. The indexed adapter first passes a frozen worst-shape transport
gate and is then tested on one maximum public-size RCPSP and VRPTW case without
loading reference answers. Unequal prompts, feedback, rounds, and execution
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

### 6.6 Independent RetailOpt-190 confirmation

The revised mechanism is evaluated on RetailOpt-190 at source commit
`d809c6b`. The 190 public scenarios form 38 archetypes with five numerical
variants each and have no lexical or numeric-template identity with the six
earlier source ledgers or Text2Opt. A deterministic router selects one to three
of ten typed cards covering inventory flow, substitution and one optional
feature. Each card contains an explicit formulation obligation and a synthetic
counterexample witness. Both arms receive the same public archetype text,
typed multiple-choice decisions, output schema, DeepSeek-V4-Flash model,
first-party compiler, Gurobi configuration and ReLoop objective-error endpoint;
only the routed evidence is withheld from Base. One decision is applied to all
five variants, giving 38 paired inferential units and 190 scored instances per
arm. Before inference, the admitted decision and shared compiler score 190/190,
so the experiment tests decision quality rather than an unvalidated compiler.

The primary gate requires at least a five-point instance gain, at least six
archetype corrections, at most two regressions, a correction-to-regression
ratio of at least two, one-sided exact McNemar $p<0.05$, and at least 99%
valid inference completion in each arm. Missing, invalid and solver-failed
records remain incorrect in the full denominator. The plan permits five
concurrent requests, at most three charged attempts per fingerprint and 40
logical starts per 60 seconds. A two-cell maximum-envelope preflight exposed
and corrected a local wire-size reservation error before the 76-cell plan was
frozen. Because the primary request included an informative internal arm label,
we subsequently froze a post hoc same-benchmark robustness replication that
removes the arm and cell labels. In that replication the retrieved evidence is
the only model-visible difference; it tests a nuisance explanation rather than
supplying a second independent sample.

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

### 7.2 The complete system improves released-label accuracy on OR-Debug-Bench

On confirmation, the generic static policy is correct on 828 of 2,845 records
(29.10%). Under the unmodified released repair identities, the complete typed
repair system is correct on 2,236 records (78.59%), with 1,408 corrections,
zero regressions, 609 both-wrong records, and a +49.49 percentage-point gain.
We use this released-label endpoint as the primary public result.

A development-frozen source-semantic correction is retained as a sensitivity.
It treats 516 type-B records declared as linear programs as continuous rather
than assigning the released integer repair category. Under that endpoint the
same frozen outputs are correct on 2,752 records (96.73%), yielding 1,924
corrections, zero regressions, and +67.63 points. The 516 disagreements span 20
groups and leave the static-policy score unchanged. Sixty-five of 100
prespecified public-shape groups improve, 35 tie, and none decline under this
sensitivity. The exact sign-test value is $p=2.71\times10^{-20}$ conditional on
that grouping key; because the key is not proven to capture every source-model
or generation-template lineage, we treat the effect counts as primary and the
probability statement as secondary. All 93 abstentions remain incorrect.

This second benchmark shows that another complete authored pipeline can improve
its frozen endpoint. It does not show transfer of one unchanged skill or
isolate the effects of acquisition, verification, routing, and promotion from
the supplied benchmark knowledge.

| Confirmation study | Frozen control | Proof-carrying skill/library | Corrections | Regressions | Absolute gain |
|---|---:|---:|---:|---:|---:|
| TSP, sizes 13--19 | 54/140 (38.57%) | 100/140 (71.43%) | 46 | 0 | +32.86 pp |
| OR-Debug, released labels (primary) | 828/2,845 (29.10%) | 2,236/2,845 (78.59%) | 1,408 | 0 | +49.49 pp |
| OR-Debug, source-corrected sensitivity | 828/2,845 (29.10%) | 2,752/2,845 (96.73%) | 1,924 | 0 | +67.63 pp |

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
| OptiTrust-style-safe-sidecar v1 | Not estimable | 0 scoreable; 38 infrastructure unavailable | Paper-structure sensitivity; repeated full-model sidecars exhausted transport |
| OptiTrust-style indexed adapter | No accuracy row | Capacity v4: 3/3 received; two method gates: 20/20 transport-complete each | Paper-structure sensitivity; 0 optimal review views and 0/2 consensus cells in both gates |

The `OptiTrust-style-safe-sidecar` v1 row recorded 199 logical requests, 282
physical attempts, 83 retries, and 161 complete provider responses before all
38 identities exhausted one terminal request fingerprint. Thirty-five cells
stopped after five logical slots, one after six, and two after nine, localizing
the failure to repeated full-model sidecar generation. Its low-level result
contains a mechanical zero, but with no scoreable method outcomes this is not
an accuracy estimate. Corrections, regressions, accuracy deltas, and paired
tests against the current method are therefore not estimable.

The bounded indexed replacement separates this transport failure from method
feasibility. Its frozen worst-shape v4 capacity gate receives all three
canonical envelopes in six physical attempts, with no halt and no restart
sends. Two separately frozen answer-blind gates then each complete 20/20
logical requests in 20 physical attempts, with no retry, infrastructure loss,
review abstention, or reference-answer access. Nevertheless, each gate yields
five terminal review views per cell but zero optimal views and zero selected
consensus cells. The OptiTrust-style indexed adapter therefore fails its method
gate before solving or scoring; common-38 is not dispatched, and these data
are not an accuracy estimate and provide no ranking of OptiTrust.

These rows cannot be ranked directly against the TSP and OR-Debug results:
the populations, prompts, feedback budgets, rounds, and endpoints differ. The
current method also has no row in this retrospective common-40 panel; inserting
its TSP or OR-Debug score would conflate benchmark sources and endpoints.

### 7.5 Fixed-cohort implementation comparison

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

Against Base, the current implementation has 30 paired corrections and no regression.
Against BIND round 1 and final it has 18 corrections and one regression; against
CoE-safe it has 26 corrections and no regression. Four prespecified one-sided
exact conditional McNemar/sign calculations reject after Holm correction
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
These probabilities are conditional on treating the 38 identities as the
inferential units; shared family and source-template lineage can make that
assumption optimistic. The paired counts are therefore the primary result. The
cohort supplies fixed-endpoint implementation and compatibility evidence; its
size, unequal construction and execution regimes, and two-family lineage do not
establish unrestricted benchmark superiority or architecture-level causality.

### 7.6 Exhaustive tests of bounded component contracts

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
and no regressions. This is an exhaustive contract test over the complete
authored shadow-guard grammar. The population and tie-breaking control were
designed for this mechanism test, so the result does not establish causal
importance in naturally generated libraries, explain the TSP/OR benchmark
gains, or measure the description length of those successful libraries.

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

### 7.8 Prospective controls do not confirm an architecture-only accuracy gain

We tested the architectural interpretation directly after freezing two new
source lineages. FormulationBench supplies the strict same-fact comparison. All
89 pairs use identical content-addressed fact multisets, totaling 4,935 fact
identities, and the same six generic checks. Flat-K is correct on 40/89
(44.94%), whereas PCK-K is correct on 36/89 (40.45%). The paired table contains
7 PCK-K corrections, 11 regressions, 29 pairs correct under both arms, and 42
incorrect under both. The prespecified one-sided exact McNemar probability is
$p=0.8811$, so the gate fails.

Execution is complete on all 178 cells with one physical send per cell, zero
retry, and zero infrastructure failure. The failure is methodological rather
than operational. Flat-K produces 77 valid typed judgments and 12 method
failures; PCK-K produces 68 valid judgments and 21 method failures. Conditional
valid-only accuracies are similar, but that selective post hoc view cannot
replace the full-denominator endpoint. The mandatory proof object consumes
decision budget and creates additional contract failures, offsetting any
decision-quality benefit.

NLEquiv-150 provides an independent but different diagnostic. Reorganizing the
same leaf facts into six typed obligations leaves accuracy unchanged at 124/150
for both Flat-K and Structured-K, with 13 corrections and 13 regressions
($p=0.5775$). Adding deterministic routed generic skill cards reaches 128/150
(85.33%), compared with 124/150 (82.67%) for Flat-K, but 13 corrections and 9
regressions yield $p=0.2617$ and the primary gate fails. The opened-label
diagnostic shows that routed skills improve equivalent-pair recognition while
remaining weak on non-equivalence witnesses. Because this is an equivalence-
classification endpoint rather than direct solver-code formulation accuracy,
it supplies a design diagnosis rather than a second formulation benchmark
gain.

These prospective controls do not invalidate the complete-system TSP,
OR-Debug, or common-38 results. They show that those gains cannot be attributed
to proof-carrying organization alone. The supported mechanism story is that
benchmark-specific knowledge is compiled into an auditable, fail-closed
runtime, while accuracy still depends on the selected knowledge and on a
bounded decision interface. Both mechanism endpoints are now development data;
they motivate, but do not contribute observations to, the independently frozen
RetailOpt-190 confirmation below.

### 7.9 Sparse proof-carrying knowledge improves independent direct-modeling accuracy

All 76 prospective inference cells complete in one physical attempt, with zero
retry, method failure or infrastructure failure; an immediate restart creates
no new send. Base is correct on 50/190 instances (26.32%), whereas the routed
knowledge method is correct on 170/190 (89.47%), a gain of 63.16 percentage
points. At the prespecified archetype unit, Base is fully correct on all five
variants for 10/38 archetypes and the knowledge method for 34/38. The paired
table contains 25 corrections and one regression, giving one-sided exact
McNemar $p=4.02\times10^{-7}$. All six prespecified confirmation conditions
pass. Both arms have 180 optimal and 10 time-limited feasible solver outcomes,
so differential solver availability does not explain the accuracy gap
(Fig. 3a,b).

The post hoc label-blind replication also completes all 76 cells without retry
or failure. Base remains at 50/190, while the knowledge method reaches 185/190
(97.37%); fully correct archetypes are 10/38 versus 37/38, with 27 corrections,
no regression and $p=7.45\times10^{-9}$. This same-benchmark result is a
robustness analysis, not an additional independent confirmation, but it rules
out the explicit arm label as the source of the primary effect (Fig. 3c).

Aggregate decision diagnostics localize the mechanism. In the primary run,
the complete core-flow card is answered correctly for 10/38 Base archetypes
and 33/38 knowledge archetypes; the substitution card is fully correct for
11/36 and 36/36, respectively. Knowledge eliminates all errors in aging and
substitution inventory binding, while its remaining endpoint errors are
concentrated in a small number of fresh-inflow decisions. The label-blind run
raises complete core-flow decisions to 37/38. These post hoc counts support the
intended semantic explanation but do not decompose a causal effect among card
wording, obligations and witnesses (Fig. 3d).

## 8. Discussion

The prospective benchmark studies support a bounded systems conclusion:
benchmark-specific optimization knowledge embedded in the complete authored
pipelines is reusable and empirically valuable on the declared endpoints. The
TSP study adds a relational constraint absent from a canonical controller,
the OR-Debug study adds typed repair knowledge, and RetailOpt-190 tests sparse
semantic guidance through a shared short-decision compiler. Their different endpoints
and skill contents prevent a pooled effect estimate, and the unmatched knowledge
content prevents attributing the gains to the proof-carrying architecture
alone. Together they show system-level replication across construction and
repair settings.

The matched mechanism studies sharpen rather than broaden this conclusion.
Holding all FormulationBench facts fixed does not improve pair-validity
accuracy under the proof-carrying presentation, and structuring the same
NLEquiv facts is neutral overall. Routed generic nonlinear-equivalence skills
are directionally positive but not statistically confirmed. The contribution
is therefore the compilation and governance of benchmark-specific knowledge,
not a claim that typed proof obligations intrinsically make a language model
more accurate. The failure pattern also supplies a concrete design rule: keep
the model's decision channel short, separate optional evidence generation, and
retrieve only the facts and counterexample checks needed by the current
obligation.

RetailOpt-190 tests that rule on a source with no detected lexical or numeric-
template overlap with the earlier ledgers. The large prospective paired gain
shows that benchmark-specific obligations and counterexample witnesses can
improve final solver-facing accuracy when the model makes a small typed
decision rather than generating a full formulation. The unchanged Base score
and larger knowledge score after arm-label removal argue against prompt-label
priming, while the matched solver-status counts argue against differential
execution. Because the knowledge cards state authored benchmark semantics,
the experiment identifies the value of supplying and compiling that knowledge;
it does not show that the library can be discovered automatically or that
proof-carrying structure alone causes the gain.

The evaluated pipelines combine several mechanisms, and the end-to-end
benchmark comparisons alone do not identify their individual causal necessity.
The finite component censuses add bounded contract evidence: semantic admission
prevents 11 unsafe admissions and resource admission prevents five in the
complete 64-member count grammar, while exactly-one routing corrects 45
forced-policy errors in the 69-envelope routing grammar. In the complete
six-shadow-guard library grammar, label-independent description length adds 63
fully correct selections and 132 correct routing decisions without a
regression relative to a proof-only frozen-hash selector. These designed
populations test the implementation contracts and do not explain the natural
benchmark gains. Typed evidence
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

Second, the TSP and OR-Debug controls do not receive the same authored semantic
or repair knowledge in an alternative representation, so those contrasts
identify complete systems rather than architectural causality. The prospective
FormulationBench comparison now supplies the missing strict same-fact test and
does not support a proof-carrying representation benefit. NLEquiv likewise
finds no aggregate benefit from structure alone; its routed-skill gain is
directional and non-significant, and its endpoint is not direct formulation
generation. RetailOpt-190 then confirms a revised short-output, sparse-retrieval
and counterexample-witness method on a new direct-modeling endpoint, but the
comparison changes knowledge availability rather than holding content fixed.
It therefore establishes a complete-method accuracy gain and the utility of
the routed benchmark knowledge, not an architecture-only effect.

The RetailOpt primary protocol has 38 paired archetype units from one source
and model. Its five numerical variants improve endpoint coverage but are not
treated as independent inferential samples. The label-blind replication was
designed after the primary result was opened and reuses the same archetypes;
it excludes an informative-label explanation but cannot serve as independent
replication. The upstream repository's root license also differs from its
README license statement, so source bodies remain under restricted custody and
only body-free aggregate evidence is eligible for release pending a rights
decision.

Third, compilation correctness cannot establish source-language faithfulness.
If a public relation is misread before it enters the typed representation, the
downstream proof concerns the wrong contract. Independent formulation review
and shifted-language evaluation remain necessary.

Fourth, the TSP confirmation remains within one source and perturbation family,
and its rows share template lineage. The OR-Debug analysis addresses dependence
through 100 prespecified public-shape groups, but that key is not proven to
capture every shared source-model or generation-template lineage. Its group
sign test is therefore conditional on the stated grouping and does not
establish transfer to unrelated industrial models. The mixed router uses
frozen known envelopes and is not a test of learned routing under distribution
shift.

Fifth, the successful TSP and OR-Debug skills are authored under the proposed
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

Sixth, the external comparison is not a uniform leaderboard. The fixed
common-38 study now supplies matched Base, BIND, CoE-safe and current-method
rows on identical public packets and the same endpoint, but their native
trajectories consume different numbers of model calls. BIND final additionally
receives answer-bearing feedback, CoE remains limited by the safe adapter, and
official OptiTrust lacks a verified runnable artifact. The separately labeled
`OptiTrust-style-safe-sidecar` v1 remains an unscoreable historical transport
failure. Its indexed replacement closes that transport boundary but fails two
prospective method gates before solver execution, so it likewise contributes
no accuracy row. The separate at-most-one-call view controls only the
inference-call ceiling and does not equalize authored library-construction cost
or provider tokens. The 38 identities cover two families from one source
lineage; the paired results can establish a large effect on this frozen cohort,
not broad moderate-effect leaderboard superiority or transfer to unrelated
optimization families.

Seventh, the endpoint panel alone cannot identify every component contribution. Semantic and
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
candidate pool, and all 2,985 mixed records occupy known unique routes. The
finite censuses avoid pseudoreplication by making narrower population claims:
semantic and resource admission are exhaustively tested on the complete
64-member typed-count grammar, and routing is exhaustively tested on the
complete 69-envelope shift and ambiguity grammar. Description-length selection
is exhaustively tested on all 64 calibration subsets of the authored six-
shadow-guard library grammar. These designed contract tests do not estimate a
proposer-distribution average, natural library evolution, unrestricted shift
robustness, or the mechanism responsible for the benchmark gains.

Finally, all paths in the current submission evidence manifest are tracked and
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
current history-free evidence surface is publicly frozen as `v1.1.1` at the
zero-parent commit `ed663fcdf8336f77c466652a516d5bc2c567f93a`. A fresh
recursive clone from the public tag acquired the pinned submodule, passed full
object checks, 81 credential-free Layer-A tests and three deterministic
reconstruction checks, and remained clean. The four release assets were
downloaded again and matched their server SHA-256 digests. The release also
closes a concurrent bookkeeping-cleanup race found while validating `v1.1.0`;
the corrected publisher then passed 500 identical-payload and 500
different-payload concurrent repetitions in the public clone. Gurobi remains a
separate commercial dependency. No archival DOI is claimed. These archival
conditions do not change the closed numerical results.

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
OR-Debug studies show large full-denominator gains for complete authored systems
over frozen controls. An independently frozen RetailOpt-190 study further shows
that sparse obligation and counterexample retrieval through a shared short-
decision compiler raises accuracy from 50/190 to 170/190, with 25 corrected
and one regressed five-variant archetype; a post hoc label-blind replication
retains the conclusion at 185/190. The released-label OR-Debug endpoint is primary; the
source-corrected endpoint is a sensitivity. The fixed common-38 implementation
comparison also shows a large difference from Base, BIND and CoE-safe on two
larger optimization families under unequal inference and construction regimes
and one source lineage. A public-only mixed router preserves all direct-family
outputs, while finite censuses exhaustively test bounded semantic-admission,
resource-admission and selective-routing contracts. External reproductions, a
negative automatic proposer, a zero-discordance matched feedback canary, a
positive finite active-acquisition census, and an exact finite description-
length-selection census delimit the current evidence. A prospective strict
same-fact comparison fails to improve FormulationBench accuracy, and a second
independent diagnostic finds neutral fact structuring plus a positive but non-
significant routed-skill effect on NLEquiv-150. The methodology therefore
supports auditable benchmark-specific skill engineering and bounded acquisition
inside an authored grammar, but not an architecture-only accuracy benefit,
universal semantic correctness, or autonomous natural-language knowledge
discovery. The historical
`OptiTrust-style-safe-sidecar` exposes a capacity failure of repeated full-model
generation; the OptiTrust-style indexed adapter removes that failure but does
not pass its frozen method gate. Neither result supplies an accuracy estimate
or ranks OptiTrust. Natural-language grammar
and fact acquisition, natural library-selection replication, and a second
independent RetailOpt-like source remain valuable extensions. Such replication
is required before claiming broad benchmark superiority, but is not needed for
the bounded RetailOpt-190 or common-38 results reported here. The completed
same-fact and NLEquiv endpoints remain negative development evidence and are
not reinterpreted as confirmation.

The public `v1.1.1` package is the current verified integrity/audit snapshot: it reconstructs
aggregate arithmetic, evidence bindings and body-free output identities, but
does not redistribute restricted task bodies or evaluator-only answers and
therefore cannot itself rescore every central endpoint. A separate frozen,
hash-bound controlled-review protocol permits endpoint recomputation under
restricted-data custody; a fresh-context, author-controlled computational review
reproduced all three central endpoint families exactly. This separation preserves the
release boundary rather than treating aggregate integrity as end-to-end public
benchmark reproduction.

## Data and code availability

First-party code, typed skill and library manifests, public-only routing and
verification code, aggregate evidence, figure Source Data and deterministic
reconstruction commands for the current indexed-closure evidence surface are
publicly available in the history-free `v1.1.1` release at
<https://github.com/ChengxiSHE/LLM4UO_EAAI> under Apache-2.0, with
explicitly marked author-owned aggregate Source Data and documentation under CC
BY 4.0. The exact release bundle and five-layer audit sidecars are attached to
the GitHub Release. A fresh public recursive clone verified the tag, current
81-path manifest, pinned submodule and credential-free integrity contract. An
archival DOI is not yet claimed. The solver-in-the-loop dataset remains an external pinned
submodule under its upstream terms, and Gurobi 13.0.1 requires a separate user
installation and license. Provider replay requires a user-supplied account and
credential; credential-free evidence reconstruction does not. Private request
and response bodies, credentials, evaluator-only answers and restricted
upstream task text are excluded from release.
RetailOpt-190 task bodies are also excluded because the upstream root license
and README license statement disagree; the release may include only the
first-party compiler, body-free custody hashes, plan metadata and aggregate
results until that rights boundary is resolved.
The public package therefore supports integrity reconstruction rather than
public rescoring from those excluded materials. Conference artifact reviewers
may recompute the TSP, OR-Debug and common-38 endpoints through the frozen
controlled-review protocol, which verifies exact input/code hashes and emits
only an aggregate attestation
([protocol](../docs/CONTROLLED_ENDPOINT_REVIEW_PROTOCOL_20261016.md)).
The completed aggregate audit is available separately
([audit](../docs/CONTROLLED_ENDPOINT_REVIEW_AUDIT_20261016.md)).
The public aggregate table can be rebuilt without restricted inputs using
`python3 scripts/build_reviewer_claim_table.py --check`; the complete reviewer
route and controlled-access conditions are listed in
[`REVIEWER_EVIDENCE_INDEX.md`](REVIEWER_EVIDENCE_INDEX.md). Controlled-access
requests may be sent to the corresponding author at
`522023150104 [at] smail.nju.edu.cn`, subject to upstream rights.

## AI-use disclosure

Language models were used in the explicitly identified candidate-generation
experiments, in software-development assistance and in manuscript drafting.
Candidate knowledge, code changes, numerical results and prose were not
accepted solely on model output. Human authors defined the research questions
and frozen evaluation contracts, reviewed the outputs, and verified the
reported evidence through deterministic checks, controlled endpoint recomputation,
source and citation audits, and reproducible reconstruction. The human authors
remain accountable for all claims, analyses, citations and released artifacts.

