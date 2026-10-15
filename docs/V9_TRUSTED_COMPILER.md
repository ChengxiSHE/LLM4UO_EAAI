# V9 trusted public-text compiler

Updated 2026-10-03. This document records the method and evidence boundary fixed before the independent V9 confirmation.

## Motivation

V7 and V8 showed that attaching source locations to model-generated coefficients improves provenance but does not guarantee formulation completeness. V8 accepted candidates on five of ten Stage-1 problems, corrected none, and regressed one. The regression omitted a quantified public relation while citing every coefficient that remained. Provenance therefore addresses where a number came from; it does not establish that every required relation was represented.

V9 changes the unit of generation for six structured Text2Opt families. A language model no longer writes their optimization program. A trusted controller recognizes a unique public-text signature, parses the annex, instantiates an audited family template, and invokes a bounded exact solver. If recognition, parsing, compilation, or optimal solution fails, the method returns the unchanged Base result. Resource-allocation prose remains outside this compiler and also falls back to Base.

## Fixed pipeline

1. **Text-only family recognition.** The router uses combinations of semantic table headings such as `Customer Time Windows`, `Execution Mode Durations`, and `Risk Costs (Depot x Unit)`. It does not use a benchmark answer or route on the benchmark problem ID.
2. **Shape-checked parsing.** Every expected index set and table dimension is checked. Missing, duplicated, non-contiguous, or ambiguous structures fail closed.
3. **Deterministic compilation.** Transportation, modified facility location, disaster response, VRPTW, RCPSP, and JSSP use fixed formulations derived only from the public statement.
4. **Exact solution.** LP/MILP models run in the credential-free numerical worker. VRPTW uses feasible-route enumeration plus set partitioning; JSSP uses Giffler--Thompson active-schedule branch and bound; RCPSP uses complete mode enumeration plus disjunctive-graph branch and bound. Disaster-response days are independent and solved separately to avoid a weak Cartesian-product MILP.
5. **Fail-closed adoption.** V9 adopts only a recognized, successfully parsed, optimal trusted result. All other records preserve Base exactly. No confidence score, self-judgment, or reference objective controls adoption.

## Development evidence

The grouped split was frozen before use. It contains 70 development records and 401 confirmation records. The 30 structured development records comprise five examples from each supported family. The compiler matched the published optimal objective on all 30/30 records under the upstream executable evaluator tolerance. On the ten-record V8 Stage-1 cohort, replaying the fixed V9 adoption rule changes Base from 5/10 to 10/10: five corrections and zero regressions. These are development results and cannot establish a confirmatory improvement.

The implementation was covered by 343 passing tests at the initial freeze. The original independent plan was `experiments/text2opt_v9_confirmation_plan.json`, hash `a07845b47f55c44969932d47046c4e548f4a21820b2dbf02f31466eacaa370ca`. A token-reservation halt required a checkpoint-preserving continuation; the final continuation plan hash was `20f166269ad881b607607cc6d13db878ec80f5c30acbf50bc39da46613f3a81c`. It changed no method, prompt, input, endpoint, model, or statistical rule.

## Independent endpoint and gate

The independent cohort contains 401 records: 153 previously unopened structured template records and 248 resource-allocation records. Base uses the frozen `gpt-6-luna` high-reasoning configuration once per record. V9 uses the trusted compiler where applicable and the identical Base result elsewhere. The primary endpoint is benchmark formulation accuracy: optimal solver status and objective agreement with the published outcome at relative tolerance `1e-5` and absolute tolerance `1e-6`.

The preregistered claim gate requires all of the following:

- at least 99% paired infrastructure completion;
- at least a five-percentage-point accuracy increase;
- at least ten corrections;
- corrections at least four times `max(1, regressions)`;
- one-sided exact paired p-value at most 0.05;
- positive change in at least four categories and negative change in at most one.

Published outcomes are loaded only after all inference checkpoints exist. A passing gate supports a benchmark formulation-accuracy improvement over Base. It does not prove universal semantic equivalence, eliminate public benchmark contamination, or show that handwritten family templates generalize to unstructured optimization prose.

## Independent result

The confirmation completed with 400 paired records and one Base infrastructure-unavailable record, for 99.75% paired completion. Base was correct on 200/400 paired records (50.00%) and V9 on 259/400 (64.75%), an absolute gain of 14.75 percentage points. There were 59 corrections and 0 regressions; the one-sided exact McNemar probability was `1.7347e-18`, and the conditional exact 95% interval for the paired gain was 12.96–14.75 percentage points. Six of seven categories improved, one tied, and none declined. Every preregistered gate condition passed.

On the all-selected denominator, Base scored 200/401 (49.88%) and V9 260/401 (64.84%). The trusted compiler was adopted on 90/401 records; 311 records retained Base. Across the original run and final continuation, the experiment used 401 physical attempts and 17,917,504 reserved-or-reported tokens, with no retries. Full aggregate reporting and claim wording are in `docs/V9_CONFIRMATORY_RESULTS.md`; the machine-readable aggregate is `results/text2opt_v9_confirmation_evaluation.json`.

## Scientific interpretation

V9 tests a narrower and more defensible claim than the earlier self-repair story: when a problem exposes a stable quantitative interface, moving arithmetic and combinatorial structure from free-form generation into a trusted compiler can improve final formulation accuracy. The language model remains necessary for the Base comparison and for unsupported prose, but the supported path replaces unverifiable coefficient generation with auditable parsing and exact algorithms.

For a paper, this should be presented as a selective neuro-symbolic system with coverage and fallback, not as a universal LLM self-correction method. The principal ablations are Base, source-indexed generation (V8), V9 without exact family-specific algorithms, and full V9. The confirmed main claim is the preregistered Text2Opt benchmark formulation-accuracy gain; full semantic equivalence remains outside the endpoint. Report compiler coverage, parse failures, solver limits, corrections, regressions, per-family effects, paired exact inference, and total API and local-solver cost.
