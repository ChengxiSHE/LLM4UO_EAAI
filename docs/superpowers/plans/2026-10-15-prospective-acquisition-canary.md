# Prospective Acquisition Canary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, freeze, run, and audit the approved eight-pair flat-versus-separating-witness automatic-acquisition canary without disclosing the authored winner or turning the canary into a publication-level efficacy claim.

**Architecture:** A pure module binds the 64-member typed count grammar, selects one historical model proposal and seven deterministic synthetic rejected seeds, constructs one six-fact verifier ledger, and derives a balanced shared teacher trace. A freezer serializes three fact-equivalent rounds for both arms and pins every input. A bounded concurrent runner reserves each request fingerprint before one physical send, stores private raw evidence, and emits a body-free terminal report. A separate offline audit recomputes membership, packet equivalence, request accounting, and the engineering progression gate.

**Tech Stack:** Python 3 standard library, existing `llm4or` canonical JSON/hash utilities, existing AntChat DeepSeek-V4-Flash request contract and isolated transport, `unittest`.

**Spec:** `docs/PROSPECTIVE_RESEARCH_PROGRAM_DECISION_20261015.md`

## Global Constraints

- Use `https://antchat.alipay.com/v1`, model `DeepSeek-V4-Flash`, temperature zero, and API concurrency five.
- Freeze exactly eight proposal units: one historical model-generated typed proposal plus seven deterministic synthetic rejected grammar members, always labeled by provenance.
- Compare `flat` and `separating_witness` on identical fact IDs, candidate schema, maximum three rounds, output ceiling, attempt policy, and token reservation rule.
- Freeze six answer-free verifier facts before dispatch; group two new facts per round. The shared minimax teacher order is computed once and used by both arms.
- Do not expose the authored winner object, winner hash, minimum repair, benchmark answer, solved vector, evaluator-only identity, request body, response body, or credential in public artifacts.
- Reserve each request key durably before sending. A request key receives at most one physical send; an uncertain or failed send remains terminal and is never replayed.
- Permit at most 48 logical requests and 48 physical attempts, with at most five active requests. There are no retries or result-driven reruns.
- Keep unavailable, invalid, and exhausted cells in the eight-pair denominator. The engineering gate is at least two treatment-only unit wins, zero flat-only unit wins, and no global safety failure; it is not a significance result.
- No solver, native evaluator, VM, library promotion, benchmark-accuracy claim, Stage 2 expansion, or Stage 3/4 execution is authorized by this plan.

## Review Focus

- A selected synthetic seed unexpectedly passes the verifier: freezing must fail rather than silently replace it after inspecting treatment outcomes.
- A treatment packet contains a fact ID absent from its flat mate, or the statements differ: packet equivalence must fail before any request.
- Two logical cells map to one request key: the plan must reject duplicate fingerprints rather than rely on the runtime cache.
- A reservation exists without a terminal response after interruption: resume must mark that cell unavailable and never resend it.
- A provider envelope reports another model, inconsistent usage, a tool call, credential echo, or malformed content: halt globally and preserve already completed cells.

---

### Task 1: Pure canary population and shared teacher

**Files:**
- Create: `llm4or/prospective_acquisition_canary.py`
- Test: `tests/test_prospective_acquisition_canary.py`

**Interfaces:**
- Consumes: `typed_count_skill.enumerate_candidates()`, `validate_candidate()`, `verify_candidate()`, and the bound historical typed proposal.
- Produces: `select_units(model_proposal, public_cases) -> list[dict]`, `build_fact_ledger() -> list[dict]`, `build_teacher_trace(facts) -> list[dict]`, `response_schema() -> dict`, and `build_payload(unit, arm, round_number, facts, trace) -> dict`.

- [ ] **Step 1: Write failing tests** for exact 8-unit provenance/uniqueness/rejection, 64→1 teacher contraction, identical fact IDs and statements across arms, no prohibited winner/answer fields, strict arm/round validation, and deterministic hashes.
- [ ] **Step 2: Run tests to verify RED**

  Run: `python3 -m unittest -v tests.test_prospective_acquisition_canary`
  Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement the pure module** with exact signatures above. Synthetic units are the first seven failing non-model candidates under candidate SHA-256 ordering; this pre-treatment eligibility rule is fixed and recorded. The six facts each bind one typed grammar choice, but no payload contains the complete winner object or its hash. The teacher minimizes the largest retained/eliminated cell with fact-SHA tie breaking.
- [ ] **Step 4: Run tests to verify GREEN**

  Run: `python3 -m unittest -v tests.test_prospective_acquisition_canary`
  Expected: all tests pass.

- [ ] **Step 5: Commit only Task 1 files**

### Task 2: Content-addressed Stage 0 freezer

**Files:**
- Create: `scripts/freeze_prospective_acquisition_canary.py`
- Create: `tests/test_freeze_prospective_acquisition_canary.py`
- Create at runtime: `experiments/prospective_acquisition_canary_plan.json`
- Create at runtime: `results/private/prospective_acquisition_canary_payloads.json`

**Interfaces:**
- Consumes: Task 1 pure functions and the approved program decision artifact.
- Produces: `build_bundle(root) -> dict`, `build_plan(root, bundle, created_at) -> dict`, and `freeze(root) -> dict`.

- [ ] **Step 1: Write failing tests** for exact 8×2×3 cells, paired fact equivalence, 48 unique request keys, model/base URL/concurrency/request ceilings, source pins, approval binding, no prohibited public fields, exclusive output creation, and mutation rejection.
- [ ] **Step 2: Run tests to verify RED**

  Run: `python3 -m unittest -v tests.test_freeze_prospective_acquisition_canary`
  Expected: import failure because the freezer does not exist.

- [ ] **Step 3: Implement the freezer**. Payloads are private; the public plan contains only cell identity, request key, payload hash, reserved-token ceiling, source pins, limits, and claim boundaries. Freeze writes with exclusive creation and fsync.
- [ ] **Step 4: Run tests to verify GREEN**

  Run: `python3 -m unittest -v tests.test_freeze_prospective_acquisition_canary`
  Expected: all tests pass.

- [ ] **Step 5: Commit only Task 2 source and test files**

### Task 3: Single-send concurrent runner

**Files:**
- Create: `scripts/run_prospective_acquisition_canary.py`
- Create: `tests/test_run_prospective_acquisition_canary.py`

**Interfaces:**
- Consumes: frozen plan and private bundle from Task 2 plus `antchat_object_pilot_transport_v2.request_once`.
- Produces: `execute(root, request_once=...) -> dict`, private per-cell reservations/envelopes/candidates, and `results/prospective_acquisition_canary_result.json` containing no bodies.

- [ ] **Step 1: Write failing tests** for peak concurrency five, round barriers, skip-after-success, one send per request key, no resend after orphan reservation, local invalid-candidate continuation, transport-failure continuation, global-halt propagation, exact usage accounting, immutable terminal closure, and no response/request bodies in the public report.
- [ ] **Step 2: Run tests to verify RED**

  Run: `python3 -m unittest -v tests.test_run_prospective_acquisition_canary`
  Expected: import failure because the runner does not exist.

- [ ] **Step 3: Implement the runner** using a five-worker `ThreadPoolExecutor`, exclusive reservation files before dispatch, one physical attempt per request key, provider-envelope validation through the existing contract, and round-level durable progress. A global safety error stops future scheduling; local content/transport failures remain per-cell terminal.
- [ ] **Step 4: Run tests to verify GREEN**

  Run: `python3 -m unittest -v tests.test_run_prospective_acquisition_canary`
  Expected: all tests pass.

- [ ] **Step 5: Commit only Task 3 source and test files**

### Task 4: Independent offline audit and progression decision

**Files:**
- Create: `scripts/audit_prospective_acquisition_canary.py`
- Create: `tests/test_audit_prospective_acquisition_canary.py`
- Create at runtime: `results/prospective_acquisition_canary_audit.json`

**Interfaces:**
- Consumes: frozen plan, private bundle, terminal result, reservations, envelopes and candidates.
- Produces: `build_audit(root) -> dict` with per-unit paired outcomes, treatment-only/flat-only/both/neither counts, gate result, source/payload/accounting verification, and strict non-claims.

- [ ] **Step 1: Write failing tests** for recomputed candidate verification, full eight-pair denominator, exact paired cell joins, tamper rejection, gate arithmetic, public privacy, and explicit canary-only claim boundaries.
- [ ] **Step 2: Run tests to verify RED**

  Run: `python3 -m unittest -v tests.test_audit_prospective_acquisition_canary`
  Expected: import failure because the audit module does not exist.

- [ ] **Step 3: Implement the offline audit** and exclusive publisher.
- [ ] **Step 4: Run tests to verify GREEN**

  Run: `python3 -m unittest -v tests.test_audit_prospective_acquisition_canary`
  Expected: all tests pass.

- [ ] **Step 5: Commit only Task 4 source and test files**

### Task 5: Freeze, execute, audit, and update the paper boundary

**Files:**
- Modify after terminal evidence: `manuscript/MANUSCRIPT_DRAFT.md`
- Modify after terminal evidence: `manuscript/MANUSCRIPT_EVIDENCE_AUDIT.md`
- Modify after terminal evidence: `experiments/paper_evidence_manifest_20261015.json`
- Modify after terminal evidence: `experiments/goal_completion_audit_20261015.json`
- Modify after terminal evidence: `docs/GOAL_COMPLETION_AUDIT_20261015.md`
- Modify after terminal evidence: `AGENTS.md`
- Modify after terminal evidence: `docs/PROJECT_HANDOFF.md`

**Interfaces:**
- Consumes: Tasks 1–4 and the frozen terminal canary audit.
- Produces: one immutable canary result and an evidence-bounded decision either to preregister Stage 2 or to retain the authored-skill fallback.

- [ ] **Step 1: Run the combined preflight suite**

  Run: `python3 -m unittest -v tests.test_prospective_acquisition_canary tests.test_freeze_prospective_acquisition_canary tests.test_run_prospective_acquisition_canary tests.test_audit_prospective_acquisition_canary`
  Expected: all tests pass.

- [ ] **Step 2: Freeze Stage 0–1** and record exact plan/bundle hashes. Do not edit frozen code or inputs afterward.
- [ ] **Step 3: Execute the frozen plan** with the AntChat DeepSeek-V4-Flash endpoint and concurrency five. Do not retry any fingerprint.
- [ ] **Step 4: Run the independent offline audit** and verify all source, payload, accounting, privacy, and gate assertions.
- [ ] **Step 5: Update manuscript and manifests** according to the observed result. If the gate fails, preserve the negative result and do not open Stage 2. If the gate passes, create a separate Stage 2 implementation plan; do not treat the canary as confirmatory evidence.
- [ ] **Step 6: Run final verification**: focused suite, paper/goal hash audit, citation closure, and `git diff --check`.

