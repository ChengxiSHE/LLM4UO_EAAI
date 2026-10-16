# Fresh Common-38 Packet and Static-Readiness Plan

**Goal:** Convert the already audited 38 larger RCPSP/VRPTW identities into one content-addressed common-evidence packet and independently measure the existing trusted static compiler's real coverage before any model dispatch.

**Architecture:** A pure builder selects records only by the frozen non-outcome size rule, projects the distributed natural-language description and structured `instance_data` into one validated public payload, and excludes all gold, solver, variable and constraint annotations. A publisher writes a private payload bundle and a body-free public manifest with exclusive ownership. The same module compiles every packet through the pinned v10 trusted compiler and reports parser/resource coverage without solving or reading reference values.

**Constraints:** Exactly 13 RCPSP plus 25 VRPTW records; zero API/model/solver/native/VM calls; no reference objective, gold solution, source variables or source constraints in either public payloads or the body-free manifest; every future method receives the exact same payload hash; static compilation failures remain in the 38-record denominator.

## Task 1: Pure packet builder and readiness audit

- Create `llm4or/fresh_common38.py`.
- Create `tests/test_fresh_common38.py` first and observe import failure.
- Verify exact selection, unique identities and hashes, validated text-plus-structured-data payloads, prohibited-field exclusion, zero overlap with the prepared 183 cohort, deterministic readiness accounting, and fail-closed mutation behavior.

## Task 2: Exclusive publisher and terminal artifacts

- Create `scripts/prepare_fresh_common38.py`.
- Publish `results/private/fresh_common38_packets_v1.json` and `experiments/fresh_common38_packet_readiness_20261015.json` with exclusive create plus file/directory fsync.
- Recompute hashes and run the focused regression suite.

## Task 3: Evidence synchronization

- Add the body-free readiness artifact to the goal and paper evidence chain.
- State that common fact-packet readiness is closed while current-method skills, external serializers, budgets, custody and outcome execution remain open.
