# Theoretical framework for benchmark-grounded knowledge evolution

Status: paper-facing design note, 2026-10-15. This note connects the current
knowledge-library construction process to explicit theoretical objects and
separates proved software properties, assumption-conditional statistical
claims, and open empirical hypotheses. It does not retroactively turn authored
skills into automatically discovered skills.

## Decision

The knowledge base and its construction process can be organized under one
coherent framework: **verified structural risk minimization over a versioned
skill library**. The framework combines five established ideas whose
composition is specific to this system:

1. finite program learning and counterexample-guided synthesis for acquiring a
   benchmark-specific skill;
2. proof-carrying artifacts and translation validation for admitting a skill;
3. description-length control for preferring compact reusable knowledge;
4. selective prediction for routing or abstaining; and
5. safe policy improvement with sequential error spending for promoting a
   library version.

The resulting paper claim should concern the executable composition of these
pieces for optimization modeling. None of the individual ingredients should be
presented as a new general theorem.

## 1. Knowledge as a typed, partial program

For benchmark family \(b\), let \(\mathcal X_b\) be its public-input space and
let \(Q_b(x,y)\in\{0,1\}\) be the frozen benchmark endpoint. A skill is

\[
k=(g,e,t,v,r,p),
\]

where \(g\) is an applicability guard, \(e\) extracts a typed contract, \(t\)
constructs or transforms a formulation, \(v\) states semantic obligations,
\(r\) states exact resource obligations, and \(p\) records provenance. The
skill is a partial program because it is intentionally undefined outside its
guard. Undefined, ambiguous, or failed cases return the previous library.

This representation separates three quantities that free-form retrieval
usually mixes:

- **content:** what relation, domain, or transformation the benchmark failure
  says is missing;
- **scope:** which public tasks justify applying that content; and
- **certificate:** which semantic and operational conditions must hold before
  the output may be used.

A library version is

\[
L_t=(K_t,\rho_t,V,E,\operatorname{ledger}_t),
\]

where \(K_t\) is a content-addressed set of skills, \(\rho_t\) is the
public-only router, \(V\) is the trusted verifier, \(E\) is the frozen empirical
endpoint, and the ledger stores accepted and rejected ancestry. The proposer
may change a candidate skill, but it may not change \(V\), \(E\), the promotion
rule, or sealed history.

## 2. Construction as verified structural risk minimization

Let \(H_b\) be a frozen finite grammar of candidate skills. For development
groups \(S_{\mathrm{dev}}\), define paired corrections
\(C(h)\), regressions \(G(h)\), prefix-code length \(\ell(h)\), and execution
cost \(c(h)\). Let \(\operatorname{Pass}_V(h)=1\) mean that every declared
semantic and resource obligation passes. Construction selects

\[
h^*\in\arg\max_{h\in H_b}
\left[C(h)-\lambda_gG(h)-\lambda_\ell\ell(h)-\lambda_cc(h)\right]
\quad\text{subject to}\quad \operatorname{Pass}_V(h)=1.
\]

This is structural risk minimization with hard verification constraints.
Correctness obligations cannot be traded for benchmark accuracy. Description
length penalizes identity-specific patches and makes the intended unit of
knowledge an auditable reusable program. The weights, grammar, verifier, and
candidate order must be frozen before the outcomes used for selection are
opened.

The same idea applies to the whole library rather than only one candidate.
Let \(\mathscr L_t\) be the admissible successors of \(L_t\), let
\(\widehat R_{\mathrm{dev}}(L)\) be full-denominator development error, let
\(\ell(L)\) encode the router and every new typed skill, and let \(c(L)\)
measure declared execution cost. A library-level construction rule is

\[
L^*\in\arg\min_{L\in\mathscr L_t}
\left[\widehat R_{\mathrm{dev}}(L)+\lambda_\ell\ell(L)
+\lambda_c c(L)\right]
\quad\text{subject to}\quad
\operatorname{Pass}_V(k)=1\ \text{for every newly admitted }k.
\]

This is a **proof-constrained library selection problem**. It makes three
otherwise informal choices explicit: adding many narrow patches increases the
description cost; changing the router is part of the learned object; and a
development winner still remains only a candidate until independent
promotion. The current positive TSP and OR-Debug results instantiate authored
successors of this rule. They do not yet establish that the proposed automatic
acquisition procedure finds the minimizer.

### The knowledge-construction operator

To connect the implemented construction workflow to this objective, write one
library transition as the composition

\[
\mathcal T=\operatorname{Promote}\circ\operatorname{Route}\circ
\operatorname{Admit}\circ\operatorname{Acquire}\circ
\operatorname{Abstract}.
\]

`Abstract` maps development failures into typed obligations such as a missing
relation, domain, binding, objective, numerical or resource condition.
`Acquire` searches the declared grammar for a candidate satisfying those
obligations. `Admit` checks its semantic and resource certificates. `Route`
defines the unique public-input region in which the candidate may replace the
previous library. `Promote` uses fresh grouped endpoint evidence to accept or
reject the content-addressed successor. This decomposition distinguishes five
objects that a free-form knowledge-base narrative otherwise conflates: the
failure evidence, the abstraction rule, the candidate program, its deployment
region and its empirical utility.

The current project has strong evidence for admission, selective deployment
and one-step promotion, but the `Abstract` and successful `Acquire` stages of
the two positive skills were authored. Consequently, the complete operator is
the methodology, whereas automatic construction is still a hypothesis. The
matched flat-versus-separating-witness study is specifically a causal test of
the `Acquire` component; it does not need to rerun the already closed
admission and endpoint results to be interpretable.

This factorization also defines clean ablations. Removing `Admit` tests the
value of certificates, removing the description penalty tests compactness,
replacing `Route` by unconditional application tests selective deployment,
and replacing separating witnesses by fact-equivalent flat feedback tests the
acquisition policy. Each ablation must keep the remaining maps, inputs, model,
budget and endpoint fixed. Otherwise the effect cannot be assigned to the
claimed theoretical component.

For a label-independent prefix code over a frozen hypothesis family, standard
Occam reasoning gives

\[
R(h)\le \widehat R_n(h)+
\sqrt{\frac{\ell(h)\ln 2+\ln(1/\delta)}{2n}}
\]

simultaneously for all candidates with probability at least \(1-\delta\),
assuming independent target-distribution units. This motivates compact skills;
it does not validate a grammar designed after viewing the same outcomes or
make dependent benchmark templates independent.

The hypothesis \(h\) in this bound may be an entire serialized library state
\(L=(K,\rho)\), provided the code for skills and router is prefix-free and was
fixed before evaluated labels were observed. Thus complexity control can be
attached to the actual paper object, the routed library, rather than to prompt
length alone. This remains an assumption-conditional interpretation until a
matched complexity ablation is run.

## 3. Evolution as version-space reduction

Every retained semantic or resource counterexample induces a predicate
\(W_j(h)\). The surviving version space after \(j\) witnesses is

\[
H^{(j)}=\{h\in H_b:W_i(h)=1\text{ for all }i\le j\}.
\]

It is monotone: \(H^{(j+1)}\subseteq H^{(j)}\). This supplies the theoretical
meaning of “skill evolution”: the system is not recursively rewriting itself;
it is eliminating inconsistent typed programs while retaining an auditable
lineage.

### Separating-witness progress condition

For a witness \(w\), let the verifier outcomes partition the current version
space. Define its worst-case contraction

\[
\beta(w,H)=\frac{\max_a|\{h\in H:O_w(h)=a\}|}{|H|}.
\]

If every non-singleton version space admits a witness with
\(\beta(w,H)\le\beta<1\), and the acquisition procedure always returns such a
witness, then after \(m\) rounds

\[
|H^{(m)}|\le \beta^m|H^{(0)}|.
\]

Consequently, a unique candidate is identified after at most

\[
\left\lceil\frac{\ln |H^{(0)}|}{\ln(1/\beta)}\right\rceil
\]

rounds. The proof follows by repeated substitution of the contraction bound.
Without the balance assumption, only the linear finite-class bound is valid.

This proposition gives a precise rationale for interaction-aware feedback:
return the smallest witness that separates the largest remaining candidate
classes rather than a long undifferentiated error message. Whether an LLM uses
such feedback more effectively is an empirical question and requires the
already planned matched acquisition experiment.

## 4. Admission as proof-carrying compilation

For a typed source contract \(C\), compiled model \(T_k(C)\), and projection
\(\pi\), the semantic obligation is

\[
g_k(C)\Rightarrow
\pi(\operatorname{Sol}(T_k(C)))=\operatorname{Sol}(C),
\]

with objective preservation for optimization. A separate resource certificate
accounts exactly for declared columns, rows, nonzeros, serialized bytes, and
backend limits. These are independent gates: semantic equivalence does not
imply executable size, and compilation does not imply semantic fidelity.

Conditional correctness composes only if the public guard is sound, extraction
recovers all correctness-relevant fields, compilation preserves feasible
solutions and objectives, the backend solves the compiled model correctly, and
projection is faithful. This leaves natural-language interpretation as an
explicit premise instead of pretending that a solver can certify it.

The admission layer is **producer agnostic**. BIND, CoE, OptiTrust, an LLM, a
human author, or enumeration can propose a skill. If two proposers emit the
same content-addressed artifact, the unchanged verifier must return the same
decision. This is the formal compatibility story: other methods can improve
proposal quality, while the proof-carrying layer controls admission. It does
not guarantee that an external method will emit a translatable or useful skill.

## 5. Routing as selective prediction

For one candidate skill, let \(A(x)\) indicate exactly-one guard acceptance,
\(B(x)\) the previous-library output, and \(K(x)\) the candidate output. The
routed system is

\[
R(x)=A(x)K(x)+(1-A(x))B(x)
\]

in functional notation. Its exact endpoint difference is

\[
\operatorname{Acc}(R)-\operatorname{Acc}(B)
=\Pr(A,B\text{ wrong},K\text{ correct})
-\Pr(A,B\text{ correct},K\text{ wrong}).
\]

This identity makes coverage and risk inseparable. A router that covers more
tasks is useful only when accepted corrections exceed accepted regressions.
Compile rate, verifier rate, and route coverage are mechanism measures rather
than substitutes for full-denominator benchmark accuracy.

### Conservative library extension

Suppose \(L_{t+1}\) wraps the exact previous library \(L_t\) and invokes a new
skill only when exactly one new public guard accepts; otherwise it returns the
stored output of \(L_t\). Then

\[
R_{t+1}(x)=R_t(x)
\]

for every input on which the new guard does not uniquely accept. This includes
no-match and overlap/ambiguity cases. The result is deterministic and requires
no statistical assumption. It establishes backward-compatible expansion of a
multi-benchmark library outside the new skill's unique acceptance region.

Inside that region, non-regression remains empirical unless pointwise dominance
is independently certified. Thus safe extensibility consists of two different
claims: exact preservation outside coverage and measured correction/regression
inside coverage.

### Modular utility of a multi-skill library

For a fixed benchmark family, or for a prespecified mixture over families in
which each sample uses its own frozen endpoint, let \(A_j(x)\) denote the event
that the router uniquely selects skill \(j\). Exactly-one routing makes these
events pairwise disjoint. With
\(q_0=Q_b(x,R_t(x))\) and \(q_j=Q_b(x,K_j(x))\), a library that selects
\(K_j\) on \(A_j\) and otherwise returns \(R_t\) satisfies

\[
\operatorname{Acc}(R)-\operatorname{Acc}(R_t)
=\sum_j\left[
\Pr(A_j,q_0=0,q_j=1)-\Pr(A_j,q_0=1,q_j=0)
\right].
\]

The result follows by writing the pointwise endpoint difference as
\(\sum_j A_j(x)(q_j-q_0)\) and taking expectations. It supplies the missing
link from individual skills to a knowledge base: under single-skill selective
routing and a fixed evaluation mixture, library value is exactly the sum of
routed corrections minus routed regressions. It does not apply unchanged when
the family mixture is changed after evaluation or when several skills jointly
rewrite one formulation; such composition needs a separate interaction
contract.

## 6. Promotion as sequential safe policy improvement

A candidate that passes the verifier may still be useless on the benchmark.
Promotion therefore operates on lineage-separated groups and requires a
positive lower confidence bound on paired gain plus an upper confidence bound
on regression mass. If generation \(t\) uses a valid conditional test with
error budget \(\alpha_t\), and \(\sum_t\alpha_t\le\alpha\), then a union bound
limits the probability that any promoted generation violates its stated gate
to at most \(\alpha\).

The same budget can control selection among several candidate libraries. Let
\(a_t\) be a generation weight with \(\sum_ta_t\le1\), and let frozen
prefix-code lengths satisfy Kraft's inequality inside generation \(t\). Giving
candidate \(L\) error budget
\(\alpha a_t2^{-\ell_t(L)}\) controls the probability of any false promotion
over all candidates and generations by \(\alpha\). This connects library
complexity to the promotion protocol: a large search over long candidates does
not receive an unpenalized family-wise error budget. It remains invalid when
the code or candidate family is chosen after the same promotion outcomes are
opened.

There is also a cumulative safety interpretation. Under one fixed target
distribution and endpoint, if every promoted transition has population
regression mass at most \(\bar\epsilon_t\), paired gain decomposition and
telescoping give

\[
\operatorname{Acc}(L_T)\ge
\operatorname{Acc}(L_0)-\sum_{t<T}\bar\epsilon_t.
\]

This is a degradation budget rather than a monotone-improvement theorem. It
does not compare versions evaluated under changing benchmark mixtures,
endpoints, or post-hoc family weights.

This gives an interpretable two-level guarantee:

- the verifier controls declared semantic and resource obligations; and
- the promotion endpoint controls observed benchmark utility.

Neither level subsumes the other. The guarantee also fails if evaluation groups
are dependent in an undisclosed way, the endpoint changes after seeing results,
or the same confirmation outcomes are reused adaptively.

## 7. Methodology implied by the theory

The complete process should be reported as seven reproducible stages:

1. **Freeze benchmark semantics.** Define public inputs, hidden endpoint,
   lineage groups, denominators, costs, and custody boundaries.
2. **Induce failure obligations.** Cluster development errors by missing
   relation, domain, binding, objective, numerical, or resource obligation.
3. **Declare a typed grammar.** Specify admissible knowledge fields, guards,
   transformations, exclusions, description code, and resource limits.
4. **Acquire by separating witnesses.** Propose or enumerate candidates,
   retain the first semantic/resource witness, and shrink the version space.
5. **Compile a proof-carrying skill.** Emit the typed program, semantic and
   resource certificates, provenance, and exact fallback target.
6. **Calibrate selective routing.** Freeze public-only guards and report
   coverage, ambiguity, abstention, corrections, and regressions.
7. **Promote and version.** Compare against the previous and strong static
   libraries on held-out groups, spend a prespecified error budget, then append
   or reject the content-addressed successor.

This is the paper's methodology. “Giving Codex a goal and letting it iterate”
is an engineering workflow used during research, not a method definition.

The seven stages align with four distinct theoretical layers:

| Layer | Stages | Formal object | Defensible guarantee |
| --- | --- | --- | --- |
| Acquisition | 2--4 | finite grammar and retained witnesses | finite termination; verifier-relative soundness; conditional contraction under balanced witnesses |
| Admission | 5 | typed skill plus semantic/resource certificate | declared contract and resource obligations pass, conditional on the checker and oracle |
| Deployment | 6 | exactly-one public router over a versioned library | exact fallback outside unique coverage; additive correction-minus-regression accounting across selected skills |
| Evolution | 1 and 7 | frozen endpoint, grouped promotion and immutable ledger | conditional control of false promotion across candidates and generations; cumulative regression budget under one fixed target |

This separation is essential for the paper. Acquisition theory cannot certify
natural-language interpretation, admission cannot imply benchmark usefulness,
and routing cannot turn observed zero regressions into a future dominance
theorem. The layers compose only through their stated interfaces.

### Statistical unit for acquisition

The construction process needs a statistical object distinct from a benchmark
row. Define one acquisition unit as a rejected typed proposal together with its
frozen grammar, verifier, endpoint, request/resource budget, parent lineage and
custody state. For fact-equivalent flat and separating-witness feedback, let
$Y_i(0)$ and $Y_i(1)$ indicate admission within the common budget. On a
predeclared finite proposal population,

\[
\tau_U=\frac1n\sum_i\left[Y_i(1)-Y_i(0)\right]
=\frac{n_{01}-n_{10}}{n}.
\]

This is an arithmetic finite-population identity. Independence is instead a
premise for confidence intervals, tests, power and generalization. Revisions
sharing one parent are a lineage cluster, not independent replication.
Per-instance formulation trajectories are evidence for failure clustering,
not automatically skill-acquisition units. Across task strata, weights must be
fixed before outcomes; otherwise a pooled effect changes its target after the
fact.

The metadata inventory exposes five DCP skill-proposal identities but only one
historical proposal under the common frozen typed grammar. It also separates
229 per-instance packing trajectories and six inspected legacy VERA identities,
neither of which is exchangeable with that typed unit. The completed eight-pair
language-model canary has zero discordance and therefore remains an engineering
negative result. A separate complete finite census over the authored semantic
grammar shows that balanced verifier-selected witnesses identify 10/10
extensional classes within three queries versus 6/10 for the frozen
canonical-order control. This exact finite-population effect does not estimate
a natural proposer distribution. For such a stronger expansion, the original
conditional power calculation remains relevant: under the illustrative
$r=.30,q=.70$ alternative, 138 independent pairs provide 80% power and 186
provide 90% power at one-sided alpha .05.

## 8. Claim-to-evidence boundary

| Theoretical component | Current evidence | What remains required |
| --- | --- | --- |
| Finite version-space elimination | Complete 64-member count grammar, exact minimum distance-two repair and ten-class balanced-witness census; balanced identifies 10/10 within three queries versus 6/10 for canonical order | Natural-language hypothesis construction outside the authored grammar |
| Proof-carrying admission | Typed TSP and OR-Debug contracts plus the complete 64-candidate gate census; removing semantic or resource admission creates 11 or 5 unsafe admissions | Natural proposer-distribution replication and undeclared resource obligations |
| Selective routing and exact fallback | 2,985/2,985 direct-family output preservation plus 69/69 correct decisions over the complete structured ambiguity grammar, versus 24/69 for forced-first | Shifted-language and unseen-family routing study |
| Modular library utility | Exact correction-minus-regression decomposition and a fresh two-family common-38 current-method comparison | Interacting multi-skill rewrites, equalized construction cost and second-source replication |
| Matched acquisition effect | Negative eight-pair language-model canary plus positive exact finite balanced-witness census | Prospective natural proposal population with independently generated semantic axes or facts |
| Sequential promotion | One grouped OR-Debug promotion followed by sealed confirmation | Complexity-weighted candidate allocation, fully replayable gate values, lineage audit, and additional generations on one fixed target |
| Compactness control | Formal prefix-code bound and complete 64-library by 64-calibration-subset shadow-guard census; MDL selects a fully correct library in 64/64 episodes versus 1/64 for proof-only frozen hash | Naturally proposed libraries and a causal result for the current TSP/OR library |
| Cross-method compatibility | Fresh common-38 current/Base/BIND/CoE-safe comparison under one frozen endpoint | Equal native budgets, a second source lineage and an official OptiTrust artifact if one becomes available |

The current positive results support **authored benchmark-specific typed skill
engineering**, bounded active acquisition inside an authored grammar, and
finite-population effects for the declared admission, routing and compactness
interventions. They do not show that the full acquisition loop discovers
natural-language semantics automatically or that the effects generalize to a
natural library distribution. Theory makes that distinction sharper; it cannot
replace those stronger experiments.

## 9. Paper framing

The strongest defensible story is:

> Optimization-modeling knowledge is treated as a small typed program selected
> from benchmark failures, not as unversioned prompt text. Counterexamples
> reduce a finite version space, a trusted compiler admits only artifacts that
> satisfy declared semantic and resource obligations, a selective router
> preserves the previous library outside unique coverage, and held-out endpoint
> tests decide whether a version is promoted.

The novelty should be claimed at the level of this benchmark-grounded,
executable composition and its evidence chain. The main falsifiable prediction
for the next study is that balanced separating-witness feedback will reduce the
number of proposals or increase verifier-valid acquisition at a fixed request
and token budget. The second prediction is that conservative routing preserves
old-family behavior while increasing full-denominator accuracy when a newly
verified family skill is added.

Recent skill-evolution work makes the scope boundary especially important.
Typed contracts, validation-gated editing, executable skill programs,
applicability filtering and versioned skill revision all have direct 2026
precedents. The project should therefore claim neither the first verifiable
skill library nor the first validation-gated skill evolution method. Its
defensible contribution is the optimization-modeling instantiation in which
the retained knowledge is a typed formulation transformation with executable
semantic and resource obligations, the endpoint is solver-facing formulation
accuracy, fallback is exact outside unique public coverage, and promotion is
audited on lineage-separated benchmark groups.
