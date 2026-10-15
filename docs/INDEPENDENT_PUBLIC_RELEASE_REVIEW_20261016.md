# Independent public release review — 2026-10-16

## Scope and independence

A fresh-context reviewer used only the unauthenticated public repository and
`v1.0.0` release. The reviewer did not read the local working tree, credentials,
private request/response bodies, task bodies or evaluator-only answers and made
no model, API or benchmark-solver call.

## What passed

The recursive public clone retrieved the zero-parent release commit
`3b870323935fa0a00ffd3fe9d1dc3512323beacf`, tree
`3c90e562c0f3f228c2a1a031320dd75b80257304` and pinned submodule
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010`. Both object graphs passed full
checks and remained clean. All 11 release-asset sizes and server-reported
SHA-256 digests matched. Layer A passed 79/79 tests and three reconstruction
commands. In a dependency-isolated provider environment, the additional release
suite passed 12/12 tests and the zero-call preflight bound DeepSeek-V4-Flash,
concurrency five and the declared CA bundle.

The reviewer independently reproduced the published aggregate arithmetic for
TSP, OR-Debug, common-38, the finite acquisition census and the finite
complexity census. The conditional theoretical statements and their declared
limits were internally consistent.

## Findings and disposition

- **Critical — public endpoint rescoring.** The public package reconstructs
  hashes, schemas, aggregate arithmetic, 70 evidence paths, 416 assertions, 15
  boundaries and 2,985 body-free identities. It does not independently rerun
  solver/provider inference or rescore the central benchmark endpoints from
  rights-restricted inputs and evaluator-only answers. The public package must
  be described as an integrity/audit package. A separate hash-bound controlled
  review path is required for endpoint verification.
- **Important — stale release prose.** The tagged manuscript and supplement
  still contained pre-publication language and old 53-test references. The
  post-release branch corrects these statements while leaving `v1.0.0`
  immutable.
- **Important — common-38 interpretation.** The fixed-cohort result uses unequal
  native call budgets, authored construction cost that was not equalized,
  answer-bearing BIND final feedback and a safe CoE adapter. The manuscript now
  states these limits in the same abstract sentence as the comparison.
- **Important — duplicate Layer-A contracts.** The release had both 53-test and
  79-test descriptions. The current branch designates one 79-test entrypoint,
  `python3 scripts/run_public_integrity.py --check`, and binds the environment
  manifest and README to it.
- **Minor — provenance, provider install and DOI.** The immutable tag is
  unsigned; the provider dependency now includes its wheel hash and an explicit
  isolated install command; no archival DOI is claimed.

## Independent conclusion

The reviewer judged `v1.0.0` successful as a history-free public release and
integrity/audit package, but not by itself a complete endpoint-reproduction
package. This distinction is now a manuscript boundary. Closing the endpoint
portion requires the controlled review protocol or a future rights-safe public
scoring bundle. DOI registration remains an independent archival task.

## Controlled-review addendum

A separate fresh-context controlled review subsequently reproduced TSP,
OR-Debug and common-38 exactly from their hash-bound restricted inputs. That
closes independent endpoint verification for the manuscript evidence chain; it
does not alter this report's finding that the public `v1.0.0` package by itself
is an integrity/audit package rather than a public endpoint-rescoring package.
