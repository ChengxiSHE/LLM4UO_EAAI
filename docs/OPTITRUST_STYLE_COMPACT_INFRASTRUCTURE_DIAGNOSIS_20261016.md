# OptiTrust-style compact run: infrastructure diagnosis

## Decision

The frozen common-38 compact-sidecar run was stopped and must not be resumed.
It is incomplete and contributes no benchmark accuracy estimate.  The failure
was caused primarily by an upstream non-streaming request cutoff near 91
seconds when the model generated a long expanded `milp-v1` object.  Changing
from the current Python/OpenSSL/`urllib` stack to the user-provided
`.venv-preparation` OpenAI/httpx stack did not remove the cutoff.

## What happened

The run stopped after 35 of 38 identities had terminal cells.  Ten were
complete, three were method failures, and twenty-two were infrastructure
unavailable.  The ledger contained 240 logical requests, 303 physical
attempts, 63 retries, and a terminal `circuit_breaker_transport_failures`
halt.  Three identities had no terminal cell.  These counts describe an
interrupted infrastructure diagnostic and must not be converted into an
accuracy denominator.

The failure location is decisive.  All 38 identities completed each of the
four short analysis slots, for 152/152 successful short requests.  At the
single canonical-candidate slot, only 12 requests completed, 24 exhausted all
three attempts, and two were still failed when the run stopped.  Only ten
identities reached all five review slots.  Recorded failures were dominated by
104 `RemoteDisconnected` events and 10 EOF events, plus one invalid JSON
response.  Successful canonical responses were much larger than earlier
stages: 12.9--39.1 KB and 5,423--14,911 completion tokens, with medians of
22.1 KB and 8,488 tokens.

## Environment comparison

The current environment uses Python 3.11.6, OpenSSL 3.0.11 and standard-library
`urllib`, with a fresh TLS connection in each worker process.  The supplied
`.venv-preparation` uses Python 3.10.1, OpenSSL 1.1.1l, OpenAI 2.54.0, httpx
0.28.1 and httpcore 1.0.9.  Both environments use the same certifi bundle byte
hash and neither has proxy variables enabled.  The preparation project's
historical DeepSeek-V4-Flash ledger contains 5,675 attempts and 5,673 nonempty
outputs, although those historical outputs were generally shorter.

In a controlled, synthetic, non-benchmark probe, three concurrent long JSON
requests through `urllib` all ended in `RemoteDisconnected` after
90.4--91.2 seconds.  The same three requests through the preparation
OpenAI/httpx stack all ended in `APIConnectionError` after 90.9--91.3 seconds.
Reducing concurrency to one did not help: one request in each environment again
failed after about 90.9 seconds.  This rules out local certificates, proxies,
Python version, OpenSSL version, client library and concurrency five as the
primary cause.

A final synthetic streaming probe stayed connected beyond ten minutes, so
streaming avoided the non-streaming idle cutoff.  It did not finish within a
reasonable bounded time and was stopped.  Streaming therefore does not meet
the current durable, bounded experimental contract even though it explains
the cutoff mechanism.

## Required redesign

The next version must not ask the model to enumerate an expanded sparse MILP in
one response.  It should return a bounded indexed parametric intermediate
representation containing sets, variable families, constraint generators and
an objective generator.  A trusted deterministic compiler should expand that
representation to `milp-v1`, validate resources and solve it.  The model-facing
candidate response should be capped at 2,048 completion tokens.

The supplied `.venv-preparation` OpenAI/httpx stack should be used for future
transport consistency, but it is not treated as a cure.  Reviewer request
exhaustion should become an abstention rather than invalidate a candidate.
Streaming should remain disabled for claim-bearing runs until partial chunks,
total wall time and restart identity have their own audited ledger contract.

Before another common-38 run, a new outcome-blind capacity gate must use frozen
worst-shape public inputs and require every compact candidate to finish under
the non-streaming limit.  The earlier four-toy canary remains valid evidence of
basic control flow, but it was too easy to expose this long-generation failure.

Machine-readable evidence is in
`experiments/optitrust_style_compact_infrastructure_diagnosis_20261016.json`.
It contains no request body, response body, benchmark answer, objective, point,
or credential.
