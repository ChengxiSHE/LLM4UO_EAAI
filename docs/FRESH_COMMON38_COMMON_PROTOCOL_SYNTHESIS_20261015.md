# Fresh common-38 common-protocol synthesis

Status: **complete, fixed-endpoint evidence; not broad benchmark superiority**.

## Method-native full-denominator results

| Method | Correct / 38 | Accuracy | RCPSP | VRPTW | Max external calls / item |
|---|---:|---:|---:|---:|---:|
| Proof-carrying compilation | 30/38 | 78.95% | 12/13 | 18/25 | 0 |
| Base | 0/38 | 0.00% | 0/13 | 0/25 | 1 |
| BIND round 1 | 13/38 | 34.21% | 13/13 | 0/25 | 1 |
| BIND final | 13/38 | 34.21% | 13/13 | 0/25 | 3 |
| CoE-safe | 4/38 | 10.53% | 2/13 | 2/25 | 11 |

## Paired contrasts against proof-carrying compilation

| Comparison | Corrections | Regressions | Delta | Exact one-sided p | Holm p |
|---|---:|---:|---:|---:|---:|
| current_vs_base | 30 | 0 | 78.95 pp | 9.31323e-10 | 3.72529e-09 |
| current_vs_bind_round_one | 18 | 1 | 44.74 pp | 3.8147e-05 | 7.62939e-05 |
| current_vs_bind_final | 18 | 1 | 44.74 pp | 3.8147e-05 | 7.62939e-05 |
| current_vs_coe_safe | 26 | 0 | 68.42 pp | 1.49012e-08 | 4.47035e-08 |

All tests retain the 38-instance denominator. Holm correction covers the four prespecified current-method contrasts.

## Budget sensitivity

Under the answer-blind ceiling of at most one external model call per item, the valid terminal methods are proof-carrying compilation (30/38), BIND round 1 (13/38), and Base (0/38). CoE-safe has no official one-call terminal artifact, while BIND final can use answer-bearing repair and more than one call. This view equalizes the inference-call ceiling, not library construction cost or provider tokens.

## Claim boundary

The result supports a large, statistically clear advantage on this fixed fresh RCPSP/VRPTW endpoint. It does not establish broad benchmark superiority, automatic knowledge acquisition, or component causality. The current library was authored; G08 acquisition and G09 component experiments remain prospective. CoE is a safe-adapter reproduction from the current official repository snapshot, whose license and complete release package remain unverified.
