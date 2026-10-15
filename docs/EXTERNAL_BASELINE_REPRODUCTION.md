# External baseline reproduction protocol

Updated 2026-10-04. This document defines which external comparisons count as reproduced evidence and records the code audits and completed development reproductions. Published paper values are targets for sanity checking; they are not results of this project.

## Evidence classes

1. **Official-code reproduction.** The authors' public source is pinned to a commit, dependencies and data are recorded, method-relevant settings match the paper, generated code is executed only in a resource-bounded sandbox, and the method is rerun by this project.
2. **Repaired official-code reproduction.** The authors' source requires bug fixes or a compatibility adapter. The paper-era and repaired variants are both preserved, every method-relevant change is disclosed, and results are reported separately.
3. **Paper-based reimplementation.** No complete official source is available. The implementation follows the paper and released prompts, but it is not called a reproduction and cannot by itself establish superiority over the named method.
4. **Published target.** A number copied from a paper is used only to detect a large reproduction mismatch. It never appears as our empirical comparison result.

## Initial artifact audit

| Method | Primary artifact | Pinned version | License state | Reproduction status | Blocking issue |
| --- | --- | --- | --- | --- | --- |
| CoE | `xzymustbexzy/Chain-of-Experts` | paper-era `9d96bcc2f067177eb0e122b1aae8227748dc6830`; current `afb89bf602690ea621f13a23c42722f20f653a43` | no license file found | official forward prompts/controller reproduced through a safe adapter; native and six-family common-input development runs complete | reflection still depends on generated-code execution; two common-input RCPSP outputs require unsupported indicator constraints; paper-era code has a duplicate expert name and conductor bugs; paper uses five forward collaborations while current README defaults to three |
| Text2Opt/BIND | `SprocketLab/text2opt-bench` | `1dac06be656c41d827ef20987cf8af0b48d382a2` | MIT | official prompt adapter and durable common-backbone runner validated on the 30-record structured development matrix | native supported-model reproduction and an untouched comparison cohort remain |
| OptiTrust | arXiv `2508.03117v1` | source archive downloaded 2026-10-03 | paper text only | official reproduction blocked | arXiv source contains no runnable code, checkpoint, data, or complete prompt set despite the paper saying code is supplementary; no verified official repository found |
| Dream-RSI | `zhengkid/Dream-RSI` and arXiv `2609.14858` | public repository state checked 2026-10-03 | to audit before use | concept only | repository states that full code and reproduction scripts are still being prepared |

The raw third-party repositories remain under ignored `data/raw/` paths. They are untrusted input. No external generated program has been executed, and no third-party code will be copied into the tracked repository unless its license permits it.

The current Mac has no Docker, Podman, Colima, Lima, Firejail, or Bubblewrap runtime. Its legacy `sandbox-exec` binary is present but a deny-by-default empty probe cannot be applied in this host configuration, including outside the workspace sandbox. The pinned Python environment also has no `gurobipy` package. Direct in-process execution remains prohibited. A pre-existing Gurobi 13.0.1 academic command-line installation is available; the project did not apply for or accept a new solver license.

A source-preserving restricted Gurobi translator now resolves this blocker for the linear/MILP Text2Opt contract. It interprets a bounded whitelist of Python AST nodes into `milp-v1`; it never imports or executes generated Python. Real file access is replaced by controller-injected, read-only JSON mapped to an exact virtual path. Unsupported syntax, paths, nonlinear expressions, model sizes, or operations fail closed. Against all 2,121 official Text2Opt gold programs, it compiled 2,067 (97.45%); every compiled model was coefficient-by-coefficient structurally equivalent to the upstream symbolic model. The 54 visible rejections comprise 50 quadratic power-transmission programs outside the LP/MILP scope and four programs beyond the frozen 2,000-variable limit. See `results/restricted_gurobi_official_audit.json` and `scripts/audit_restricted_gurobi.py`.

This evidence validates the translator on upstream reference programs, not every future LLM output. The BIND prompt adapter was additionally checked against the pinned author helper on all 680 released instance-data prompts and three repair cases: all 683 strings matched byte for byte. The audited helper is imported only by the offline differential test; production parses the pinned source as data and reimplements the helper without executing author code.

The first common-backbone BIND development pilot used one frozen record from each of the six retained template families. With the trusted Gurobi command-line backend, all six first-round outputs matched the official optimal status and objective. The same generated outputs scored only 4/6 with the earlier HiGHS budget, showing that solver choice was a material evaluation confound rather than a method failure.

The subsequent frozen 30-record matrix covered all five development records in each retained family. Round one matched 25/30 outcomes (83.33%). Official oracle repair corrected five records, producing 30/30 final matches: four successes in round two and one in round three. Two outer JSON-format attempts across the continuation lineage failed visibly; the affected fingerprints were retried within the global three-attempt allowance, and no item, authorization, or ledger was silently reset. The final logical result used 36 responses and 703,955 reserved-or-reported tokens. The expansion itself made 32 physical attempts (30 completed, two failed) and recorded 957,490 reserved-or-reported tokens; six final responses were exact cache hits from the prior pilot. This result is still development compatibility evidence: the outcomes are exposed and cannot support a superiority or confirmatory claim. The prompt audit is in `results/bind_prompt_adapter_audit.json`; the final matrix aggregate is in `results/text2opt_bind_development_matrix_evaluation.json`; accounting is in `results/text2opt_bind_development_matrix_lineage.json`; the six-record pilot remains in `results/text2opt_bind_development_pilot_evaluation.json`.

The CoE prompt/controller adapter is now hash-bound to both official commits and was differentially checked on all 288 LPWP plus 18 ComplexOR problems. Across both snapshots, 5,508 rendered conductor, expert and reducer prompts matched direct literal rendering from the pinned author source with zero mismatches. The adapter deliberately preserves the paper snapshot's duplicate `Programming Expert` name, string-length collaboration-count bug, set-derived remaining-expert order and repeated-expert behavior; the current snapshot preserves the authors' later fixes. Production never imports the unlicensed upstream Python. See `results/coe_prompt_adapter_audit.json`.

The safe native execution boundary now supports the observed forward outputs without executing generated modules: a bounded AST interpreter handles Gurobi-style model construction, SciPy `linprog`, and bounded pure-Python dynamic programs, emits or solves only validated `milp-v1`, and then reproduces the generated function's post-solve return value. On the 18 released current ComplexOR implementation fixtures, 15 compile; the remaining three fail inside the released implementation/data pairing because of invalid indices. Only ten of the 18 compiled/released programs agree with their released sample output, exposing upstream fixture conflicts that cannot be attributed to CoE. See `results/coe_native_safe_adapter_audit.json`.

A frozen three-problem native development pilot used five forward collaborations, `gpt-6-luna` at high reasoning, and both official snapshots. It made 66 logical requests, 67 physical attempts, one retry and 1,075,207 reserved-or-reported tokens, with no infrastructure failure or circuit break. After a zero-call adapter replay, the current fixed snapshot matched 3/3 author endpoints; the paper snapshot matched 2/3. Its remaining failure solved `netasgn` to the correct objective but returned a dictionary where the released evaluator requires one scalar, so the official exact contract correctly marks it wrong. These are outcome-exposed adapter fixtures, not an accuracy comparison. See `results/coe_native_development_pilot_safe_replay.json`.

The frozen six-family common-input development pilot is also complete under plan hash `6a990725e686e44f65400628721fdba9c37ecdc5d6aa65b6bbc07a781ee2ad6d`. It ran the paper and current official forward controllers on the same six Text2Opt records, used five collaborations, and made 124 logical requests, 130 physical attempts, six retries, and 2,434,482 reserved-or-reported tokens. Eleven of twelve cells completed; the current disaster-response cell was infrastructure-unavailable after three recorded transport attempts and was not converted into a model failure. The authorization is closed.

The immutable online report scored the paper snapshot 1/6 and the current snapshot 0/5 on the exact single-scalar return contract, but most failures occurred at the then-frozen safe-adapter boundary. A zero-request replay extended only the bounded interpreter: it never imported generated Python and accepted nine of eleven completed outputs. Exact scoring remained paper 1/6 and current 0/5 because eight otherwise interpretable programs returned dictionaries despite the supplied skeleton explicitly requiring one numeric objective. A clearly post-hoc diagnostic projected only the recognized fields `objective_value`, `total_cost`, or `makespan`; it found the reference objective in 5/6 paper cells and 3/5 current cells. This projection was defined after observing development output and is invalid for confirmatory scoring. The two RCPSP programs remain visibly unsupported because exact Gurobi indicator semantics cannot be lowered safely without finite bounds; they are not counted as CoE errors. See `results/coe_common_development_pilot_evaluation.json` for the frozen online result and `results/coe_common_development_pilot_safe_replay.json` for the adapter replay.

## CoE reproduction design

Two variants are necessary because the April 2024 paper snapshot and the current repository differ materially:

- **CoE-paper:** commit `9d96bcc...`, paper settings, five forward expert collaborations, temperature zero, and the disclosed reflection/trial rule.
- **CoE-fixed:** current commit `afb89bf...`, the same scientific settings, plus the maintainers' later runtime and correctness fixes.

The original evaluator writes `generated_code.py` and imports it in the controller process. That code path will not be used. A compatibility wrapper will retain CoE's prompts, conductor, expert order, reducer, and feedback. The common Text2Opt-Gurobi variant can use the restricted translator. Native LPWP/ComplexOR reproduction still needs a multi-library isolated worker or equivalent restricted adapters. The wrapper may normalize result transport and accounting but may not alter prompts or silently repair models. Every divergence from the pinned source will be listed in a patch manifest.

Both development validations are complete. The second pilot ran both snapshots on the same six public Text2Opt records used by the BIND pilot. It supplied a generic no-answer `solve_problem()` skeleton because Text2Opt does not release CoE-style problem-specific function signatures. This is a disclosed common-input adaptation, not a native CoE result. Paper-era and current-code results remain separate and are not pooled. The low exact score is informative about contract-following under this adaptation, while the post-hoc projection suggests that many underlying objective computations were correct; neither result is an independent accuracy comparison.

## BIND reproduction design

The pinned official code serializes either template `instance_data` or the resource-allocation arrays to JSON, asks the model to load that file, and permits repair using execution/evaluation feedback. The implemented common-backbone runner preserves the instance-data semantics and official three-round budget. The local adapter maps the exact prompt-visible path to controller-provided JSON, interprets allowed model-building syntax, and sends only the resulting `milp-v1` model to the trusted Gurobi command-line worker. This preserves data-loading and formulation behavior without executing generated Python. Unsupported outputs remain evaluation failures and may receive only the official repair feedback/budget. Because the local Codex transport is stateless, the official message history is flattened into a labeled transcript; this transport deviation is disclosed in every result.

Two comparisons are required:

- **Native BIND:** official supported model and native budget, to establish that the code path reproduces the intended method.
- **Common-backbone BIND:** the same backbone and API generation configuration as Base, via a thin endpoint adapter, to isolate the method effect.

Native-budget and budget-matched variants remain separate. Oracle-guided repair, executable-only repair, and the trained binding specialist are distinct methods and must not share a label.

The 30-record development expansion is complete. V9 and final BIND both score 30/30 on this matrix; BIND's first-round score is 25/30 and its oracle repair corrects the remaining five. This is a tie on final development accuracy, not evidence that either method is superior. V9's compiler uses no answer oracle or repair request, but it relies on handwritten family formulations; BIND generalizes through model-generated code but receives structured instance data and answer-bearing repair feedback. The eventual main-table comparison requires a fresh grouped cohort and, for the native row, an author-supported model or checkpoint under the official budget.

The generic selective wrapper has also been replayed over all 30 completed BIND development records. It adopted the trusted compiler on all 30 and retained 30/30 accuracy, producing zero corrections and zero regressions. This verifies the intended composition path (`BIND + selective compiler`) and exact backend preservation on abstention in unit tests. It does not establish that the wrapper improves BIND because the final BIND result leaves no backend errors to correct.

## OptiTrust handling

The source archive includes partial prompt structures but explicitly says some details are omitted and additional prompts are in a zipped code artifact that is absent from the archive. The next artifact step is to check the venue supplement and contact the authors for the exact repository, prompts, cleaned datasets, checkpoint, and inference scripts.

Until those files are obtained, the main external table will show `not reproducible from released artifacts`, not an estimated score. A separate paper-based implementation may be useful for ablation or compatibility work, but it must be labeled `OptiTrust-style reimplementation` and cannot support a claim that our system outperforms OptiTrust.

## VERA-Opt composition boundary

VERA-Opt is a selective harness wrapper, so its architecture can compose with a one-shot Base, BIND, CoE, or another backend after that backend is normalized to the common result contract. Composition supplies an exact fallback property: when no skill adopts, the wrapper returns that backend's stored result unchanged. It does not supply a universal improvement guarantee. A stronger backend may leave no correctable cases, and a recognizer/compiler error can still create a regression inside the adoption region.

The current evidence establishes composition mechanics only. Static V9 preserved final BIND's 30/30 development score. VERA-Opt's automatic Knapsack skill was evaluated over the one-shot Base and has not been rerun over BIND or CoE. Each `backend × wrapper` cell therefore needs its own local official-code run and paired analysis. No score copied from a CoE, BIND, or OptiTrust paper may fill a missing cell.

## Common experimental protocol

All locally rerun methods will share:

- immutable public inputs and dataset revisions;
- evaluator-only references loaded after an inference checkpoint;
- the same status/objective endpoint and tolerances, plus expert semantic audit on a stratified subset;
- per-record physical-request, token, latency, solver, retry, and failure accounting;
- grouped splits that keep related templates and parameter variants together;
- both native-budget and matched-budget reports;
- paired corrections/regressions and confidence intervals rather than unpaired headline percentages alone;
- frozen manifests, source hashes, adapter patches, environment lockfiles, and durable checkpoints.

The existing 401-record V9 confirmation set is already outcome-exposed and can support a retrospective comparison only. Any new method choice informed by those outcomes requires an untouched grouped confirmation set.

## Promotion rule for an empirical comparator

An external method enters the main paper table only when all of the following hold:

1. the official artifact and exact revision are identified;
2. the method-relevant settings are frozen against the paper and source;
3. the adapter passes native fixtures without changing prompts or reasoning logic;
4. arbitrary generated code is isolated;
5. inference completes with durable accounting and visible failures;
6. evaluation is independent of development and uses the shared endpoint;
7. any deviations, fixes, unavailable resources, and licensing limits are reported.

If any item fails, the result stays in an audit or sensitivity appendix.
