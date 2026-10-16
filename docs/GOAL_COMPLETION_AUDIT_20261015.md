# Goal completion audit

**Status:** active with only archival DOI completion open, updated 2026-10-17
after the independent RetailOpt-190 confirmation. The machine-readable source is
[`goal_completion_audit_20261015.json`](../experiments/goal_completion_audit_20261015.json).

## Decision

The project has a coherent artifact methodology, three source-level modeling
accuracy studies, a fixed common-38 implementation comparison, exhaustive
finite contract tests, locally rerun external baselines, publication-size
figures, a public history-free release, and a controlled endpoint-review path.

The review changed the completion decision. TSP and OR-Debug improve final
formulation accuracy relative to their frozen controls, but those comparisons
also change the supplied semantic knowledge. They do not causally identify the
value of proof-carrying representation, verification, routing, or promotion
relative to another implementation of the same knowledge. The strict
FormulationBench same-fact comparison and the independent NLEquiv diagnostic
are complete; neither passes its prespecified mechanism gate. G09 therefore
closes with the boundary that architecture-only accuracy improvement remains
unsupported. A revised short-decision, sparse-retrieval and counterexample-
witness method subsequently passes its prospectively frozen RetailOpt-190 gate:
50/190 for Base versus 170/190 for routed knowledge, with 25 corrected and one
regressed archetype. A post hoc label-blind replication reaches 185/190 and
removes arm-label priming as an alternative explanation. G15 therefore closes
with a single-source, authored-knowledge boundary. G13 remains open because no
external archival DOI has been verified.

## Requirement-level status

| ID | Status | Current strongest evidence or boundary |
|---|---|---|
| G01 | Closed | `Abstract -> Acquire -> Admit -> Route -> Promote` is implemented as a versioned skill/router library with content-addressed manifests and exact 2,985-output reconstruction. The novelty claim is limited to the optimization-modeling-specific composition. |
| G02 | Closed | TSP improves 54/140 to 100/140. OR-Debug released-label accuracy improves 828/2,845 to 2,236/2,845; the source-corrected 2,752/2,845 result is a sensitivity. |
| G03 | Closed with boundary | Mixed routing reconstructs 2,985/2,985 direct outputs. Unrestricted paraphrase and new-family routing remain untested. |
| G04 | Closed with boundary | BIND is locally rerun: 31/40 answer-blind first round and 40/40 answer-bearing final on the retrospective panel; common-38 is 13/38 in both rows. |
| G05 | Closed with boundary | CoE official-code snapshots are locally rerun through the fixed safe adapter; unsupported generated programs remain explicit. |
| G06 | External artifact unavailable | The audited OptiTrust source has no verified runnable official package. Published scores are not substituted. |
| G07 | Closed with boundary | Common-38 scores are current/Base/BIND-round1/BIND-final/CoE-safe = 30/0/13/13/4. This is an unequal-regime implementation comparison over two families and one source lineage. |
| G08 | Closed with boundary | The language-model canary is negative; the finite authored grammar has a positive exact 10-class active-acquisition census. Natural-language fact discovery remains unsupported. |
| G09 | **Closed with boundary** | Finite authored populations exhaustively test semantic admission, resource admission, exactly-one routing, and description-length selection. On the strict 89-pair same-fact FormulationBench comparison, PCK-K scores 36/89 versus Flat-K 40/89 (`p=0.8811`) and the mechanism gate fails. On independent NLEquiv-150, same-fact structuring ties 124/150 and routed generic skills reach 128/150 versus 124/150 (`p=0.2617`); that gate also fails. Architecture-only accuracy improvement is unsupported. |
| G10 | Closed with boundary | The manuscript has a direct public aggregate reconstruction command, evidence index, 18/18 citation closure, controlled-review boundary, synchronized paper frame, and blind-review synthesis. Stronger integrated-system novelty still requires faithful common-task comparison. |
| G11 | Closed | Public `v1.1.1` is a zero-parent history-free release; a fresh recursive clone passed 81 Layer-A tests and three deterministic checks, including remote submodule acquisition. |
| G12 | Closed | The worked example and both main figures pass source, resolution, font, collision, alignment, and final-size QA. |
| G13 | **Partial** | Author metadata, licenses, NOTICE, disclosures, repository, release, and deposit packet are complete. An externally verified DOI is absent. |
| G14 | Closed with boundary | The expanded OptiTrust-style run ended in transport failure; the indexed replacement passed capacity but failed two method gates and therefore has no accuracy row. |
| G15 | **Closed with boundary** | On independent RetailOpt-190, Base/knowledge score 50/170 of 190 and 10/34 of 38 five-variant archetypes, with 25 corrections, one regression and `p=4.02e-7`. The post hoc label-blind robustness is 50/185 and 10/37 with 27/0. This establishes a bounded complete-method gain from authored routed knowledge, not architecture-only causality or automatic acquisition. |

## Blind-review resolution

| Concern | State | Action |
|---|---|---|
| BR-C1: knowledge and architecture are confounded | Closed with negative boundary | Claims remain narrowed to complete-system gains. The strict FormulationBench same-fact comparison is negative, and NLEquiv provides neutral structure-only plus directional but non-significant routed-skill evidence. Neither supports architecture-level accuracy improvement. |
| BR-C2: review evidence is hard to traverse | Closed with boundary | Added public claim-table builder, generated aggregate table, reviewer evidence index, and controlled-access contact route. Restricted rescoring remains non-public. |
| BR-C3: corrected OR-Debug endpoint dominates the headline | Closed with boundary | Released labels are primary; source correction is a sensitivity. |
| BR-C4: finite censuses described as causal evidence | Closed | Recast as exhaustive contract tests over authored populations. |
| BR-C5: mixed evidence levels and stale status prose | Closed | Rewrote the abstract and replaced the historical paper frame with one current evidence hierarchy. |
| BR-C6: revised method lacks direct-modeling confirmation | Closed with boundary | RetailOpt-190 supplies an independent prospectively frozen endpoint and a passed paired gate; the label-blind run is same-benchmark post hoc robustness. Broad benchmark superiority remains unsupported. |
| BR-N1: closest-method novelty | Partial | Added a claim-level precedent map; stronger superiority needs faithful common-task implementation. |

## Next valid work

1. Preserve FormulationBench and NLEquiv as opened negative development
   evidence; do not reinterpret them as confirmation of RetailOpt.
2. Keep the label-blind replication explicitly post hoc and do not count the
   five numerical variants as independent inferential units.
3. Resolve the RetailOpt root-license/README discrepancy before redistributing
   any upstream task body.
4. Deposit the exact public `v1.1.1` release and current evidence overlay
   externally and bind only a verified
   DOI.

Existing TSP, OR-Debug, common-38, exposed DCP, and historical Text2Opt outcomes
cannot be reused as a new confirmation set. The RetailOpt studies used frozen
AntChat DeepSeek-V4-Flash transport contracts and 157 physical API attempts,
154 successful model responses and 1,140 local solver calls across source,
compiler, primary and robustness checks. Public audit artifacts contain no
credential, request body, response body, objective or per-item result.
