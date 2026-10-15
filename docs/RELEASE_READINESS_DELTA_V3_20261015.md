# Release-readiness delta v3

Status: **not ready; release surface unchanged**, 2026-10-15. The
machine-readable source is
[`release_readiness_delta_v3_20261015.json`](../experiments/release_readiness_delta_v3_20261015.json).

## Decision

The manuscript and paper evidence manifest now state two additional boundaries
relative to v2. First, the implemented skills and mixed router satisfy the
formal roles behaviorally, but the current library is distributed across pinned
modules, plans and result closures rather than represented by one canonical
answer-free manifest. Second, complexity-weighted candidate promotion and a
cumulative regression budget are prospective conditional protocol guarantees;
the current runs did not implement the former and do not form one fixed-target
sequence for the latter.

This correction does not change the public release surface. The current paper
manifest still binds 46 unique paths, of which 7 are Git tracked and 39 are
untracked; none is missing. The sorted path-set hash is
`804cf10abdf2c354f7206b6a0bc07465c7484278ce0d945859e78dace752702a`,
identical to the v2 inventory. The changed bound hashes are the main draft, its
evidence audit, the theory supplement, the paper-facing theory framework and the
claim-to-evidence matrix.

## Scientific effect

No benchmark endpoint, external-baseline value, automatic-acquisition result,
component-effect claim, or quantitative figure datum changed. The paper adds
one artifact limitation and two prospective promotion corollaries; Figure 1
adds the corresponding risk-budget boundary. The paper manifest now contains
ten global claim boundaries instead of eight in v2.

## Release effect

The two-level skill/library manifest contract is designed, but design is not
implementation. There is still no validator, exclusive publisher, materialized
current skill manifest, parent-linked library manifest or manifest-driven
reconstruction of the sealed direct and mixed hashes. The root license,
rights-safe projections, complete environment, initialized submodule and
credential-free recursive clean-clone rebuild also remain open.

Therefore the correct statement is that the manuscript now describes the
release gap more accurately. It would be incorrect to claim that the new design
makes the current repository clean-clone reproducible or supplies an empirical
complexity-control result.

This audit made no API, model, solver, native-evaluator or VM call; modified no
Git index or history; and read no request body, response body, evaluator-only
answer or credential.
