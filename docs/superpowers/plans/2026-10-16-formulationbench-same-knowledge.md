# FormulationBench Same-Knowledge Mechanism Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed FormulationBench custodian and deterministic same-fact dual-view experiment, then freeze an 89-pair prospective comparison only after offline and synthetic capacity gates pass.

**Architecture:** A source validator creates disjoint inference, metadata and evaluator projections from one fixed upstream commit. A canonical fact graph feeds Flat-K and PCK-K serializers whose hash multisets must match. A short-output controller reuses the existing durable ledger and isolated `.venv-preparation` transport worker; labels remain evaluator-only until all predictions are terminal.

**Tech Stack:** Python 3.11 controller, Python 3.10 OpenAI/httpx transport worker, canonical JSON, SHA-256, SQLite request ledger, existing atomic publisher, unittest, and the fixed FormulationBench Git snapshot.

**Spec:** `docs/superpowers/specs/2026-10-16-formulationbench-same-knowledge-design.md`

## Global Constraints

- Never print or publish task bodies, parameter/data values, formulation algebra, labels, solutions, code bodies, Lean proof bodies, requests, responses or credentials.
- Do not run an API, model, solver, Lean process, native evaluator or VM before its named gate opens.
- Use all 89 official pairs; no post-audit or post-outcome subset selection.
- Flat-K and PCK-K must bind identical semantic fact-hash multisets.
- One fingerprint produces at most one physical send at a time; retries remain ledgered.
- The failed OptiTrust expanded run remains stopped and is never resumed by this plan.

## Review Focus

- A pair with a proof file must not leak proof presence through file counts, paths, ordering, byte counts or metadata.
- Different formulation orderings must canonicalize to the same fact graph without changing variable or constraint scope.
- Parameter maps with nested/indexed domains must preserve direction and quantifier coverage in both views.
- A failed whole-source validation or atomic publication must leave no partial inference/evaluator root.
- Retry recovery must reuse completed fingerprints and must not duplicate a physical send.

---

### Task 1: Fixed-source body-free materialization audit

**Files:**
- Create: `llm4or/formulationbench_custody.py`
- Create: `tests/test_formulationbench_custody.py`
- Create: `scripts/build_formulationbench_custody.py`

**Interfaces:**
- Consumes: fixed repository root, commit and tree strings.
- Produces: `census_source(root, identity) -> dict` and a CLI `--schema-census` mode that emits only path/type/count/hash aggregates.

- [x] Write failing synthetic tests for exact 20/109/89-style directory relationships, unknown files, links, path escape, missing pair sides, duplicate identities and body-free error messages.
- [x] Run the focused tests and confirm they fail before implementation.
- [x] Implement the strict source census and CLI without loading solutions, labels or proof bodies.
- [x] Run focused tests, compileall and `git diff --check`; verify all pass.
- [x] Commit the source validator and body-free fixed-source audit.

### Task 2: Three-projection fail-closed custodian

**Files:**
- Modify: `llm4or/formulationbench_custody.py`
- Modify: `tests/test_formulationbench_custody.py`
- Modify: `scripts/build_formulationbench_custody.py`

**Interfaces:**
- Consumes: Task 1 validated source.
- Produces: `build_custody_bundle(root, identity) -> dict[str, bytes]`, `publish_custody_bundle(...)`, and CLI `--write`/`--check` modes.

- [x] Add failing fixtures proving inference excludes solutions, labels, proof bodies and proof-presence metadata while evaluator preserves exact private bytes.
- [x] Add failure tests for incomplete source, drift, collisions, symlinked destinations and interrupted publication.
- [x] Implement canonical projections using the existing atomic publisher.
- [x] Verify deterministic write/check replay and zero partial output on every failure.
- [x] Commit the custodian and fixed-source public audit.

### Task 3: Canonical fact graph and dual serializers

**Files:**
- Create: `llm4or/formulationbench_fact_graph.py`
- Create: `tests/test_formulationbench_fact_graph.py`

**Interfaces:**
- Consumes: one inference pair from Task 2.
- Produces: `parse_fact_graph(pair) -> FactGraph`, `serialize_flat(graph) -> View`, `serialize_pck(graph) -> View`, and `verify_same_facts(flat, pck) -> None`.

- [x] Write failing tests for scalar/indexed variables, bounds, integrality, objective sense, constraint scope, nested parameter maps and reordered source objects.
- [x] Test that any added, missing or changed fact causes the same-knowledge verifier to fail.
- [x] Implement canonical typed nodes/edges and both serializers.
- [x] Verify byte determinism and exact fact-hash multiset identity over all 89 pairs.
- [x] Commit the serializer layer and full-population audit.

### Task 4: Typed short-output controller and durable audit

**Files:**
- Create: `llm4or/formulationbench_same_knowledge.py`
- Create: `tests/test_formulationbench_same_knowledge.py`
- Create: `scripts/freeze_formulationbench_capacity_canary.py`
- Create: `scripts/run_formulationbench_capacity_canary.py`
- Create: `scripts/audit_formulationbench_capacity_canary.py`

**Interfaces:**
- Consumes: Task 3 views and the existing isolated OpenAI/httpx worker.
- Produces: strict response validator, ledgered two-arm scheduler, body-free progress/result/audit and a four-pair synthetic capacity plan.

- [x] Add tests for strict JSON, unknown fact hashes, missing obligations, duplicate sends, checkpoint reuse, retry exhaustion and global halts.
- [x] Implement the controller with 1,024 completion tokens, concurrency five and three ledgered attempts.
- [x] Freeze the four-pair synthetic canary before any provider call.
- [x] Run offline reconstruction only; do not dispatch until hashes, credentials isolation and zero-answer checks pass.
- [ ] Commit the frozen canary.

### Task 5: Capacity gate and full 89-pair freeze

**Files:**
- Create: `experiments/formulationbench_capacity_canary_result_20261016.json`
- Create: `docs/FORMULATIONBENCH_CAPACITY_CANARY_20261016.md`
- Create: `scripts/freeze_formulationbench_same_knowledge.py`

**Interfaces:**
- Consumes: Task 4 canary and Task 2 complete custody bundle.
- Produces: terminal capacity decision and, only on pass, a frozen 178-request full plan.

- [x] Run the synthetic canary through the preparation transport worker and audit every ledger slot.
- [x] If any capacity condition fails, publish the negative gate and stop without creating a full plan. (Not activated: the gate passed.)
- [x] If it passes, freeze all 89 opaque pair identities, both view hashes, model, prompt, budgets, concurrency, retry policy and statistical gate.
- [x] Independently reconstruct the plan and verify evaluator paths remain absent.
- [ ] Commit the capacity evidence and optional full plan.

### Task 6: Prospective execution, evaluator-only scoring and paper synchronization

**Files:**
- Create: `scripts/run_formulationbench_same_knowledge.py`
- Create: `scripts/evaluate_formulationbench_same_knowledge.py`
- Create: `scripts/audit_formulationbench_same_knowledge.py`
- Create: terminal machine/human result artifacts under `experiments/` and `docs/`.
- Modify: paper evidence manifest, goal audit, manuscript evidence audit and method roadmap only after terminal scoring.

**Interfaces:**
- Consumes: Task 5 frozen full plan and private evaluator projection.
- Produces: full-denominator paired result, independent reconstruction audit and synchronized claim boundary.

- [x] Execute with checkpoint-preserving recovery; never change cohort, prompt, model, budget or endpoint after first send.
- [x] Join predictions to labels only after all 178 logical slots are terminal.
- [x] Compute full-denominator accuracy, subgroup accuracy, corrections/regressions, exact McNemar probability and Wilson intervals.
- [x] Audit plan, ledger, responses and aggregate reconstruction without publishing bodies or labels.
- [ ] Synchronize the paper with a positive or negative mechanism conclusion exactly as the prespecified gate dictates.
- [ ] Run the complete credential-free public-integrity entrypoint and commit the terminal evidence.
