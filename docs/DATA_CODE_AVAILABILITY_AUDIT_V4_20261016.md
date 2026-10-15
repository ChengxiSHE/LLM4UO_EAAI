# Data and code availability audit v4 — 2026-10-16

## Public release

The public, history-free repository is
<https://github.com/ChengxiSHE/LLM4UO_EAAI>. Release `v1.0.0` resolves to the
single zero-parent commit `3b870323935fa0a00ffd3fe9d1dc3512323beacf` and tree
`3c90e562c0f3f228c2a1a031320dd75b80257304`. The exact verified candidate
bundle, A--E layer audits and post-publication checksums are attached at
<https://github.com/ChengxiSHE/LLM4UO_EAAI/releases/tag/v1.0.0>.

An unauthenticated recursive clean clone retrieved the public repository and
the pinned solver-in-the-loop submodule. Ninety-one credential-free tests and
six deterministic checks passed, both Git object graphs passed full checks, and
the checkout remained clean. The public tag therefore closes the repository,
history, dependency-acquisition and credential-free reconstruction portions of
the release contract.

This is an integrity/audit reconstruction, not public endpoint rescoring. The
release recomputes evidence hashes, aggregate arithmetic, content-addressed
library identities and body-free output identities without restricted task
bodies or evaluator-only answers. The frozen controlled-review protocol gives
an independent reviewer a hash-bound, non-redistributive path to recompute the
TSP, OR-Debug and common-38 endpoints and publish only an aggregate
attestation.

That controlled review has now passed: TSP, OR-Debug and common-38 were
recomputed exactly, with only aggregate counts and hashes released. This closes
independent endpoint verification for the evidence chain while preserving the
non-redistribution boundary.

## Licensing and exclusions

First-party software and machine-readable artifacts are released under
Apache-2.0. Explicitly marked author-owned aggregate Source Data and
documentation are released under CC BY 4.0. The NOTICE preserves third-party
scope. Upstream benchmark content, the solver-in-the-loop submodule, CoE,
Gurobi and other third-party material remain under upstream terms and are not
relicensed by the root license.

Private request/response bodies, credentials, evaluator-only answers,
restricted upstream task text and the private experiment request-envelope
runtime are excluded. The public provider surface binds only endpoint, model,
concurrency, CA identity and TLS construction and makes zero provider calls.

## Remaining archival item

No archival DOI has been verified. The GitHub Release and its server-reported
asset digests are public, but the manuscript must keep the DOI pending until an
external archival service records the deposit. This is now the only open
availability identifier; it does not change the public code, evidence or
numerical results.
