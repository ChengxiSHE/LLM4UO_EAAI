# Infrastructure root-cause closure

Status: **the affected experiments are stopped; no matching controller or
transport worker remains active**.

## Decision

The large `infrastructure_unavailable` counts came from two different provider
boundary failures. They were not caused by a missing local modeling package or
by selecting the wrong Python environment. The user-supplied
`/Users/chengxi-nju/Desktop/LLM4UO/.venv-preparation` interpreter was already
the transport worker for the claim-bearing runs.

The stopped runs remain immutable diagnostics. They must not be resumed or
converted into accuracy estimates. The completed rate-shaped NLEquiv restart
is terminal and will not send more requests.

## Incident 1: expanded OptiTrust-style sidecars

The original expanded-sidecar run ended with 10 completed cells, 3 method
failures, 22 infrastructure-unavailable cells, and 3 unfinished cells. It used
303 physical attempts, including 63 retries. Failures concentrated on long
expanded model outputs and reproduced at about 91 seconds with both the
original Python/`urllib` client and the supplied OpenAI/httpx environment,
including at concurrency one.

The root cause was a provider or front-gateway non-streaming duration cutoff,
not certificates, proxies, Python/OpenSSL selection, client library, or
concurrency five. The effective remedy was a bounded indexed representation
expanded by a trusted local compiler; changing virtual environments alone did
not remedy the cutoff. The expanded run is closed and must not be resumed.

## Incident 2: unpaced NLEquiv dispatch

The first 450-cell NLEquiv run checkpointed 190 cells: 180 completed and 10
infrastructure unavailable, while 260 were never dispatched to a terminal
checkpoint. Its 227 physical attempts included 34 retries. Every recorded
failed attempt was HTTP 429. Two provider windows each admitted exactly 60 new
requests before the transport circuit breaker opened.

This is a provider request-rate window. It is not an authentication, model,
schema, local package, TLS, or general network failure. That run is closed
without evaluation and must not be resumed.

The clean restart used the same 450 request identities, prompts, model,
endpoint, skill library, and statistical gate, with no response reuse. A
durable process-safe rate gate admitted at most 40 logical starts in any
rolling 60-second window while retaining API concurrency five. It completed
450/450 cells with zero method failure, zero infrastructure-unavailable cell,
452 physical attempts, and two successfully recovered connection retries.
Restart validation caused zero new sends. This confirms that rate shaping, not
environment replacement, closed the NLEquiv failure.

## Environment finding

The environment is intentionally split:

| Layer | Interpreter | Role | Relevant observation |
|---|---|---|---|
| Controller/solver | `.venv-fresh38` Python 3.11.6 | orchestration, numerical libraries, solver-facing work | has NumPy, SciPy, and psutil; does not currently contain pytest |
| Provider transport | `.venv-preparation` Python 3.10.1 | OpenAI/httpx single-attempt worker | OpenAI 2.54.0, httpx 0.28.1, httpcore 1.0.9, Pydantic 2.13.4 |

The supplied transport environment is usable but not self-contained:
`include-system-site-packages` and the user site are enabled, and its OpenAI,
httpx, Pydantic, and certifi modules resolve from the Python 3.10 user-site
directory. Frozen plans record the interpreter and observed package versions,
so this does not invalidate the completed run. It remains a clean-clone
reproducibility gap that should later be closed with a dedicated provider
lock/environment.

The absence of pytest from the controller environment is also a separate test
environment gap. It did not cause any API cell to become infrastructure
unavailable and must not be presented as the explanation for either incident.

## Final classification

1. The OptiTrust-style failures were **output-duration/representation**
   failures and required bounded output redesign.
2. The NLEquiv failures were **request-rate** failures and required a durable
   rolling rate gate.
3. The supplied `.venv-preparation` configuration was already in use and is
   retained as the transport configuration for the closed runs.
4. No experiment process is active, and neither stopped run is eligible for
   continuation or benchmark scoring.

Machine-readable evidence is in
`experiments/infrastructure_root_cause_closure_20261017.json`. It contains no
request body, response body, credential, per-item prediction, or evaluator
label.
