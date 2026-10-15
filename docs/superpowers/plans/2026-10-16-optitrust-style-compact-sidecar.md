# OptiTrust-style compact sidecar v2 implementation plan

> Execute autonomously under the user's standing approval. Use test-driven
> development and stop the benchmark dispatch if the synthetic capacity gate
> fails.

**Goal:** Close G14 with a prospectively frozen, scoreable paper-structure
OptiTrust-style sensitivity or an audited canary failure that determines the
next representation change without reading benchmark answers.

**Spec:** `docs/superpowers/specs/2026-10-16-optitrust-style-compact-sidecar-design.md`

### Task 1: Attempt-cap recovery invariant

- Add a failing gateway regression in `tests/test_formal_preparation.py`.
- Make the third failed attempt terminal before raising a circuit interruption.
- Reopen the ledger after clearing only the circuit and prove no fourth send.
- Run all formal gateway and fresh external tests; commit separately.

### Task 2: Pure compact runtime

- Create `tests/test_optitrust_style_compact_runtime.py`.
- Create `llm4or/optitrust_style_compact_runtime.py`.
- Define ten fixed stages, 8 KiB analysis caps, one canonical-model request,
  strict hash-bound review schema, bounded edit composer, resource checks,
  five trusted solves and strict majority.
- Test malformed/stale/duplicate/oversized edits, invalid models, majority,
  reference-last ordering and absence of generated-code execution.

### Task 3: Gateway contract and controller

- Extend `llm4or/formal_gateway.py` without weakening v1/Base/BIND/CoE paths.
- Create `llm4or/fresh_common38_optitrust_style_compact.py` and tests.
- Freeze exact ten-slot identities, concurrency five, three-attempt cap,
  full-denominator scoring and recursive privacy exclusions.
- Add freeze/run/score/audit entrypoints and independent reconstruction.

### Task 4: Synthetic capacity canary

- Freeze four generated non-benchmark public inputs before provider dispatch.
- Run the canary with AntChat DeepSeek-V4-Flash at concurrency four.
- Independently audit 40 contiguous logical slots, attempts, restart identity,
  parsed artifacts, privacy and zero-new-call reconstruction.
- Open Task 5 only if the prespecified capacity gate passes.

### Task 5: Frozen common-38 execution

- Freeze a new common-38 plan once, including exact source, environment,
  solver, code and transport identities.
- Run/resume at concurrency five, retaining every failure.
- Publish a body-free result and no-new-call independent audit.
- Never retune current, Base, BIND or CoE rows.

### Task 6: Synthesis, paper evidence and history-safe publication

- Compute paired statistics only over the declared full endpoint and only when
  the compact row has scoreable outcomes.
- Keep official OptiTrust artifact unavailability separate.
- Update manuscript, evidence ledger, paper manifest, goal audit and Layer-A
  expected counts.
- Run targeted tests, the canonical 79-test public contract, deterministic
  reconstruction, JSON/privacy scans and clean-clone checks.
- Publish through the history-safe public-main workflow; leave `v1.0.0`
  immutable and the archival DOI external.

