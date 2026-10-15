# Release-safe projection rebinding audit

## Decision

The four unsafe paper-manifest bindings are closed. Each frozen source now has
a deterministic metadata-only projection, and the paper manifest binds those
projections instead of the body-bearing or repair-bearing source files. All 69
manifest paths are tracked locally; the manifest still contains 408 structured
assertions and 15 global claim boundaries. No endpoint value, baseline value,
or paper conclusion changed.

This closes the projection and manifest-tracking portion of G11. It does not
make the repository release-ready: license and attribution decisions, two
tracked private-file exclusions, prompt disclosure, canonical skill/library
manifests, layered environments, the solver contract and a credential-free
recursive clean-clone rebuild remain open.

## Projection contract

| Projection | Records | Retained public evidence | Omitted material |
| --- | ---: | --- | --- |
| Mixed confirmation bundle | 2,985 | record identity, source, counts, custody, source and order hashes | task text; each complete envelope remains hash-bound |
| OR-Debug evaluation | 2,845 | every aggregate comparison and inference object, shape group, endpoint/status metadata | corrected and released repair identities; each complete source record remains hash-bound |
| OR-Debug method outputs | 2,845 | identities, status, counts and existing non-content hashes | repair objects and solver objectives; each complete endpoint output remains hash-bound |
| Mixed method outputs | 2,985 | identities, route/status, route and status counts, non-content metadata | repair objects and solver objectives; each complete routed output remains hash-bound |

All projections carry explicit false privacy flags for task text, repair
identity/object, solver objective/point, request/response bodies, evaluator
answers and credentials. A recursive deny-list validator rejects those keys at
any depth.

## Reproducibility and failure behavior

The fixed builder checks the exact SHA-256 of every frozen source before JSON
parsing. Canonical SHA-256 binds omitted records and outputs. Saved JSON is
sorted and deterministic. Write mode uses an exclusive temporary file, file
`fsync`, exclusive terminal reservation, atomic replacement and directory
`fsync`; it refuses an occupied target. Check mode accepts only byte-identical
existing artifacts. Absolute paths, parent traversal, symlink components,
root escape, duplicate identities, missing fields and source-hash drift fail
closed.

The focused suite has 11 tests after manifest rebinding. It reconstructs the
2,845-record OR-Debug assertions from the public projection, checks both
2,985-record mixed artifacts, verifies all projection hashes and rejects any
of the four source paths in the paper manifest.

## Claim boundary

The safe projections improve the release evidence surface; they do not rerun
or rescore an experiment. Their source hashes preserve lineage but do not grant
redistribution rights. The machine-readable audit is
`experiments/release_projection_rebinding_audit_20261015.json`.
