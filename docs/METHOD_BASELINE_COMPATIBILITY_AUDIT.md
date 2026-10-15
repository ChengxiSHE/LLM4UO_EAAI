# Method, baseline, and compatibility audit

Updated 2026-10-03. This note fixes the paper-facing interpretation of the current method, distinguishes the experimental Base from external methods, and records what can and cannot be inferred from published CoE, OptiTrust, and Text2Opt-Bench results.

## Current assessment

The confirmed V9 contribution is a **selective trusted-compilation harness**. It is not a confirmed generic self-improving agent and it is not an LLM-only formulation method. For a recognized structured Text2Opt family, the harness parses the public text, instantiates a handwritten audited formulation, solves it with a bounded trusted solver, and adopts the result only after an optimal solve. Otherwise it returns the unchanged language-model Base.

The independent result is valid within that scope: among 400 completed pairs from the frozen 401-record confirmation cohort, Base scored 200/400 (50.00%) and V9 scored 259/400 (64.75%), a gain of 14.75 percentage points with 59 corrections, 0 regressions, and one-sided exact McNemar `p=1.7347e-18`. This is a benchmark formulation-accuracy result under the published status/objective endpoint. It is not proof of full formulation equivalence, unseen-family generalization, or superiority over CoE or OptiTrust.

No experiment in the repository has run CoE or OptiTrust on the frozen V9 cohort. Conversely, V9 has not been run on the seven cleaned datasets used by OptiTrust. Therefore the current paper has a confirmed within-system Base comparison, but no apples-to-apples external-method comparison.

## What the current Base is

`Base` is one `gpt-6-luna` request at high reasoning effort for each public problem description. It receives no reference answer and must return either one sparse structured `milp-v1` model or an explicit unsupported status. The structured model contains variables, domains and bounds, sparse linear constraints, and one objective. The trusted numerical worker solves the returned model. No generated Python is executed.

The confirmation used one frozen replicate and one request per problem. V9 shares that exact Base result; it does not make a second language-model request. Thus the comparison isolates the trusted-compiler adoption rule from language-model sampling differences:

\[
W_B(x)=
\begin{cases}
C(x), & A(x)=1,\\
B(x), & A(x)=0,
\end{cases}
\]

where `B` is the Base generator plus trusted solve, `C` is the deterministic family compiler plus exact solve, and `A` is the public-input-only adoption predicate.

This Base is not CoT, CoE, OptiMUS, OptiTrust, pass@k, or repair@k. It is a strong single-request structured-generation baseline with a modern closed model, but its absolute score cannot be interpreted as a leaderboard position because the output contract differs from the executable-code protocols used in most prior work.

## Current method stack

1. **Public-input boundary.** The model and compiler see only the public problem statement. References are opened after inference checkpoints exist.
2. **Text-only recognition.** A deterministic router recognizes transportation, modified facility location, disaster response, VRPTW, RCPSP, and JSSP from semantic headings and public structure, never from a problem identifier or outcome.
3. **Shape-checked parsing.** Missing, duplicated, non-contiguous, ambiguous, or dimensionally inconsistent data cause abstention.
4. **Completeness by construction.** A fixed family formulation replaces free-form coefficient generation on supported records.
5. **Bounded trusted solving.** LP/MILP or family-specific exact algorithms produce the candidate result without executing model-generated code.
6. **Fail-closed adoption.** Only an optimal trusted result replaces Base. Every other record preserves Base exactly.
7. **Independent paired evaluation.** The primary endpoint is optimal status and objective agreement at relative tolerance `1e-5` and absolute tolerance `1e-6`; unsupported and failed records stay in the denominator.

The project history matters to the argument but should not be conflated with the confirmed method. V3--V8 tested same-model repair, teacher disagreement, semantic contracts, two-view review, and source-indexed generation. Those studies identified correlated errors, low trigger coverage, and the fact that coefficient provenance does not guarantee relation completeness. They did not establish a positive main effect. V9 is the first independently confirmed positive method.

## Relationship to CoE, OptiTrust, and BIND

Published scores are used only to identify target settings and to check whether a reproduction is grossly inconsistent with the source paper. They are **not** empirical comparators for V9. A method enters the paper's comparison tables only after its authors' code has been pinned, audited, adapted without changing the scientific method, and rerun under a disclosed common protocol. If official code is unavailable, a paper-based implementation must be labeled a reimplementation and kept separate from official-code reproductions.

### Chain-of-Experts

CoE is a multi-agent prompting architecture. A conductor selects specialized experts, a reducer compresses their comments, and backward reflection uses execution feedback. Its official repository is available and has been pinned locally, so CoE is eligible for an official-code reproduction after a safety adapter is completed. The source-paper scores remain reproduction targets only because they use different datasets, backbones, execution contracts, and budgets. Source: [Xiao et al., ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/file/d45ee77826332c100a1e15f7765b99ff-Paper-Conference.pdf).

### OptiTrust

OptiTrust combines a three-stage decomposition/formulation/code agent, iterative debugging, reflection, five modeling languages, solution-majority voting, and a fine-tuned open model. The paper states that code is in supplementary material. Direct inspection of the arXiv v1 source archive found only TeX, figures, bibliography, and partial prompt templates; no runnable code, training data, checkpoints, or complete prompts were included. No official public repository has yet been verified. OptiTrust therefore cannot currently enter the official-code reproduction table. If the missing artifact cannot be obtained from the authors or venue supplement, a paper-faithful reimplementation may be reported in a separately labeled table, never as an official reproduction. Source: [Lima et al., arXiv:2508.03117](https://arxiv.org/html/2508.03117v1).

### The more relevant Text2Opt baseline: BIND

Because V9 is evaluated on Text2Opt-Bench, the benchmark paper's BIND family is a closer comparison than CoE or OptiTrust. BIND externalizes numeric instance data to structured files so the model loads values programmatically instead of transcribing them. Its official MIT-licensed repository is pinned locally and includes the evaluation and agentic-offload implementation, so it is eligible for an official-code reproduction after its generated-code evaluator is sandboxed. The paper's reported values are reproduction targets only. Source: [Gao et al., arXiv:2605.21751](https://arxiv.org/html/2605.21751).

V9 and BIND address related binding failures in materially different ways. BIND exposes structured instance data and retains model-generated formulation code; V9 recovers data from the public text and replaces both binding and formulation with a trusted family compiler on its adoption region. V9 uses no outcome oracle and no extra LLM request, but it relies on handwritten family knowledge and covers only part of the selected benchmark. The manuscript must not imply that V9 is the Text2Opt state of the art without rerunning BIND and V9 under a common protocol.

## What can be compared now

| Question | Current answer |
| --- | --- |
| Does V9 improve over its exact single-request Base? | Yes: +14.75 points, 59/0 corrections/regressions, preregistered independent confirmation. |
| Does V9 outperform CoE? | Unknown. They have not been run on the same frozen inputs, backbone, contract, or budget. |
| Does V9 outperform OptiTrust? | Unknown. The published datasets and training/inference resources differ. |
| Is V9 competitive with Text2Opt BIND? | On the exposed 30-record development matrix, both finish at 30/30; BIND starts at 25/30 and uses five oracle-repair corrections. A fresh common-protocol cohort is still required for a confirmatory comparison. |
| Is the original self-repair/evolution story confirmed? | No. The confirmed mechanism is selective completeness by construction. |
| Is V9 a harness-level contribution? | Yes, provided it is described specifically as a selective trusted-compilation and fallback harness. |

## Compatibility with other methods

The framework can wrap another generator if a small adapter maps that generator's output into either a structured model or a normalized solve result. Three integration modes are plausible:

1. **Backend replacement.** Replace the current one-shot Base with CoE, OptiTrust, OptiMUS, or another generator. The V9 compiler still overrides only on its supported public-text path and otherwise returns that backend's result.
2. **Trusted expert.** Add the compiler as a non-LLM expert inside a multi-agent system. Adoption must remain controlled by deterministic public-input checks, rather than by an LLM's self-confidence.
3. **Compiler-first cascade.** Run the cheap trusted compiler first and call the expensive agent only on abstention. This is attractive for deployment cost, but differs from the confirmation protocol and needs a separate evaluation.

CoE normally emits solver code, so its adapter must execute code in a real sandbox or translate it into the repository's structured model contract. OptiTrust produces code in five languages and votes over resulting solutions; the safest integration point is after its majority vote, using a normalized status/objective result, or before code generation by requiring its formulation stage to emit `milp-v1`.

The backend-neutral wrapper is now implemented in `llm4or/selective_harness.py`. It treats a backend result as opaque, proves exact hash equality on fallback, and replaces it only with an optimal trusted compiler result. Replaying it over all 30 completed BIND development records adopted the compiler on all 30 and preserved accuracy at 30/30, with zero corrections and zero regressions (`results/bind_selective_harness_compatibility_replay.json`). Because final BIND and the compiler were both perfect on this exposed matrix, this is a mechanical compatibility result rather than evidence of an incremental gain. CoE and OptiTrust adapters remain pending.

Adding a new compiler family requires a public-text recognizer, a total parser/schema for the claimed input region, a canonical formulation, a bounded solver or certificate, adversarial negative tests, development-only debugging, and a fresh grouped confirmation set. Unknown families must abstain.

## What is and is not guaranteed after integration

The fallback design gives three structural invariants for any wrapped Base:

- when the compiler abstains, the wrapped output is exactly the Base output;
- the compiler does not need reference outcomes or an additional LLM request;
- recognition, parsing, and solving failures remain visible and fail back to Base.

It does **not** guarantee a positive accuracy delta after replacing Base. On a fixed test set,

\[
\Delta(B)=\frac{\#\{A,C\text{ correct},B\text{ wrong}\}-\#\{A,C\text{ wrong},B\text{ correct}\}}{N}.
\]

A stronger Base reduces the first term because it leaves fewer errors to correct. It can also expose compiler errors that the current weaker Base did not reveal, increasing regressions. The observed 59 corrections and 0 regressions are therefore empirical facts for `gpt-6-luna` on the frozen cohort, not a universal non-regression theorem.

A true non-degradation guarantee would require a sound certificate that the compiler output is semantically correct on every adopted instance. Current checks establish parse shape, deterministic compilation, and optimal solution of the compiled problem; the benchmark endpoint checks status/objective. They do not prove that the compiled feasible region is fully equivalent to the natural-language intent. Consequently, the defensible guarantee is **fallback equality outside adoption**, while the accuracy effect inside adoption must be re-measured for every backend, dataset version, and new family.

## Required external-baseline study

The paper should add a two-axis experiment based only on locally rerun methods rather than quoting published leaderboards as results:

| Generator/backend | Native method | Native method + frozen trusted compiler |
| --- | --- | --- |
| One-shot structured LLM | current Base | current V9 |
| CoE-style multi-agent backend | CoE | CoE + compiler |
| OptiTrust official code, if obtained | OptiTrust | OptiTrust + compiler |
| Text2Opt binding-aware backend | BIND or trained binding specialist | BIND + compiler |

Every cell should use the same public inputs, outcome-hidden inference, model/version disclosure, executable endpoint, and per-record accounting. Report absolute accuracy, paired incremental gain, corrections, regressions, adoption, category effects, physical requests, tokens, latency, and solver cost. Budget-matched and native-budget results should be separated. A paper-based OptiTrust reimplementation, if needed, belongs in a separate sensitivity table and must not be used to claim superiority over OptiTrust itself.

The opened 401-record cohort can support a retrospective frozen-method comparison, but it cannot supply a new independent confirmation after implementation choices have been informed by its outcomes. The confirmatory comparison should therefore use untouched Text2Opt instances or a newly generated solver-verified cohort, grouped by template/family so near-duplicate variants cannot cross development and test. Pairwise tests should be preregistered and multiplicity controlled.

For the current manuscript, the external-comparison claim must remain: V9 is empirically superior to its exact Base on the frozen Text2Opt cohort; its relative position against CoE, OptiTrust, and BIND remains to be established under a common protocol.
