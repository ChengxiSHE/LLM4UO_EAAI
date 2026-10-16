# MIPLIB-NL Answer-Blind Custodian Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and rehearse a fail-closed three-projection custodian that prevents MIPLIB-NL evaluator material from reaching inference workers.

**Architecture:** A standard-library-only module validates the fixed raw tree and constructs one immutable file bundle containing disjoint inference, answer-free metadata, evaluator, and private-ledger projections. The existing atomic publisher commits the bundle without replacement; a CLI supports body-free schema census, write, and read-only check modes. The repository receives only a body-free audit after a 223-instance zero-model/zero-solver rehearsal.

**Tech Stack:** Python 3.11 standard library, `unittest`, existing `llm4or.atomic_publisher`, canonical JSON and SHA-256.

**Spec:** `docs/superpowers/specs/2026-10-16-miplib-nl-custodian-design.md`

## Global Constraints

- Fixed upstream commit: `9f14ad1782eaa547f7dad982d1edb186321ffd88`.
- Fixed dataset tree: `96132c089bbead0909c1ab9e55df59195ba8ec6f`.
- No API, model, solver, native evaluator, VM, credential, or reference-code execution.
- Raw task bodies, data values, optimal values, model text, and code never enter public artifacts or command output.
- Unknown schema, non-finite JSON, links, special files, path escape, undeclared data, unsafe CSV headers, drift, or collision fails closed.
- Private outputs stay outside the tracked release; only body-free aggregate evidence is added to the repository.

## Review Focus

- JSON duplicate keys or non-finite values must fail before projection; Task 1 pins both.
- A declared data path whose lexical form is safe but resolves through a symlink must fail; Task 1 pins this.
- Nested file metadata that uses answer-like keys must never be copied; Task 2 pins recursive rejection.
- A crash or second writer must not expose a mixed inference/evaluator generation; Task 3 pins atomic publication and collision behavior.
- Check mode must be read-only and detect one-byte drift without echoing the changed value; Task 4 pins this.

---

### Task 1: Strict source parsing, schema census, and path boundary

**Files:**
- Create: `llm4or/miplib_nl_custody.py`
- Create: `tests/test_miplib_nl_custody.py`

**Interfaces:**
- Consumes: raw dataset root plus fixed commit/tree strings.
- Produces: `CustodyError`, `SourceIdentity`, `load_instance(path: Path) -> dict[str, Any]`, `build_schema_census(dataset_root: Path, source: SourceIdentity) -> dict[str, Any]`, and safe-file helpers used by Task 2.

- [ ] **Step 1: Write failing tests for duplicate JSON keys, NaN/Infinity, exact top-level keys, missing required files, path escape, symlink traversal, special files, duplicate normalized data paths, and the body-free schema census.**

- [ ] **Step 2: Run `python3 -m unittest tests.test_miplib_nl_custody -v`; verify failures are missing-interface failures rather than passing accidentally.**

- [ ] **Step 3: Implement the minimal parser, type census, opaque identity, regular-file/no-follow checks, and confined path resolver. Error messages contain only opaque IDs and reason codes.**

- [ ] **Step 4: Rerun the Task 1 tests and verify they pass.**

- [ ] **Step 5: Commit `llm4or/miplib_nl_custody.py` and `tests/test_miplib_nl_custody.py` with message `feat: add strict MIPLIB-NL source validator`.**

### Task 2: Three disjoint deterministic projections

**Files:**
- Modify: `llm4or/miplib_nl_custody.py`
- Modify: `tests/test_miplib_nl_custody.py`

**Interfaces:**
- Consumes: Task 1 validators and one complete raw dataset tree.
- Produces: immutable `CustodyBundle(entries: Mapping[str, bytes], public_audit: Mapping[str, Any], private_ledger: Mapping[str, Any])` and `build_custody_bundle(dataset_root: Path, source: SourceIdentity) -> CustodyBundle`.

- [ ] **Step 1: Add failing synthetic-fixture tests showing inference contains only canonical redacted `instance.json` plus declared CSVs, evaluator contains the exact objective/model/code, metadata contains types and counts but no values, and optional `model.md` absence is explicit.**

- [ ] **Step 2: Add failing tests for unknown top-level keys, nested sensitive keys, undeclared files, non-CSV files, unsafe CSV headers, malformed UTF-8, duplicate instance identities, and deterministic rebuilds.**

- [ ] **Step 3: Run the focused test module and verify the new tests fail.**

- [ ] **Step 4: Implement canonical projections, CSV structural counts, recursive sensitive-key validation, private cross-binding ledger, and aggregate public audit.**

- [ ] **Step 5: Run the focused test module and verify all projection and privacy assertions pass.**

- [ ] **Step 6: Commit with message `feat: split MIPLIB-NL inference and evaluator custody`.**

### Task 3: Durable no-clobber bundle publication

**Files:**
- Modify: `llm4or/miplib_nl_custody.py`
- Modify: `tests/test_miplib_nl_custody.py`

**Interfaces:**
- Consumes: Task 2 `CustodyBundle` and existing `llm4or.atomic_publisher.publish_bundle`.
- Produces: `publish_custody_bundle(root: Path, bundle: CustodyBundle) -> PublicationResult` and `check_custody_bundle(root: Path, bundle: CustodyBundle) -> None`.

- [ ] **Step 1: Add failing tests for complete publication, byte-identical replay, collision, failed-validation no-publication, one-byte check drift, symlinked destination, and absence of cross-root links.**

- [ ] **Step 2: Run the focused test module and verify failures.**

- [ ] **Step 3: Implement one atomic multi-file transaction and a strictly read-only comparator that reports only relative safe paths and reason codes.**

- [ ] **Step 4: Run focused tests plus `tests.test_atomic_publisher`; verify all pass.**

- [ ] **Step 5: Commit with message `feat: publish MIPLIB-NL custody bundle atomically`.**

### Task 4: CLI and body-free audit contract

**Files:**
- Create: `scripts/build_miplib_nl_custody.py`
- Modify: `tests/test_miplib_nl_custody.py`

**Interfaces:**
- Consumes: Tasks 1–3 APIs.
- Produces: mutually exclusive `--schema-census`, `--write`, and `--check` CLI modes with explicit `--raw-root`, `--custody-root`, `--source-commit`, `--dataset-tree`, and `--public-audit` arguments.

- [ ] **Step 1: Add failing subprocess tests for each mode, argument rejection, body-free stdout, deterministic public audit bytes, read-only check mode, and drift failure without value disclosure.**

- [ ] **Step 2: Run the focused test module and verify failures.**

- [ ] **Step 3: Implement the CLI and publish the public audit only after the private bundle succeeds.**

- [ ] **Step 4: Run focused tests, compileall, and diff checks; verify all pass.**

- [ ] **Step 5: Commit with message `feat: add MIPLIB-NL custody CLI`.**

### Task 5: Fixed-snapshot zero-model rehearsal and evidence closure

**Outcome:** closed with a source-integrity boundary. The whole-source
rehearsal found 220/223 exact directories and three path-identity mismatches
(five missing declared files and five undeclared materialized files). The
fail-closed publisher emitted no custody bundle and no experiment was
dispatched. The implementation is verified; the current upstream release is
not eligible for this study.

**Files:**
- Create: `experiments/miplib_nl_custody_rehearsal_20261016.json`
- Create: `docs/MIPLIB_NL_CUSTODY_REHEARSAL_20261016.md`
- Modify: `experiments/miplib_nl_same_knowledge_source_gate_20261016.json`
- Modify: `docs/MIPLIB_NL_SAME_KNOWLEDGE_SOURCE_GATE_20261016.md`
- Modify: `experiments/same_knowledge_task_level_study_design_20261016.json`
- Modify: `docs/SAME_KNOWLEDGE_TASK_LEVEL_STUDY_DESIGN_20261016.md`
- Modify: evidence manifests, goal audit, and reconstruction count constants/results only as required by the new bound paths.

**Interfaces:**
- Consumes: fixed upstream snapshot and Task 4 CLI.
- Produces: a private 223-instance custody bundle and a public body-free terminal rehearsal audit; no experiment plan or dispatch authorization.

- [x] **Step 1: Materialize the fixed upstream snapshot in a private temporary root without printing task, data, model, code, or answer bodies. Verify Git commit/tree identities and 223 directories.**

- [x] **Step 2: Run schema census only. If the strict contract fails, inspect only field/type census output, revise the versioned allowlist with synthetic tests, and rerun; never print values.**

- [x] **Step 3: Run `--write` into a new private custody root. The attempt failed before publication at the whole-source materialization gate, so `--check` and terminal-count assertions were correctly not reached.**

- [x] **Step 4: Verify that the failed rehearsal left zero published files and that the body-free failure audit records fixed source identities, aggregate mismatch counts, privacy flags, and zero-call execution fields.**

- [x] **Step 5: Publish the human/machine rehearsal evidence. Mark source materialization and packet completeness failed for the current release; preserve all downstream gates as closed to dispatch.**

- [ ] **Step 6: Run focused tests, the credential-free release-evidence reconstruction, public-integrity entrypoint, JSON validation, compileall, and `git diff --check`.**

- [ ] **Step 7: Commit with message `evidence: close MIPLIB-NL answer-blind custody rehearsal`.**
