# G09 finite component census

Status: **complete for the two frozen finite populations; broader component causality remains bounded**.

## Admission census

All 64 members of the frozen typed-count grammar were enumerated, and the semantic and resource gates were measured independently rather than short-circuited. The census contains all four semantic/resource cells: 47 fail both gates, 11 fail only semantics, 5 fail only resources, and 1 passes both. Full admission accepts 1/64 with 0 unsafe admissions. Removing the semantic gate accepts 12/64 and creates 11 unsafe admissions; removing the resource gate accepts 6/64 and creates 5 unsafe admissions. The full policy prevents all sixteen unsafe admissions without rejecting the one safe candidate.

| Arm | Admitted | Unsafe admissions | Correct admission decisions |
|---|---:|---:|---:|
| Full | 1 | 0 | 64/64 |
| No semantic gate | 12 | 11 | 53/64 |
| No resource gate | 6 | 5 | 59/64 |

## Routing census

The frozen envelope grammar contains 69 unique key patterns: 43 zero-match, 24 unique-match and 2 multiple-match cases, including missing-key, renamed-key, additive, partial cross-family, unrelated and new-family shifts. Exactly-one routing is correct on all 69. Forced-first routing is correct on 24/69; exactly-one fallback corrects 45 cases with 0 regressions. A policy that falls back only on zero matches but forces ambiguous multiple matches reaches 67/69.

| Policy | Correct |
|---|---:|
| Exactly one, otherwise fallback | 69/69 |
| Forced first match/default | 24/69 |
| Fallback on zero, force multiple | 67/69 |

## Complexity and inference boundary

No empirical complexity-control effect is reported because there are no independent common-pool library-selection episodes. Prefix-code/MDL control remains a theoretical and prospective protocol component. These are complete deterministic censuses, so sampling p-values and Holm correction are inapplicable to the frozen populations. The results do not generalize automatically to a proposer distribution or unrestricted schema shift. No API, solver, native evaluator, credential, request body, response body, or reference answer was used.
