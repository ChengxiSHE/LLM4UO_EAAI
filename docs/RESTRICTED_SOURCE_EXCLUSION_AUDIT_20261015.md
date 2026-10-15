# Restricted-source exclusion audit

## Decision

The candidate public Git tree now excludes all six identified body- or
repair-bearing frozen sources. Five previously tracked sources are removed from
the current index, and the full OR-Debug evaluation remains untracked and
ignored. Local frozen copies remain available under ignore rules for internal
lineage checks; they are not part of the candidate release tree.

This closes current-tree source exclusion, while public release remains open.
The restricted blobs exist in local branch ancestry, so an ordinary push of
this branch would expose them. The eventual public artifact must be a
history-free, rights-reviewed snapshot or use author-approved history
sanitization before any push.

## Public replacements

Six deterministic projections replace the omitted sources:

| Projection | Records | Public evidence retained |
| --- | ---: | --- |
| Mixed bundle | 2,985 | identity, family and complete-envelope hash |
| OR-Debug evaluation | 2,845 | aggregate endpoints, group metadata and complete-record hash |
| OR-Debug direct outputs | 2,845 | status/resource metadata and complete-output hash |
| Mixed outputs | 2,985 | route, status and complete-output hash |
| TSP public input | 140 | identity, size and task-text hash |
| TSP direct candidates | 140 per arm | identity, size and complete-candidate hash |

The new public mixed-identity audit compares these hashes and reproduces all
2,985 exact matches, with zero route, output, source or terminal mismatch. Its
seven claim-bearing fields are identical to the earlier object-level v2 audit.
No endpoint was rescored.

## Verification

The projection and mixed-audit suites contain 20 focused tests, and the wider
mixed execution set brings the targeted total to 32. They verify deterministic
hashes, privacy deny-lists, duplicate and path failures, the six fixed
projections, hash-only direct/mixed equality and Git-package prerequisites.

The paper manifest remains at 69 paths, 408 structured assertions and 15
boundaries, with no restricted source bound. Current-paper references use
`results/mixed_skill_confirmation_public_audit_v3_20261015.json`, SHA-256
`3c9b8700639cfe5599fc76b18cca4318b14d4b0865fb5bd343f5c0d26fead08f`.

## Remaining G11 work

Release still requires a root license and attribution policy, prompt disclosure,
canonical skill/library manifests, replacement or wrapping of historical
producers, layered environments and commands, the solver submodule/Gurobi
contract, a credential-free recursive clean-clone rebuild, and creation of a
history-safe public snapshot.
