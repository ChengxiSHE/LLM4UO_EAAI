# Main-figure evidence plan

Status: Figures 1 and 2 rendered and final-size QA passed with the saved Python
backend on 2026-10-15. No numerical result in this plan is newly computed.

## Figure 1 — method architecture

**Core conclusion.** Benchmark failures can be converted into versioned,
checkable modeling skills without allowing the proposer to modify the verifier,
endpoint or promotion rule.

**Results-level question.** What is the reproducible method, and where do its
formal and empirical guarantees enter?

**Archetype.** Schematic-led composite.

**Panel map.**

- **a — Library state.** Show
  `skill = guard + evidence + transform + verifier + resources + provenance`
  inside `library = skills + public router + immutable verifier + frozen
  endpoint + lineage ledger`.
- **b — Construction loop.** Failure obligation to finite candidate grammar,
  verifier counterexample, version-space elimination and admitted skill. Mark
  the language model or external method as an untrusted proposer.
- **c — Execution path.** Public input to exactly-one guard, proof-carrying
  compilation, exact resource admission and solver/projector. Zero or multiple
  guards abstain to the unchanged fallback.
- **d — Promotion path.** Paired full-denominator endpoint outcomes split into
  correction, regression, unchanged-correct and unchanged-wrong. A frozen
  confidence gate appends an accepted content-addressed version or leaves the
  previous version unchanged.

**Boundary labels required in the figure.** Finite-domain guarantee;
conditional accepted-path correctness; empirical benchmark gain; no universal
natural-language proof; no unrestricted recursive self-improvement.

This figure should establish vocabulary and process, not display the headline
accuracy results. It should use the same neutral, method and warning colors as
the quantitative result figure.

**Delivered output.** The four-panel schematic is rendered at 180 mm as
editable PDF/SVG with 600-dpi PNG/TIFF companions. Strict source, rendered
text, collision, panel-alignment and final-size visual checks pass. The
machine audit is `experiments/figure1_render_qa_20261015.json`.

## Figure 2 — endpoint improvement and preservation

**Core conclusion.** Proof-carrying skill libraries improve full-denominator
benchmark accuracy in two separately frozen studies with no observed paired
regressions, while the public-only composition router preserves every direct
family output.

**Results-level question.** Does the admitted knowledge improve the endpoint
relative to a strong frozen control, and does composition introduce behavioral
drift?

**Figure archetype.** Quantitative grid with an asymmetric hero panel.

**Delivered output.** Main-text vector PDF and SVG at 180 mm width; editable
text; all glyphs at least 5 pt at final size; companion source-data tables; 600
dpi PNG and TIFF. The saved backend is Python/Matplotlib. Strict source,
rendered-text, collision, panel-alignment and final-size visual checks pass; the
machine audit is `experiments/figure2_render_qa_20261015.json`.

### Panel map

| Panel | Scientific question | Evidence role | Decisive comparison | Unique inference |
| --- | --- | --- | --- | --- |
| **a — Full-denominator accuracy** | Does the method improve each frozen endpoint? | Primary quantitative evidence; largest panel | TSP 38.57% to 71.43%; OR-Debug 29.10% to 96.73% | Establishes large within-study endpoint gains without pooling unlike endpoints |
| **b — Paired outcome decomposition** | Are gains corrections or hidden regressions? | Mechanism/control | TSP: 54 both correct, 46 corrections, 0 regressions, 40 both wrong; OR-Debug: 828 both correct, 1,924 corrections, 0 regressions, 93 both wrong | Shows that the observed deltas arise entirely from corrections on the two evaluated cohorts |
| **c — Group consistency** | Are results concentrated in a narrow subgroup? | Stratification | TSP: positive gain at all seven evaluated sizes 13--19; OR-Debug: 65 positive, 35 tied, 0 negative structural groups | Bounds concentration and makes the valid dependence unit visible |
| **d — Composition identity** | Does the mixed router alter direct-family behavior? | Orthogonal validation | 140/140 TSP and 2,845/2,845 OR-Debug outputs exactly match direct execution; all mismatch and failure counts are zero | Establishes frozen-interface preservation, not new accuracy |

### Evidence hierarchy

- **Hero evidence:** panel a, within-study full-denominator accuracy.
- **Primary control:** panel b, paired corrections and regressions.
- **Breadth evidence:** panel c, size- and group-level consistency.
- **Reliability evidence:** panel d, exact mixed-router identity.

### Visual encoding

- Frozen controls use a neutral grey-blue.
- Proof-carrying skills use one saturated blue.
- Corrections use restrained green; regressions reserve red even though their
  observed count is zero. Both-wrong remains light grey.
- TSP and OR-Debug retain the same method colors in every panel; benchmark
  families are separated by position and labels rather than unrelated hues.
- Panel a uses paired horizontal bars on a common 0--100% accuracy axis. Panel
  b uses 100% stacked bars with exact counts printed
  outside narrow segments. Panel c must distinguish seven TSP size strata from
  100 OR-Debug structural groups and must not imply equal sampling units. Panel
  d should show exact-match counts and an explicit `accuracy not rescored`
  annotation.

### Statistics and integrity

- TSP rows share template lineage; do not attach an item-level significance
  marker to panel a. Display `n=140`, seven size strata and the shared-lineage
  note.
- OR-Debug inference uses 100 structural groups: 65 positive, 35 tied and zero
  negative; the prespecified group sign test is
  `p=2.710505431213761e-20`. Display the group count and test definition in the
  legend, not as an unexplained star.
- Zero regressions is an observation, not a distribution-free guarantee.
- Panel d inherits direct-family outputs and does not recompute endpoint
  accuracy.
- No error bars are appropriate for the exact frozen finite-cohort percentages.
  If confidence intervals are later added, they must be group-aware and clearly
  separated from the finite-cohort descriptive values.

### Source-data contract

The figure source table should contain only aggregate non-secret fields:

```text
study, denominator, control_correct, method_correct,
both_correct, corrections, regressions, both_wrong,
group_unit, positive_groups, tied_groups, negative_groups
```

The router source table should contain family, records, exact matches, route
mismatches, output mismatches, source mismatches and terminal failures. It must
not contain task text, request bodies, response bodies, evaluator-only answers
or credentials.

### Reviewer risks

1. The two endpoint definitions differ. Keep them as two within-study contrasts
   and do not report a pooled effect.
2. TSP item rows are not independent. Show size strata and avoid nominal
   item-level inference.
3. The OR-Debug gain is large enough that reviewers may suspect evaluator
   leakage. State the frozen custody boundary and that confirmation scoring made
   zero model/API calls.
4. A zero-height regression segment can disappear. Preserve a visible
   zero-regression label and red key rather than implying the category was
   omitted.
5. Mixed-router identity is retrospective composition. Keep it visually
   subordinate to endpoint accuracy and label it as identity rather than a new
   performance estimate.

### Draft legend

**Fig. 2 | Endpoint gains and frozen-interface preservation.** **a,**
Full-denominator benchmark accuracy of the frozen control and proof-carrying
skill or library for the TSP confirmation cohort (`n=140`) and OR-Debug
confirmation cohort (`n=2,845`). Lines connect methods evaluated on the same
records; percentages are descriptive values for each frozen finite cohort.
**b,** Paired endpoint outcomes partition each cohort into both correct,
correction, regression and both wrong. No paired regression is observed in
either study. **c,** Direction of the paired effect across the seven evaluated
TSP sizes and 100 OR-Debug structural groups. The OR-Debug group sign test uses
65 positive, 35 tied and zero negative groups
(`p=2.710505431213761e-20`, prespecified one-sided test). TSP rows share template
lineage and receive no item-level significance claim. **d,** Exact output
identity of the public-only mixed router relative to pinned direct-family
execution: 140 of 140 TSP and 2,845 of 2,845 OR-Debug records match, with zero
route, output, source or terminal mismatches. Panel d is a retrospective
composition audit and does not recompute accuracy. Source data are provided as
a Source Data file.

## Additional figures if space permits

- **Figure 3 — construction mechanism:** show both completed acquisition
  results. The eight-pair language-model canary has zero discordance and fails
  its progression gate. In the separate complete ten-class census, balanced
  verifier-selected witnesses identify 10/10 classes within three queries
  versus 6/10 for frozen canonical-order witnesses. Label the positive result
  as an exact effect inside an authored grammar, not natural-language skill
  discovery.
- **Figure 4 — fresh common protocol:** show the completed 38-identity
  RCPSP/VRPTW cohort. Current, Base, BIND round one, BIND answer-bearing final
  and CoE-safe score 30, 0, 13, 13 and 4 of 38. Keep the answer-blind
  at-most-one-call sensitivity separate, and display the one-source-lineage,
  unequal-native-budget and non-equalized-construction-cost boundaries.
- **Extended Data:** retrospective fixed common-40 reproduction boundaries,
  typed-count negative proposer and exact distance-two repair, finite
  semantic/resource/routing/complexity censuses, resource accounting, and
  release provenance.
