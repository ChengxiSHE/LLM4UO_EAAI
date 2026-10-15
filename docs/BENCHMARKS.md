# Benchmarks, provenance, and evaluation status

Updated 2026-10-04. This document consolidates the former benchmark plan, source audit, input audit, MILP extension report, and readiness report. Machine-readable revisions and hashes remain authoritative.

## Frozen source inventory

| Benchmark | Role | Records | Frozen version |
| --- | --- | ---: | --- |
| IndustryOR | core | 100 | Cardinal-Operations/SIRL `b329ff2`, `IndustryOR_fixedV2.json` |
| MAMO ComplexLP | core | 203 | Cardinal-Operations/SIRL `b329ff2`, fixed 203-row release; original 211 retained only for comparison |
| OptMATH-Bench | core | 166 | optsuite/OptMATH `f15bbc4`, author benchmark rather than a nonidentical mirror |
| ComplexOR | core | 37 | XiaoAI1989/ORMind `f5bc4ff`, restructured 37-problem distribution |
| OptiBench | coverage | 605 | yangzhch6/ReSocratic `27ff7ec` |
| NL4Opt | basic control | 245 | Cardinal-Operations/SIRL `b329ff2`, objective-value execution version |

The sum, 1,356, is a complete-source reporting cohort. It is not the size of an independent unseen test set. Exact URLs, full revisions, SHA-256 values, local paths, and license observations are in `experiments/benchmark_plan.json` and `data/manifests/*.json`.

## Input boundary and revisions

Adapters construct public payloads from whitelisted problem text, parameter definitions, and parameter values. They exclude answers, formulations, code, difficulty labels, historical success statistics, scaffolds, and retrieved insights. Evaluation references are stored separately and are not imported by the inference runtime.

Raw source snapshots are read-only. ComplexOR uses a separate `complexor-parameter-metadata-v1` revision: two problems received three parameter-shape metadata corrections based on public definitions; wording and numeric values were not changed, and all 37 problems remain. Source and revised versions are never mixed under one label.

Four ComplexOR records remain input-ambiguous: `cut`, `fleet`, `net1`, and `netmcol`. The supplied cut modes exceed roll width; the other three retain axis/topology conflicts. `steel4` retains a reference conflict. These cases are reported as unresolved rather than guessed, silently repaired, or removed.

## Execution coverage

The `milp-v1` contract represents sparse linear objectives and constraints with continuous, integer, and binary domains. The controlled worker reports status, objective, bounds, and gaps. Solver limits and numerical tolerances are frozen in `experiments/milp_protocol.json`.

Nonlinear, conic, missing-input, ambiguous-input, and schema-capacity cases must abstain explicitly. They are not relaxed or linearized for convenience. The solver never executes arbitrary model-generated Python. Earlier numerical checks included 24 synthetic integer/mixed-integer cases against a separate rational enumeration oracle; this validates the implementation path, not benchmark modeling accuracy.

## Reference audit

| Status | Count | Interpretation |
| --- | ---: | --- |
| Numeric transcription and native label agree | 12 | Separately transcribed model and native result agree numerically |
| Native parsed, not independently certified | 1,243 | Usable for benchmark formulation accuracy against the published answer |
| Native parse unresolved | 96 | Retained as unresolved |
| Input ambiguity | 4 | Retained as unresolved |
| Reference conflict | 1 | Retained as conflict |

The primary benchmark formulation-accuracy endpoint is final objective/status agreement with the published answer. This operational definition supports normal benchmark accuracy comparisons. It does not imply that equal objective/status establishes equivalent constraints, variables, units, or business semantics. Independent numerical transcription and blinded semantic review are therefore reported as separate evidence rather than silently folded into the benchmark metric.

## External confirmation cohort

Text2Opt-Bench is pinned from `SprocketLab/Text2Opt-Bench` at revision `1dac06be656c41d827ef20987cf8af0b48d382a2` under the upstream MIT license. The upstream JSON files are treated only as data: their gold programs are neither imported nor executed, and evaluator fields are not copied into model-visible snapshots.

Two input-level cohorts are frozen before v7 outcome access:

| Cohort | Records | Families/categories | Role |
| --- | ---: | ---: | --- |
| Official unstructured resource-allocation eval | 248 | 1 | External instance-level confirmation |
| Capacity-compatible template subset | 183 | 6 | External family-diverse confirmation |
| Combined | 431 | 7 | Paired accuracy and category-level sensitivity |

The 183 template cases were selected without answers from the standard small tiers of transportation, disaster response, job-shop scheduling, vehicle routing with time windows, resource-constrained project scheduling, and modified facility location. The fixed capacity rule retains only instances with at most 96 variables and 192 constraints. MIQP, nonlinear, multi-objective, large stochastic, alternate prose/capped variants, and larger cases are excluded before scoring because they fall outside the current structured-output scope. All counts, source-file hashes, public-text hashes, prepared-snapshot hashes, and leakage checks are recorded in `data/manifests/text2opt_resource_allocation_v1.json` and `data/manifests/text2opt_template_confirmation_v1.json`.

The 764 official resource-allocation training cases are available only for provenance checks and are not used for current method development. Their normalized public texts have zero exact overlap with the 248 eval texts, although train and eval still share the same resource-allocation template family. Therefore the 248-case cohort supports external instance-level benchmark accuracy, not unseen-family transfer by itself. The full 431-case analysis must report pooled accuracy, paired corrections/regressions, exact confidence or permutation tests, and category-level sensitivity. Public pretraining contamination remains possible.

The outcome-blind statistical protocol is frozen at `experiments/text2opt_confirmation_protocol.json` with hash `939cc7649dcb0070ff4b4786caf88da54b789abc88eefa424f4e0c357ae52b90`. The pinned executable upstream evaluator uses `rel_tol=1e-5` and `abs_tol=1e-6`; these code values take precedence over README prose stating `1e-4`. Confirmation requires both `FullV7` versus `Base` and `FullV7` versus `V6` to pass a joint rule: at least 99% paired infrastructure completion, at least +2 percentage points accuracy, corrections at least twice regressions, Holm-adjusted one-sided exact McNemar `p <= 0.05`, positive category deltas in at least four of seven categories, and a negative delta in at most one. Failures to parse, satisfy the contract, or solve count as incorrect; only explicit transport interruptions may be excluded pairwise, and the 99% guard prevents infrastructure filtering from manufacturing a claim.

## Family isolation

All 4,000 old and current public problem texts were connected using normalized exact matches, number-masked templates, reviewed problem names, text similarity, and 23 broad semantic templates. Known development exposure propagates through connected components before assigning roles.

| Role | Records | Groups |
| --- | ---: | ---: |
| Proposal development | 67 | 46 |
| Candidate selection | 83 | 62 |
| Operational update-gate pool | 176 | 124 |
| Operational held-out test block | 522 | 372 |
| Prior exposure / conservative quarantine | 508 | 9 |

Two fixed, disjoint 24-family batches are reserved for the two workflow generations. These are operational blocks, not expert-certified independent semantic families. Similar paraphrases may remain undetected, broad templates may overmerge, and public pretraining contamination cannot be ruled out. Consequently update results are described empirically; nominal error control is stated only conditional on its independence and label assumptions.

## Executed transfer cohort: OPT-Engine canonical Knapsack

The official ICML 2026 OPT-Engine repository is pinned locally at commit `d84a4b49187071debf16f50ba03a193776213edd` without executing upstream code. Its four JSONL files contain 5,570 records: 1,810 canonical cases across ten problem classes and 3,760 Inventory/Knapsack/TSP perturbation records covering linguistic complexity, objective changes, and constraint augmentation. Exact-text audit shows that 530--580 canonical originals recur in each perturbation file. Every original and derived version must therefore share one split group; treating the 5,570 rows as independent would be invalid.

The first VERA-Opt cycle used only the 260 canonical Knapsack records. Public projections removed all answer fields before proposal or inference. Item count defined a strict extrapolation split: 60 development records at sizes 5--10, 90 hidden-promotion records at sizes 11--19, and 110 final-confirmation records at sizes 20--30. Answers were loaded only after the corresponding inference checkpoint. Canonical records from the other nine classes supplied 1,550 answer-free negative-recognition challenges. Perturbation records remain unused because their original/derived grouping and independence require further review.

Generation-one induction achieved 60/60 development outcomes, but its 90-record hidden promotion failed the joint gate despite improving Base 85/90 to VERA 90/90. A failure-driven generation-two candidate achieved 150/150 on opened data and zero false adoptions over the 1,550 negative challenges. On the 110-record final cohort, VERA was exact on all 110 and Base was correct on 101. Three Base requests were infrastructure-unavailable, so the 107-pair preregistered test produced 6 corrections, 0 regressions, and `p=0.015625`; its joint gate failed. A separately frozen post-lock infrastructure-only sensitivity completed all 110 pairs and produced Base 103/110 versus VERA 110/110, 7 corrections, 0 regressions, and `p=0.0078125`. It is not the primary result. See `VERA_OPT_RESULTS.md` and `data/manifests/optengine_artifact_audit_v1.json`.

The repository root contains no license file, and public questions and answers are co-located upstream. Raw or derived OPT-Engine records therefore remain excluded from Git. This study supports canonical Knapsack size extrapolation only; it does not establish transfer to the other nine classes, to the perturbation suites, or to private prose.

## Redistribution and reproducibility

Raw and derived benchmark contents are excluded from Git because permissions differ by upstream source and a repository license does not automatically cover all embedded data. Private model traffic and evaluator-only artifacts are also excluded. The repository retains preparation scripts, source manifests where safe, frozen revisions, hashes, status counts, and non-secret verification summaries. A full local reproduction must acquire each upstream source under its own terms and recreate the prepared data.

No test answer may guide prompts, workflow selection, problem selection, or revisions. Any future corrected dataset must use a new version, document every edit, bind new hashes, and trigger a new experimental freeze.
