# NLEquiv-150 routed-skill result

Status: **complete; directional improvement observed, prespecified gate not
passed; experiment closed**.

## Execution

The clean rate-shaped run completed all 450 planned predictions over 150
nonlinear-equivalence pairs and three frozen arms. It used 452 physical
attempts, including two recovered transient connection retries, with zero
method failure, zero infrastructure-unavailable prediction, no global halt,
and zero new send on restart. A persistent process-safe limiter admitted at
most 40 logical starts in any rolling 60-second window while preserving API
concurrency five.

The source is independent of the earlier TSP, OR-Debug, Text2Opt and
FormulationBench lineages. Inference remained label blind until every response
checkpoint existed. The result is a nonlinear-equivalence classification
endpoint, not direct solver-code formulation accuracy.

## Primary result

| Arm | Correct | Accuracy |
|---|---:|---:|
| Flat-K short | 124/150 | 82.67% |
| Structured-K short | 124/150 | 82.67% |
| Routed-skill short | 128/150 | 85.33% |

Against Flat-K, the routed-skill arm gained 4 correct pairs, or 2.67
percentage points. The paired table contained 13 corrections, 9 regressions,
115 pairs correct under both arms, and 13 incorrect under both. The
prespecified one-sided exact McNemar probability was 0.2617. The primary gate
required both a positive accuracy difference and `p <= 0.05`, so it failed.

The result therefore supports a directional observation only. It does not
confirm a statistically reliable accuracy improvement and must not be written
as benchmark superiority.

## Diagnostic result

Merely reorganizing the same facts into structured obligations was neutral
overall: Structured-K and Flat-K both scored 124/150, with 13 corrections and
13 regressions (`p = 0.5775`). This rules out a simple claim that structure by
itself improved the endpoint under this frozen protocol.

The opened-label subgroup diagnostic localizes the routed skill's limitation:

| Label subgroup | Flat-K | Structured-K | Routed skill |
|---|---:|---:|---:|
| Equivalent | 86/100 | 97/100 | 96/100 |
| Non-equivalent | 38/50 | 27/50 | 32/50 |

The skill strongly favored proof of equivalence but did not provide enough
necessary-condition and counterexample-search guidance for non-equivalent
pairs. This diagnostic was computed after opening evaluator labels and is now
development evidence. Any revised failure-witness skill must be tested on a
new independently frozen endpoint before a confirmatory claim.

## Claim boundary

Supported claims are limited to complete execution, an independent source
lineage, exact full-denominator accuracies, and the observed positive but
non-significant routed-skill delta. Unsupported claims include confirmed
accuracy improvement, automatic skill acquisition, direct optimization-model
generation accuracy, universal skill benefit, or superiority over external
methods.

The unpaced predecessor remains closed without evaluation because it hit the
provider's request-rate window. It is not pooled with this run. The current
experiment is terminal and no controller or transport worker remains active.

Machine-readable evidence:

- `experiments/nlequiv_skill_paced_execution_20261017.json`
- `experiments/nlequiv_skill_paced_result_20261017.json`
- `experiments/nlequiv_skill_paced_terminal_audit_20261017.json`
- `experiments/infrastructure_root_cause_closure_20261017.json`

These artifacts contain no request body, response body, credential, per-pair
prediction, or evaluator label.
