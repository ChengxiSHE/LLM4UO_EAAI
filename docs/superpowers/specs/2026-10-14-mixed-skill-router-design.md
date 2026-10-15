# Mixed TSP/OR-Debug public-only router design

Status: implementation specification, 2026-10-14.

## Purpose

Test whether two independently confirmed benchmark-specific skills compose
behind one public-only router without changing either skill's output.  This is
a compositional identity experiment over already exposed confirmation public
inputs.  It is not a new accuracy confirmation, a learned-router experiment or
evidence that one skill transfers across sources.

## Frozen inputs and direct comparators

- TSP: the 140 public rows in
  `results/private/tsp_constraint_confirmation_public_20261014.json` and the
  frozen skill rows in
  `results/private/tsp_constraint_confirmation_candidates_20261014.json`.
- OR-Debug: the 2,845 public rows in
  `experiments/or_debug_confirmation_public_bundle_20261014.json` and the
  frozen evolved rows in
  `results/or_debug_confirmation_method_outputs_20261014.json`.
- No reference answer, repair target, evaluator label, recorded optimum or
  benchmark correctness bit enters the router or mixed method runner.

## Public envelope and guards

The router accepts exactly one of two complete envelopes:

```text
TSP = {public_text: str, size: int, question_sha256: sha256}
OR-Debug = {problem_nl: str, model_file: str, mps_sha256: sha256}
```

`problem_id` is retained only as an outer ledger key and is never provided to
the guard.  The TSP guard validates the exact key set, size range 13--19 and
text hash.  The OR-Debug guard validates the exact key set, non-empty strings,
SHA syntax and a relative model path; the delegated executor independently
checks path containment, file existence and content hash.  A union-shaped,
partial, unknown or otherwise malformed envelope matches zero guards.  The
router also fails closed if implementation changes ever cause multiple guards
to match.

## Router output

The pure decision function returns one of:

- `tsp_constraint_xor_v2_scalable`
- `or_debug_typed_repair_v1`
- `None`, with reason `no_unique_public_guard`

The dispatcher records the route and delegates unchanged public fields to the
already frozen family executor.  It does not normalize, repair or reinterpret
the family output.

## Identity endpoint

For every mixed record, the delegated output is compacted with the exact
family-specific historical convention and compared with the corresponding
frozen direct output.  Success requires:

1. 2,985/2,985 records route to exactly one expected skill;
2. zero route collisions, unknown routes or dispatcher failures;
3. 140/140 TSP compact outputs equal the frozen direct skill rows;
4. 2,845/2,845 OR-Debug outputs equal the frozen direct evolved rows;
5. the known direct confirmation counts remain inherited by exact identity,
   not recomputed or presented as new test outcomes.

Synthetic negative tests cover empty, partial, union-shaped, bad-hash,
absolute-path and unknown envelopes.  They must abstain without calling either
family executor.

## Execution and claims

All execution is local with Gurobi concurrency at most five and zero model/API
requests.  The experiment may establish public-interface route separability,
fail-closed ambiguity behavior and exact compositional preservation.  It may
not establish learned routing, new benchmark accuracy, fresh generalization,
automatic skill construction or operating-system-level answer isolation.
