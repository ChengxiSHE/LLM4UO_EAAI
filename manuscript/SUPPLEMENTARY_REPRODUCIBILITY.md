# Supplementary experimental methods and reproducibility

## R1. Evidence hierarchy and custody

Every reported result follows the same source-of-truth order: terminal closure
or evaluation JSON, machine-readable evidence ledger, claim-to-evidence matrix,
and paper narrative. The manifest
[`paper_evidence_manifest_20261015.json`](../experiments/paper_evidence_manifest_20261015.json)
binds headline claims to exact file hashes and field-level assertions.

Development data may be used to construct a skill. Promotion data are opened
only after the candidate, router, compiler, endpoint, denominator and inference
unit are frozen. Confirmation data are opened once after promotion and cannot
cause another method update. Evaluator-only references may score a durably
recorded method output but may not select a skill, repair a candidate, choose a
route or generate a fallback. Unsupported, abstained, method-failed and
infrastructure-unavailable records stay in their prespecified denominator
unless a table explicitly labels availability as a separate quantity.

Private request bodies, response bodies, evaluator-only answers and credentials
are excluded from this supplement and from the public release. The public
history-free repository uses aggregate records, hashes and upstream
reconstruction instructions where redistribution rights do not permit
publishing raw task text. A separate controlled-review protocol permits an
independent reviewer to recompute restricted endpoints without redistributing
those materials.

## R2. Recorded environment

The verified offline environment used Python 3.11.16 with NumPy 2.4.4, SciPy
1.17.1, jsonschema 4.26.0 and scikit-learn 1.9.0. The host default Python was
3.10.1 and is not the environment claimed for full reproduction. Solver-backed
evaluations used Gurobi 13.0.1; Gurobi is commercial software and reproducers
must obtain their own installation and license.

OR-Debug is pinned through the `solver-in-the-loop` submodule at commit
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` under its upstream CC BY 4.0
terms. A clean checkout must initialize submodules recursively. OPT-Engine,
DCP-Bench-Open, text2opt-bench and Chain-of-Experts are retrieved at pinned
upstream revisions rather than silently relicensed by this project.

The history-free public repository is available at
<https://github.com/ChengxiSHE/LLM4UO_EAAI>. Release `v1.0.0` resolves to the
single zero-parent commit `3b870323935fa0a00ffd3fe9d1dc3512323beacf` and tree
`3c90e562c0f3f228c2a1a031320dd75b80257304`. An unauthenticated recursive
clone retrieved the exact pinned submodule, both Git object graphs passed full
checks, and the canonical credential-free Layer-A contract passed 79 tests and
three deterministic reconstruction checks. Twelve additional release/provider
tests passed after installing the separately declared provider dependency.
The release contains all 70 paper-manifest paths and replaces restricted task
text and repair-bearing records with metadata-only projections.

The public package is an integrity/audit package: it reconstructs aggregate
arithmetic, content-addressed library identities and 2,985 body-free output
identities, but it does not rerun provider inference or rescore restricted
benchmark endpoints from evaluator-only answers. Endpoint recomputation uses
the hash-bound
[`CONTROLLED_ENDPOINT_REVIEW_PROTOCOL_20261016.md`](../docs/CONTROLLED_ENDPOINT_REVIEW_PROTOCOL_20261016.md).
A fresh-context reviewer executed that protocol and reproduced the TSP,
OR-Debug and common-38 endpoints exactly; the aggregate-only result is recorded
in
[`CONTROLLED_ENDPOINT_REVIEW_AUDIT_20261016.md`](../docs/CONTROLLED_ENDPOINT_REVIEW_AUDIT_20261016.md).
No archival DOI is claimed.

## R3. TSP constraint-skill study

### R3.1 Split and information boundary

The constraint-augmentation TSP study uses one pinned OPT-Engine source and a
deterministic size split:

| Role | Sizes | Records | Use |
| --- | ---: | ---: | --- |
| Development | 4--8 | 100 | Construct and verify the typed skill |
| Promotion | 9--12 | 80 | Freeze and test prospective size transfer |
| Confirmation | 13--19 | 140 | One-shot sealed confirmation |

Each size contributes 20 records. The method-visible split contains public
questions and source identities but not evaluator-only objectives. Shared
source templates make rows within and across sizes dependent; size is the
appropriate descriptive stratum, and item-level exact tests are nominal rather
than independent-sample guarantees.

### R3.2 Control, skill and trusted backend

The frozen canonical controller recognizes complete TSP tasks and
constructs the standard directed Miller--Tucker--Zemlin formulation. The typed
skill additionally accepts one public contract: an undirected graph with one
forbidden edge and an exclusive-or obligation requiring exactly one of two
specified present edges in a closed minimum Hamiltonian tour. Unknown,
contradictory or incomplete inputs abstain.

Both arms use the same scalable exact backend, exact decimal objective scaling,
fixed solver contract and independently decoded tour checker. Before
confirmation, a replay over all 180 size-4--12 rows preserved route, status,
adoption and objective behavior; all 162 previously solved objectives matched.
This gate changed the shared resource backend without changing the semantic
skill or fallback policy.

The confirmation endpoint follows OPT-Engine: absolute objective error must be
at most `0.002 * abs(reference)`. An adopted output must also decode to a valid
tour satisfying the typed graph constraints. All 40 skill abstentions remain
incorrect in the 140-record denominator. Confirmation scoring made no model or
API request and no new candidate-solver call.

### R3.3 Frozen decisions

Development produced 48/100 for the static control and 98/100 for the skill.
Promotion produced 32/80 versus 64/80, with 32 corrections, zero regressions
and a positive difference at every size 9--12. No method component changed
after promotion. Confirmation produced 54/140 versus 100/140, with 46
corrections, zero regressions and a positive difference at every size 13--19.
The authoritative closure is
[`tsp_constraint_confirmation_root_closure_20261014.json`](../results/tsp_constraint_confirmation_root_closure_20261014.json).

## R4. OR-Debug replication study

### R4.1 Grouped split

The second source contains corrupted LP and MIP models with nine error types.
Deterministic hashing assigns complete structural groups to one role; no group
crosses roles.

| Role | Records | Structural groups |
| --- | ---: | ---: |
| Development | 999 | 43 |
| Promotion | 1,118 | 37 |
| Confirmation | 2,845 | 100 |

All nine error types and both LP/MIP classes occur in every split. The grouping
key is exactly `problem_type|n_variables|n_constraints`; hashing this key keeps
an identical public shape inside one role. A public MPS-signature check covers
500 records and 245 signature groups with zero observed cross-role overlap.
Neither check proves that every shared source model or generation template is
captured. Promotion and confirmation inference are therefore conditional on
the prespecified structural grouping rather than evidence of fully independent
templates.

A rights-safe aggregate membership and endpoint ledger covers all 100
confirmation groups. Group sizes range from 1 to 126, membership is bound by a
hash of sorted public problem identifiers, and all 2,845 records are accounted
for. The 516 evolved-output disagreements between corrected-primary and
released-primary occur across 20 groups and are all type B; the static control
has zero endpoint disagreements. The ledger contains no task text, reference
repair, repair identity or evaluator-only answer.

### R4.2 Repair language and endpoint

The public bundle exposes problem text, corrupted-model identity and the frozen
repair interface but withholds the reference repair and endpoint outcome. The
repair language contains six inert operation types: remove a constraint, change
a variable category, change a right-hand side, change an objective coefficient,
change an upper bound and change a lower bound. Development normalization maps
all 999 released repairs into this language without parse failure, producing
1,947 operations.

The generic control recomputes a fresh irreducible infeasible subsystem and
applies a static repair policy. The evolved library routes public evidence to
typed repair skills. Both arms share the six-operation patcher, Gurobi backend
and independent endpoint evaluator. The corrected-primary endpoint requires
the source-corrected repair identity and applicable collateral checks; the
released-primary interpretation is retained as a separate sensitivity result.
For type-B records declared as LP, the released repair assigns an integer
variable category; the source-corrected rule uses a continuous category to
preserve the declared LP domain. This deterministic rule was frozen during
development before promotion and confirmation. Feasibility alone is
insufficient.

### R4.3 Promotion and confirmation

Development produced 266/999 for the static policy and 958/999 for the evolved
library. After freezing, promotion produced 327/1,118 versus 1,080/1,118, with
753 corrections and zero regressions. At the grouped level, 28 groups improved,
nine tied and none declined; the prespecified one-sided group sign test gave
`p=3.725290298461914e-09`. The upper confidence bound on regression-group mass
was 0.11169, below the frozen 0.12 gate, so promotion passed.

No rule changed after promotion. One-shot confirmation produced 828/2,845
versus 2,752/2,845 under corrected-primary, with 1,924 corrections and zero
regressions. Under released-primary, the same frozen outputs give 828/2,845
versus 2,236/2,845, with 1,408 corrections, zero regressions and 609 both
wrong. The 516-record endpoint difference is confined to type-B LP records.
Sixty-five of 100 groups improved, 35 tied and none declined
(`p=2.710505431213761e-20`). Ninety-three ambiguity abstentions remain wrong in
the denominator. Confirmation evaluation made zero model or API calls. The
authoritative result is
[`or_debug_confirmation_evaluation_20261014.json`](../results/or_debug_confirmation_evaluation_20261014.json).

## R5. Mixed public-only router

The retrospective composition bundle interleaves the 140 TSP and 2,845
OR-Debug confirmation envelopes. Guards inspect only the frozen public envelope
shape. Exactly one guard must match; zero or multiple matches fail closed. The
audit requires expected-family routing, source identity and byte-equivalent
compact output relative to pinned direct-family execution.

All 2,985 records route uniquely and exactly match their direct output. There
are zero route, output or source mismatches; zero terminal failures; and zero
missing, duplicate, invalid or unexpected rows. This demonstrates behavior
preservation for known frozen interfaces. Accuracy is inherited descriptively
and was not recomputed. The authoritative audit is
[`mixed_skill_confirmation_public_audit_v3_20261015.json`](../results/mixed_skill_confirmation_public_audit_v3_20261015.json).
The v3 audit compares canonical output hashes from metadata-only projections;
the omitted task text and repair objects are not required for this identity
check.

## R6. External baseline reproduction

### R6.1 Retrospective common identities

The current external panel contains 40 fixed text2opt-bench identities: 20
RCPSP and 20 VRPTW. Locally rerun rows use the `gpt-6-luna` backbone at high
reasoning effort. The cohort equalizes identities and backbone but does not
equalize input representation, answer feedback, method rounds, safe execution
coverage or native compute. It is therefore a disclosed retrospective panel,
not an unconditional leaderboard.

### R6.2 BIND

BIND is adapted from `SprocketLab/text2opt-bench` at commit
`1dac06be656c41d827ef20987cf8af0b48d382a2`. Its first round receives the
official structured instance and no answer feedback; it obtains 31/40. The
official final procedure uses answer-bearing repair feedback and obtains 40/40.
Generated Gurobi Python is handled by the disclosed safe adapter rather than
unrestricted native execution. First-round and final results are never merged
as if they had the same information budget.

### R6.3 Chain-of-Experts

The paper snapshot is pinned at
`9d96bcc2f067177eb0e122b1aae8227748dc6830`; the audited current snapshot is
`afb89bf602690ea621f13a23c42722f20f653a43`. Both use official code with the
fixed safe adapter. The adapter is a bounded interpreter for supported
generated-program constructs that emits a validated model and invokes the
trusted solver; unsupported constructs fail closed and no generated module is
imported. Under strict author-scalar scoring, the scalar returned through the
official `solve_problem` contract must equal the single expected scalar
exactly. The paper and current snapshots obtain 3/40 and 1/40. One and two
records, respectively, are
infrastructure unavailable; one method failure occurs in each condition.
Twenty-five and 29 completed outputs fall outside the safe adapter. Those rows
remain failures in the full denominator but cannot be attributed to native CoE
reasoning.

### R6.4 OptiTrust

The audited OptiTrust artifact is arXiv `2508.03117v1`. The inspected source
archive contains manuscript assets but no verified runnable implementation,
complete prompts, training data, checkpoint or inference script. A bounded
public-channel recheck also found no verified author-linked runnable package.
The paper therefore reports `artifact unavailable`; it neither imports a
published score nor claims that no implementation exists globally.

### R6.5 Request accounting

| Condition | Logical requests | Physical attempts | Retries | Recorded ledger token quantity |
| --- | ---: | ---: | ---: | ---: |
| Base, 40 | 40 | 40 | 0 | 3,533,793 |
| BIND first round, 40 | 40 | 40 | 0 | 872,896 |
| BIND all official rounds, 40 | 50 | 50 | 0 | 1,104,963 |
| CoE paper snapshot, 40 | 434 | 463 | 29 | 13,107,292 |
| CoE current snapshot, 40 | 427 | 452 | 25 | 12,418,518 |

These are ledger quantities rather than provider invoices. The source ledgers
do not consistently distinguish reserved from reported tokens at the aggregate
row level, so these quantities are not treated as directly comparable usage.
BIND all-round cost includes its first round and must not be added to the
first-round row. All
method and adapter failures stay in planned denominators; infrastructure
unavailability is also reported explicitly.

The full ledger is
[`external_baseline_evidence_ledger_20261014.json`](../experiments/external_baseline_evidence_ledger_20261014.json).

## R7. Automatic-construction diagnostic

The diagnostic freezes a 64-member partial-count grammar, public cases, a
20,977-assignment semantic oracle and exact compiler resource obligations. One
bounded AntChat `DeepSeek-V4-Flash` request proposes a member of the grammar.
The response passes every semantic assignment but retains a declared-length
domain that violates the exact indicator limit; it is rejected as
`resource_model_rejected`. No recovery or promotion is attributed to the
model.

An answer-free deterministic certificate subsequently exhausts all 64 grammar
members. All six distance-one neighbors fail, while changing the bound strategy
and zero-tail policy jointly gives the unique passing distance-two repair. The
certificate makes zero model/API, solver, native or VM call and reads no
reference answer. It establishes finite-grammar repair minimality, not general
automatic skill acquisition or benchmark accuracy.

## R8. Accuracy, pairing and inference

Every primary accuracy is `correct / full frozen denominator`. Abstentions,
unsupported method outputs and terminal method failures count as incorrect.
Infrastructure unavailability remains in the planned denominator and is also
reported separately.

For paired methods, each record is classified as both correct, correction,
regression or both wrong. The absolute accuracy difference equals
`(corrections - regressions) / denominator`. TSP size rows share templates, so
the paper reports stratified effects and treats item-level exact tests as
nominal. OR-Debug uses the frozen structural group as its inference unit and a
prespecified one-sided sign test over non-tied group effects. Repeated library
generations require a prespecified error allocation; current evidence contains
one OR-Debug promotion-to-confirmation transition rather than an unlimited
sequence.

No significance test is selected from the retrospective external common-40
panel. AlphaOPT repetitions, where reported in supplementary reproduction
tables, remain repetitions over 40 identities rather than independent new
problems.

## R9. What can currently be reproduced

The public evidence package binds terminal aggregates, split manifests,
compiler and evaluator identities, selected source hashes, targeted offline
tests and narrative claims. The single canonical command
`python3 scripts/run_public_integrity.py --check` runs 79 credential-free
Layer-A tests and three deterministic checks without model, API,
benchmark-solver or native-evaluator calls. Figure 2 aggregate Source Data were
independently recomputed from four sealed result files and verified field by
field.

The `v1.0.0` tag is a one-commit, zero-parent history-free release. All 70
paper-manifest paths are tracked; restricted embedded text and repair-bearing
records are represented by metadata-only projections; exact offline, local
solver, provider-transport and figure environments have separate audits. The
pinned submodule was acquired recursively from its public Git remote with zero
missing reachable objects and a passing full object check. Gurobi remains
separately licensed. This public reconstruction verifies integrity and
aggregate arithmetic, not end-to-end endpoint rescoring from excluded private
or evaluator-only material. The controlled-review protocol supplies that
separate path; DOI registration remains pending.

## R10. Completed prospective studies and stronger open claims

The matched eight-pair language-model canary and the fresh common-38 protocol
were executed under their frozen gates. The canary has zero discordance and
does not support an effect for reorganizing the same authored facts. A separate
complete finite census over the authored count grammar shows that balanced
verifier-selected witnesses identify 10/10 extensional classes within three
queries versus 6/10 for a canonical-order separating-witness control. This is
an exact bounded acquisition result, not evidence for language-model proposal
quality or natural-language fact discovery.

The common-38 cohort contains 13 larger RCPSP and 25 larger VRPTW identities
from the pinned Text2Opt revision. All IDs and public-text hashes are unique,
their overlap with the earlier 183 prepared public-text hashes is zero, and
their reference endpoints are finite. Under the frozen full-denominator
endpoint, the current method scores 30/38, versus Base 0/38, BIND round one
13/38, BIND answer-bearing final 13/38 and CoE-safe 4/38. Native inference
budgets and provider tokens differ, authored construction cost is not
equalized, and both families share one source lineage. The result supports the
declared size-generalization cohort and observed large paired effects, but not
broad moderate-effect superiority across unrelated benchmarks.

Stronger open studies would acquire semantic axes or atomic facts from natural
language, test naturally proposed libraries rather than the authored
shadow-guard grammar, replicate the common-protocol advantage on a second
source lineage, or evaluate a learned router under unrestricted paraphrase and
family shift. Native-budget and equal-budget views must remain separate, BIND
answer-bearing final remains a distinct information condition, and OptiTrust
enters a numerical table only if a verified runnable author artifact becomes
available.
