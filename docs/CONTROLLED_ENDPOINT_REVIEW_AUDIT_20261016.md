# Controlled endpoint review audit — 2026-10-16

## Independent execution

A fresh-context reviewer executed the frozen controlled-review protocol from
hash-bound private inputs and public scoring code. All temporary programs and
solver workspaces were confined to `/private/tmp`; the project tree was not
written. The aggregate attestation contains no problem body, reference value,
point, repair object, request body, response body, credential or per-instance
row.

## TSP sealed confirmation

All 10 plan pins matched. In-memory scoring reproduced the complete 140-row
public and private evaluations and every root-closure field and byte hash. The
static controller scored 54/140 and the typed skill 100/140, with 46
corrections, zero regressions and one-sided exact
`p=1.4210854715202004e-14`. No new model, API or scoring-solver call was made.

## OR-Debug confirmation

The reviewer verified the dataset, split, plans, terminal method outputs and
all nine evaluator-code hashes. A no-solver preflight matched 22,388/22,388
deterministic fields. A full temporary re-evaluation then made 5,597 local
Gurobi calls and reproduced all 2,845 records and 5,690 arm objects exactly.
The corrected endpoint was 828/2,845 versus 2,752/2,845, with 1,924 corrections
and no regressions. The released-label endpoint was 828/2,845 versus
2,236/2,845, with 1,408 corrections and no regressions. The 100-group result
was 65 positive, 35 tied and zero negative groups, with one-sided
`p=2.710505431213761e-20`. Model/API calls were zero.

## Fresh common-38

The final compliant path did not call the historical Base, BIND or CoE audit
builders and did not open their SQLite ledgers. It checked the three plans,
three public results and three private ledgers by raw-byte SHA-256 only; no
request or response payload was parsed. The public synthesis then reproduced
all 38 aligned identities, method counts `30/0/13/13/4`, paired
corrections/regressions `30/0`, `18/1`, `18/1`, `26/0`, and every exact and
Holm-adjusted test. Model, API and solver calls were zero.

An earlier exploratory builder run had deserialized frozen response JSON in
process while verifying response hashes. The reviewer did not inspect or emit
those contents, and the final common-38 conclusion does not depend on that run;
it depends only on the byte-hash-only path above.

## Conclusion and boundary

No numerical, identity, scoring or paired-statistic discrepancy was found. The
controlled review independently recomputes the three central endpoint families
under restricted-data custody. It strengthens the endpoint evidence but does
not make the restricted material redistributable or turn the public
`v1.0.0` integrity package into a public endpoint-rescoring package.
Common-38 remains a fixed-cohort comparison with unequal native budgets,
non-equalized authored construction cost and one source lineage. TSP and
OR-Debug remain within-source confirmations and do not establish automatic
knowledge acquisition or unrestricted self-improvement.
