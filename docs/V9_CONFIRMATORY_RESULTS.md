# V9 confirmatory results: trusted compilation improves Text2Opt benchmark formulation accuracy

Updated 2026-10-03. This is the paper-facing record of the preregistered V9 confirmation. It separates development evidence, independent confirmation, and claim boundaries.

## Core argument

For optimization problems with a stable public quantitative interface, a selective trusted compiler can replace free-form coefficient generation with shape-checked parsing, deterministic family templates, and exact solution. On an outcome-hidden, grouped Text2Opt confirmation cohort, this design improved final benchmark formulation accuracy over the same language-model Base while failing closed to Base outside its supported path.

## Method and preregistration

V9 recognizes six structured families from public table headings and prose signatures: disaster response, job-shop scheduling (JSSP), modified facility location, resource-constrained project scheduling (RCPSP), transportation, and vehicle routing with time windows (VRPTW). Recognition never uses the problem identifier or reference result. The parser validates index sets and table shapes; the compiler instantiates fixed formulations; bounded exact solvers produce a candidate; and adoption occurs only after an optimal solve. Any recognition, parsing, compilation, or solve failure returns the unchanged Base result. Resource-allocation prose is unsupported and also returns Base.

The grouped split was frozen before confirmation and excludes rewritten variants across roles. The 401-record confirmation cohort contained 153 structured-template records and 248 resource-allocation records across seven categories. Base used one `gpt-6-luna` high-reasoning request per record. V9 used the identical Base result plus the frozen trusted compiler. Published outcomes were loaded only after all inference checkpoints existed. The endpoint was optimal solver status and objective agreement with the published result at relative tolerance `1e-5` and absolute tolerance `1e-6`.

The final continuation plan hash was `20f166269ad881b607607cc6d13db878ec80f5c30acbf50bc39da46613f3a81c`. The preregistered claim gate jointly required at least 99% paired completion, a gain of at least five percentage points, at least ten corrections, corrections at least four times `max(1, regressions)`, a one-sided exact McNemar `p <= 0.05`, improvement in at least four categories, and decline in at most one category.

## Development evidence

Before confirmation, the fixed compiler matched the published objective on 30/30 structured development records, five per supported family. On the ten-record V8 Stage-1 development cohort, the frozen V9 adoption rule changed Base from 5/10 to 10/10, with five corrections and no regressions. These results motivated confirmation but are excluded from the confirmatory estimate.

## Independent confirmation

One Base request was infrastructure-unavailable, leaving 400 paired records and a paired completion rate of 99.75%. Base was correct on 200/400 paired records (50.00%); V9 was correct on 259/400 (64.75%). The absolute paired gain was **14.75 percentage points**, with 59 corrections and 0 regressions. The one-sided exact McNemar probability was `1.7347e-18`, and the conditional exact 95% interval for the paired gain was `[12.96, 14.75]` percentage points. All seven preregistered gate conditions passed.

Across the full selected denominator, including the Base infrastructure failure as incorrect, Base was correct on 200/401 (49.88%, Wilson 95% CI 45.01–54.75%) and V9 on 260/401 (64.84%, Wilson 95% CI 60.04–69.35%). The compiler was adopted on 90/401 records (22.44%); the other 311 records preserved Base. Thus, the gain was not produced by removing unsupported or failed records from the denominator.

| Category | Paired n | Base accuracy | V9 accuracy | Gain | Corrections / regressions | One-sided exact p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Disaster response | 21 | 9.52% | 90.48% | +80.95 pp | 17 / 0 | `7.63e-6` |
| JSSP | 30 | 30.00% | 100.00% | +70.00 pp | 21 / 0 | `4.77e-7` |
| Modified facility location | 24 | 12.50% | 20.83% | +8.33 pp | 2 / 0 | 0.25 |
| RCPSP | 32 | 12.50% | 43.75% | +31.25 pp | 10 / 0 | `9.77e-4` |
| Resource allocation | 248 | 66.13% | 66.13% | 0.00 pp | 0 / 0 | 1.0 |
| Transportation | 25 | 64.00% | 88.00% | +24.00 pp | 6 / 0 | 0.0156 |
| VRPTW | 20 | 10.00% | 25.00% | +15.00 pp | 3 / 0 | 0.125 |

Six categories improved and one tied; none declined. The category-macro gain was 32.79 percentage points. Category-level `p` values are descriptive sensitivity analyses and are not separate primary claims.

## Reliability and cost accounting

The confirmation used 401 physical model attempts and 17,917,504 reserved-or-reported tokens across the original run and the final continuation, with zero retries. The original run made 397 attempts and halted after a token-reservation overrun; 345 valid response checkpoints and all accounting were preserved. An intermediate continuation made zero physical requests because its per-scope reservation was too small. The final frozen continuation imported the valid checkpoints, made four new attempts (122,788 tokens), and completed with 400 records plus one infrastructure-unavailable record. These events changed neither the cohort, method, endpoint, model, prompt, nor statistical gate.

Local trusted compilation adds deterministic parsing and solver cost but no additional language-model request per record. The public report contains aggregate outcomes only; request/response contents, reference-only answers, and credentials remain private.

## Interpretation and ablation logic

The result supports a preregistered Text2Opt benchmark formulation-accuracy improvement over Base. It also clarifies the mechanism trajectory. Same-backbone repair (v4) could share the original algebraic error; narrow semantic contracts (v6) were safe but had little coverage; dual-view provenance (v7) was mechanically brittle; and source-indexed generation (v8) verified the provenance of included numbers without proving that all required relations were present. V9 improves reliability by making supported formulations complete by construction and using the language model only through an unchanged fallback outside that scope.

The central ablation comparison is therefore conceptual and empirical: V8 provenance validation produced 0 corrections and 1 regression on its frozen development stage, whereas V9's fixed compiler produced 5 corrections and 0 regressions on the same ten development records and then 59 corrections and 0 regressions on the independent confirmation cohort. A future paper should additionally report controlled removals of shape validation, exact solution, and fail-closed adoption if those variants can be evaluated without reusing the confirmation set for tuning.

## Claim boundary

The defensible main claim is:

> On the preregistered 401-record Text2Opt confirmation cohort, selective trusted compilation increased paired benchmark formulation accuracy from 50.00% to 64.75% (+14.75 percentage points; 59 corrections, 0 regressions; one-sided exact McNemar `p=1.73e-18`) relative to the same `gpt-6-luna` Base.

This claim does not establish universal semantic equivalence. The endpoint checks final status and objective, so distinct feasible regions may still receive the same score. The supported structured families expose stable interfaces and may not represent unconstrained natural-language optimization problems. Public benchmark material may have appeared in model pretraining. The six structured categories contain related instances rather than certified IID semantic families, and the method uses handwritten family knowledge. The resource-allocation category shows no gain because V9 deliberately falls back to Base there. These limitations bound generalization but do not invalidate the preregistered within-cohort paired comparison.

## Main-text allocation

- **Main Results:** paired accuracy, 59/0 discordances, exact `p`, paired completion, and six-positive/zero-negative category direction.
- **Main Method:** text-only recognition, shape-checked parsing, deterministic templates, exact solution, and fail-closed fallback.
- **Main Discussion:** completeness-by-construction versus provenance-only generation, plus the supported-family boundary.
- **Supplementary Information:** all category intervals, run-continuation accounting, frozen hashes, compiler algorithms, and full gate checklist.
- **Do not claim:** universal formulation equivalence, a general solution for arbitrary optimization prose, contamination-free generalization, or top-conference acceptance.

Machine-readable aggregate: `results/text2opt_v9_confirmation_evaluation.json`. Method record: `docs/V9_TRUSTED_COMPILER.md`.
