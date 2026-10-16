# Manuscript claim and evidence audit

Status: public-release revision audited against terminal evidence on 2026-10-16. This
file is a human-readable companion to
[`paper_evidence_manifest_20261015.json`](../experiments/paper_evidence_manifest_20261015.json).
The machine-readable manifest remains authoritative when narrative documents
disagree.

## Audit result

The closed numerical and artifact-availability claims in
[`MANUSCRIPT_DRAFT.md`](MANUSCRIPT_DRAFT.md) are consistent with their terminal
evidence. The current draft has 1,079 lines, 8,491 whitespace-delimited words
and SHA-256
`72abf87dbeabe3075bf5af70110761657add680be0cc46a7b149eabd829458f1`.
All 18 citation keys used by the draft are present in
[`references.bib`](references.bib), and every bibliography entry is cited.

The history-free `v1.0.0` repository and release are publicly available at
<https://github.com/ChengxiSHE/LLM4UO_EAAI>. An unauthenticated recursive
clean clone retrieved the main repository and pinned submodule, then passed 91
credential-free release tests and six reconstruction/preflight commands. All 11
release-asset server digests match the local bundle and sidecars. An archival
DOI remains pending and is not claimed by the manuscript.

A fresh-context reviewer then used only the unauthenticated public repository
and release. The reviewer reproduced the Git identities, 11 asset digests,
79-test Layer-A contract, additional 12-test release suite, aggregate
arithmetic and bounded theoretical statements. The reviewer correctly found
that the public package is an integrity/audit package rather than an
end-to-end endpoint-rescoring package because restricted task bodies and
evaluator-only answers are intentionally excluded. The draft now states this
boundary and binds a controlled, aggregate-only endpoint-review protocol. A
fresh-context reviewer subsequently recomputed all three central endpoint
families from the hash-bound restricted inputs: TSP matched exactly, OR-Debug
matched all 2,845 records and 5,690 arm objects after 5,597 local Gurobi calls,
and common-38 matched through a byte-hash-only ledger path that parsed no
request or response payload. The controlled result remains separate from the
public integrity checks.

The revision adds no endpoint result. It makes the construction operator
explicit as `Abstract -> Acquire -> Admit -> Route -> Promote`, labels the
successful TSP and OR-Debug abstraction/acquisition steps as authored, and
positions the general skill-library mechanisms against seven recent primary
sources. Typed contracts, validation-gated revision, executable skill
programs, applicability filtering and versioned verifiable libraries are no
longer eligible as broad priority claims. The retained method claim is the
optimization-modeling-specific composition of executable semantic/resource
obligations, frozen solver-facing formulation endpoints, exact fallback and
lineage-separated promotion evidence. The paper-facing name is now
**Benchmark-Grounded Proof-Carrying Knowledge Compilation**; “skill evolution”
remains a descriptive library-transition process rather than the claimed
general novelty.

The Related Work comparison table is a primary-source scope map, not a
negative feature audit. It records each concurrent system's stated retained
object and update or acceptance signal, then isolates this paper's
solver-facing semantic/resource certificates and exact fallback. The table
does not claim that mechanisms omitted from a source abstract or method summary
are absent from that system, and it introduces no local performance row.

The new limitation paragraph is supported by
[`theory_implementation_conformance_audit_20261015.json`](../experiments/theory_implementation_conformance_audit_20261015.json)
and the answer-free two-level design in
[`content_addressed_library_manifest_design_20261015.json`](../experiments/content_addressed_library_manifest_design_20261015.json).
It distinguishes behavioral conformance from canonical artifact
reconstruction. The implemented answer-free two-skill/one-library manifest now
has an operational semantic-envelope measurement of 17,728 bits, but the code
and encoding were frozen after development outcomes were known. The value is
therefore an artifact description rather than a retrospective generalization
bound. No endpoint claim was added by this measurement.

The formal appendix
[`SUPPLEMENTARY_THEORY.md`](SUPPLEMENTARY_THEORY.md) contains 12 bounded
propositions, six corollaries and proof sketches over 563 lines (SHA-256
`5e613994a5e4e36dc20664ce5abfa82e2786aa7acee7becc5a2708390f029cf2`).
It states the assumptions for finite construction, exact repair,
proof-carrying execution, selective fallback, paired-gain decomposition,
modular multi-skill utility, matched acquisition, library-level prefix-code
complexity control, complexity-weighted candidate promotion and cumulative
regression budgeting. The authored shadow-guard census identifies the bounded
library-selection effect of prefix-code complexity, while complexity-weighted
error allocation and cumulative regression budgeting remain prospective
protocol guarantees. The current runs do not form one repeated sequence on a
fixed target. The appendix does not add an
empirical claim or extend a theorem beyond the declared grammar, verifier,
sampling and endpoint assumptions. Its theory-to-evidence table also records
the software mechanism, current empirical instantiation and prohibited
extrapolation for every proposition class.

The experimental supplement
[`SUPPLEMENTARY_REPRODUCIBILITY.md`](SUPPLEMENTARY_REPRODUCIBILITY.md) records
the evidence hierarchy, environment, information boundaries, full-denominator
endpoints, external-baseline adaptations, request accounting and current
release limitations over 365 lines (SHA-256
`10f52e359d566de0954b99438f40f21c6b79db7f8b2bca011707086f4efc0b6a`).
It adds no endpoint result beyond the sealed artifacts in the headline claim
ledger.

This audit does not certify that the study is submission-complete. The matched
knowledge-construction engineering canary is complete and negative; the fresh
common-38 comparison, bounded semantic/resource/routing component censuses and
exact finite active-acquisition and library-complexity censuses are complete.
Natural-language grammar and fact acquisition, natural library-selection replication, broader
source replication and the archival DOI remain open. The history-free public
release, controlled endpoint review, author metadata and disclosure
fields are closed. Figures 1 and 2 have passed
strict source, editable-text, collision, alignment and final-size visual QA;
these renders add no benchmark result.

## Headline claim ledger

| Manuscript claim | Terminal evidence | Verified fields | Permitted interpretation | Boundary retained in draft |
| --- | --- | --- | --- | --- |
| TSP skill improves the frozen confirmation endpoint | [`tsp_constraint_confirmation_root_closure_20261014.json`](../results/tsp_constraint_confirmation_root_closure_20261014.json), SHA-256 `0a0aef6aad14e720f537c3201b5cc585b0177c0a05150a18d0300f3e498c437d` | denominator 140; static 54; skill 100; 46 corrections; 0 regressions; 40 abstentions counted wrong; positive gain at sizes 13--19 | Benchmark-specific formulation-accuracy improvement over the frozen strong static controller | Same-source size transfer with shared template lineage; authored skill, not automatic discovery |
| OR-Debug methodology replication improves the confirmation endpoint | [`or_debug_confirmation_evaluation_projection_20261015.json`](../results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json), SHA-256 `7f83555e8b81ff15bad510b95bf7e2617d87bb139786777407704a55e10a70ca`; [`or_debug_group_endpoint_sensitivity_audit_20261015.json`](../results/or_debug_group_endpoint_sensitivity_audit_20261015.json), SHA-256 `613fd34cd25a844813c9decf22e800a4c99eba651d25b887b50d897327e33a33` | 2,845 records; corrected-primary static 828 and evolved 2,752, with 1,924 corrections, 0 regressions and 93 both wrong; released-primary static 828 and evolved 2,236, with 1,408 corrections, 0 regressions and 609 both wrong; 100 groups of size 1--126; 516 evolved endpoint disagreements across 20 groups, all type B; static endpoint disagreements 0; corrected-primary has 65 positive, 35 tied, 0 negative groups and sign-test `p=2.710505431213761e-20` | Replication of the construction, verification, routing and promotion methodology on a second source and task type, with endpoint sensitivity and complete aggregate group accounting disclosed | The public projection removes repair identities while binding every complete frozen source record by canonical SHA-256. Separate authored repair skills remain; corrected-primary depends on a development-frozen source correction; released-primary remains materially lower; the public-shape group key is not proven to capture every source/template lineage; no unchanged-skill transfer or automatic synthesis claim |
| Mixed public-only routing preserves direct-family behavior | [`mixed_skill_confirmation_public_audit_v3_20261015.json`](../results/mixed_skill_confirmation_public_audit_v3_20261015.json), SHA-256 `3c9b8700639cfe5599fc76b18cca4318b14d4b0865fb5bd343f5c0d26fead08f` | 2,985/2,985 exact output-hash matches; zero route, output, source or terminal mismatches; no missing, duplicate, invalid or unexpected rows | Exact output identity on the frozen TSP and OR-Debug envelopes, reconstructed only from metadata projections | Retrospective composition only; canonical hashes bind omitted outputs but do not disclose them; endpoint accuracy was inherited rather than rescored; no learned routing or shift claim |
| BIND and CoE were locally rerun on a fixed common-40 cohort | [`external_fixed_common40_summary.json`](../results/external_fixed_common40_summary.json), SHA-256 `22c588da5167f6cb76615340ea81551021b8473b9db2a4ea83d717c93a77a38c`; [`external_baseline_evidence_ledger_20261014.json`](../experiments/external_baseline_evidence_ledger_20261014.json), SHA-256 `f9aaa74190c1735105fc0061662be1ca2b0411479c77bbafcc3b4f9272c7d0e7` | BIND first round 31/40 and final 40/40, both with 0 infrastructure-unavailable records; CoE paper/current author-exact 3/40 and 1/40, with 38/37 completed, 1/1 method failures, 1/2 infrastructure-unavailable records, and 25/29 completed outputs unsupported by the safe adapter | Local official-prompt or official-code adaptations on the same identities and `gpt-6-luna` backbone | BIND final is answer-bearing; CoE adapter coverage is material; all method/adapter failures remain in the planned denominator while infrastructure unavailability is separate; unequal interfaces and budgets preclude an unconditional leaderboard; the current method has no common-40 row |
| The current method outperforms locally rerun Base, BIND and CoE-safe on fresh common-38 | [`fresh_common38_common_protocol_synthesis_20261015.json`](../experiments/fresh_common38_common_protocol_synthesis_20261015.json), SHA-256 `a678008a7449d588e12eb59bf019875fb08d7cb8f4e9c177ca8aaf9f0fb2aa9e` | current/Base/BIND-round1/BIND-final/CoE-safe correct 30/0/13/13/4 of 38; current paired corrections/regressions 30/0, 18/1, 18/1 and 26/0; four Holm-adjusted p-values `3.7253e-9`, `7.6294e-5`, `7.6294e-5`, `4.47035e-8`; RCPSP/VRPTW current 12/13 and 18/25 | Large fixed-endpoint advantage on the frozen larger RCPSP/VRPTW cohort; answer-blind at-most-one-call sensitivity includes current, BIND round 1 and Base | Two families and one source lineage; native budgets and provider tokens differ; construction cost is not equalized; BIND final is answer-bearing; no broad benchmark-superiority claim |
| Exact finite component censuses identify bounded semantic-admission, resource-admission and selective-routing effects | [`g09_finite_component_census_v2_20261015.json`](../experiments/g09_finite_component_census_v2_20261015.json), SHA-256 `11e68dbff762893924430608c69dae1cfdb41756f5b5d66c981b96584e8b8911` | independently measured semantic/resource cells 47 fail-both, 11 semantic-only failures, 5 resource-only failures and 1 pass-both; full admission 1/64 safe; no-semantic 12/64 with 11 unsafe; no-resource 6/64 with 5 unsafe; exactly-one routing 69/69, forced-first 24/69, 45 corrections and 0 regressions; relaxed-multiple 67/69 | Exact effects over the complete frozen 64-candidate and 69-envelope populations | Deployment verification remains fail-fast, while ablation measurement runs both gates; no proposer-distribution or unrestricted-shift generalization; no sampling p-value |
| Prefix-code complexity improves proof-constrained library selection in the complete shadow-guard grammar | [`g09_library_complexity_census_20261015.json`](../experiments/g09_library_complexity_census_20261015.json), SHA-256 `d6deb6b5c538f78e431cd00c91dd239e48029854d73135fed2acfdc4e3ea8f1b` | 64 candidate libraries; 64 calibration-subset episodes; common pool and label-independent prefix code; MDL fully correct 64/64 versus proof-only frozen hash 1/64; routing decisions 4,416/4,416 versus 4,284/4,416; 63 fully-correct corrections and 0 regressions; 132 routing-decision corrections and 0 regressions | Exact bounded complexity-control effect over the complete authored six-shadow-guard library grammar | Not a sample from natural library evolution; current TSP/OR library description length remains unmeasured; no benchmark-accuracy or promotion claim; no sampling p-value |
| No verified runnable official OptiTrust artifact was found in the audited channels | [`optitrust_arxiv_source_audit_20261014.json`](../results/optitrust_arxiv_source_audit_20261014.json) and [`optitrust_artifact_recheck_20261014.json`](../results/optitrust_artifact_recheck_20261014.json) | zero runnable files in the inspected arXiv v1 source; no verified author-linked runnable package in the bounded public recheck | Artifact unavailability under the disclosed audit | Not proof that no artifact exists globally; no published score is substituted for a local run |
| The paper-based OptiTrust-style v1 sensitivity is unscoreable | [`fresh_common38_optitrust_style_synthesis_20261016.json`](../experiments/fresh_common38_optitrust_style_synthesis_20261016.json), SHA-256 `1d844184f5fd2984e3e4aa98ffc5916af48bf949dae82b0aff65a160c8673f2a` | 38 planned; 0 scoreable; 38 infrastructure unavailable; 199 logical requests; 282 physical attempts; 83 retries; 161 complete provider responses; terminal slot distribution 35/1/2 at 5/6/9 slots | Audited adapter-capacity and transport failure for `OptiTrust-style-safe-sidecar`; not an accuracy estimate | Not official OptiTrust, not native five-language execution, no paired accuracy statistic, and no published score substituted |
| The bounded automatic count proposer fails exact resource admission | [`dcp_typed_count_cegis_revision_20261014_audit.json`](../results/dcp_typed_count_cegis_revision_20261014_audit.json), SHA-256 `c3fb17f664ccfbf4e46d08b7695e9730111bcd4b3ccf01cb48074307c6cc03f2` | one physical attempt; 64-member grammar; 20,977 semantic assignments pass; `resource_model_rejected`; candidate not promoted | Falsifiable negative construction trace | Exposed development material; no independent accuracy or general automatic-acquisition claim |
| Exhaustive verification identifies one unique minimum distance-two repair | [`dcp_typed_count_repair_certificate_v3_20261014.json`](../results/dcp_typed_count_repair_certificate_v3_20261014.json), SHA-256 `43af5c30bc8bc69f0c60a990f133fe842e9cfee149119bbcf37b08159730d911` | all 64 hypotheses verified; all six distance-one neighbors fail; minimum passing distance 2; one minimum candidate | Exact minimum repair within the frozen grammar and verifier | Deterministic verifier result, not model discovery, grammar completeness or benchmark-accuracy evidence |
| Matched partition feedback does not pass its engineering progression gate | [`prospective_acquisition_canary_audit.json`](../results/prospective_acquisition_canary_audit.json), SHA-256 `4957610b0fd1bc00dd805957c8e5bd612822fb829cea2bbc314f217101f3645e` | 8 prospective pairs; treatment-only 0; flat-only 0; both 8; neither 0; 44 physical sends; 47,520 total provider tokens; no global safety failure; gate false | A prospective negative result for this fact-equivalent feedback-organization intervention | Six facts were authored; seven units were deterministic synthetic rejected seeds; the canary is underpowered for efficacy and does not test automatic fact discovery, benchmark accuracy, or component necessity |
| Balanced active acquisition improves budgeted identification inside the frozen semantic grammar | [`g08_finite_acquisition_census_20261015.json`](../experiments/g08_finite_acquisition_census_20261015.json), SHA-256 `e588d581da44acf9c6e29999da892940cb849059131afd32e43e3acf203320d2` | complete 20,977-query domain; 32 semantic candidates induce 10 extensional classes; within three queries balanced identifies 10/10 and fixed-order control 6/10; total queries 26 versus 30; worst case 3 versus 4; paired balanced-only 4, control-only 0, both 6, neither 0 | Exact finite-population evidence that balanced verifier-selected witnesses improve bounded behavior-class acquisition in the authored grammar | No sampling p-value; the grammar, oracle and domain are authored; no natural-language fact discovery, resource-policy acquisition, language-model proposer efficacy, benchmark-accuracy or promotion claim |
| Theory components map to separately identifiable interventions | [`component_ablation_identifiability_audit_20261015.json`](../experiments/component_ablation_identifiability_audit_20261015.json), SHA-256 `7c13e7921b38baa89cea5da335131609268bd5dff278c9edd6fe10ba91163bd7` | proposal-level semantic/resource interventions, library-level complexity intervention, envelope-level routing intervention; four planned contrasts; N=38 power 3.1--60.0% over the displayed alpha=.0125 scenarios; seven zero-regression corrections for raw one-sided p<.0125 | A theory-to-experiment identifiability map with immutable outer safety caps | Design and power evidence only; no component effect or necessity claim |
| Historical units do not close the component-ablation sample requirement | [`component_ablation_power_and_unit_inventory_20261015.json`](../experiments/component_ablation_power_and_unit_inventory_20261015.json), SHA-256 `0f75cb740d2f2202a4699598f47e26f02ca3c9c37b211a5bcbc8577a208e1a5e` | at `r=.30,q=.70`, 205/263 valid units for 80%/90% power; one strict historical typed proposal; zero independent repeated common-pool library selections; 2,985 known unique-route envelopes with zero observed no/overlap route outcomes | Exact Holm-conservative planning and metadata-level unit inventory | Planning values are alternatives rather than estimates; no component outcome or dispatch authorization |

## Theory claim classes

### Established within declared scope

- Finite termination when the candidate grammar is finite and each rejection
  removes at least the current candidate.
- Extensional correctness on an exhaustively enumerated finite verification
  domain, conditional on the oracle.
- Exact minimum repair and uniqueness inside a frozen finite grammar.
- Conditional accepted-path correctness when guard, extraction, compilation,
  exact solving and projection obligations all hold.
- Exact resource-limit satisfaction when the compiler accounting is complete.
- Byte-identical fallback outside adoption for the implemented selective
  wrapper.

### Conditional design results

- The prefix-code generalization bound requires a label-independent code,
  frozen hypothesis family and valid independent evaluation units. The current
  authored development grammars do not themselves establish this result.
- Anytime promotion control requires fresh valid groups, a frozen candidate for
  every generation and prespecified error allocations whose sum is bounded.
- Complexity-weighted promotion additionally requires a candidate family and
  prefix code frozen before the same promotion outcomes; the current runs did
  not implement this allocation.
- Cumulative regression budgeting requires one unchanged target distribution
  and endpoint across versions. TSP and OR-Debug are different targets and
  cannot be telescoped into a repeated-evolution guarantee.
- Geometric version-space contraction requires a uniformly balanced separating
  witness at every reachable non-singleton state. This premise has not been
  established for the current proposer.
- Conservative extension guarantees exact previous-library behavior outside
  unique new-skill coverage, but provides no accuracy guarantee inside that
  coverage region.
- Modular library utility is an exact sum of routed corrections minus routed
  regressions only when the router selects at most one skill. It does not
  establish correctness for interacting multi-skill rewrites.
- Library-level prefix-code control requires the serialized router-and-skill
  code to be label-independent and frozen before the evaluated outcomes. The
  current authored libraries do not isolate this effect empirically.
- Conservative non-degradation requires true dominance inside the adopted
  region. Zero observed regressions is empirical evidence on the evaluated
  cohorts, not a distribution-free theorem.

The post-review revision limits component-level causal language to its valid
experimental unit. A prospective identifiability audit separates semantic and
resource admission at proposal level, complexity control at library-selection
level, and routing at envelope level. A single final benchmark table cannot
isolate these effects. Complete finite-population censuses now identify
semantic- and resource-admission effects in the 64-member typed-count grammar,
an exactly-one routing effect in the 69-envelope grammar, and a
complexity-control effect over all 64 calibration subsets of the authored
six-shadow-guard library grammar. Independent gate measurement reveals all
four semantic/resource cells. The complexity result is exact for its finite
grammar and does not estimate natural library evolution or the description
length of the current TSP/OR libraries.

G07 is now closed only for its stated bounded requirement: the completed fresh
common-38 protocol compares current, Base, BIND and CoE-safe on one fixed
endpoint. The separate scope audit preserves the stronger broad-superiority
boundary. It does not open the 219 reserved DCP confirmation identities after
the prespecified development gate failed, and it does not dispatch MIPLIB-NL
before that source has a frozen scoreable endpoint, semantic-lineage review and
resource/reference contract. A second source remains a future replication
requirement for broad benchmark superiority rather than a missing cell in the
reported common-38 estimand.

The synthetic four-node worked example in [`WORKED_EXAMPLE.md`](WORKED_EXAMPLE.md)
has SHA-256
`11f41d0809fc62c03b6109da3e28cf665c0ee8bd552a17bf2f25a3d31d414152`.
Direct enumeration leaves three tours up to reversal: costs 10, 6 and 12; only
the cost-12 tour satisfies both the forbidden-edge and exclusive-or contract.
The example is explanatory and contributes no benchmark row or endpoint claim.

### Hypotheses requiring new experiments

- A redesigned intervention that acquires or selects correctness-relevant
  atomic facts improves typed-skill construction relative to a matched control.
  The tested partition-annotation intervention is not advanced because its
  eight-pair engineering gate failed with zero discordance.
- A compact `OptiTrust-style-safe-sidecar` adapter that generates one canonical
  model plus five hash-bound typed reviews passes an outcome-blind canary and
  yields scoreable terminal outcomes. The failed v1 full-model representation
  may localize capacity risk but cannot supply an accuracy estimate.
- For a future broad-superiority claim, the fresh common-38 advantage
  replicates on a second source lineage or a larger independently frozen
  multi-family cohort. The bounded common-38 claim itself is complete.
- The bounded description-length result replicates under naturally proposed
  libraries rather than the authored shadow-guard grammar.
- A learned router, beyond the deterministic exactly-one rule, preserves
  calibrated risk under unrestricted language and family shift.

## Main-text and supplement allocation

Keep the skill tuple, library transition, five conditional properties, paired
accuracy decomposition, TSP and OR-Debug results, mixed-router identity, and
the bounded external-comparison table in the main paper. Place full
counterexample ledgers, compiler accounting, hashes, adapter failure taxonomies,
nominal item-level statistics and request-cost ledgers in supplementary
material. SkillOpt and AlphaOPT common-40 rows may appear in a supplementary
reproduction table; they should not be inserted into the main comparison as if
all methods shared one native protocol.

## Submission-critical boundaries and optional extensions

1. **Natural-language acquisition beyond the bounded census.** Preserve the
   completed negative eight-pair canary and the positive exact finite census.
   The next acquisition study must derive candidate semantic axes or atomic
   facts from natural-language benchmark failures under outcome-blind custody,
   while keeping the proposer outside the verifier and promotion boundary. Do
   not expand the ineffective partition-annotation treatment or relabel the
   authored finite grammar as discovered knowledge.
2. **Fresh common replication for any broader claim.** The RCPSP/VRPTW
   Base/current/BIND/CoE-safe comparison closes the bounded G07 requirement.
   Add a second source lineage or larger independently frozen multi-family
   cohort only before making a broad superiority claim. Do not open the sealed
   DCP confirmation set after its failed promotion gate, and do not dispatch
   MIPLIB-NL before it is score-ready. Official OptiTrust remains
   artifact-unavailable unless a verified runnable author package is obtained.
   Keep `OptiTrust-style-safe-sidecar` separate; its v1 result has zero
   scoreable outcomes and is not an accuracy estimate.
3. **Natural component replication.** Preserve the exact finite semantic,
   resource, routing and complexity censuses. A stronger claim requires
   naturally proposed libraries or a second independently authored library
   grammar. Do not convert deterministic census rows into sampling p-values or
   broad necessity claims.
4. **Controlled endpoint review (closed).** A fresh-context reviewer reproduced
   TSP, OR-Debug and common-38 exactly from hash-bound restricted inputs. Keep
   this aggregate attestation distinct from the public integrity package: it
   verifies endpoint custody but does not grant redistribution rights.
5. **Archival completion.** The public history-free repository, author
   metadata, scoped licenses, disclosure text, final figures and worked
   example are complete. Deposit the exact release in an external archive and
   add the verified DOI; do not infer a DOI from the GitHub Release.

## Validation performed for this audit

- Recomputed every current file hash referenced above.
- Compared the TSP, OR-Debug, mixed-router, external common-40, automatic
  proposer and exact-repair numeric fields with the manuscript prose.
- Recomputed the metadata-only proposal-class counts and every exact paired
  power-table entry used to delimit the automatic-acquisition study.
- Reparsed all 44 provider envelopes in the matched canary, reverified every
  typed response, reconstructed the full eight-pair denominator and token
  accounting, and confirmed the 0/0/8/0 paired table and failed progression
  gate without reading request or response bodies into this public audit.
- Reconstructed the 38-record larger RCPSP/VRPTW metadata projection from the
  pinned source, checked uniqueness, zero prepared-text overlap, endpoint
  availability and every displayed common-protocol power entry.
- Reconstructed all 38 common public packets, verified that their public
  readiness manifest contains no packet bodies, and independently recompiled
  them through the authored RCPSP/VRPTW typed router. All 38 route uniquely,
  pass the fixed resource caps and match the source-reported variable and
  constraint counts; no solver or endpoint score was invoked, so this is
  structural readiness rather than accuracy evidence.
- Reconstructed the frozen one-thread current-method native plan and all 38
  private solver checkpoints, recompiled every model, rescored every endpoint,
  and reproduced the body-free 30/38 result exactly. The 30 optimal cells are
  all correct; seven limits and one unresolved numerical status are retained as
  solver unavailable rather than retried or silently excluded.
- Reconstructed the fresh common-38 Base, BIND and CoE-safe public results from
  their private ledgers without new API calls, aligned all five method views on
  the same 38 identities, recomputed the four paired correction/regression
  tables and exact tests, and reproduced the Holm-adjusted p-values and
  answer-blind at-most-one-call sensitivity view.
- Independently recomputed the controlled TSP, OR-Debug and common-38
  endpoints. TSP reproduced 54/140 versus 100/140; OR-Debug reproduced every
  one of 2,845 records and 5,690 arm objects after 5,597 local Gurobi calls;
  common-38 reproduced 30/0/13/13/4 and all paired/Holm values using raw-byte
  ledger hashes without parsing request or response payloads. The attestation
  contains aggregate values and hashes only.
- Verified the G07 scope decision against the failed DCP development gate and
  still-sealed 219-identity confirmation partition, and against MIPLIB-NL's
  metadata-only, non-score-ready status. No new source was dispatched.
- Enumerated all 64 typed-count candidates and all 69 frozen routing envelopes,
  recomputed every admission and routing decision, and reproduced the bounded
  resource and exactly-one routing effects without API, solver, native or
  evaluator-only access.
- Enumerated all 64 optional-shadow-guard libraries and all 64 calibration
  subsets, reconstructed both selectors and reproduced 63 fully-correct and
  132 routing-decision corrections with zero regressions.
- Recomputed all four alpha=.0125 component power rows, the seven-correction
  zero-regression threshold, and the proposal/library/envelope intervention
  mapping without opening benchmark outcomes.
- Recomputed the exact 80% and 90% sample-size tables and verified that the
  historical proposal, library-selection and routing counts do not satisfy the
  corresponding unit definitions.
- Verified the public `v1.0.0` zero-parent candidate, all release assets and the
  remote recursive main/submodule acquisition. The canonical public-integrity
  entrypoint runs 79 Layer-A tests and three deterministic checks; 12 additional
  release/provider tests pass in the separately declared provider environment.
  The current manifest binds the full tracked public evidence surface with zero
  restricted or private source paths. The public package reconstructs integrity
  and aggregate arithmetic, while restricted endpoint rescoring remains under
  the separate controlled-review protocol. Scoped licenses, rights decisions,
  NOTICE, publisher migration and public release are closed; the DOI is open.
- Rechecked every numeric statement in the theory-to-evidence mapping against
  the sealed count, TSP, OR-Debug and mixed-router artifacts.
- Checked that the main draft records the transition from distributed pinned
  closures to the implemented canonical skill/library manifests while limiting
  empirical complexity evidence to the authored finite shadow-guard grammar.
- Confirmed that every manuscript citation key resolves and that no bibliography
  entry is unused.
- Confirmed zero carriage returns, zero control character `0x01`, zero doubled
  inline-math backslashes and a clean `git diff --check` result after formula
  normalization.
- Made no model, API, benchmark-solver, native-evaluator or VM call and read no
  credentials, request bodies, response bodies or evaluator-only answers.
