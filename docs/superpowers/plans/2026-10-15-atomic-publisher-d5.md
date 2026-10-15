# D5 Atomic Publisher Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved shared durable no-clobber publisher and route all nine audited historical publishers through byte-preserving thin adapters.

**Architecture:** Historical producer sources remain byte identical and retain their frozen self-hashes. `llm4or.atomic_publisher` owns secure path traversal, content-bound reservations, durable no-clobber publication, idempotence, and replay recovery; `llm4or.reconstruction_publishers` supplies nine producer-specific capture adapters and one registry-driven CLI.

**Tech Stack:** Python 3.11 standard library, POSIX directory file descriptors and hard links, `unittest`, SHA-256, canonical JSON metadata.

**Spec:** `docs/ATOMIC_PUBLISHER_D5_DESIGN_20261015.md`

## Global Constraints

- Preserve all nine historical producer files byte-for-byte and verify their frozen SHA-256 before invocation.
- Preserve scientific fields, input identity checks, serializers, output paths, bytes, and fail-closed validation behavior.
- Never replace a terminal file; byte-identical replay is success and differing bytes are a conflict.
- Reject path escape and symlinks under the trusted repository root.
- Make cross-directory multi-output publication replay-recoverable without TTL takeover.
- Make no API/model, solver, native evaluator, VM, credential, licensing, DOI, or repository-publication action.

## Review Focus

- Concurrent same-payload writers must both succeed without a partial terminal.
- Concurrent different-payload writers must leave exactly one complete payload and report a conflict.
- A crash after the first member of a cross-directory pair must be recoverable only by byte-identical replay.
- Existing symlink/non-regular terminals and symlinked parent components must fail without mutation.
- A source-hash or output-inventory mismatch in any thin adapter must fail before publication.

---

### Task 1: Durable no-clobber transaction core

**Files:**
- Create: `llm4or/atomic_publisher.py`
- Create: `tests/test_atomic_publisher.py`

**Interfaces:**
- Produces: `publish_bytes(root: Path, path: Path | str, payload: bytes, *, _fault=None) -> PublicationResult`.
- Produces: `publish_bundle(root: Path, entries: Mapping[Path | str, bytes], *, _fault=None) -> PublicationResult`.
- Produces: `PublicationConflict`, `PublicationBoundaryError`, and immutable `PublicationResult`.

- [ ] **Step 1: Write failing boundary/idempotence tests**

Add tests for first publication, byte-identical replay, different-byte conflict,
path escape, parent symlink, terminal symlink, and non-regular terminal.

- [ ] **Step 2: Run the new test module and verify import/behavior failures**

Run: `python3 -m unittest tests.test_atomic_publisher -v`

Expected: FAIL because `llm4or.atomic_publisher` does not exist.

- [ ] **Step 3: Implement the minimal single-transaction publisher**

Use secure root-relative directory traversal, content-bound canonical metadata,
unique `fsync`ed temporary files, exclusive hard-link commits, exact-byte checks,
and directory `fsync`.

- [ ] **Step 4: Add failing concurrency and crash-replay tests**

Add two-process same/different payload races and fault injection after journal,
reservations, first destination, and before cleanup.

- [ ] **Step 5: Implement bundle reservations and replay recovery**

Reserve all destinations before linking the first payload; retain reservations
and journal until every destination is durable.

- [ ] **Step 6: Run Task 1 tests**

Run: `python3 -m unittest tests.test_atomic_publisher -v`

Expected: all Task 1 tests pass.

- [ ] **Step 7: Commit**

Commit message: `feat: add durable no-clobber publisher`

### Task 2: Nine byte-preserving producer adapters

**Files:**
- Create: `llm4or/reconstruction_publishers.py`
- Create: `scripts/publish_reconstructed_artifact.py`
- Create: `tests/test_reconstruction_publishers.py`
- Add unchanged audited sources: the nine paths listed by the D5 boundary audit.

**Interfaces:**
- Consumes: `publish_bundle` from Task 1.
- Produces: `PUBLISHERS`, `run_publisher(name: str, root: Path) -> PublicationResult`, and CLI `--publisher`/`--list`.

- [ ] **Step 1: Write failing registry, source-pin, and serializer tests**

Assert exactly nine IDs, exact source hashes, exact historical bytes for compact,
pretty, private/public pair, and JSON/Markdown pair adapters, and rejection of an
unexpected captured output.

- [ ] **Step 2: Run adapter tests and verify missing-module failures**

Run: `python3 -m unittest tests.test_reconstruction_publishers -v`

Expected: FAIL because the adapter registry does not exist.

- [ ] **Step 3: Implement capture contexts and the nine adapters**

Import each unchanged producer after verifying its bound SHA. Capture only its
declared write seam or redirected terminal constant, require the exact audited
output inventory, then publish already serialized bytes through Task 1.

- [ ] **Step 4: Implement the registry CLI**

The CLI lists adapters or runs exactly one; it performs no implicit batch/API/
solver execution.

- [ ] **Step 5: Run Task 2 and Task 1 tests**

Run: `python3 -m unittest tests.test_atomic_publisher tests.test_reconstruction_publishers -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

Commit message: `feat: add nine reconstruction publisher adapters`

### Task 3: Approval record and machine-verifiable migration audit

**Files:**
- Modify: `experiments/author_release_decision_packet_20261015.json`
- Modify: `tests/test_release_evidence_reconstruction.py`
- Create: `experiments/atomic_publisher_migration_audit_20261015.json`
- Create: `docs/ATOMIC_PUBLISHER_MIGRATION_AUDIT_20261015.md`
- Modify: `experiments/goal_completion_audit_20261015.json`
- Modify: `llm4or/release_evidence_reconstruction.py`
- Modify: `results/release_evidence_reconstruction_v1_20261015.json`

**Interfaces:**
- Consumes: Task 1/2 source and test results.
- Produces: a D5-approved decision record and hash-bound migration evidence.

- [ ] **Step 1: Write failing release-evidence assertions**

Assert D5 alone is approved, D1--D4/D6--D8 remain false, publisher code changed
is true, nine source hashes remain frozen, nine adapters exist, and the migration
audit records concurrency/recovery tests with zero API/model/solver calls.

- [ ] **Step 2: Run the release-evidence test and verify it fails on old D5 state**

Run: `python3 -m unittest tests.test_release_evidence_reconstruction -v`

Expected: FAIL because D5 is still recorded as unapproved and no migration audit exists.

- [ ] **Step 3: Update the decision and create the migration audit**

Record only the user's D5 approval. Preserve the legal and publication boundary.

- [ ] **Step 4: Add the two migration artifacts to G11 evidence and rebuild counts**

Update expected goal reference/path counts and regenerate the deterministic
release evidence report.

- [ ] **Step 5: Run release reconstruction checks**

Run: `python3 scripts/reconstruct_release_evidence.py --check`

Expected: exit 0 and a deterministic report SHA.

- [ ] **Step 6: Commit**

Commit message: `release: record and verify D5 publisher migration`

### Task 4: Full verification and clean-clone evidence

**Files:**
- Modify only if generated hashes require it: Layer A audit/control artifacts.

**Interfaces:**
- Consumes: all earlier tasks.
- Produces: a clean, reproducible D5 branch with bounded remaining author gates.

- [ ] **Step 1: Run all repository tests**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests pass; any unrelated missing external dependency is named and
the credential-free Layer A subset is still required to pass.

- [ ] **Step 2: Run deterministic builders and checks**

Run the current-library manifest check, current-library reconstruction check,
release-evidence reconstruction check, `git diff --check`, and exact frozen-source
hash check for all nine historical producers.

- [ ] **Step 3: Run isolated credential-free Layer A from the committed branch**

Run: `python3 scripts/run_clean_clone_layer_a.py --local-submodule-source vendor/solver-in-the-loop --output /tmp/llm4or-d5-layer-a.json`

Expected: passed status, zero credentials/API/model calls, and all Layer A tests pass.

- [ ] **Step 4: Review the complete branch against the spec**

Use the executing-plans final review package and record every ruling or deferred
minor. Fix Critical/Important findings through a new failing test before code.

- [ ] **Step 5: Commit any verification-only artifact update**

Commit message: `test: verify atomic publisher release boundary`
