# Final blind-review synthesis — 2026-10-16

Three reviewers assessed the same immutable packet independently: one focused
on originality and significance, one on technical validity, and one on
reproducibility and readability. Reports were frozen before synthesis. A point
is called consensus only when at least two reviewers raised it independently.

## Decision

The evidence supports a **bounded systems result**: two authored,
benchmark-specific knowledge pipelines improve final formulation accuracy over
their frozen controls, a public-only router preserves 2,985 direct outputs, and
the released integrity surface is unusually well audited. The packet does not
yet support a causal claim that proof-carrying representation, verification,
routing, or promotion explains the benchmark gains beyond supplying the
benchmark-specific knowledge itself.

The current submission posture is therefore **major revision**, not a failed
experiment. The accuracy results remain valid on their declared endpoints. The
paper must distinguish those system-level results from finite contract tests
and from prospective theory.

## Consensus concerns

| ID | Concern | Reviewers | Disposition |
|---|---|---|---|
| BR-C1 | Benchmark gains change knowledge content and mechanism together; they do not isolate the architecture's causal contribution. | R1, R2 | Blocking for a mechanism-superiority claim. The manuscript is narrowed to a complete-system case study; a same-knowledge task-level control remains open. |
| BR-C2 | The review packet did not give one direct route from supplied public artifacts to the headline tables, and restricted endpoint recomputation was described more clearly than it was operationalized. | R2, R3 | Addressed by a public aggregate reconstruction script, generated claim table, evidence index, and explicit controlled-access route. Restricted rescoring remains custody-limited. |
| BR-C3 | The 516-record OR-Debug source correction materially changes the headline result and lacks public record-level adjudication. | R2, R3 | The unmodified released-label endpoint becomes primary; the source-corrected endpoint is retained as a prespecified sensitivity. |
| BR-C4 | Constructed finite censuses verify declared contracts but were described too strongly as causal mechanism evidence. | R1, R2 | Recast as exhaustive contract tests over authored finite populations. They do not explain the natural benchmark gains. |
| BR-C5 | The abstract and status documents mix endpoint results, retrospective identity checks, unequal-budget comparisons, finite censuses, and prospective theory. | R1, R3 | Abstract and authoritative paper frame are rewritten around an explicit evidence hierarchy; historical status prose is removed from the current frame. |
| BR-C6 | Generality remains limited by authored skills, one common-cohort source lineage, and unresolved lineage dependence in inferential units. | R1, R2 | Effect counts remain; probability language is made conditional and secondary. Broad benchmark superiority remains unsupported. |

## Additional non-consensus concerns

- **BR-N1:** novelty relative to the nearest integrated skill/versioning and
  verification systems needs a traceable, claim-level comparison. This was a
  blocking concern for the originality reviewer and remains open.
- **BR-N2:** the public release, independent review snapshot, and submission
  overlay used nearby path and test counts. A reconciliation table now names
  each surface explicitly.
- **BR-N3:** “independent reviewer” could imply unaffiliated human replication.
  Current prose uses “fresh-context, author-controlled computational review.”
- **BR-N4:** the common-38 table needed terminal-status and execution-contract
  context. The supplement now gives a compact protocol/status table.

## Claim posture after revision

Permitted:

- final formulation accuracy increased on the frozen TSP and OR-Debug
  benchmarks relative to the named controls;
- the released-label OR-Debug result is 2,236/2,845 versus 828/2,845, with
  1,408 corrections and no regressions;
- the source-corrected OR-Debug sensitivity is 2,752/2,845;
- the complete authored pipelines score 30/38, 0/38, 13/38, 13/38, and 4/38
  on the fixed common cohort under disclosed unequal regimes;
- the finite censuses exhaustively test the declared contracts in their
  authored populations.

Not permitted without new evidence:

- the proof-carrying architecture caused the benchmark gains relative to an
  alternative implementation of the same knowledge;
- the common-38 table is an equal-budget algorithmic leaderboard;
- the corrected OR-Debug endpoint is more authoritative than the released
  labels;
- finite authored censuses establish behavior under natural proposals,
  libraries, or distribution shift;
- automatic natural-language knowledge discovery or broad benchmark
  superiority.

## Remaining scientific gate

A stronger methodology claim requires a prospectively frozen task-level study
that holds the semantic knowledge fixed and varies its representation or
admission/deployment mechanism. Reusing already opened TSP, OR-Debug, or
common-38 outcomes would not satisfy this gate. Until such a study exists, the
publishable contribution is the audited system and evidence discipline rather
than a causal decomposition of its gains.
