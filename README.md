# LLM4UO-EAAI

> **Release scope.** First-party software and machine-readable artifacts are
> licensed under Apache-2.0. Explicitly marked author-owned aggregate Source
> Data and documentation are licensed under CC BY 4.0. Third-party benchmarks,
> the external `solver-in-the-loop` submodule, CoE, and Gurobi remain under
> their own terms; see [`NOTICE`](NOTICE) and [`LICENSE-DATA`](LICENSE-DATA).

Research prototype for **evidence-directed verification and workflow evolution in language-to-optimization modeling**. The system turns a natural-language operations-research problem into a structured LP/IP/MILP model, executes it in a controlled solver, searches for semantic disagreements, applies scoped repairs, and evolves a bounded verification workflow on development families.

The main question is empirical: can executable semantic feedback and guarded workflow evolution improve modeling quality without introducing more regressions than corrections, after controlling for model, information, and token budget?

## Method at a glance

The implementation connects two components:

- **A — executable semantic feedback:** a same-backbone teacher and the current model are compared through aligned variables, feasibility witnesses, objective-preference evidence, and domain checks. Evidence is tied to source clauses; repairs are local and must pass a within-instance gate or roll back.
- **B — bounded workflow evolution:** development traces are used to propose typed local patches to a small control-flow DSL. Candidates are selected on development data, frozen, and evaluated on disjoint operational gate families before inheritance.
- **Full coupling:** paired incumbent/candidate trajectories expose corrections and regressions at the first changed action. This connects A's localized evidence to B's reusable workflow updates.

The formal comparison is `Base`, `SolverRepair`, `A`, `B`, `SimpleAB`, and `Full`. Standard solvers, teachers, binomial tests, and workflow search are not claimed as individually novel. The contribution under test is their evidence-directed connection and its measured behavior.

The later V9 method follows the mechanism evidence from those comparisons. For six Text2Opt families with stable quantitative interfaces, it recognizes the public structure, parses shape-checked tables, instantiates audited formulations, solves them exactly, and otherwise preserves the same Base result. This selective trusted-compilation path is the first method in the project to pass an independent preregistered benchmark-accuracy gate.

## Current state

As of 2026-10-04:

- **V9 independent confirmation passed.** On 400 infrastructure-complete paired Text2Opt records, Base achieved 50.00% benchmark formulation accuracy and V9 achieved 64.75%, an absolute gain of 14.75 percentage points with 59 corrections, 0 regressions, and one-sided exact McNemar `p=1.7347e-18`. Six of seven categories improved and one tied. All preregistered conditions passed.
- The full selected cohort contained 401 records. One Base request was infrastructure-unavailable; V9 compiled and adopted 90 records and preserved Base on 311. Across the original run and final checkpoint-preserving continuation, confirmation used 401 physical attempts, 17,917,504 reserved-or-reported tokens, and no retries. See [`docs/V9_CONFIRMATORY_RESULTS.md`](docs/V9_CONFIRMATORY_RESULTS.md).
- **VERA-Opt automatic harness evolution has now been executed, with mixed confirmatory evidence.** A fixed proposer automatically induced a typed Knapsack compiler skill, and a second failure-driven proposal repaired its only hidden-promotion abstention without changing executable code or reading hidden answers. Generation one improved Base from 85/90 to 90/90 but failed its strict promotion gate. On the 110-record generation-two final cohort, Base scored 101/110 and VERA 110/110; among 107 complete primary pairs the gain was 5.61 points with 6 corrections, 0 regressions, and `p=0.015625`. The preregistered joint gate failed because three Base calls were infrastructure-unavailable and the allocated threshold was `p<=0.0125`. A separately frozen post-lock infrastructure-only sensitivity completed all 110 pairs and yielded 103/110 versus 110/110, 7 corrections, 0 regressions, and `p=0.0078125`; this is sensitivity evidence, not the primary result. See [`docs/VERA_OPT_RESULTS.md`](docs/VERA_OPT_RESULTS.md).
- **A second automatically induced family now shows a large independent accuracy gain.** On hidden BinPacking promotion, Base scored 21/100 and VERA 100/100 (+79 points, 79/0 corrections/regressions, `p=1.65e-24`) and passed every promotion gate. On the untouched 150-record size-extrapolation confirmation, Base scored 2/150 and VERA 139/150 (+91.33 points, 137/0, `p=5.74e-42`), with all 15 size groups positive. The strict joint gate still failed because 11 public inputs triggered safe abstention, violating the precommitted 150/150 coverage condition. See [`docs/VERA_BINPACKING_RESULTS.md`](docs/VERA_BINPACKING_RESULTS.md).

- LP, integer, and mixed-integer sparse models are supported through a structured `milp-v1` contract; arbitrary model-generated Python is never executed.
- Teacher packets, executable differences, scoped repair/rollback, the bounded DSL, two-generation proposal/selection/gating/inheritance, isolated evaluation, a durable API ledger, bounded retries, resumable checkpoints, circuit breaking, and a local progress page are implemented.
- The formal scope covers 1,356 source records, six methods, three request namespaces, and three logical token budgets: 73,224 inference cells. Its global ceilings remain 328,986 requests and 2,927,886,336 reserved-or-reported tokens; retries consume these ceilings rather than expanding them.
- The formal v3 run completed with `DeepSeek-V4-Flash`: all 73,224 matrix cells are present, backed by 19,241 physical attempts and a reconciled durable ledger.
- Result validation found and repaired an evaluation-cache binding defect. The corrected `formal-evaluation-v2` retains model-format failures in the denominator and excludes only 2,926 true infrastructure interruptions. The raw inference artifacts remain unchanged.
- On the locked test block, all six original methods have benchmark formulation accuracy between 51.831% and 51.916%, where accuracy is operationally defined as final objective/status agreement with the published benchmark answer. `Full` equals `SimpleAB`, no evolved workflow differs from its initial program, and the observed discordances are too sparse to support an improvement claim. See the formal validation report before using any result.
- The v4 development diagnostic is complete and closed: 24/24 cells, 35 physical API attempts, no retry or infrastructure failure, but 0 proxy corrections and 1 regression. The failure showed that two same-backbone reviews can agree on the same algebraic mistake and that choosing only between initial/teacher cannot repair cases where both are wrong.
- v5 adds controller-owned semantic contracts for high-confidence indivisible counts, percentage-of-total clauses, and stock-flow balances. Its post-hoc development replay produced 3 corrections and 0 regressions across all 150 development-role records (two operational families). A hash-frozen offline locked evaluation produced two changes in one family, with 0 observable proxy corrections and 0 regressions; one remained proxy-indeterminate. This is a promising development mechanism, not a confirmed benchmark improvement. See the redesign stage report.
- The v5 formulation audit remains a frozen earlier artifact: 13 blinded items across nine operational families, including three changed A/B pairs. It was superseded for the active claim by the broader v6 audit and is not used to tune v6.
- v6 preserves the frozen v5 implementation and adds a separate, fail-closed contract grammar for explicit counts of discrete objects. Development replay improved from v5's 3 corrections to 6 corrections across five families, with 0 regressions. A separately frozen secondary evaluation changed 12 locked records across eight families and produced 4 benchmark-answer corrections, 0 regressions, and 1 indeterminate outcome relative to Base; all four corrections were incremental to v5. Under the fixed 522-record denominator this is a +0.77 percentage-point formulation-accuracy change, but its one-sided exact record-level probability is 0.0625, so it is directional rather than conventionally significant evidence.
- The v6 blind formulation audit is complete. Two context-isolated reviewers independently agreed on all 12 randomized pairs: 11 improvements, 1 unresolved case, and 0 regressions; seven of eight changed families contain an improvement. The frozen targeted-mechanism rule passed without adjudication. Because the audit intentionally contains only changed cases, it supports the repair mechanism rather than estimating whole-benchmark accuracy.
- A fresh label-free check of the 176-record update-gate block found zero v6 model changes, so its labels were not opened. The original 431-record Text2Opt V6 confirmation plan was retired prospectively because none of its public inputs could trigger V6. A grouped replacement split then fixed 70 development and 401 confirmation records before further result access.
- v7's candidate-independent dual-view source ledger completed Stage 1 but added no measured benefit over V6. V8's controller-owned numeric source index accepted five of ten Stage-1 candidates yet produced 0 corrections and 1 regression, showing that coefficient provenance alone does not guarantee formulation completeness.
- V9 replaces free-form model generation with complete-by-construction audited templates on recognized structured families and fails closed to Base elsewhere. Its development and confirmation artifacts, checkpoint recovery, aggregate-only scoring, and claim boundaries are implemented and recorded.
- The next research phase is a fresh-family VERA-Opt confirmation plus official-code external reproduction under one protocol. CoE and BIND source revisions are pinned. BIND now has a hash-bound official-prompt adapter, a durable common-backbone runner, and a no-exec Gurobi path. On the 30-record structured development matrix, BIND improved from 25/30 to 30/30 through five official oracle-repair corrections; V9 also scored 30/30, and the composed wrapper preserved 30/30. CoE's paper/current controllers have 5,508/5,508 exact prompt checks; native development replay scored 2/3 and 3/3. Its completed six-family common-input development run exposed a different weakness: nine of eleven completed outputs were safely interpretable, but eight violated the explicit scalar return contract. These are local development and compatibility findings, not superiority evidence. OptiTrust's arXiv source does not contain the promised runnable supplement, so it is presently unreproducible from official artifacts. Published scores are reproduction targets only and will not be used as empirical comparison rows.
- A bounded, no-exec Gurobi AST translator now supports the BIND/common-Text2Opt execution contract. It compiled 2,067/2,121 official Text2Opt gold programs (97.45%); all 2,067 compiled models were structurally equivalent to the upstream symbolic models. Fifty quadratic programs and four over-limit programs were rejected visibly. The safe CoE path additionally interprets bounded SciPy, NumPy-like array, combinatorial-search, and post-solve return idioms without importing generated modules; exact Gurobi indicator lowering remains fail-closed when finite bounds are unavailable.
- The complete offline suite passes all 416 tests in the pinned Python 3.11.16 environment, including V9 compilation, official BIND/CoE prompt adapters and runtimes, restricted external-code translation, trusted Gurobi command-line solving, automatic typed-skill induction and repair, verified skill-library lineage, backend-neutral fallback, sequential promotion statistics, confirmation statistics, checkpoint recovery, source grounding, solver isolation, and legacy regressions.

Two earlier development probes are complete and closed. S1 used 46 requests / 46,001 tokens on ten easy LP problems; S2 used 15 requests / 32,852 tokens on four more involved continuous LPs. All final models matched the available references, but neither probe showed a quality gain. These small development results do not establish benchmark saturation or method effectiveness.

## Repository map

| Path | Purpose |
| --- | --- |
| [`docs/PROJECT_HANDOFF.md`](docs/PROJECT_HANDOFF.md) | Authoritative continuation state and next action |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Executable method and experimental information boundaries |
| [`docs/SEMANTIC_FEEDBACK.md`](docs/SEMANTIC_FEEDBACK.md) | Semantic-difference, teacher, and two-gate design |
| [`docs/THEORY.md`](docs/THEORY.md) | Assumption-qualified analysis and proof sketches |
| [`docs/NOVELTY_AUDIT.md`](docs/NOVELTY_AUDIT.md) | Prior-art and claim boundaries |
| [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) | Data versions, audit status, family split, and licensing limits |
| [`docs/PILOT_HISTORY.md`](docs/PILOT_HISTORY.md) | S0/S1/S2 history and exact measured outcomes |
| [`docs/FULL_RUN_REVIEW.md`](docs/FULL_RUN_REVIEW.md) | Frozen full-run scope, risks, accounting, and recovery policy |
| [`docs/FORMAL_RESULTS_VALIDATION.md`](docs/FORMAL_RESULTS_VALIDATION.md) | Corrected formal results, integrity checks, and claim boundaries |
| [`docs/TRAJECTORY_DIAGNOSIS_AND_RESEARCH_FRAMEWORK.md`](docs/TRAJECTORY_DIAGNOSIS_AND_RESEARCH_FRAMEWORK.md) | Mechanism analysis and the staged, paper-ready improvement plan |
| [`docs/MECHANISM_REDESIGN_STAGE_REPORT.md`](docs/MECHANISM_REDESIGN_STAGE_REPORT.md) | Executed v2–v9 mechanism trajectory, negative evidence, and confirmed redesign |
| [`docs/V9_TRUSTED_COMPILER.md`](docs/V9_TRUSTED_COMPILER.md) | Frozen V9 mechanism, endpoint, gate, and confirmed outcome |
| [`docs/V9_CONFIRMATORY_RESULTS.md`](docs/V9_CONFIRMATORY_RESULTS.md) | Paper-facing independent result, statistics, cost, and claim boundary |
| [`docs/VERA_OPT_RESULTS.md`](docs/VERA_OPT_RESULTS.md) | Executed automatic skill evolution, promotion/confirmation decisions, infrastructure sensitivity, and claim boundary |
| [`docs/VERA_BINPACKING_RESULTS.md`](docs/VERA_BINPACKING_RESULTS.md) | Second-family automatic induction, passed promotion, untouched confirmation gain, and remaining coverage failure |
| [`docs/METHOD_BASELINE_COMPATIBILITY_AUDIT.md`](docs/METHOD_BASELINE_COMPATIBILITY_AUDIT.md) | Exact Base definition, method scope, wrapper compatibility, and current external-comparison boundary |
| [`docs/EXTERNAL_BASELINE_REPRODUCTION.md`](docs/EXTERNAL_BASELINE_REPRODUCTION.md) | Official-code reproduction classes, pinned artifacts, safety blockers, and common protocol |
| [`docs/TOP_CONFERENCE_METHOD_ROADMAP.md`](docs/TOP_CONFERENCE_METHOD_ROADMAP.md) | Verified recursive harness-evolution design, theory targets, experiments, and go/no-go criteria |
| [`experiments/v5_blind_semantic_audit_protocol.json`](experiments/v5_blind_semantic_audit_protocol.json) | Frozen independent-review design, bindings, decision rules, and claim boundary |
| [`experiments/v6_secondary_evaluation_plan.json`](experiments/v6_secondary_evaluation_plan.json) | Frozen v6 secondary proxy evaluation and success rule |
| [`experiments/v6_blind_semantic_audit_protocol.json`](experiments/v6_blind_semantic_audit_protocol.json) | Frozen independent formulation review for all v6-changed pairs |
| [`results/v6_blind_semantic_audit_summary.json`](results/v6_blind_semantic_audit_summary.json) | Public aggregate of the completed two-reviewer v6 blind audit |
| [`experiments/v7_source_ledger_pilot_plan.json`](experiments/v7_source_ledger_pilot_plan.json) | Frozen two-stage v7 development plan and stopping rules |
| [`data/manifests/text2opt_resource_allocation_v1.json`](data/manifests/text2opt_resource_allocation_v1.json) | Pinned external resource-allocation cohort and leakage checks |
| [`data/manifests/text2opt_template_confirmation_v1.json`](data/manifests/text2opt_template_confirmation_v1.json) | Pinned six-category external confirmation cohort |
| [`experiments/text2opt_confirmation_protocol.json`](experiments/text2opt_confirmation_protocol.json) | Outcome-blind external accuracy endpoint, statistics, multiplicity correction, and success rule |
| [`experiments/external_baseline_reproduction_manifest.json`](experiments/external_baseline_reproduction_manifest.json) | Machine-readable source pins and external-comparison eligibility state |
| [`results/restricted_gurobi_official_audit.json`](results/restricted_gurobi_official_audit.json) | Official Text2Opt no-exec translation coverage and coefficient-level equivalence audit |
| `llm4or/` | Structured models, solver, feedback, evolution, gateway, and evaluator |
| `scripts/` | Preparation, audit, verification, approval, execution, and scoring entry points |
| `tests/` | Offline contract and regression tests |
| `experiments/` | Machine-readable protocols, frozen split/plan, and authorization records |
| `results/` | Non-secret verification summaries; private request records are ignored |
| [`manuscript/OUTLINE.md`](manuscript/OUTLINE.md) | V9-centered paper argument, section plan, evidence allocation, and claim limits |

## Offline verification

The validated environment uses Python 3.11.16 and the pinned packages in `requirements-offline.txt`.

```bash
python3 -m pip install -r requirements-offline.txt
python3 -m unittest discover -s tests -v
```

The complete frozen-plan audit requires the locally provisioned benchmark snapshots and derived evaluation files listed in the manifests:

```bash
python3 scripts/run_formal.py
python3 scripts/verify_full_preparation.py
```

Both commands are read-only preflight operations. They do not approve spending, read the API key contents, or call a model. Live execution additionally requires an explicit authorization matching the frozen plan.

## Data and security boundaries

Raw benchmark snapshots, prepared records, evaluator-only references, private request/response ledgers, and API credentials are excluded from Git. Source URLs, pinned revisions, hashes, and status summaries are retained where redistribution is safe. Upstream repository licenses do not automatically grant redistribution rights for every derived dataset; see [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md).

The API credential lives outside this repository and is read only by an authorized transport worker. Every physical attempt is durably reserved before dispatch. A transient failure is retried within a fixed allowance; an exhausted item remains in the experiment denominator as infrastructure-unavailable while independent work continues. Repeated transport failure, authentication/model drift, accounting violations, budget exhaustion, or corrupted checkpoints still stop the controller.

## Scientific limits

The primary benchmark formulation-accuracy metric is final objective/status agreement with the published answer. This is a reproducible task-level accuracy measure, but equal objective/status does not prove that two formulations have identical variables, constraints, units, or feasible regions. Independent blinded semantic review therefore provides separate mechanism evidence. Public-benchmark pretraining contamination remains possible, and the category instances are not certified IID semantic families. Unsupported, ambiguous, and unresolved records stay visible in the denominator. V9 now has a significant preregistered improvement on the frozen Text2Opt cohort; that result is bounded to the evaluated dataset, supported template families, Base model, and endpoint.

ARK is not part of the algorithm or formal run. Its role is limited to optional outer research organization; the frozen experiment uses this repository's runner and ledger directly.

## Citation and release metadata

Verified author and software citation metadata are provided in
[`CITATION.cff`](CITATION.cff) and [`.zenodo.json`](.zenodo.json). No archival
DOI is claimed until an external archival deposit has been completed and
verified.
