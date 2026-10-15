# Supplementary theory for Benchmark-Grounded Proof-Carrying Knowledge Compilation

## S1. Scope

This supplement formalizes the bounded claims used by the main manuscript. The
individual proof techniques follow established finite synthesis,
proof-carrying-code, translation-validation, selective-prediction and
high-confidence-improvement ideas
[@solarlezama2008sketching; @alur2013sygus; @necula1997proofcarrying;
@pnueli1998translation; @elyaniv2010selective; @thomas2015hcpi]. The project
contribution is their executable composition for benchmark-grounded
optimization-modeling skills. None of the statements below proves arbitrary
natural-language understanding, grammar completeness, universal formulation
equivalence, distribution-free non-regression or unrestricted recursive
self-improvement.

## S2. Definitions

Let $b$ index a benchmark family, $\mathcal X_b$ its public-input space, and
$Q_b(x,y)\in\{0,1\}$ its frozen endpoint applied to an output $y$ for public
input $x$. An endpoint may combine status, feasibility, objective agreement,
repair identity or another prespecified benchmark rule.

A skill is

\[
k=(g,e,t,v,r,p),
\]

where $g:\mathcal X_b\to\{0,1\}$ is a public-input guard, $e$ extracts a typed
contract, $t$ constructs or transforms a formulation, $v$ checks declared
semantic obligations, $r$ checks exact declared resource limits, and $p$
records provenance.

A library version is

\[
L_t=(K_t,\rho_t,V,E,\operatorname{ledger}_t),
\]

where $K_t$ is a content-addressed set of skills, $\rho_t$ is a public-only
router, $V$ is the trusted admission verifier, $E$ is the frozen empirical
endpoint, and the ledger stores accepted and rejected ancestry. The proposer
may suggest a member of $K_{t+1}$ but may not modify $V$, $E$, the promotion
rule or a previously sealed ledger.

For one proposed skill, let $H_b$ be a declared finite candidate grammar,
$D_b$ a finite verification domain and $O_b$ an independently implemented
contract oracle. Write $V(h)=1$ when candidate $h\in H_b$ satisfies every
declared semantic and resource obligation. A rejected candidate may carry a
first witness $x\in D_b$ such that $h(x)\neq O_b(x)$ or an exact resource-limit
violation.

For deployment, let $B(x)$ be the frozen previous-library output, $K(x)$ the
candidate-skill output and $A(x)\in\{0,1\}$ the event that exactly one pinned
public guard accepts. The routed output is

\[
R(x)=\begin{cases}
K(x), & A(x)=1,\\
B(x), & A(x)=0.
\end{cases}
\]

The definitions deliberately separate verifier acceptance from endpoint
correctness. The former concerns the declared contract; the latter remains a
benchmark observation.

An acquisition unit is a proposal state

\[
u=(b,H_b,D_b,O_b,V,h_0,a,c),
\]

where $h_0$ is the rejected starting proposal, $a$ fixes the request and
resource budget, and $c$ records parent lineage and custody. Let feedback
policies $f_0$ and $f_1$ receive the same content-addressed atomic facts, with
$f_1$ additionally receiving only a verifier-derived partition of those
facts. Write $Y_u(z)\in\{0,1\}$ for whether policy $f_z$ produces an admitted
candidate within $a$. Per-instance formulations, free-text rules outside
$H_b$, and sequential revisions sharing a parent are not automatically
independent acquisition units.

For a multi-skill extension, let $A_j(x)$ be the event that the router uniquely
selects skill $j$. Exactly-one routing makes the events $A_1,\ldots,A_m$
pairwise disjoint; zero matches and overlapping guards belong to the fallback
event. This definition covers alternative family skills selected one at a
time, not several transformations composed on the same formulation.

## S3. Finite construction

### Proposition S1 — finite termination

Assume $H_b$ is finite, candidates are considered under a fixed policy, and
every failed decision permanently removes at least the current candidate. Then
the construction procedure terminates after at most $|H_b|$ candidate
decisions.

**Proof.** Initially at most $|H_b|$ candidates remain. Every failed decision
strictly decreases this integer by at least one. Acceptance terminates the
procedure earlier; otherwise no candidate remains after at most $|H_b|$
failures. Therefore the procedure cannot make more than $|H_b|$ candidate
decisions. $\square$

The conclusion does not apply to an open-ended language-model program space or
to a procedure that can reintroduce rejected candidates.

### Proposition S2 — enumerated-domain soundness

Assume the verifier evaluates every $x\in D_b$ and accepts $h$ only if
$h(x)=O_b(x)$ for all $x\in D_b$. Then an accepted $h$ is extensionally equal
to $O_b$ on $D_b$.

**Proof.** Acceptance is defined by the conjunction
$\bigwedge_{x\in D_b}[h(x)=O_b(x)]$. Every conjunct is therefore true for an
accepted candidate. $\square$

This is a verifier-relative finite statement. It does not establish correctness
outside $D_b$, correctness of $O_b$, completeness of $H_b$, or faithfulness of
the typed contract to the source prose.

### Proposition S3 — exact minimum repair in a frozen grammar

Let $h_0\in H_b$ be rejected, let $d$ be a declared distance on $H_b$, and let
$P=\{h\in H_b:V(h)=1\}$. If exhaustive verification evaluates every member of
$H_b$ and $P\neq\varnothing$, then

\[
d^*=\min_{h\in P}d(h_0,h)
\]

and the reported set $P^*=\{h\in P:d(h_0,h)=d^*\}$ are exact. In particular,
the repair is unique if and only if $|P^*|=1$.

**Proof.** Finiteness of $H_b$ makes $P$ finite. Exhaustive verification
classifies every member, so no passing candidate is omitted. Taking the minimum
over this complete finite set gives the exact minimum, and filtering by equality
to that minimum gives all and only the minimum-distance repairs. $\square$

If $P=\varnothing$, exhaustive verification instead certifies absence of a
passing repair inside the grammar. Neither case says whether a better program
exists outside $H_b$.

### Proposition S4 — monotone version-space elimination

Let $W_1,W_2,\ldots$ be fixed predicates induced by retained rejecting
witnesses, and define

\[
H^{(j)}=\{h\in H_b: W_i(h)=1\text{ for every }i\le j\}.
\]

Then $H^{(j+1)}\subseteq H^{(j)}$ for every $j$. If every rejected candidate
fails a retained predicate and rejected candidates are never repeated, a
passing member, when one exists, is found after at most $|H_b|-1$ rejections;
an empty passing set is exhausted after $|H_b|$ rejections.

**Proof.** $H^{(j+1)}$ adds one conjunct to the definition of $H^{(j)}$, so it
cannot add members. The rejection bounds follow by counting distinct eliminated
members of the finite set. $\square$

No logarithmic query bound follows without an additional balance condition on
the witnesses. Generalized binary search motivates separating-witness choice,
but its stronger rates are not inherited automatically [@nowak2011gbs].

### Proposition S4.1 — conditional balanced-witness contraction

Let a witness $w$ partition a nonempty version space $H$ by verifier outcome,
and define

\[
\beta(w,H)=\frac{\max_a|\{h\in H:O_w(h)=a\}|}{|H|}.
\]

Assume that for every non-singleton reachable $H^{(j)}$, the acquisition
procedure chooses a witness with
$\beta(w_j,H^{(j)})\le\beta<1$. Then

\[
|H^{(m)}|\le\beta^m|H^{(0)}|,
\]

and a nonempty version space is a singleton after at most

\[
\left\lceil\frac{\ln |H^{(0)}|}{\ln(1/\beta)}\right\rceil
\]

witnesses.

**Proof.** The outcome observed at round $j$ retains one cell of the witness
partition, whose size is at most $\beta|H^{(j)}|$. Repeated substitution gives
the geometric bound. At the displayed round count the nonempty integer size is
at most one, hence exactly one. $\square$

This is a conditional teaching bound, not a property established for the
current language-model proposer. In the complete ten-class extensional
population induced by the authored count grammar, the balanced witness policy
identifies 10/10 classes within three queries, versus 6/10 for the frozen
canonical-order separating-witness control. This exact census establishes the
bounded policy effect only for that grammar and oracle; it does not establish
language-model proposal quality or natural-language fact discovery. Without
the balance premise, Proposition S4 supplies only the linear finite-class
bound.

## S4. Proof-carrying execution

### Proposition S5 — conditional accepted-path correctness

For a public task $x$, assume:

1. $g(x)=1$ only when $x$ satisfies a source contract $C$;
2. $e(x)$ recovers every correctness-relevant field of $C$;
3. compilation produces $T_k(C)$ whose feasible solutions and objective are
   preserved under projection $\pi$;
4. the backend returns an exact optimum $z^*$ of $T_k(C)$; and
5. output projection returns $\pi(z^*)$ without alteration.

Then the accepted output is optimal for $C$.

**Proof.** By assumptions 1 and 2, the compiler receives the correct complete
typed contract. Assumption 3 maps every compiled optimum under $\pi$ to a
feasible source solution with the same objective and preserves the source
optimum. Assumption 4 supplies such a compiled optimum, and assumption 5
returns its projection. Therefore the returned solution is feasible and
optimal for $C$. $\square$

The proposition is deliberately conditional. A downstream solver cannot
repair an unsound guard, missing extracted field or incorrect source
interpretation.

### Proposition S6 — declared resource safety

Let $c(T)$ be the compiler's exact accounting vector for a compiled model $T$
and $u$ the vector of declared limits. If the accounting is complete for those
limits and admission requires $c(T)\le u$ componentwise, every admitted model
satisfies the declared limits.

**Proof.** Admission implies each checked component of $c(T)$ is at most its
corresponding component of $u$. Completeness means no declared component is
omitted. $\square$

This property does not bound wall-clock runtime, prove solver success, or cover
an unmeasured resource.

## S5. Selective deployment

### Proposition S7 — exact fallback identity

For every $x$ with $A(x)=0$, $R(x)=B(x)$. If the implementation returns the
stored baseline artifact rather than regenerating it, this equality can be
strengthened to byte identity.

**Proof.** Substitute $A(x)=0$ into the definition of $R$. $\square$

### Corollary S7.1 — conservative extension under dominance

If $Q_b(x,K(x))\ge Q_b(x,B(x))$ for every accepted $x$, then the routed system
cannot have lower population accuracy than the baseline.

**Proof.** Outside acceptance, Proposition S7 gives identical endpoint values.
Inside acceptance, the assumed pointwise dominance makes every difference
nonnegative. Taking expectations preserves the inequality. $\square$

Observed zero regressions does not establish the premise for future samples.
The corollary states what a true dominance certificate would imply.

### Proposition S8 — paired gain decomposition

Let $q_K=Q_b(x,K(x))$ and $q_B=Q_b(x,B(x))$. Then

\[
\operatorname{Acc}(R)-\operatorname{Acc}(B)
=\Pr(A=1,q_B=0,q_K=1)-\Pr(A=1,q_B=1,q_K=0).
\]

**Proof.** Pointwise,

\[
Q_b(x,R(x))-q_B=A(x)(q_K-q_B).
\]

The factor is $+1$ only for an accepted correction, $-1$ only for an accepted
regression and zero otherwise. Taking expectations gives the identity.
$\square$

This identity explains why coverage, compilation rate and verifier acceptance
cannot replace full-denominator endpoint accuracy.

### Proposition S8.1 — conservative library extension

Let $R_t$ be the exact previous-library policy. Define a successor wrapper with
a new candidate skill $K_{t+1}$ and public acceptance event $A_{t+1}$ by

\[
R_{t+1}(x)=\begin{cases}
K_{t+1}(x), & A_{t+1}(x)=1,\\
R_t(x), & A_{t+1}(x)=0,
\end{cases}
\]

where $A_{t+1}(x)=1$ only for exactly-one new-guard acceptance; no match or
multiple matches set $A_{t+1}(x)=0$. Then
$R_{t+1}(x)=R_t(x)$ for every input outside unique new-skill acceptance.

**Proof.** For every such input, $A_{t+1}(x)=0$ by definition. Substitution
selects the second branch, which is the stored previous-library policy.
$\square$

The proposition establishes backward-compatible expansion outside the new
coverage region, including ambiguity. It says nothing about endpoint risk
inside that region; paired corrections and regressions remain empirical unless
pointwise dominance is independently certified.

### Corollary S8.2 — modular multi-skill gain decomposition

Fix one benchmark family, or a prespecified mixture over $(b,x)$ in which each
sample is scored by its family endpoint $Q_b$. Let $R_t$ be the
previous-library policy, and let a successor choose $K_j(x)$ on the
pairwise-disjoint event $A_j(x)$ for $j=1,\ldots,m$, returning $R_t(x)$
otherwise. Write $q_0=Q_b(x,R_t(x))$ and $q_j=Q_b(x,K_j(x))$. Then

\[
\operatorname{Acc}(R)-\operatorname{Acc}(R_t)
=\sum_{j=1}^m\left[
\Pr(A_j=1,q_0=0,q_j=1)-
\Pr(A_j=1,q_0=1,q_j=0)
\right].
\]

**Proof.** Pairwise disjointness gives the pointwise identity

\[
Q_b(x,R(x))-q_0=\sum_{j=1}^m A_j(x)(q_j-q_0).
\]

Each summand is $+1$ on a routed correction, $-1$ on a routed regression and
zero otherwise. Taking expectations and using linearity proves the result.
$\square$

The corollary supplies a library-level utility accounting rule for selective
single-skill routing under that fixed evaluation distribution. It does not
justify changing family weights after seeing results and does not cover a
pipeline in which multiple skills interact on one formulation; that setting
requires a joint skill or a separate composition verifier.

### Corollary S8.3 — matched acquisition estimand

Fix before outcomes a finite collection $U=\{u_1,\ldots,u_n\}$ of acquisition
states and two fact-equivalent feedback policies $f_0,f_1$. Assume both
potential outcomes $Y_i(0),Y_i(1)$ are evaluated under the same frozen grammar,
verifier, endpoint and budget. Then the finite-population acquisition effect is

\[
\tau_U=\frac1n\sum_{i=1}^n\bigl(Y_i(1)-Y_i(0)\bigr)
=\frac{n_{01}-n_{10}}{n},
\]

where $n_{01}$ counts flat failures followed by separating-witness successes
and $n_{10}$ counts the reverse discordance.

**Proof.** For each unit, the paired difference is $+1$ on a $01$ discordance,
$-1$ on a $10$ discordance and zero on concordant outcomes. Summation and
division by $n$ give the identity. $\square$

The identity itself needs no independence assumption. A superpopulation test,
confidence interval or power claim does: proposal states must be independently
sampled or analyzed at a valid lineage-cluster level. Sequential revisions of
one parent cannot be counted as independent units. For prespecified strata
$s$, the target effect is $\sum_s w_s\tau_s$ only when weights $w_s$ are fixed
before outcomes; post-hoc pooling changes the estimand. Exact paired inference
may condition on the number of discordant independent units, but it does not
repair packet nonequivalence, opened outcomes or invalid custody.

## S6. Complexity control

### Proposition S9 — prefix-code generalization bound

Let $H$ be a countable hypothesis family with a label-independent prefix code
of lengths $\ell(h)$ satisfying Kraft's inequality
$\sum_{h\in H}2^{-\ell(h)}\le1$. Let $R(h)$ be Bernoulli population error and
$\widehat R_n(h)$ empirical error over $n$ independent target-distribution
units. Then, with probability at least $1-\delta$, simultaneously for every
$h\in H$,

\[
R(h)\le \widehat R_n(h)+
\sqrt{\frac{\ell(h)\ln2+\ln(1/\delta)}{2n}}.
\]

**Proof.** Hoeffding's inequality gives
$\Pr[R(h)-\widehat R_n(h)>\epsilon]\le e^{-2n\epsilon^2}$ for each fixed $h$.
Allocate failure probability $\delta 2^{-\ell(h)}$ to $h$ and solve for
$\epsilon$. A union bound and Kraft's inequality give total failure probability
at most $\delta$. $\square$

The result is an Occam-style interpretation of compact skills
[@blumer1987occam]. It applies only when the code and family are frozen before
the evaluated labels and the sampling units are valid. It does not justify a
grammar authored after inspecting the same development outcomes.

### Corollary S9.1 — library-level complexity control

Let $\mathscr L$ be a countable family of serialized library states and let
$\ell(L)$ be a label-independent prefix-code length encoding both the router
and its typed skills. Applying Proposition S9 with $H=\mathscr L$ yields,
simultaneously for every $L\in\mathscr L$,

\[
R(L)\le \widehat R_n(L)+
\sqrt{\frac{\ell(L)\ln2+\ln(1/\delta)}{2n}}.
\]

**Proof.** Substitute the library family $\mathscr L$ and its prefix code for
$H$ and $\ell(h)$ in Proposition S9. $\square$

The corollary justifies treating router complexity and accumulated narrow
skills as part of the same structural-risk penalty. Its premises still require
a code fixed before the evaluated labels and independent target-distribution
units; current authored libraries do not isolate an empirical complexity
effect.

## S7. Repeated promotion

### Proposition S10 — anytime control of erroneous promotion

Let $F_t$ be the event that generation $t$ is promoted even though its stated
promotion condition is false. Let $\mathcal F_{t-1}$ denote the history before
generation $t$ outcomes are opened. Suppose the candidate and router are frozen
before those outcomes and the generation-specific procedure satisfies

\[
\Pr(F_t\mid\mathcal F_{t-1})\le\alpha_t
\]

for prespecified $\alpha_t$ with $\sum_t\alpha_t\le\alpha$. Then

\[
\Pr\left(\bigcup_t F_t\right)\le\alpha.
\]

**Proof.** Taking expectations gives $\Pr(F_t)\le\alpha_t$. The union bound
then yields
$\Pr(\bigcup_tF_t)\le\sum_t\Pr(F_t)\le\sum_t\alpha_t\le\alpha$.
$\square$

The conditional premise permits adaptive candidate generation from the past,
but each generation still needs a valid fresh evaluation unit and a procedure
whose error bound holds conditional on that history. The theorem does not
protect against a wrong endpoint, dependent pseudo-replicates, invalid grouping
or undisclosed outcome reuse.

### Corollary S10.1 — complexity-weighted anytime promotion

At generation $t$, let $\mathscr C_t$ be a finite or countable candidate set
frozen before the promotion outcomes are opened. Let $a_t\geq0$ satisfy
$\sum_t a_t\leq1$, and let the label-independent code lengths
$\ell_t(L)$ satisfy

\[
\sum_{L\in\mathscr C_t}2^{-\ell_t(L)}\leq1.
\]

If the conditional probability that a false candidate $L$ passes its promotion
gate is at most $\alpha a_t2^{-\ell_t(L)}$, then the probability that any false
candidate is promoted at any generation is at most $\alpha$.

**Proof.** Conditional on the prior history, union-bound over
$L\in\mathscr C_t$ and apply Kraft's inequality to obtain generation-$t$
failure probability at most $\alpha a_t$. Taking expectations and union-bound
over generations gives at most $\alpha\sum_ta_t\leq\alpha$. $\square$

This allocation connects the serialized library object to statistical
selection: larger candidate libraries and longer skills receive no free
multiple-testing budget. It does not show that compact skills are more accurate,
and it is invalid if the code or candidate set is chosen after inspecting the
same promotion outcomes.

### Corollary S10.2 — cumulative regression budget

Fix one target distribution and endpoint across library versions. For a
promoted transition $R_t\rightarrow R_{t+1}$, let

\[
\epsilon_t=\Pr[Q(x,R_t(x))=1,\ Q(x,R_{t+1}(x))=0]
\]

be its population regression mass. If all promoted transitions through $T$
satisfy $\epsilon_t\leq\bar\epsilon_t$, then

\[
\operatorname{Acc}(R_T)\geq
\operatorname{Acc}(R_0)-\sum_{t=0}^{T-1}\bar\epsilon_t.
\]

If the bounds hold simultaneously with probability at least $1-\alpha$ under
Proposition S10 or Corollary S10.1, the cumulative statement holds with the
same probability.

**Proof.** Proposition S8 gives
$\operatorname{Acc}(R_{t+1})-\operatorname{Acc}(R_t)$ as correction mass minus
regression mass, which is at least $-\epsilon_t$. Sum the inequalities over
$t=0,\ldots,T-1$ and apply the simultaneous event. $\square$

The result is a degradation budget, not a monotone-improvement theorem. It
requires the same prespecified target distribution and endpoint at every
generation; changing family weights or endpoints breaks the telescoping target.

## S8. Engineering invariants

The content-addressed implementation adds deterministic invariants that are
separate from statistical accuracy:

1. **Rejected-lineage exclusion.** A rejected candidate hash cannot become an
   accepted ancestor unless a new, separately identified artifact is proposed
   and admitted.
2. **Fallback preservation.** Outside exactly-one guard acceptance, the pinned
   previous output is returned unchanged.
3. **Guard non-overlap.** Zero or multiple matching guards cause abstention;
   ambiguity cannot be resolved silently by skill order.
4. **Rollback reconstruction.** Parent hashes and immutable artifacts identify
   the exact prior library state.
5. **Endpoint custody.** Evaluator-only answers may score a terminal output but
   cannot select, repair or route it.

These properties are auditable software contracts. They do not imply that a
future input lies inside a skill's semantic scope or that every admitted skill
improves the benchmark.

## S9. Empirical instantiations and remaining gaps

The count-family certificate instantiates Propositions S1--S4 for a 64-member
grammar. The TSP and OR-Debug studies instantiate paired endpoint promotion and
confirmation; the mixed-router replay instantiates exact fallback and
composition identity on frozen interfaces. These empirical studies support the
methodology but do not strengthen the propositions beyond their assumptions.

| Theory component | Construction or deployment mechanism | Current empirical instantiation | Boundary that remains |
| --- | --- | --- | --- |
| S1, finite termination | Enumerate or propose inside a frozen finite grammar and eliminate every rejected candidate | All 64 count candidates were decidable under the frozen verifier | No claim for an unrestricted natural-language hypothesis space |
| S2, finite-domain soundness | Compare a candidate with the oracle on every declared semantic assignment | The proposed count candidate passed 20,977 assignments before failing a separate resource obligation | Correctness outside the enumerated domain and correctness of the oracle are not proved |
| S3, exact minimum repair | Search the complete frozen grammar by edit distance | Six distance-one count repairs failed; one distance-two repair was uniquely minimal | Minimality is relative to the grammar, distance and verifier |
| S4, monotone version space; S4.1, balanced contraction | Retain rejecting witnesses, remove every inconsistent candidate, and measure the largest surviving outcome cell | Over all 10 extensional classes induced by the authored count grammar, balanced witnesses identify 10/10 within three queries versus 6/10 for frozen canonical-order witnesses; total queries are 26 versus 30 | Exact finite-population evidence only; no language-model proposer, natural-language fact discovery or guarantee outside the authored grammar and oracle |
| S5--S6, proof-carrying execution | Require guard, extraction, compilation, resource and endpoint obligations before adoption | TSP typed constraints and OR-Debug typed repairs share frozen compilers and independent endpoint checks | Natural-language faithfulness and undeclared resource limits remain outside the proof |
| S7, exact fallback; S8.1, conservative extension | Adopt only on one matching public guard; otherwise return the pinned prior output | The mixed router preserves byte-equivalent direct-family outputs on all 2,985 known envelopes; zero or multiple guard matches are fail-closed software contracts | Preservation holds outside new unique coverage; no robustness or non-regression claim inside coverage under paraphrases, new schemas or new families |
| S8, paired gain decomposition | Score correction and regression on the same frozen records | TSP has 46 corrections and zero regressions; OR-Debug has 1,924 and zero | Observed zero regression is not distribution-free dominance |
| S8.2, modular multi-skill gain | Sum routed corrections minus regressions across disjoint exactly-one skill-selection events | The fresh common-38 RCPSP/VRPTW comparison scores the current two-family method at 30/38 versus Base 0/38, BIND round one 13/38, BIND final 13/38 and CoE-safe 4/38 | One source lineage, unequal native budgets and authored construction cost; the comparison does not identify additive multi-skill utility or interacting rewrites |
| S8.3, matched acquisition estimand | Pair fact-equivalent feedback policies on a predeclared population of frozen proposal states and retain parent lineage | The eight-pair language-model canary has zero discordance and fails its engineering gate; the separate complete ten-class census identifies the bounded balanced-witness policy effect | The canary does not support efficacy and the positive census is an authored finite population, not a proposer-distribution estimate |
| S9 and S9.1, prefix-code control | Freeze a label-independent code and penalize the serialized skills and router during library selection | Across all 64 libraries and 64 calibration subsets in the authored six-shadow-guard grammar, proof-constrained MDL selects a fully correct library in 64/64 episodes versus 1/64 for the proof-only frozen-hash selector | Exact effect only for the authored shadow-guard grammar; it does not measure natural library evolution or the current TSP/OR library description length |
| S10 and S10.1, anytime promotion | Spend a prespecified generation budget over fresh grouped decisions and a prefix-code-weighted budget over every candidate opened within a generation | One grouped OR-Debug promotion precedes one sealed confirmation; complexity-weighted multi-candidate testing is a prospective protocol requirement | Unlimited adaptive evolution, outcome-dependent codes and dependent pseudo-replicates are not covered |
| S10.2, cumulative regression budget | Keep one target distribution and endpoint fixed, bound every promoted transition's regression mass, and telescope the bounds | TSP and OR-Debug each show zero observed paired regressions in one frozen transition, but they are different target families rather than one repeated sequence | No empirical repeated-generation guarantee; changing family weights or endpoints invalidates the cumulative target |

Three stronger claims remain empirical and open:

1. natural-language semantic axes or atomic facts can be acquired rather than
   supplied through an authored finite grammar;
2. the fresh common-38 advantage replicates on a second source lineage or a
   larger independently frozen multi-family cohort; and
3. a learned router maintains controlled risk under paraphrase and family
   shift.

These claims must be decided by prespecified experiments. They cannot be
derived from the finite proofs above.
