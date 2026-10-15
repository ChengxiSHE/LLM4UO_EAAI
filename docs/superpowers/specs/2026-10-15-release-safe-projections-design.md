# Release-safe evidence projections design

## Purpose

Replace four paper-manifest bindings that expose upstream task text, repair
identity, or repair objects with deterministic metadata-only artifacts. The
public projections must retain every aggregate and identity relation used by
the paper while never emitting task text, repair identity/object, solver
points, request/response bodies, evaluator-only values, or credentials.

## Scope

The subsystem consumes the four frozen local source artifacts and emits four
new JSON artifacts:

1. mixed confirmation bundle projection;
2. OR-Debug confirmation evaluation projection;
3. OR-Debug direct method-output projection;
4. mixed method-output projection.

It does not modify the frozen sources, rescore an endpoint, call a model or
solver, initialize a submodule, select a license, or publish remotely.

## Data contract

Every projection contains a schema identifier, the SHA-256 and byte size of
its full source, aggregate counts needed by the paper, and a sorted record
array. Record order is source order unless the frozen artifact already declares
another order. Each record contains its public identity and only allowed
metadata. A `source_record_sha256` or `output_sha256` binds omitted material
without disclosing it.

The mixed-bundle projection retains record ID, source, public-envelope SHA,
counts, custody, source hashes, and mixed-order hash. The evaluation projection
retains the complete aggregate comparison and confirmation-inference objects,
plan/custody/execution metadata, record ID, shape group, and static/evolved
endpoint/status fields after removing both repair-identity fields. The direct
and mixed output projections retain identities, route/status, counts, status,
existing non-content hashes, and a canonical hash of the full omitted output;
they omit `repair` and `solve_objective`.

All outputs carry explicit privacy booleans. A recursive deny-list validator
rejects forbidden keys anywhere in a projection.

## Determinism and publication

Canonical content hashing uses UTF-8 JSON with sorted keys and compact
separators. Saved artifacts use sorted, indented UTF-8 JSON plus one final
newline. Generation checks the exact frozen input SHA before parsing.

Publication uses exclusive file creation, file flush and `fsync`, atomic
rename from an exclusive temporary file, and directory `fsync`. Existing
identical output is accepted only in `--check` mode; write mode fails closed on
an occupied terminal path. Path resolution is repository-relative and rejects
absolute paths, `..`, symlinks, and root escape.

## Verification

Tests must prove:

- each projection reproduces the declared record and aggregate counts;
- all forbidden keys and credential/body literal patterns are absent;
- source and record hashes are deterministic;
- shuffled mapping-key order does not change bytes;
- duplicate identities, source-hash mismatch, missing required fields and
  output-path collisions fail closed;
- the OR-Debug aggregate assertions and mixed 2,985-record routing counts used
  by the paper are unchanged;
- the paper manifest can bind the four projections while preserving all 408
  structured assertions and 15 global boundaries.

## Claim boundary

The projections make the evidence surface safer and reconstruct the published
aggregates. They do not prove rights clearance, source semantic correctness,
clean-clone executability, or the missing canonical skill/library manifests.
