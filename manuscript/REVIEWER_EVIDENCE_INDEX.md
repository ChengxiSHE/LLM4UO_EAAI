# Reviewer evidence index

This page is the shortest route from the public, answer-free artifacts to the
paper's displayed numerical claims. It distinguishes aggregate reconstruction
from restricted endpoint rescoring.

## One-command aggregate reconstruction

From the repository root, run:

```bash
python3 scripts/build_reviewer_claim_table.py --check
```

The command reads exactly four public aggregate artifacts and verifies
[`results/reviewer_claim_table_v1_20261016.json`](../results/reviewer_claim_table_v1_20261016.json):

| Claim family | Public input |
|---|---|
| TSP endpoint | [`results/tsp_constraint_confirmation_root_closure_20261014.json`](../results/tsp_constraint_confirmation_root_closure_20261014.json) |
| OR-Debug released and source-corrected endpoints | [`results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json`](../results/public_projections/or_debug_confirmation_evaluation_projection_20261015.json) |
| Fresh common-38 implementation comparison | [`experiments/fresh_common38_common_protocol_synthesis_20261015.json`](../experiments/fresh_common38_common_protocol_synthesis_20261015.json) |
| Mixed-router identity reconstruction | [`results/mixed_skill_confirmation_public_audit_v3_20261015.json`](../results/mixed_skill_confirmation_public_audit_v3_20261015.json) |

The generated table contains aggregate counts and input hashes only. It does
not contain task bodies, item-level outputs, provider traffic, evaluator-only
answers, or credentials. The OR-Debug released-label endpoint is the paper's
primary public endpoint; the source-corrected endpoint is a sensitivity.

## Evidence surfaces and counts

Path counts and test counts describe different objects. Their equal value in
the `v1.1.1` row is coincidental.

| Surface | Identity | Evidence paths | Executed tests | Purpose |
|---|---|---:|---:|---|
| Superseded independent public review snapshot | pre-`v1.1.1` review | 70 paper-evidence paths | 79 Layer-A tests; 12 additional dependency-enabled release tests reported separately | Historical externalized integrity review; superseded after the publisher cleanup race was fixed |
| Immutable public release | tag `v1.1.1`, commit `ed663fcdf8336f77c466652a516d5bc2c567f93a` | 81 release-manifest paths | 81 Layer-A tests plus 3 deterministic reconstruction checks | Current public, history-free integrity package |
| Frozen pre-review submission overlay | commit `183789ab988b3e3e4035763ea74b394896fbf2a3` | 86 paper-evidence paths | 82 Layer-A tests plus 3 deterministic checks | Adds manuscript and archival-deposit evidence without changing the immutable release |
| Current post-review overlay | working revision after prospective mechanism studies | 139 paper-evidence paths | 150 Layer-A tests plus 4 deterministic checks | Adds claim calibration, reviewer reconstruction, completed FormulationBench and NLEquiv mechanism results, infrastructure root-cause closure, and the aggregate mechanism synthesis |

The post-review counts are bound by the current paper manifest and are not
retroactively assigned to the immutable `v1.1.1` release.

## What can be reproduced publicly

The public package reconstructs:

- the displayed TSP, OR-Debug, common-38, and mixed-router aggregate tables;
- input byte hashes and claim boundaries;
- the 2,985 direct-versus-mixed output identities from metadata-only
  projections;
- release provenance, scoped licensing, figure Source Data, and the
  credential-free integrity suite.

It cannot publicly rescore restricted upstream task bodies or evaluator-only
answers. A hash proves identity only when the referenced artifact is available;
the generated claim table therefore binds only public aggregate inputs.

## Controlled endpoint recomputation

The restricted recomputation protocol is frozen in
[`docs/CONTROLLED_ENDPOINT_REVIEW_PROTOCOL_20261016.md`](../docs/CONTROLLED_ENDPOINT_REVIEW_PROTOCOL_20261016.md),
and its aggregate-only audit is
[`docs/CONTROLLED_ENDPOINT_REVIEW_AUDIT_20261016.md`](../docs/CONTROLLED_ENDPOINT_REVIEW_AUDIT_20261016.md).
It recomputes TSP, OR-Debug, and common-38 endpoints without publishing task
bodies, response bodies, or evaluator-only answers. The completed audit was a
fresh-context, author-controlled computational review; it is not presented as
an unaffiliated human replication.

Artifact reviewers may request controlled access from the corresponding author
at `522023150104@smail.nju.edu.cn`. Access is conditional on the upstream
benchmark terms and must use the frozen hashes and aggregate-only output policy.
The custodian cannot grant redistribution rights that the upstream sources do
not provide.

## Interpretation boundary

The aggregate reconstruction verifies reported counts. It does not establish
that the proof-carrying architecture caused the TSP or OR-Debug gains relative
to another implementation of the same semantic knowledge. The finite
component censuses are exhaustive contract tests of authored populations, not
a substitute for a task-level matched comparison.

That matched question has now been tested prospectively. The strict
FormulationBench same-fact study scores Flat-K at 40/89 and PCK-K at 36/89,
with 7 PCK-K corrections, 11 regressions and `p=0.8811`. NLEquiv-150 scores
Flat-K and Structured-K at 124/150 each; routed generic skills reach 128/150,
but the paired gate fails at `p=0.2617`. Reviewers should therefore read the
paper as evidence for complete benchmark-specific knowledge compilation into
an auditable fail-closed runtime, not as evidence that proof-carrying structure
alone improves accuracy. The aggregate-only synthesis is
[`same_knowledge_mechanism_synthesis_20261017.json`](../experiments/same_knowledge_mechanism_synthesis_20261017.json).
