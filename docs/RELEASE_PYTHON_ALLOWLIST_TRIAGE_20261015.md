# Python source triage for headline reconstruction

Status: provisional read-only triage, 2026-10-15. The machine-readable audit is
`experiments/release_python_allowlist_triage_20261015.json`, SHA-256
`da56d4924a5cc33639795dae6ab3a432d3269cf1930f8e18bb709bd4fc1801ea`.
This document does not authorize staging or public release.

## Decision

The 83 untracked Python files in the conservative headline reconstruction
closure must not be bulk-added. They separate into four disjoint queues:

| Queue | Files | Release interpretation |
| --- | ---: | --- |
| Explicitly bound by frozen evidence | 23 | Highest-priority semantic, authorship, rights and minimum-disclosure review |
| External common-40 record reconstruction | 5 | Needed for stored BIND/CoE cohort union and summary reconstruction; not an inference-replay closure |
| Other direct entrypoints or tests | 5 | Directly exercised by the inspected evidence surface but not contained in the three frozen source-binding sets |
| Incidental historical import fanout | 50 | Must not enter an allowlist unless an executed reconstruction test proves necessity or an approved behavior-equivalent redesign cannot remove the dependency |

The partition covers all 83 files exactly once. It narrows the first review
queue from 83 to 28 files without claiming that any of those 28 is already
rights-safe or sufficient for clean-clone reproduction.

## Frozen source bindings

The current bytes still match every explicit source hash:

| Evidence family | Bound Python files | Tracked now | Untracked inside closure | Outside inspected closure | Hash mismatches |
| --- | ---: | ---: | ---: | ---: | ---: |
| TSP confirmation | 11 | 2 | 6 | 3 | 0 |
| OR-Debug confirmation | 17 | 6 | 9 | 2 | 0 |
| Typed-count exact repair | 11 | 3 | 8 | 0 | 0 |

The five outside-closure files are still bound by the frozen plans. They are
outside only because the conservative closure starts from a smaller set of
current headline entrypoints and tests. A final reconstruction manifest must
include them or state why their historical result is record-only.

## Risk signals

The audit emits file names and counts, never literal values. The following are
heuristic review triggers rather than findings of leakage or misconduct:

| Signal | Files |
| --- | ---: |
| Network/provider-related names or imports | 21 |
| Credential/environment-related names | 9 |
| Solver backend references | 8 |
| Subprocess/native-related references | 5 |
| Private/evaluator-related terms | 20 |
| String literals of at least 500 characters | 19 |
| File-write calls | 18 |
| Dynamic execution or import calls | 3 |

The earlier literal screen found no Bearer, OpenAI-style key or quoted-secret
assignment. All 83 files parse as Python. Neither result is release clearance.
No file has a per-file SPDX, copyright or `Licensed under` signal, and the
repository still lacks an author-selected root license.

## Provenance boundary

The reachable Git object listing contains path-name hints and current blob
objects for all 83 files. A stricter search did not find any reachable commit
that contains a current byte-identical blob at the same path. Object-store
presence can arise from snapshots or alternative paths and does not establish
a public provenance chain. Release review must therefore bind the selected
current bytes explicitly instead of inferring provenance from object presence.

## Minimal release direction

The first source review should cover the 23 evidence-bound files and five
external record-reconstruction files. For each file it must answer:

1. Is the current byte identity needed to reconstruct a paper claim?
2. Is the file first-party or otherwise redistributable under the selected
   repository license and attribution policy?
3. Does it contain benchmark text, repair identity, evaluator-only information,
   response content, or environment-specific paths that require projection?
4. Can its behavior be exercised through a deterministic, credential-free
   layer-specific test?
5. Are its non-Python inputs, binaries, services and licenses separately fixed?

The 50 incidental fanout files remain excluded by default. TSP preparation and
the historical count terminal audit currently import broad provider, review
and packing stacks. Reducing those imports requires the already identified
architecture design and behavior-equivalence gate; this audit does not grant
implementation approval.

## Claim boundary

This audit supports one bounded statement: the untracked Python closure now has
a complete, disjoint evidentiary triage and a 28-file first review queue. It
does not establish a release allowlist, runnable inference replay, rights-safe
distribution, complete runtime closure or clean-clone reproducibility. No
network, model/API, solver, native evaluator or VM call was made, and no
request/response body, evaluator-only answer or credential was read.
