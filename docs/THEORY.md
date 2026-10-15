# Theoretical design and proof sketches

Status: proposed analysis, updated 2026-10-04. No universal empirical performance theorem is claimed. The results below are elementary reductions, compositions, or adaptations of standard tools; they are not, by themselves, a claim of new learning theory.

Current positioning: the user accepts a motivated combination of established mechanisms. SEMANTIC_FEEDBACK.md defines the proposed connection between executable model disagreement, a same-backbone teacher, repair gating and workflow-evolution gating. The prior-art audit still prevents claiming individual modules or standard identities as new; it does not veto studying their useful combination.

## Semantic-feedback analysis for v0.4

Compare model behavior only through an aligned decision/parameter interface and canonical objective direction/units. A feasible-set witness is a point in the symmetric difference of the observable feasible sets; for bounded nonempty LPs in a shared variable space, the row-maximization construction in Section 2 generates such witnesses. Reverse the comparison to detect overrestriction as well as omission. Positive residuals establish differences relative to formal clauses, not which natural-language interpretation is correct.

For canonical linear objectives on a common feasible domain, maximize eta>=0 subject to f_s(x)-f_s(y)>=eta and f_t(y)-f_t(x)>=eta, with x and y feasible for both models. A positive eta witnesses opposing strict preferences. Zero eta does not establish objective equivalence because ties and untested behavior remain. Positive objective scaling may preserve preferences while requiring value-unit conversion; multiple optima do not by themselves imply semantic disagreement.

Finite-probe agreement and agreement of two equally wrong candidates cannot establish correctness. Report disagreement, definite-response coverage and unknowns separately. Teacher interpretations require independent audit; neither reduced disagreement nor teacher approval is an admissible substitute for terminal correctness. Existing repair/evolution identities below explain measurable hypotheses, not guaranteed efficacy of these modules.

The expanded trusted local script checks nine synthetic cases, including equal-optimum omissions/overrestrictions, equivalent row scaling, variable permutation, solver-generated preference reversals, finite-probe/shared-error failures, integrality and objective-unit conversion. It exercises the definitions, not automatic semantic extraction or empirical modeling accuracy.

Revision after user feedback: benchmark modeling accuracy is the central objective. Equal-backbone comparisons are experimental controls; token matching is a compute-confound check. Theory should explain correction, regression and transferable workflow updates. Bandits are optional implementation choices, not mandatory modules added to justify a theorem. The engineering case is supplementary.

## 0. Current v1 method: guarded program evolution, not bandit learning

The implementation contract is [METHODOLOGY.md](METHODOLOGY.md). The evolvable object is H=(G,Gamma,Sigma): bounded control flow, evidence guards and repair-scope rules. The LLM, role prompts, primitive tools, mandatory execution protection and independent evaluator are fixed. A frozen LLM proposes typed local patches from development traces; candidate screening precedes fresh-family paired acceptance. Final tests never update the program.

The main analysis now follows the update itself. Couple a candidate and incumbent so their trajectories agree until the first modified decision. Let E be reaching that divergence, p=P(E), g=P(new correct, old wrong | E), and l=P(new wrong, old correct | E). With binary terminal quality and identical behavior outside E,

    J(H') - J(H) = p * (g-l).

This is an exact elementary total-expectation identity under the specified coupling, not a global optimization guarantee. It links guard coverage to complete-continuation correction and regression. A changed guard that requires additional model calls must count those calls as the divergence; there is no hidden free preprocessing. Pairing conventions affect g/l individually and must be reported. Formal conditions and proof are in METHODOLOGY.md Section 5.2.

For binary per-family paired outcomes, v1 specifies a one-sided exact discordant-pair binomial gate with delta_k=delta/[k(k+1)]. Candidate selection precedes each fresh gate; under independent identically distributed families, fixed evaluator and fixed sample sizes, a union bound controls ever accepting a non-improving candidate by delta. This is a standard statistical construction, not a new test. Section 5 below remains a conservative alternative for bounded family-average utilities, not a second test to choose after observing results. Small data may yield no accepted updates; neither gate guarantees progress or distribution-shift robustness.

The sequential-decision and OR-check sections below support the method. Sections 3–4 on bandits are historical optional analyses, **not used by v1**, and cannot be cited as a guarantee for local DSL search. The directly applicable proxy-quality caveat is that a proxy gain can overstate true gain by up to 2 epsilon only if a uniform epsilon calibration bound has independently been established.

## 1. Sequential decision model: useful formulation, not a guarantee

Let a problem consist of a natural-language specification d and admissible data z. A trajectory history h_t contains the specification, extracted clauses, current mathematical model, execution artifacts, prior checks and repairs, and remaining budget b_t. Actions include checking a clause, running a solver/test, repairing a localized defect, rolling back, and stopping.

The actual semantic correctness of a model is unobserved at deployment. Consequently a POMDP is a more honest description than assuming that a short error vector is a sufficient Markov state. Full history can be used as a formal state; a compact feature vector phi(h_t) is an engineering approximation whose sufficiency must not be asserted without evidence.

The primary objective is to maximize E[Q(final artifact)]; resource limits define feasible execution/evaluation conditions. A quality-minus-cost scalarization is a separate secondary objective and is not automatically equivalent to the constrained problem. Solver status, an LLM critique, or passing self-generated tests are observations/proxies, not Q itself. A finite horizon or a strictly decreasing resource budget gives termination; this does not imply semantic correctness or optimal planning.

MDP/Bayesian adaptive MDP connections in LLM agents already exist, e.g. [RAFA](https://openreview.net/forum?id=MGkeWJxQVl). We will not claim novelty for this formalization.

### 1.1 Correction versus regression: a directly testable identity

Let Y_t indicate whether the retained candidate at checkpoint t is correct according to an independent evaluator, and q_t = P(Y_t=1). Define alpha_t = P(Y_{t+1}=1 | Y_t=0), the correction probability, and beta_t = P(Y_{t+1}=0 | Y_t=1), the regression probability (when the conditioning event has positive probability). Stopped runs retain their final candidate at subsequent checkpoints.

By the law of total probability, without requiring a Markov assumption:

    q_{t+1} - q_t = (1-q_t) alpha_t - q_t beta_t.

Thus another repair step improves expected correctness only if its correction gain exceeds its regression loss. This is an elementary identity, not a new theorem or a guarantee of monotonic improvement. It motivates measuring both directions rather than counting successful repairs alone.

Hypothesis: evidence-based routing increases alpha_t, while scoped edits and regression checks reduce beta_t; development-only workflow evolution transfers these changes to unseen tasks. Compare paired branches from the same initial candidates to isolate the components. Natural-language correctness remains difficult to label: use independently audited reference cases and explicitly distinguish true-correctness estimates from objective-match proxies. Labels are evaluator-only and never revealed to the harness. Correlated repeated checkpoints are not independent samples.

## 2. OR-specific check: a solver witness can refute containment

Suppose P = {x : A x <= b} and Q = {x : C x <= d} are nonempty bounded polytopes in the **same aligned variable space**, with bounds included as rows. To check Q subseteq P, solve, for each row i:

    v_i = max_{x in Q} (A_i x - b_i).

Then Q subseteq P iff every v_i <= 0.

Proof: containment implies every P inequality holds for every point in Q, hence each maximum is nonpositive. Conversely, if all maxima are nonpositive, every point in Q satisfies every P inequality, hence belongs to P. A returned feasible point with positive residual is a concrete counterexample. Running the reverse checks establishes equality of feasible sets under these assumptions.

This is standard optimization reasoning, not a newly discovered equivalence algorithm. Finite-precision implementations need explicit tolerances, scaled residuals and solver certificates. A feasible violating witness refutes containment even if the search is incomplete; timeout or failure to find a witness does not certify containment. Empty sets, unboundedness, integer domains, auxiliary variables and variable projections require separate treatment. With MILPs, the domain/integrality mapping must also match and any absence certificate requires globally valid bounds.

At test inference no gold model is available. Such checks can compare a candidate to independently extracted formal clauses, but are sound only **relative to those clauses**. Gold reference formulations belong to an isolated evaluator, never to the inference harness. Equal feasible sets also do not check objective semantics; objective coefficients, direction, units and decision decoding must be audited separately.

### Minimal executable example

Correct model: maximize x subject to 0 <= x,y <= 1 and x+y <= 1.

Incorrect model: maximize x subject only to 0 <= x,y <= 1.

Both objective values equal 1. Yet (1,1) is feasible only in the incorrect model and violates the missing constraint by 1. This demonstrates an insufficiency of objective matching; it is not a benchmark experiment. See `scripts/check_mechanism.py` and `results/mechanism_check.json`.

Model validation and mutation tests have already been studied in [Zadorojniy et al.](https://arxiv.org/abs/2511.16383); certified structural comparison also has restricted-regime results in [ORGEVAL](https://openreview.net/pdf/9a43ee3d4df293304e2a9af6dd62e739c09dedf2.pdf). Our hypothesized contribution is evidence-directed workflow selection, localized correction, regression prevention and development-time evolution that transfers to unseen tasks; verification alone is not the novelty claim.

## 3. Outer-loop selection: a restricted, analyzable bandit

Within epoch e, freeze the backbone/version, verifier, memory and K complete harness variants. A bandit action chooses a complete downstream budgeted policy, **not one arbitrary step in a state-changing repair trajectory**. Let a finite, prespecified context bin b be computed only from agent-visible inputs/common initialization. Every selected policy produces normalized terminal reward U in [0,1].

Assumptions: problem arrivals and randomized model outputs give stationary independent reward draws per (b,k), with mean mu_bk; context binning and policies are fixed during the epoch; there is no shared evolving memory or leaked answer; the cost normalization is fixed. Arbitrarily adaptive task selection, a changing API model, changing rewards and changing policies violate these assumptions.

For UCB1 independently in each context, the standard gap-dependent result gives:

    E[R_e] <= sum_b sum_{k: Delta_bk>0} [8 log(T_b) / Delta_bk]
              + (1 + pi^2/3) sum_b sum_k Delta_bk,

where Delta_bk = max_j mu_bj - mu_bk and T_b is the number of visits to b (with the usual initialization and zero/one-visit conventions).

This follows by applying the ordinary bounded-reward UCB1 theorem separately to each bin and summing. It competes only with the best **fixed candidate per context**, not the globally optimal POMDP policy. It is an adaptation of [Auer, Cesa-Bianchi and Fischer (2002)](https://link.springer.com/article/10.1023/A:1013689704352), not an original regret theorem.

Continuous-feature linear contextual bandits are a possible extension, but require realizability/noise assumptions; see [Abbasi-Yadkori et al. (2011)](https://arxiv.org/abs/1102.2670). We will not attach their rate to an arbitrary neural router.

For evolving epochs, reset/version the estimates and sum valid epoch-wise bounds. This does not automatically provide a favorable dynamic-regret bound: many short epochs can erase the advantage. Standard frozen-test experiments measure generalization, not online regret.

## 4. Relating proxy selection to true quality

For a fixed epoch and context let the true expected normalized utility be mu_k and proxy mean be nu_k. Assume a uniform calibration bound |mu_k - nu_k| <= epsilon for every candidate k.

For any chosen k_t, the corresponding pseudo-regrets satisfy:

    R_true(T) <= R_proxy(T) + 2 epsilon T.

Proof: max_k mu_k <= max_k nu_k + epsilon, while mu_{k_t} >= nu_{k_t} - epsilon. Subtract and sum. Apply the same argument per context/epoch if epsilon varies.

The point is substantive: optimizing an unreliable verifier can incur a linear-in-T quality penalty even when the proxy bandit has sublinear regret. The bound does **not** establish that epsilon is small. Estimate calibration on independent expert/reference-audited cases, with simultaneous uncertainty for a finite candidate set; if this evidence is absent, report only proxy performance. Average calibration alone does not imply the required uniform bound.

This is a proof sketch of an elementary inequality, not a claim of a new general regret rate. A meaningful paper must demonstrate that the proposed evidence/validation design reduces this discrepancy at useful cost.

## 5. A conservative update acceptance rule

Before update k, choose a candidate and incumbent using training/history only. Evaluate their frozen policies on n_k **fresh independent problem families**, not a repeatedly queried holdout. Define paired normalized utility difference D_i = U(candidate,i)-U(incumbent,i) in [-1,1]. Set delta_k = delta/[k(k+1)] and

    r_k = sqrt(2 log(1/delta_k) / n_k).

Accept only if mean(D) > r_k. Hoeffding's inequality implies P(mean(D)-E[D] >= r_k | past) <= delta_k. Consequently, conditional on the assumptions, the probability of ever accepting a non-improving update is at most sum_k delta_k = delta, by a union bound.

An epoch's samples are independent across families; pairing two policies on each instance does not require independence between those two outcomes. The gate must cover the actual candidate system being deployed (including router and frozen memory), not merely an attractive prompt fragment.

If D uses proxy quality with uniform error epsilon for both policies, a true-quality guarantee needs the stronger gate mean(D) > r_k + 2 epsilon. Without such calibration only proxy non-degradation is covered. Reusing a holdout adaptively, selecting a candidate after looking at its gate labels, optional stopping at an unadjusted threshold, or assuming paraphrases are independent invalidates this argument.

This bound can be prohibitively conservative with small data. A failed gate means insufficient evidence, not a harmful candidate. The pilot cannot justify a high-confidence improvement guarantee; sample requirements and gate acceptance rates must be reported. Fresh family-level samples may be scarce, which is a real design constraint rather than something to omit from the theory.

## 6. What would count as a theoretical contribution?

The above creates a mathematically consistent starting point. Publication-level novelty is still conditional: a sharper result tied to localized OR defects, action-specific evidence costs and calibrated verifiers may be needed. We must not simply rename UCB or Hoeffding as a new theorem. If the main contributions are empirical/engineering, state this clearly and use these results as design justification with full assumptions.

## 7. Selective trusted compilation: a compositional guarantee

The static V9 result and the executed VERA-Opt extension use a more direct object than the earlier repair policy. Let `B(x)` be the frozen backend output, `C_t(x)` the output of accepted typed skills at generation `t`, and `A_t(x)` a deterministic decision computed only from the public problem and non-evaluator execution state. Define

    W_t(x) = C_t(x) if A_t(x)=1, and B(x) otherwise.

Every recognizer, parser, dimension check, compiler, solver, and decoder failure must force `A_t(x)=0`. The following propositions describe what this architecture guarantees and what it does not.

### Proposition 1: exact fallback and localized regression risk

Assume the implementation returns the stored backend result byte-for-byte whenever `A_t(x)=0`. Then:

1. `W_t(x)=B(x)` on the abstention region; and
2. for any binary evaluator `Q`,

       P(Q(B)=1, Q(W_t)=0)
       = P(A_t=1, Q(B)=1, Q(C_t)=0)
       <= P(A_t=1, S_t=0) + epsilon_exec,

   where `S_t` is the event that the recognized public instance satisfies the accepted skill's stated semantic contract, and `epsilon_exec` covers violations of the trusted compiler/solver/decoder assumptions.

The equality is immediate because regression is impossible when the wrapper returns `B`. The inequality follows because, on `A_t=1`, `S_t=1`, and correct trusted execution, the skill contract makes `C_t` correct for the canonical specification. This is a risk localization result, not proof that the recognizer understands arbitrary language: evidence is still required that `P(A_t=1,S_t=0)` and `epsilon_exec` are small.

The same partition yields the exact accuracy identity

    P(Q(W_t)=1)-P(Q(B)=1)
      = P(Q(B)=0,Q(W_t)=1)-P(Q(B)=1,Q(W_t)=0).

Thus coverage alone is not a gain guarantee. A useful selective compiler must create more corrections inside its adoption region than regressions.

### Proposition 2: conditional semantic preservation by composition

Suppose an accepted skill has (i) a sound recognizer for a declared family, (ii) a total parser whose output satisfies its typed schema, (iii) a compiler proven or exhaustively checked to implement the family's canonical formulation for every schema-valid parse, and (iv) a correct solver/decoder for the declared objective and decision domain. Whenever the skill adopts, its returned result is semantically equivalent to that canonical formulation.

This is ordinary compositional correctness. Its research value comes from making each assumption an inspectable artifact: the adoption schema, parser, canonical intermediate representation, invariants, metamorphic tests, solver boundary, and provenance are versioned together. Natural-language family membership remains the critical conditional assumption and must be attacked with negative and shifted examples.

### Proposition 3: anytime control for recursively promoted harnesses

At generation `t`, freeze the candidate before opening one fresh binary incumbent/candidate outcome per independently sampled target family. Spend

    alpha_t = alpha / [t(t+1)]

and split it between (a) an exact one-sided paired-gain test and (b) a one-sided exact upper confidence bound on the family-level regression probability. Promote only if both pass and the regression upper bound is at most the precommitted tolerance `rho`.

Under the test assumptions, the probability that any generation ever passes an invalid gain condition or an invalid regression-risk condition is at most

    sum_t alpha_t = alpha.

This follows from test validity conditional on the past and a union bound; it permits adaptively proposed candidates but not reused promotion outcomes, outcome-dependent family selection, or post-hoc regrouping. The implemented primitive is `llm4or/verified_harness_promotion.py`. It deliberately reports that its caller, rather than the function, must enforce freshness and family independence. `llm4or/verified_skill_library.py` separately binds every package to a trusted implementation digest and every promotion to a content-addressed lineage, preventing a rejected or silently edited skill from entering the accepted ancestry.

Together, Propositions 1--3 give a narrow safety case for verified recursive harness evolution: failures outside the certified region preserve the exact backend, accepted skills have inspectable conditional correctness obligations, and repeated promotion does not silently multiply a fixed significance threshold. They do **not** prove that useful skills will be discovered, that public benchmark answers are semantically perfect, or that target distributions remain stationary. Those are empirical questions for grouped held-out tests and independent formulation review.

## 8. Soundness target for the no-execution modeling front end

The compatibility layer interprets a finite whitelist of Python syntax as a modeling DSL. Its relevant semantics are not CPython semantics in general. Let `P` be an accepted function whose imports, data reads, control flow, expressions, and Gurobi/SciPy calls all belong to the documented whitelist; let `D` be finite controller-injected JSON; and let `T(P,D)` be the emitted `milp-v1` model. Define the comparison semantics `G(P,D)` as execution in an idealized Gurobi-style model builder with the same finite numeric operations, loop order, variable domains, bounds, linear expression algebra, constraint senses, and objective direction.

### Proposition 4: model-construction preservation for accepted programs

Subject to the whitelist's numeric assumptions and resource bounds, if translation accepts before the optimizer boundary, then `T(P,D)` and `G(P,D)` have the same named decision variables and domains, the same finite bounds, the same objective direction/offset/coefficient map, and the same ordered multiset of normalized linear constraints.

The proof is by structural induction over accepted statements and expressions. Constants and injected JSON evaluate identically by definition. The linear-expression constructors preserve coefficient maps under addition, subtraction, scalar multiplication, and bounded summation. Finite `for`/comprehension expansion preserves the comparison builder's iteration order. `addVar(s)`, `addConstr(s)`, and `setObjective` append the corresponding normalized objects. Unsupported imports, attributes, nonlinear products, dynamic file access, reflection, private names, unbounded loops, and size-limit violations have no accepted inductive case and therefore fail closed. `optimize()` ends construction and delegates only the validated IR to the trusted solver.

This is presently a proof sketch for the specified abstract semantics, not a machine-checked proof and not equivalence to every behavior of a particular `gurobipy` version. Floating-point evaluation order, duplicate-row normalization, solver tolerances, and post-solve return logic must be stated separately. The 2,121-program official-artifact audit is empirical support for implementation fidelity: 2,067 accepted reference programs were coefficient-level equivalent to the upstream symbolic models, while unsupported quadratic or oversized programs were rejected. The audit does not prove that arbitrary future model output will be accepted or correct.

For a paper-level theorem, the whitelist grammar, small-step construction semantics, normalization relation, and induction must be included in the supplement. A lightweight mechanization would materially strengthen the contribution; absent that, Proposition 4 should be labeled a checked proof sketch rather than formal verification.

## 9. Outcome separation and lineage safety in VERA-Opt

The executed evolution cycle adds two implementation-level properties that are useful but narrower than semantic correctness.

### Proposition 5: outcome-blind proposal noninterference

Let `P_t` be the complete proposal input at generation `t`, containing only public problem text, public structural diagnostics, frozen prior skill packages, and public execution failures. Let hidden evaluation outcomes be `H_t`. If candidate construction is a deterministic function of `P_t` and proposer randomness `R_t`, and neither `P_t` nor `R_t` depends on `H_t`, then the candidate package is conditionally independent of `H_t` given `P_t`:

    Candidate_t = f(P_t, R_t),
    Candidate_t independent of H_t given P_t.

This follows directly from the dataflow. It does not remove public-benchmark pretraining contamination, and it does not prove that a public diagnostic contains no semantic shortcut. It states the audit obligation: proposal calls and structural repair must finish before the controller loads hidden answers, and every consumed input must be hash-bound in the plan.

In the Knapsack execution, the generation-one proposer used all 60 public development questions before their answers were loaded. The generation-two proposer received the one opened public abstention trace and was allowed to add only record prefixes; it could not modify the compiler, normalizer, algebra, solver, endpoint, or evaluator. These phase boundaries are recorded in the plan and result artifacts.

### Proposition 6: rejected-ancestor exclusion

Represent every skill and promotion event by the hash of its canonical serialized content. Let the library accept a child only if its parent hash is already in the accepted set and the event verifies the exact candidate hash, parent hash, plan hash, and gate decision. By induction on event order, no rejected skill can be an ancestor of an accepted skill.

When useful research ancestry includes a rejected candidate, a deployment package may be deterministically squashed into a new root whose content is revalidated and whose metadata separately records the research lineage. This preserves the accepted-ancestry invariant without erasing provenance. It does not convert the rejected generation into a successful promotion.

The first VERA-Opt cycle exercised this rule: generation one failed promotion and remained rejected; generation two was exported as a separately validated deploy candidate rather than being attached to a fictitiously accepted parent. Its final primary confirmation then failed, so the repository records a rejected deployment event as well.

### Empirical instantiation and limit

The theory predicts safe abstention and valid sequential decisions, not guaranteed positive gain. The observed record follows that distinction:

- generation-one hidden promotion produced five corrections and zero regressions but failed the 0.0125 alpha-spend and all-record-adoption conditions;
- generation two produced 110/110 candidate outcomes, but three missing Base cells left 107 pairs and the paired exact probability `0.015625`, so the preregistered primary gate failed;
- an infrastructure-only post-lock sensitivity produced seven corrections, zero regressions, and `p=0.0078125`, but cannot retroactively change the primary decision.

This is evidence that the gate and lineage machinery can reject empirically promising candidates rather than evidence of a universal monotonic-improvement theorem. A future paper should present the safety properties as architecture and statistical guarantees under their assumptions, and the accuracy effect as a separate empirical claim.
