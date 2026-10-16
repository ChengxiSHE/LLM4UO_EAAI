# Data and code availability audit v5 — 2026-10-16

## Current public release

The current history-free release is
[`v1.1.1`](https://github.com/ChengxiSHE/LLM4UO_EAAI/releases/tag/v1.1.1),
commit `ed663fcdf8336f77c466652a516d5bc2c567f93a`, tree
`93fc594cfe9d51a5674608a75d6ec3821b4fdba5`. It contains one reachable,
zero-parent commit and the 81-path indexed-closure evidence surface. A fresh
recursive clone from the public tag remotely acquired the pinned solver
submodule, passed full object checks, 81 credential-free Layer-A tests and
three deterministic reconstruction checks, and remained clean.

All four release assets were downloaded again and matched their server
SHA-256 digests. The patched durable publisher passed 500 identical-payload
and 500 different-payload concurrent repetitions in the public clone.
`v1.1.0` remains immutable but is superseded for reconstruction because its
public-clone validation exposed a shared-journal cleanup race.

The package reconstructs evidence hashes, aggregate arithmetic,
content-addressed library identities and 2,985 body-free output identities. It
does not redistribute restricted task text or evaluator-only answers and does
not itself rescore every benchmark endpoint. The separate frozen
controlled-review protocol has exactly recomputed TSP, OR-Debug and common-38
under restricted-data custody.

## Licensing and exclusions

First-party software and machine-readable artifacts are released under
Apache-2.0. Explicitly marked author-owned aggregate Source Data and
documentation are released under CC BY 4.0. The NOTICE preserves third-party
scope. Reused benchmarks, the solver submodule, CoE, Gurobi and other
third-party material retain their upstream terms.

Private request and response bodies, credentials, evaluator-only answers and
restricted upstream task text are excluded. Provider replay and the commercial
solver remain separately provisioned layers; neither is needed for the
credential-free integrity reconstruction.

## Archival state

The exact four-file deposit, creator metadata, licenses, related identifiers
and checksums are frozen in
[`archival_deposit_packet_v1_1_1_20261016.json`](../experiments/archival_deposit_packet_v1_1_1_20261016.json).
A public Zenodo query found no record for this repository on 2026-10-16, so no
archival DOI is claimed. The remaining action is external deposit of this exact
release followed by verification and insertion of the returned DOI. The DOI
must not be guessed from the GitHub Release.
