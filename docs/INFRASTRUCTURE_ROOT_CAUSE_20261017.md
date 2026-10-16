# Infrastructure root-cause closure (2026-10-17)

The legacy `formal_v3_20260912` experiment is closed and must not be resumed. Its controller record is terminal (`completed`), PID 41906 is no longer alive, the ledger has no global halt, and this audit made zero model calls.

## What “3,995 infrastructure unavailable” actually contains

The formal test matrix contains 73,224 cells: 69,229 completed and 3,995 were recorded as unavailable (5.456%). The unavailable bucket mixes four different phenomena:

| terminal cause | cells | share of the 3,995 |
|---|---:|---:|
| transport timeout | 2,780 | 69.59% |
| invalid JSON response | 675 | 16.90% |
| incomplete response | 358 | 8.96% |
| method-level `Invalid` | 112 | 2.80% |
| trajectory budget exhausted | 70 | 1.75% |

Only the first three are transport/response infrastructure failures. The last two are method or budget outcomes and should not be pooled under an infrastructure label in future experiments.

At the physical-attempt level, there were 1,170 timeout failures, 26 incomplete-response failures, seven invalid-JSON failures, five HTTP 500 responses, and only three HTTP 429 responses. This rules out rate limiting as the dominant explanation. The old campaign used a direct `urllib` worker under the controller's Python 3.11 runtime with a hard 90-second request bound. It did not use the later sidecar worker in `/Users/chengxi-nju/Desktop/LLM4UO/.venv-preparation`.

The failures also depend on request shape. OptMATH had 1,905/8,964 unavailable cells (21.25%), compared with 308/32,670 for OptiBench (0.94%). The unavailable rate increased from 2.70% at the 16,384-token trajectory cap to 6.75% and 6.92% at 32,768 and 65,536. Rates across methods were much closer (4.92% to 6.24%). This pattern is consistent with long or difficult generations crossing the transport/provider duration envelope, rather than a broken local package installation or a single bad method.

## Environment diagnosis

The requested preparation environment is usable and its worker imports pass an offline smoke test. It provides Python 3.10.1, OpenAI 2.54.0, httpx 0.28.1, httpcore 1.0.9, requests 2.34.2, and certifi 2026.7.22. The current bounded sidecar disables environment proxies and SDK retries; the durable controller owns retry accounting.

Two later runs provide a direct control:

- The paced, short-response NLEquiv run used this exact sidecar environment and completed 450/450 logical requests with 452 physical attempts and no global halt.
- The long OptiTrust-style capacity run used the same environment, but three attempts still ended in `APIConnectionError` around 93–96 seconds before later retries completed all 3/3 logical requests.

Therefore the environment is not the primary root cause. Using it removes ambiguity in the HTTP client stack and is the correct configuration for future calls, but it cannot overcome a provider or front-gateway duration cutoff for long requests. The environment is also configured with `include-system-site-packages = true`, so every future plan must freeze the interpreter hash, package versions, module paths, OpenSSL version, and CA hash; the directory name alone is not a reproducibility guarantee.

The alternative `/Users/chengxi-nju/Desktop/LLM4DRO/.venv` was also reviewed without making an API call or modifying that environment. It is better isolated (`include-system-site-packages = false`) and passed all three bounded-worker unit tests, but it failed two of five provider-environment tests: its certifi 2026.2.25 bundle hash does not match the project's frozen certifi 2026.7.22 bundle. It is therefore rejected **as currently installed**. It may become a cleaner fallback after a separately pinned rebuild and a full preflight, but another project's environment will not be mutated in place.

## Binding policy for the next experiment

1. Keep `.venv-fresh38` for the controller, parsing, evaluation, and solver work.
2. Use `/Users/chengxi-nju/Desktop/LLM4UO/.venv-preparation/bin/python` only for the pinned OpenAI/httpx transport worker.
3. Run a small, short-response transport canary before any new campaign. A canary may verify connectivity and rate headroom, but it may not inspect benchmark outcomes or alter a frozen method.
4. Replace long monolithic generations with short decisions, sparse retrieval, or bounded chunks. Increasing the local timeout alone is not an adequate fix because the long-run failures occurred near an external 90-second envelope even when the client allowed 150 seconds.
5. Report transport unavailable, response-format failure, method invalidity, and budget exhaustion as separate denominators while retaining every item in the full benchmark denominator.
6. Preserve durable single-fingerprint accounting, at most three attempts, checkpointed continuation, and no automatic resend of an unknown-outcome request.

The machine-readable record is `experiments/infrastructure_root_cause_audit_20261017.json`.
