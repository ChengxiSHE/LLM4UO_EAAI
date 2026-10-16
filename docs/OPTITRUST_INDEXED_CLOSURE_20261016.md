# OptiTrust-style indexed adapter closure

## Decision

The interrupted expanded-model experiment is closed and must not be resumed.
Its infrastructure failure has been isolated and remediated, but the disclosed
safe OptiTrust-style adapter did not pass its frozen two-family method gate.
Accordingly, no common-38 accuracy run is authorized and no OptiTrust accuracy
number is reported.

This is a bounded negative result for the adapter implemented in this
repository. It is not an official OptiTrust reproduction and says nothing about
the native unreleased system or its reported paper results.

## Why the original run failed

The stopped common-38 v2 run reached 35/38 terminal cells: 10 completed, 3
method failures, 22 infrastructure-unavailable, and 3 without a terminal cell.
It used 303 physical attempts for 240 logical requests, including 63 retries,
before the transport circuit breaker opened. All 152 short analysis requests
in slots 0--3 completed. Failures concentrated at the expanded `milp-v1`
candidate slot, where only 12/38 completed and the successful outputs were much
longer than the historical pipeline.

Controlled non-benchmark probes reproduced a disconnect near 91 seconds in
both the original Python 3.11/urllib stack and the user-supplied Python
3.10/OpenAI-httpx stack, including at concurrency one. The primary cause was a
provider or front-gateway non-streaming duration cutoff, not certificates,
proxy variables, Python/OpenSSL selection, or concurrency five.

The supplied `.venv-preparation` directory is usable but is not self-contained:
OpenAI 2.54.0 and httpx 0.28.1 resolve from the Python 3.10 user site under
`~/Library/Python/3.10`. The frozen plans record this dependency source rather
than describing it as an isolated virtual environment.

## Remediation and capacity evidence

The replacement protocol sends a bounded `indexed-milp-ir-v1` proposal and
expands it locally with a deterministic, benchmark-agnostic compiler. Expanded
solver models never cross the provider boundary. The OpenAI/httpx worker runs
from the supplied environment with SDK retries disabled and environment proxy
discovery disabled; the existing SQLite ledger remains the sole retry and
deduplication authority.

Four prospective worst-shape capacity gates were frozen in sequence:

| Gate | Outcome | Physical/logical | Finding |
|---|---:|---:|---|
| v1 | fail | 3/3 | All candidates hit the 2,048-token length limit. |
| v2 | fail | 4/3 | All three JSON envelopes completed under 3,072 tokens, but strict nested compilation failed. |
| v3 | fail | 6/3 | Two envelopes completed; one malformed JSON response was not retried. |
| v4 | **pass** | 6/3 | Three bounded envelopes received, zero infrastructure-unavailable cells, no halt, and restart added zero sends. |

The v4 completion maximum was 2,714 tokens and the largest canonical candidate
was 5,014 bytes, below the frozen 3,072-token and 32 KiB limits. Strict nested
compilation remained diagnostic at the capacity gate because the subsequent
review stages are the component permitted to repair a surface-valid proposal;
no proposal can reach a solver without later strict admission.

## Method feasibility result

After capacity passed, two answer-blind end-to-end gates selected one maximum
public-size case from each family. Each gate executed 20/20 contiguous logical
requests with 20 physical attempts, zero retries, zero infrastructure-unavailable
cells, zero review abstentions, no circuit breaker, and zero restart sends. No
reference answer was loaded.

Both gates failed the method criterion:

| Gate | Views per cell | Minimum optimal views | Cells with selected consensus |
|---|---:|---:|---:|
| feasibility v1 | 5 | 0 | 0/2 |
| feasibility v2 | 5 | 0 | 0/2 |

The failures were typed IR/admission or review-composition failures. There were
no valid models to send to the solver, so these are not accuracy observations.
They show that the disclosed safe adapter, under its frozen bounded review
contract, was not ready for full-denominator evaluation.

## Scientific boundary

Supported claim: the bounded indexed representation and supplied transport
environment close the original upstream duration failure, while the safe
OptiTrust-style adapter fails a prospective two-family method gate. The full
common-38 run was therefore not dispatched.

Unsupported claims include official OptiTrust reproduction, native
five-language execution, OptiTrust benchmark accuracy, equal-budget comparison,
or OptiTrust superiority/inferiority. Further prompt or adapter tuning was
stopped because the project instruction is to reproduce baselines normally,
not repeatedly optimize a weak baseline.

The machine-readable closure is
`experiments/optitrust_indexed_closure_20261016.json` (SHA-256
`10f074655918d84e758ae99dc031e8492513479b90e591646340ea9282ab6d5d`).
