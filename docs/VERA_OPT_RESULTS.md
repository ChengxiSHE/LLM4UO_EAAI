# VERA-Opt: verified harness-evolution results

Updated 2026-10-04. This document is the authoritative record for the first executed VERA-Opt evolution cycle. It separates development, hidden promotion, preregistered confirmation, and post-lock infrastructure recovery. The last category is a sensitivity analysis and must not be relabeled as the primary result.

## What the method is

VERA-Opt stands for **Verified Evolution of Reliable Artifacts for Optimization**. It treats the inference harness, rather than the foundation-model weights, as the object of improvement. A fixed proposer may emit only an inert, typed skill package. An immutable controller then:

1. validates its finite recognizer and typed extraction contract;
2. binds it by hash to a trusted compiler and solver;
3. runs public-only structural repair without answer access;
4. checks solver and metamorphic invariants;
5. evaluates the candidate on a grouped hidden promotion set under alpha spending;
6. adopts it only through an immutable, content-addressed lineage; and
7. returns the unchanged backend result whenever recognition, parsing, verification, or solving fails.

The implemented proposal language cannot emit or execute Python, change the optimizer, alter the evaluation endpoint, or read hidden answers. The first learned family is canonical OPT-Engine Knapsack. Its typed artifact extracts a capacity and item records, normalizes currency units, compiles a binary selection model, and delegates optimization to the trusted solver.

This is a bounded form of recursive harness improvement. It is not unrestricted recursive self-improvement: model weights, verifier, compiler implementation, solver, budgets, and promotion rules remain outside the editable loop.

## Data boundary

The pinned canonical Knapsack cohort contains 260 records and is split by item count:

| Role | Sizes | Records | Answer access |
| --- | ---: | ---: | --- |
| public development | 5--10 | 60 | opened only after all proposal calls completed |
| hidden promotion | 11--19 | 90 | opened after generation-one freeze |
| final confirmation | 20--30 | 110 | opened after generation-two freeze |

The split tests size extrapolation rather than lexical paraphrase transfer. The 1,550 canonical records from the other nine OPT-Engine families form a negative-recognition challenge; their answers are not needed for that check. The upstream artifact has no license file at the pinned revision, so raw data are not redistributed.

## Generation one: automatic induction

Several failed proposal revisions are preserved rather than erased. Earlier candidates exposed schema, numeric-identifier, unit-normalization, and recognizer-specificity failures. The final frozen proposal plan has SHA-256 `5878f434ef7bebab3a7ebace023732a4e0b34b9dc0da0a96f9299f119f222489`.

Under that plan, three `gpt-6-luna` high-reasoning proposal requests used 83,695 reserved-or-reported tokens. Two candidates passed static validation; both achieved 60/60 exact development outcomes, 60/60 adoption, and 20/20 metamorphic checks. The selected skill hash is `56709a3979729d84db27b6177d5436e03cbcca3abf8ef7555732beedc5123580`.

The hidden promotion plan hash is `6ccebbff037d222163c3da7b8c9a4c562c822de3c6b0068098a7d54caca0dd60`. Base achieved 85/90 (94.44%) and VERA achieved 90/90 (100%), a gain of 5.56 percentage points with five corrections and no regressions. The one-sided exact paired probability was 0.03125, and the candidate abstained once. The strict gate therefore failed both all-record adoption and the prespecified alpha-spend threshold of 0.0125. Generation one was rejected and was not inserted into the accepted lineage.

This is positive mechanism evidence but not a successful promotion.

## Generation two: failure-driven revision

The only generation-one abstention was a public structural trace: the recognizer accepted an item label that the record-prefix grammar did not. A second frozen proposer was allowed to add only record prefixes grounded in that trace. It could not change code, regex behavior, algebra, unit normalization, solver, endpoint, or answers.

The update plan hash is `39fea8c1d9dee8ed0563dc092441a5c6ac4135305c67300a841a1984b95a9b32`. One `gpt-6-luna` request used 15,595 tokens and produced child skill hash `9594a4e7c5d210e11cfda7c549effc3efde3853c8687f168ebd1fef2fd029157`. It achieved 150/150 exact and adopted outcomes over public development plus the now-open promotion cohort, with zero false adoptions on all 1,550 negative-family records.

Because generation one had failed promotion, deployment ancestry was deterministically squashed rather than pretending that a rejected parent had been accepted. The deployable candidate hash is `3a357964ff3a70a87c06f1c3c353d8bfef240c0645658dfe22317c5fd8832231`; its research metadata still records both proposal generations.

## Preregistered final confirmation

The final confirmation plan hash is `69e10ed1ca12c0ac18f21f0ec1d4900c90b003d903caa91a750206712209cf04`. It froze the 110 size-20--30 records, same Base model and prompt, skill hash, compiler, endpoint, retry policy, 0.0125 alpha spend, and joint success rule before outcomes were opened.

The run used 110 logical requests, 145 physical attempts, 35 retries, and 8,567,069 reserved-or-reported tokens. Three Base requests exhausted the retry policy because of CLI runtime failures; VERA itself produced an adopted exact result for all 110 records.

| View | Base | VERA | Difference | Corrections / regressions | One-sided exact p |
| --- | ---: | ---: | ---: | ---: | ---: |
| all 110 selected records | 101/110 (91.82%) | 110/110 (100%) | +8.18 pp | not a complete paired test | not applicable |
| 107 infrastructure-complete pairs | 101/107 (94.39%) | 107/107 (100%) | +5.61 pp | 6 / 0 | 0.015625 |

Six of eleven size groups improved, five tied, and none declined. Nevertheless, the **preregistered joint confirmation gate failed**: paired completion was 107/110 rather than 110/110, and `p=0.015625` exceeded the allocated 0.0125 threshold. The frozen evaluator also conservatively marks candidate exactness false when three paired rows are absent, although the method summary records 110/110 candidate exact/adopted outcomes. That implementation detail is preserved; it does not change the failed decision because the completion and p-value conditions already fail.

The repository therefore records a rejected lineage event. It must not be rewritten as an accepted primary confirmation.

## Post-lock infrastructure-only sensitivity

After the primary report was locked, a separate plan selected exactly the three records whose Base status was `infrastructure_unavailable`; it did not select by correctness. The model, prompt, candidate, endpoint, and retry ceiling were unchanged. The recovery plan hash is `c69ed379708c265eb2fba5a544af24ea3ad79db44d3c2e3126a97c5b9cce74ae`.

The recovery used three logical requests, six physical attempts, three retries, and 709,572 tokens. Combining those infrastructure reruns with the locked primary data gives Base 103/110 (93.64%) and VERA 110/110 (100%), a 6.36-point gain with seven corrections, zero regressions, `p=0.0078125`, six positive size groups, and a 3.91% one-sided upper bound on the regression probability. Every frozen sensitivity check passes.

This analysis shows that the failed primary decision is sensitive to transport incompleteness. It remains post-lock evidence and is not the preregistered primary result.

## What is established

- A model automatically proposed a non-executable typed optimization skill that passed development, solver, and metamorphic checks.
- A failure trace supported a second, narrowly scoped skill revision without hidden-answer access.
- The immutable runtime preserved exact fallback, rejected an unsuccessful promotion, and maintained hash-linked provenance.
- On the final all-selected cohort, the evolved skill attained 110/110 while Base attained 101/110; on completed primary pairs it produced six corrections and no regressions.
- A prespecified-statistic sensitivity analysis completed the missing infrastructure cells and passed its frozen checks.

## What is not established

- The preregistered generation-two primary confirmation did not pass its joint gate.
- The current evidence does not establish arbitrary-prose generalization, full feasible-region equivalence, or universal non-regression.
- It does not establish superiority over CoE, BIND, or OptiTrust. Those claims require locally rerun official artifacts under one common protocol.
- One induced family on one backbone is not enough to claim broad recursive self-improvement.
- Zero observed regressions is empirical evidence under a finite cohort, not a proof that accuracy can never decrease.

## Paper contribution and remaining bar

The strongest defensible paper story combines two evidence levels:

1. **Selective trusted compilation:** V9 already has a passed independent Text2Opt confirmation, with a 14.75-point gain and 59/0 paired corrections/regressions.
2. **Verified harness evolution:** VERA-Opt operationalizes bounded RSI through typed artifacts, immutable verification, sequential hidden promotion, exact fallback, and content-addressed rollback. The executed cycle demonstrates real automatic induction and revision, while its failed primary gate supplies an honest limit.

This combination is more than a prompt-engineering contribution: the editable object, accepted language, safety boundary, statistical adoption rule, and lineage semantics are all explicit. It is not yet a complete top-conference evidence package. A strong final submission still needs at least one fresh independent family or organization-held-out cohort on which automatic induction passes the primary gate, plus common-protocol official-code reruns for available external systems and a backend-transfer ablation.

## Reproducibility map

- Development: `results/vera_opt_generation1_development.json`
- Generation-one promotion: `results/vera_opt_generation1_promotion.json`
- Generation-two update: `results/vera_opt_generation2_development.json`
- Primary confirmation: `results/vera_opt_generation2_confirmation.json`
- Infrastructure sensitivity: `results/vera_opt_generation2_confirmation_recovery.json`
- Rejected lineage event: `experiments/vera_opt_accepted_skill_lineage.json`
- Proposal and runtime implementation: `llm4or/vera_opt_proposal.py`, `llm4or/vera_opt_repair.py`, `llm4or/vera_opt_evolution.py`, and `llm4or/verified_skill_library.py`
- Trusted typed compiler: `llm4or/declarative_selection_compiler.py`
