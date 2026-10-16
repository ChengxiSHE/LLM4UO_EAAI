# OptiTrust-style compact sidecar v2 design

## Purpose

Produce a scoreable paper-structure sensitivity on the frozen common-38
endpoint without claiming an official OptiTrust reproduction or executing
generated Python. The v1 experiment is immutable evidence that five repeated
full-model sidecars are not operationally viable on the bounded AntChat
transport: all 38 cells were infrastructure unavailable. V2 changes only the
representation and trajectory before any new benchmark response is opened.

## Scientific label and boundary

The paper label is `OptiTrust-style-compact-sidecar`. It measures a disclosed
paper-inspired multi-view trajectory through a trusted safe adapter. It is not
the authors' native five-language implementation, fine-tuned checkpoint,
training procedure, or official result. Its row must remain separate from the
official artifact-unavailable row and from equal-budget leaderboards.

## Frozen ten-slot trajectory

Each identity has exactly ten logical slots:

1. bounded component decomposition;
2. bounded decomposition reflection;
3. bounded formulation outline;
4. bounded formulation reflection;
5. one canonical strict `milp-v1` candidate;
6. Pyomo-conditioned review of the immutable candidate;
7. Gurobipy-conditioned review;
8. DOcplex-conditioned review;
9. CVXPY-conditioned review; and
10. PySCIPOpt-conditioned review.

Natural-language intermediate fields are capped at 8 KiB and are not copied
into the canonical-candidate request. That request receives the original public
problem plus hashes of the four bounded analyses. This retains provenance
without making the wire body grow with the entire trajectory.

The five reviewers receive the original public problem, the canonical model,
its SHA-256 identity, and one language label. They return only a strict
`optitrust-review-v1` object. A review may accept, reject, or propose at most 16
typed model edits. Allowed edits replace one variable record, upsert or delete
one constraint, or replace the objective. The trusted composer rejects stale
candidate hashes, duplicate targets, unknown targets, oversized reviews,
invalid edited models, and resource-limit violations. Generated code is never
executed.

Each accepted or valid repaired view is solved by the same trusted Gurobi
endpoint. The final result uses the previously frozen strict objective majority
of at least three of five with `rtol=1e-5` and `atol=1e-6`. Rejected or invalid
views remain explicit votes with no objective. The evaluator-only reference is
loaded only after all ten requests and candidate solves terminate.

## Reliability contract

- Concurrency remains five across distinct identities.
- One request fingerprint permits at most three recorded physical attempts.
- The attempt row becomes `exhausted` before a same-attempt circuit interruption
  is raised, so clearing a circuit cannot create a fourth send.
- Identical fingerprints are sent once and reused durably.
- Item-level exhaustion produces `infrastructure_unavailable` for that identity
  while unrelated work continues unless the global circuit remains open.
- Authentication, model drift, budget, ledger integrity and frozen-file drift
  remain global failures.
- Public artifacts contain no request or response bodies, problem text,
  candidate models, objectives, points, references or credentials.

## Outcome-blind canary

Before common-38 dispatch, run four synthetic, non-benchmark identities: one
small binary model, one integer scheduling model, one moderate sparse routing
model, and one deliberately invalid-review case. The capacity gate requires:

- 4/4 terminal cells;
- zero infrastructure-unavailable cells;
- all 40 logical slots durably present and contiguous;
- no fourth physical attempt for any fingerprint;
- at least one valid canonical model and five parsed reviews across the set;
- byte-exact restart with zero new physical attempts; and
- a body-free independent audit with zero new provider or solver calls.

The canary does not estimate benchmark accuracy. A failed gate blocks the
common-38 run and may justify another representation design, but the same
canary responses may not be repeatedly prompt-tuned.

## Full-run endpoint

If the canary passes, freeze a new plan, authorization, code hashes, source
revision, solver identity, package versions, limits, 38 identities and all
public-input hashes. Run all 38 once under the original endpoint and full
denominator. Report correct, incorrect, method failure and infrastructure
unavailable separately. Paired comparisons are permitted only if at least one
scoreable method outcome exists; an all-infrastructure row is again declared
not estimable.

## Alternatives rejected

- Five full `milp-v1` models repeat the v1 capacity failure.
- Executing generated Pyomo/Gurobipy/DOcplex/CVXPY/PySCIPOpt code enlarges the
  trusted surface and requires unavailable native environments.
- Compiling benchmark-specific answer templates would inject the proposed
  method's authored knowledge into the comparator.
- Reusing endpoint answers to tune prompts would invalidate the prospective
  sensitivity.

