# Development pilot history

Updated 2026-09-12. This document consolidates the S0 implementation report, pilot-data review, preflight notes, S1 report, post-S1 preparation, and S2 ceiling probe. Authorization JSON files and non-secret machine summaries remain unchanged.

## S0: offline prototype

The first stage implemented a strict continuous-LP schema, controlled HiGHS execution, bidirectional model differences, fixed-response teacher/repair behavior, independent evaluation, persistent request limits, and restart checks. It used no model API. Ten NL4Opt development problems were selected through a label-separated manifest; their references were cross-checked numerically but were not presented as expert gold.

This stage did not implement complete workflow evolution or a formal benchmark evaluation. Its purpose was execution and safety validation.

## S1: ten-problem live pilot

The user authorized at most 60 AntChat requests, no more than six per problem, and at most 2,048 output tokens per request. The authorization is closed.

| Item | Result |
| --- | ---: |
| Actual requests | 46 |
| Provider-reported tokens | 46,001 |
| Initial / ordinary repair / semantic final reference matches | 10/10 for each branch |
| Valid teacher models | 9/10 |
| Observed quality improvement | 0 |

The first response schema was valid for 4/10 problems. Seven explicit format retries were recorded; one teacher response remained invalid. At least two teacher explanations misstated their own model: one invented a missing upper bound, and one confused an objective coefficient with a constraint coefficient. No semantic repair was triggered. These failures led to the structured `teacher-v2` claim protocol and executable fact checks.

Unused S1 allowance did not transfer to later work. Detailed request/response records remain in the ignored private archive; `results/pilot_s1_summary.json` is the non-secret summary.

## Post-S1 offline work

The output contract was tightened, teacher interpretations were separated from checkable claims, and bound/row/implication assertions were replayed through the controlled solver. The two observed false teacher claims were manually converted into the new structure and correctly rejected; this was a retrospective interface check, not a new live-model result.

Four table/ratio-heavy OptiBench development candidates were prepared, while eight problems requiring unsupported discrete logic, containing ambiguity, or yielding problematic domains were excluded from that small probe. A broader family-overlap audit was begun so development variants could not later appear as independent tests.

## S2: four-problem ceiling probe

A separate authorization allowed at most 20 AntChat requests on four fixed continuous-LP development problems. It is closed.

| Item | Result |
| --- | ---: |
| Actual requests | 15 |
| Provider-reported tokens | 32,852 |
| Base / ordinary repair / semantic final reference matches | 4/4 for each branch |
| Semantic-branch tokens | 24,478 |
| Base tokens | 6,994 |
| Observed quality improvement | 0 |

The semantic branch used about 3.5 times the Base tokens without improving the available proxy. Three response bodies contained only an opening brace, and one teacher record treated an objective term as a constraint row. All failures were retained; there were no hidden retries.

## Interpretation

S1 and S2 established that the real interface and controlled execution path could run, and exposed format and teacher-grounding problems. They did not show a quality benefit because the initial models already matched the limited references. Fourteen development problems cannot establish that optimization-modeling benchmarks are saturated, that the backbone is universally strong, or that the proposed framework works or fails.

The formal experiment therefore moved to six broader benchmarks, integer/mixed-integer support, stronger information isolation, bounded workflow evolution, explicit compute controls, and separate proxy/independent evaluation. Neither closed pilot authorization can start or subsidize that experiment.
