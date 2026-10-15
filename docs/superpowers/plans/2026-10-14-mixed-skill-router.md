# Mixed Skill Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and evaluate a fail-closed public-only router that delegates frozen TSP and OR-Debug confirmation inputs without changing direct family outputs.

**Architecture:** A pure guard module classifies exact public envelopes without seeing problem IDs. A preparation script joins already exposed public records into one hash-pinned mixed bundle. A local runner delegates to frozen family executors and compares compact outputs with terminal direct outputs; a separate audit summarizes route and identity preservation.

**Tech Stack:** Python 3.10, `unittest`, existing TSP/OR-Debug modules, local Gurobi CLI, JSON/SHA256 audit artifacts.

**Spec:** `docs/superpowers/specs/2026-10-14-mixed-skill-router-design.md`

## Global Constraints

- Do not expose reference answers, target repairs, saved IIS labels, recorded optima or correctness bits to router code.
- Do not use `problem_id` in guard selection.
- Preserve both family executors and their terminal result artifacts byte-for-byte.
- Zero or multiple matches abstain; no fallback guesses.
- Use zero model/API requests and local solver concurrency at most five.
- Treat the mixed result as compositional identity evidence, not fresh accuracy.

## Review Focus

- A union-shaped envelope must abstain instead of choosing by key precedence; pin in Task 1 tests.
- Absolute or parent-traversing OR-Debug paths must abstain before dispatch; pin in Task 1 tests.
- A syntactically valid but wrong SHA must abstain for TSP and fail delegated content binding for OR-Debug; pin across Tasks 1 and 3.
- Dispatcher exceptions must become explicit record failures without changing another record; pin in Task 3 tests.
- Family output compaction must match historical conventions exactly; pin in Task 3 tests and Task 4 full audit.

---

### Task 1: Pure public-envelope router

**Files:**
- Create: `llm4or/mixed_skill_router.py`
- Test: `tests/test_mixed_skill_router.py`

**Interfaces:**
- Consumes: public envelope dictionaries only.
- Produces: `route_public_envelope(envelope: dict) -> dict` with `route` and `reason`; constants `TSP_ROUTE` and `OR_DEBUG_ROUTE`.

- [ ] **Step 1: Write failing tests** for valid TSP, valid OR-Debug, empty, partial, union-shaped, bad-hash, absolute-path and parent-traversal envelopes; assert no problem ID is accepted inside an envelope.
- [ ] **Step 2: Run** `python3 -m unittest tests.test_mixed_skill_router` and verify import failure.
- [ ] **Step 3: Implement** exact guards and unique-match selection in `llm4or/mixed_skill_router.py`.
- [ ] **Step 4: Re-run** the test module and require all tests to pass.
- [ ] **Step 5: Commit only Task 1 files** with message `feat: add fail-closed mixed skill router`.

### Task 2: Frozen mixed public bundle

**Files:**
- Create: `scripts/prepare_mixed_skill_confirmation_bundle.py`
- Create: `tests/test_prepare_mixed_skill_confirmation_bundle.py`
- Create on execution: `experiments/mixed_skill_confirmation_bundle_20261014.json`

**Interfaces:**
- Consumes: the two frozen public confirmation artifacts and their pinned SHA256 values.
- Produces: 2,985 records with outer `record_id`, `source`, and inner `public_envelope`, plus source hashes and a deterministic mixed-order digest.

- [ ] **Step 1: Write failing fixture tests** for count, exact inner fields, no hidden fields, deterministic ordering and source-hash mismatch.
- [ ] **Step 2: Run** the targeted test and verify failure before the script exists.
- [ ] **Step 3: Implement** `build_bundle(root: Path) -> dict`; interleave sources by SHA256 of a source-neutral record receipt rather than by outcome.
- [ ] **Step 4: Run** targeted tests and require pass.
- [ ] **Step 5: Execute once** to write the bundle, then audit 140 TSP and 2,845 OR-Debug records with zero forbidden fields.
- [ ] **Step 6: Commit Task 2 source/test files and the immutable bundle** with message `feat: freeze mixed skill public bundle`.

### Task 3: Delegating mixed runner

**Files:**
- Create: `llm4or/mixed_skill_execution.py`
- Create: `tests/test_mixed_skill_execution.py`
- Create: `scripts/run_mixed_skill_confirmation.py`
- Create on execution: `results/mixed_skill_confirmation_outputs_20261014.json`

**Interfaces:**
- Consumes: mixed records, `model_root`, per-record workspace and frozen family executors.
- Produces: `execute_mixed_record(record, *, model_root, workspace) -> dict` containing route, terminal status and untouched family output; runner output for all 2,985 records.

- [ ] **Step 1: Write failing tests** with injected fake executors for exact delegation, abstention without calls, exception localization, and no outer ID passed to guards.
- [ ] **Step 2: Run** targeted tests and verify failure.
- [ ] **Step 3: Implement** dispatcher and the family-specific TSP compaction helper matching `scripts/run_tsp_constraint_confirmation.py::_compact`.
- [ ] **Step 4: Run** Task 1 and Task 3 tests and require pass.
- [ ] **Step 5: Implement** the immutable runner with source/code hash pins, concurrency five and refusal to overwrite.
- [ ] **Step 6: Run** all 2,985 records once; retain record-level failures and never retry.
- [ ] **Step 7: Commit Task 3 source/test/runner and terminal output** with message `feat: execute frozen mixed skill router`.

### Task 4: Independent identity audit and paper synchronization

**Files:**
- Create: `scripts/audit_mixed_skill_confirmation.py`
- Create: `tests/test_audit_mixed_skill_confirmation.py`
- Create on execution: `results/mixed_skill_confirmation_audit_20261014.json`
- Modify: `docs/THEORY_CLAIM_EVIDENCE_MATRIX.md`
- Modify: `docs/TOP_CONFERENCE_PAPER_FRAME.md`
- Modify: `docs/PROJECT_HANDOFF.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: frozen direct outputs, mixed bundle and mixed terminal outputs.
- Produces: route counts, collision/abstention/failure counts, per-family exact-output equality, inherited endpoint statement and claim guard.

- [ ] **Step 1: Write failing tests** for one TSP mismatch, one OR-Debug mismatch, missing record, duplicate record and a fully equal fixture.
- [ ] **Step 2: Run** targeted tests and verify failure.
- [ ] **Step 3: Implement** pure `audit_identity(...) -> dict` and immutable CLI pins.
- [ ] **Step 4: Run** all mixed-router tests and require pass.
- [ ] **Step 5: Execute** the full audit; require 2,985 unique routes and 2,985 exact direct-output matches before any preservation claim.
- [ ] **Step 6: Update** theory and paper documents with the measured result and explicit retrospective-composition boundary.
- [ ] **Step 7: Run** all OR-Debug, TSP scalable and mixed-router tests plus Markdown-link and headline-hash checks.
- [ ] **Step 8: Commit Task 4 files** with message `docs: close mixed skill composition evidence`.
