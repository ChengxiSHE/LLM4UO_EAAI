# Remote recursive Layer A audit — HTTP/1.1

Status: passed for the pinned remote submodule at main source commit
`2002b29851b2ab118001251566b21d76ac339474`, 2026-10-15. The
machine-readable record is
`experiments/clean_clone_layer_a_remote_http1_audit_20261015.json`.

## Result

The initial default Git transport had failed first with an HTTP/2 framing
error and then with a 75-second connection timeout. A bounded read-only probe
forced Git HTTPS to HTTP/1.1 without changing repository or user
configuration. `ls-remote` returned the declared `main` and `HEAD` commit
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` in 1.778 seconds.

A new no-local clone of the bound main source commit then obtained
`vendor/solver-in-the-loop` recursively from
`https://github.com/agentic-or-benchmark/solver-in-the-loop.git` over HTTP/1.1.
The submodule checkout completed in 18.310 seconds at the exact pinned commit.
Its reachable object graph contained zero missing objects and `git fsck --full`
passed.

The fresh recursive checkout subsequently passed 53 credential-free Layer A
unit tests, current skill/library manifest verification, the 2,985-identity
library reconstruction audit, and paper-evidence reconstruction. The checkout
remained clean. No credential, inherited secret value, request/response body or
evaluator-only answer was read, and no model/API, solver, native evaluator or
VM call occurred.

## Claim boundary

This closes current-run remote acquisition for the pinned external submodule
when Git HTTPS uses HTTP/1.1. It does not show that the main repository is
already available from a public remote, grant redistribution rights, execute
the separately licensed solver, fix the nine historical publisher ownership
gaps, or authorize a public release.
