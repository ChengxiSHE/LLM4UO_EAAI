# VERA-Opt BinPacking independent-family results

Updated 2026-10-04. This document records the second automatically induced VERA-Opt family. Published comparator scores are not used.

## Frozen data boundary

The pinned OPT-Engine canonical BinPacking cohort uses indices 0--9 only: 60 public development records at sizes 10--15, 100 hidden promotion records at sizes 16--25, and 150 untouched confirmation records at sizes 26--40. Indices 10--19 remain an unused reserve. Candidate proposal and repair finished before development answers were opened; promotion and confirmation answers were opened only after their respective inference matrices completed.

## Automatic induction and promotion

Three proposer requests produced two recoverable typed packages. A public-only recognizer repair yielded two candidates with 60/60 exact development outcomes, 60/60 adoption, and 20/20 metamorphic checks. The selected skill hash is `1793de50c1b4408ed979329572e842de3bc0b376d5afff38365685e08c813954`.

The 100-record hidden promotion passed every frozen gate. Base scored 21/100 (21.00%) and VERA scored 100/100 (100.00%): +79.00 percentage points, 79 corrections, zero regressions, exact one-sided paired `p=1.6544e-24`, ten positive size groups, and a 4.95% one-sided upper bound on the regression probability. The accepted event is content-addressed in `experiments/vera_opt_binpacking_promotion_event.json`.

## Untouched confirmation

The confirmation plan was frozen before outcomes under hash `372ebd9c088fce7e9703701166417a29b0a725121405b8905b9f4489ac2ce0c0`; checkpoint-preserving continuations ended at hash `229183818e8c91eaeb5ed654afa77d5a634a9f9c1d08175020cdf18a1b86b1b3`. All 150 paired records completed. Base scored 2/150 (1.33%) and VERA scored 139/150 (92.67%), a +91.33-point gain with 137 corrections, zero regressions, exact one-sided paired `p=5.7397e-42`, all 15 size groups positive, none negative, and a 3.77% one-sided regression upper bound.

The strict joint gate nevertheless failed because the candidate abstained on 11 records, so it did not satisfy the precommitted 150/150 adoption and exactness conditions. Ten abstentions were trusted-compiler failures and one was a recognizer miss. This result supports a large benchmark formulation-accuracy improvement on the frozen cohort. It does not support full coverage, arbitrary-prose semantic equivalence, or a universal monotonicity guarantee.

The runner completed inference and evaluation but initially raised a post-evaluation `KeyError` by reading `confirmation_gate.promoted` instead of `confirmation_gate.confirmed`. A zero-call finalizer verified all 150 checkpoints and the plan-bound public report, then closed the failed gate state. No sample was rerun and no statistic changed.

## Next generation

The opened public structural traces identify three bounded revision targets: broaden one family recognizer literal, treat repeated display labels as distinct row-indexed items, and replace the custom exact branch-and-bound limit with the existing trusted MILP solver interface. Any revision must be frozen before evaluation and tested only on the unused reserve cohort; the exposed 150-record confirmation cannot be reused as confirmatory evidence.

