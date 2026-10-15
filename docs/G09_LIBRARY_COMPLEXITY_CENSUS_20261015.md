# G09 library-complexity census

Status: **complete for the frozen finite library-selection population**.

## Design

The common pool contains all 64 libraries induced by six optional shadow guards on top of the already verified exactly-one-or-fallback router. Each optional branch overrides one public zero- or multiple-match envelope and is therefore an overfitting branch: it can fit any calibration subset that omits its witness but fails that witness in the full 69-envelope endpoint. The complete episode population contains all 64 calibration subsets. Both arms see the same admitted candidate pool in every episode. The treatment chooses the shortest candidate under a label-independent prefix code and the control uses a frozen content-hash tie-break only.

The six-bit membership header declares the suffix payloads, so the code is self-delimiting and prefix-free. Code lengths, candidate identities, the pool, calibration subsets and endpoint were frozen independently of episode labels.

## Exact result

| Selector | Fully correct libraries | Correct routing decisions | Selected optional branches |
|---|---:|---:|---:|
| Proof-constrained MDL | 64/64 | 4416/4416 | 0 |
| Proof-only frozen hash | 1/64 | 4284/4416 | 132 |

The paired census contains **63 fully correct library selections** unique to MDL, 0 unique to control, 1 correct under both and 0 under neither. At the routing-decision level, MDL produces 132 corrections and 0 regressions relative to the frozen hash control.

## Boundary

This is an exact causal contrast over the complete authored shadow-guard grammar, not a sample from natural library evolution. It identifies why a label-independent complexity preference can reject gratuitous branches after proof constraints, but it does not measure the description length of the current authored TSP/OR libraries, establish behavior under a natural proposer distribution, add benchmark-accuracy evidence or perform promotion. No sampling p-value is attached. No API, model, solver, native evaluator, VM, credential, problem body, request body, response body or reference answer was used.
