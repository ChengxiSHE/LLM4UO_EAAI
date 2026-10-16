# RetailOpt-190 source and endpoint gate — 2026-10-17

## Decision

RetailOpt-190 at commit `d809c6bbeb42cb99b0564c41bfb8f331f0156b9d`
passes the source-completeness, inference/evaluator-separation and project-source
independence gates. It is eligible as the next independent direct-modeling
source for G15. The scalar endpoint must use the behavior implemented by the
fixed ReLoop repository, namely relative objective error strictly below 1% on
the full denominator. The stricter prose endpoint in the RetailOpt README is
not reproducible and must not be used for the confirmatory claim.

No language-model API call was made in this gate.

## Source custody

The fixed source contains 190 unique records: 38 archetypes in eight families,
each with five variants. The aggregate JSONL agrees exactly with all 380
schema/full prompt files, agrees semantically with all 190 structured-data
files, and agrees in status and objective with all 190 rows in the published
benchmark CSV. All reference objectives are finite. The body-free public audit
is `experiments/retailopt190_source_custody_audit_20261017.json` (SHA-256
`637da7c1c4c0b69d97e79d81eade9b95e655bdd5c6cc90f43ebfe370de729223`).
The ignored custody bundle separates 190 inference records from 190 evaluator
records and binds them with opaque identities.

The repository's rights metadata is internally inconsistent. The README says
MIT for code and CC BY 4.0 for data, while the root `LICENSE` contains the
custom ReLoop Research and Education License v1.0. We therefore do not
redistribute task, data, reference or solver bodies; the release contains only
hashes, counts and attribution metadata.

## Independence from prior project sources

The candidate business descriptions were compared with all 1,356 records in
the six-source historical registry and all 2,121 public Text2Opt descriptions.
There were zero exact normalized matches and zero numeric-template matches.
For every candidate, the maximum five-token-shingle Jaccard similarity was
below 0.006 in both modes; no record approached the frozen 0.8 near-duplicate
gate. The body-free audit is
`experiments/retailopt190_independence_audit_20261017.json` (SHA-256
`14b0dbe347d70d09a014f8872d1c30050fc30a7f2b9ef6da4ddf2a5cbbd311da`).
This rules out reuse of the enumerated project inputs; it cannot rule out
pretraining contamination or broad conceptual similarity.

## Offline endpoint replay

The source was replayed with the already approved transport/solver environment
`/Users/chengxi-nju/Desktop/LLM4UO/.venv-preparation`, Python 3.10.1 and
Gurobi 13.0.3. The frozen replay used five workers, one Gurobi thread per
instance and seed zero. It completed 190/190 instances with no worker crash,
timeout or import failure. The controller checkpointed every terminal record,
so an interruption would rerun only missing records.

Under the RetailOpt README contract, 185/190 reproduce. All five misses are the
five variants of the MOQ-binary archetype. Four retain the same optimal status
but exceed the README's 0.01% objective tolerance; one reaches the source time
limit in the five-worker replay. The maximum relative objective difference is
0.846%. Independent single-item reruns in both the offered LLM4DRO environment
(Gurobi 13.0.1) and `.venv-preparation` (Gurobi 13.0.3) produce the same
objective behavior for all five MOQ variants. This excludes the Python virtual
environment and Gurobi patch version as the primary cause.

The contract conflict is upstream. The reference solver terminates at a 1%
MIP gap, while the RetailOpt README applies a 0.01% tolerance to MOQ-binary.
The fixed ReLoop implementation classifies objective errors below 1% as
correct. Under that code-defined endpoint, the same replay is 190/190. The
machine-readable reconciliation is
`experiments/retailopt190_endpoint_stability_audit_20261017.json` (SHA-256
`d494b12c56d73e1977cbc6509e0e01bf6094a52733129503adf32d2a77776621`).

## Frozen boundary for G15

The next experiment may use RetailOpt-190 only under these rules:

1. score the full 190-record denominator;
2. define final correctness as successful execution with relative objective
   error strictly below 1%, matching the fixed ReLoop code;
3. report execution success and solver status separately, without silently
   excluding infrastructure or status failures;
4. keep all reference objectives, source identities and evaluator code outside
   the inference context;
5. freeze the matched baseline, knowledge library, sparse router, short
   decision schema, evidence budget and paired statistical gate before any new
   method result is opened;
6. use the public benchmark specification only as declared knowledge-source
   material, and do not copy the evaluator-only universal solver into the
   method library.

Passing this gate does not establish method accuracy or improvement. It only
closes the source and endpoint prerequisites for the prospective G15 test.
