# Release-safe Evidence Projections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace four restricted paper-evidence bindings with deterministic metadata-only projections without changing any paper endpoint or assertion.

**Architecture:** One focused Python module implements four pure projection functions, a deny-list validator, canonical hashing, and an exclusive publisher. A small CLI materializes or checks the fixed artifacts; the paper manifest is rebound only after independent tests reconstruct every current claim.

**Tech Stack:** Python 3 standard library (`json`, `hashlib`, `os`, `pathlib`, `tempfile`, `argparse`), `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-15-release-safe-projections-design.md`

## Global Constraints

- No API, model, solver, native-evaluator, VM, network, credential, request-body, response-body, or evaluator-only-answer access.
- Never display or persist task text, repair identity/object, solver points, or solve objective in a projection.
- Preserve all 408 paper-manifest assertions and 15 global boundaries.
- Fail closed on source-hash mismatch, duplicate identity, invalid path, collision, symlink, missing field, or forbidden output key.
- Do not modify or delete the four frozen source artifacts.

## Review Focus

- A forbidden key nested in a list or mapping must be rejected recursively.
- Hashing must be invariant to mapping insertion order but sensitive to list order and value changes.
- Duplicate record identities must fail before output publication.
- A partially occupied terminal path or symlink must never be overwritten.
- Public artifacts must remain sufficient to recompute every manifest assertion after rebinding.

---

### Task 1: Pure projection and validation module

**Files:**
- Create: `tests/test_release_safe_projections.py`
- Create: `llm4or/release_safe_projections.py`

**Interfaces:**
- Produces: `canonical_bytes(value) -> bytes`, `project_mixed_bundle(source, source_bytes) -> dict`, `project_or_debug_evaluation(source, source_bytes) -> dict`, `project_or_debug_outputs(source, source_bytes) -> dict`, `project_mixed_outputs(source, source_bytes) -> dict`, `validate_public_projection(value) -> None`.

- [ ] Write tests for source hashes, exact counts, forbidden-key recursion, duplicate identities, deterministic bytes, and all four projection schemas.
- [ ] Run `python3 -m unittest tests.test_release_safe_projections` and verify the new module import fails.
- [ ] Implement the minimal pure functions and validators.
- [ ] Run the focused tests and verify they pass.
- [ ] Commit the module and tests.

### Task 2: Exclusive materializer and fixed artifacts

**Files:**
- Modify: `tests/test_release_safe_projections.py`
- Modify: `llm4or/release_safe_projections.py`
- Create: `scripts/build_release_safe_projections.py`
- Create: `experiments/public_projections/mixed_skill_confirmation_bundle_projection_20261015.json`
- Create: `results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json`
- Create: `results/public_projections/or_debug_confirmation_method_outputs_projection_20261015.json`
- Create: `results/public_projections/mixed_skill_confirmation_outputs_projection_20261015.json`

**Interfaces:**
- Consumes: Task 1 projection functions.
- Produces: `publish_exclusive(path, value, repo_root) -> str` and CLI modes `--write` / `--check`.

- [ ] Add failing tests for root containment, symlink rejection, terminal collision, identical check mode, file fsync and deterministic materialization.
- [ ] Run the focused tests and verify the new publisher tests fail.
- [ ] Implement the publisher and fixed CLI.
- [ ] Run the CLI in write mode once, then check mode, and verify byte-identical outputs.
- [ ] Run focused tests and commit code plus generated projections.

### Task 3: Rebind paper evidence and release audits

**Files:**
- Modify: `tests/test_release_safe_projections.py`
- Modify: `experiments/paper_evidence_manifest_20261015.json`
- Modify: `manuscript/MANUSCRIPT_EVIDENCE_AUDIT.md`
- Modify: `experiments/goal_completion_audit_20261015.json`
- Modify: `docs/GOAL_COMPLETION_AUDIT_20261015.md`
- Create: `experiments/release_projection_rebinding_audit_20261015.json`
- Create: `docs/RELEASE_PROJECTION_REBINDING_AUDIT_20261015.md`

**Interfaces:**
- Consumes: Task 2 fixed projections.
- Produces: a paper manifest with 69 safe bound paths, unchanged 408 assertions and 15 boundaries, plus a machine/human rebinding audit.

- [ ] Add a failing test that rejects any of the four old restricted paths in the paper manifest and recomputes all affected assertions from projections.
- [ ] Run the focused test and verify it fails against the old bindings.
- [ ] Rebind the manifest, update exact hashes and write the audit pair.
- [ ] Run focused tests, full manifest/goal/citation validation and `git diff --check`.
- [ ] Commit the rebinding and synchronized evidence documents.

### Task 4: Final branch verification

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/PROJECT_HANDOFF.md`

**Interfaces:**
- Consumes: Tasks 1--3.
- Produces: current handoff hashes and a verified projection status.

- [ ] Run all projection tests plus the targeted paper-evidence tests named by the current manifest.
- [ ] Verify 69/69 manifest paths are tracked, zero restricted source paths remain bound, 408 assertions and 15 boundaries pass, and 18/18 citations close.
- [ ] Run secret/body-key scans over all bound paths without displaying values.
- [ ] Update handoff files with final hashes, run `git diff --check`, and commit.
