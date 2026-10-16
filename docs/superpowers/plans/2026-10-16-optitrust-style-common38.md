# OptiTrust-style Common-38 Sensitivity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute and independently audit a paper-based, safely adapted OptiTrust-style row on the frozen common-38 endpoint.

**Architecture:** A pure nine-slot runtime produces decomposition, reflected decomposition, formulation, reflected formulation and five language-conditioned `milp-v1` candidates. The existing durable gateway and trusted solver execute the frozen plan; a separate controller publishes only body-free aggregates and an audit reconstructs them without new model calls.

**Tech Stack:** Python 3.11, `unittest`, SQLite formal gateway, strict JSON Schema/`milp-v1`, trusted Gurobi CLI 13.0.1, DeepSeek-V4-Flash through AntChat.

**Spec:** `docs/superpowers/specs/2026-10-16-optitrust-style-common38-design.md`

## Global Constraints

- Label every artifact `OptiTrust-style-safe-sidecar`; never call it official OptiTrust reproduction.
- Use exactly nine logical slots per identity and languages `Pyomo`, `Gurobipy`, `DOcplex`, `CVXPY`, `PySCIPOpt` in that order.
- Require a strict objective majority of at least three of five with `rtol=1e-5`, `atol=1e-6`.
- Keep concurrency at five and at most three recorded physical attempts per request.
- Do not execute generated Python or expose bodies, objective values, points, references or credentials publicly.
- Load evaluator-only references only after all nine responses and candidate solves have terminated.
- Preserve every failure in the 38-record denominator.

## Review Focus

- A malformed decomposition/formulation JSON must become a method failure without shifting later slot identities; Task 1 tests this.
- Three numerically matching objectives plus two invalid candidates must form a majority; two-versus-two-versus-one must not; Task 1 tests both.
- A resumed slot with altered language, stage or public-input hash must fail closed; Task 2 tests this.
- One exhausted request must yield infrastructure-unavailable for that identity while independent cells continue; Task 3 tests this.
- Public results must contain no request/response text, model bodies, objectives, points or evaluator answers; Tasks 3 and 4 test recursive key/content scans.

---

### Task 1: Pure OptiTrust-style runtime

**Files:**
- Create: `tests/test_optitrust_style_runtime.py`
- Create: `llm4or/optitrust_style_runtime.py`

**Interfaces:**
- Consumes: public benchmark packet; gateway `register`/`request`; trusted solver callable.
- Produces: `stage_payload(public, slot, state) -> dict`, `strict_majority(candidates, rtol, atol) -> dict`, and `run_optitrust_style(public, gateway, scope, replicate, token_cap, solver, solver_config, reference_loader) -> dict`.

- [ ] **Step 1: Write failing tests** for nine fixed stages, original-problem access at every stage, five exact language contexts, strict majority, no-majority, malformed output, candidate schema rejection and reference loading after the final request.
- [ ] **Step 2: Run** `python3 -m unittest tests.test_optitrust_style_runtime` and verify failures are caused by the missing module/API.
- [ ] **Step 3: Implement** the minimal pure runtime, paraphrased instructions, strict schemas and post-inference reference comparison.
- [ ] **Step 4: Run** the targeted test and verify all cases pass.
- [ ] **Step 5: Commit** runtime and tests.

### Task 2: Formal gateway authorization for nine slots

**Files:**
- Modify: `tests/test_formal_preparation.py`
- Modify: `llm4or/formal_gateway.py`

**Interfaces:**
- Consumes: `fresh_common_external` plan with method name `OptiTrustStyle` and `stage_slots`.
- Produces: fail-closed `validate_fresh_external_payload` support for the exact slot/stage/language mapping.

- [ ] **Step 1: Add failing tests** that accept all nine exact payloads and reject stage drift, language drift, public hash drift, slot reuse and extra context fields.
- [ ] **Step 2: Run** the exact new test cases and verify expected validation failures.
- [ ] **Step 3: Implement** the `OptiTrustStyle` validation branch without weakening Base/BIND/CoE checks.
- [ ] **Step 4: Run** the targeted tests plus all existing formal gateway tests.
- [ ] **Step 5: Commit** gateway support and tests.

### Task 3: Frozen common-38 controller and scorer

**Files:**
- Create: `tests/test_fresh_common38_optitrust_style.py`
- Create: `llm4or/fresh_common38_optitrust_style.py`

**Interfaces:**
- Consumes: frozen common-38 bundle, Task 1 runtime, Task 2 gateway, trusted Gurobi CLI.
- Produces: `build_plan`, `authorization`, `run_plan`, `load_cells`, `ledger_summary`, `score_cells`, exclusive publisher and body-free result.

- [ ] **Step 1: Add failing tests** for 38 bindings, nine-call budget, concurrency five, plan reconstruction, checkpoint reuse, independent failure continuation, denominator retention and recursive privacy exclusions.
- [ ] **Step 2: Run** `python3 -m unittest tests.test_fresh_common38_optitrust_style` and verify missing implementation failures.
- [ ] **Step 3: Implement** the controller by following existing Base/CoE durable patterns while keeping the new method boundary explicit.
- [ ] **Step 4: Run** Task 3 tests and the existing common-38 Base/BIND/CoE suites.
- [ ] **Step 5: Commit** controller and tests.

### Task 4: Freeze, run, score and independent-audit entrypoints

**Files:**
- Create: `scripts/freeze_fresh_common38_optitrust_style.py`
- Create: `scripts/run_fresh_common38_optitrust_style.py`
- Create: `scripts/score_fresh_common38_optitrust_style.py`
- Create: `scripts/audit_fresh_common38_optitrust_style.py`
- Modify: `tests/test_fresh_common38_optitrust_style.py`

**Interfaces:**
- Consumes: Task 3 plan/controller and private ledger.
- Produces: exclusive plan/authorization/result/audit artifacts and `--check` audit mode.

- [ ] **Step 1: Add failing CLI/audit tests** for exclusive writes, check-mode byte identity, zero-network audit, ledger totals and body-free output.
- [ ] **Step 2: Run** the exact tests and verify failure before scripts exist.
- [ ] **Step 3: Implement** four small entrypoints; the audit rebuilds the plan, cells, score and accounting and records zero new calls.
- [ ] **Step 4: Run** targeted tests, compile checks and JSON parsing.
- [ ] **Step 5: Commit** entrypoints and tests.

### Task 5: Freeze and dry-run the exact experiment

**Files:**
- Create ignored private source checkout under `data/raw/`.
- Create: `experiments/fresh_common38_optitrust_style_plan_v1_20261016.json`
- Create: `experiments/fresh_common38_optitrust_style_authorization_v1_20261016.json`
- Create ignored offline simulation under `results/private/`.

**Interfaces:**
- Consumes: exact pinned Text2Opt source revision and completed implementation.
- Produces: immutable plan hash, authorization and no-network 38-cell simulation evidence.

- [ ] **Step 1: Materialize** the exact ignored source checkout and prepared manifest from the authoritative private workspace.
- [ ] **Step 2: Freeze** the plan once and record its digest, 38 identities, 342 logical calls, 1,026 physical-attempt ceiling and concurrency five.
- [ ] **Step 3: Run** an offline deterministic gateway simulation covering all terminal and restart paths without model/API calls.
- [ ] **Step 4: Verify** plan reconstruction, solver pin, source hashes, privacy scans and full targeted suite.
- [ ] **Step 5: Commit** only public plan/authorization and verification changes; keep bodies ignored.

### Task 6: Live execution and independent reconstruction

**Files:**
- Create ignored live run under `results/private/fresh_common38_optitrust_style_v1/`.
- Create: `experiments/fresh_common38_optitrust_style_result_v1_20261016.json`
- Create: `experiments/fresh_common38_optitrust_style_audit_v1_20261016.json`

**Interfaces:**
- Consumes: Task 5 frozen plan and existing provider profile.
- Produces: 38 terminal cells, body-free result and read-only independent audit.

- [ ] **Step 1: Run** the resumable controller at concurrency five; continue after item-level exhaustion and stop only on declared global faults.
- [ ] **Step 2: Inspect** progress and ledger read-only until all 38 identities are terminal.
- [ ] **Step 3: Publish** the body-free result exactly once.
- [ ] **Step 4: Run** the independent audit with zero new provider calls and verify exact result/accounting reconstruction.
- [ ] **Step 5: Commit** public result and audit.

### Task 7: Common-protocol synthesis and paper evidence

**Files:**
- Create: `experiments/fresh_common38_optitrust_style_synthesis_20261016.json`
- Create: `docs/OPTITRUST_STYLE_COMMON38_RESULTS_20261016.md`
- Modify: `manuscript/MANUSCRIPT_DRAFT.md`
- Modify: `manuscript/MANUSCRIPT_EVIDENCE_AUDIT.md`
- Modify: `docs/TOP_CONFERENCE_METHOD_ROADMAP.md`
- Modify: `experiments/external_baseline_evidence_ledger_20261014.json`
- Modify: `experiments/paper_evidence_manifest_20261015.json`
- Modify: `experiments/goal_completion_audit_20261015.json`

**Interfaces:**
- Consumes: audited OptiTrust-style result and frozen current/Base/BIND/CoE-safe results.
- Produces: paired corrections/regressions, bounded narrative, updated evidence hashes and honest remaining-goal decision.

- [ ] **Step 1: Write failing evidence tests** for the new row, labels, boundaries and manifest hash binding.
- [ ] **Step 2: Build** paired statistics without retuning any baseline or opening new outcomes.
- [ ] **Step 3: Update** paper text and tables while preserving official-artifact unavailability and unequal-budget caveats.
- [ ] **Step 4: Run** the canonical 79-test public contract, new tests, deterministic checks, JSON parse, sensitive scan and `git diff --check`.
- [ ] **Step 5: Commit and publish** through the history-safe public-main workflow; leave DOI as an external archival step.

## Autonomous execution choice

The user has already selected native autonomous execution and delegated
intermediate approvals. Implement this plan in the current isolated worktree
with `superpowers:executing-plans`; do not stop for another confirmation.
