# Atomic publisher D5 migration audit

Status: **passed — shared publisher and nine thin adapters implemented**, 2026-10-15.
Machine-readable audit: `experiments/atomic_publisher_migration_audit_20261015.json`,
SHA-256 `8eda814dd970c452da08de2d72897ae6783924ecd6fcc2bc2d543a6343c3f474`.

## Result

The user-approved D5 architecture is implemented as one root-confined durable
no-clobber publisher, nine source-hash-bound adapters, and an explicit CLI that
lists adapters or runs exactly one named adapter. All nine historical producer
files retain the SHA-256 values frozen by the prior boundary audit. They were not
edited in place, so their plan pins and embedded self-hashes remain valid.

The shared publisher accepts only already serialized bytes. It reserves every
terminal before publishing the first payload, writes unique same-directory
temporary files, fsyncs files and directories, commits with a no-clobber hard
link, accepts only byte-identical replay, and rejects a differing terminal. A
durable content-bound journal and reservations permit deterministic replay after
interruption without a TTL or abandoned-owner takeover. Cross-directory
JSON/Markdown pairs are recoverable transactions: a crash may expose the first
member, but only the byte-identical transaction can finish the pair.

## Verification

Twenty-two focused tests passed. They cover same-payload and different-payload
multiprocess races, interruption after journal/reservation/first-terminal and
before-cleanup phases, cross-directory recovery, symlink/path-escape and
non-regular-terminal rejection, file and directory fsync, exact compact/pretty
serialization, private/public and JSON/Markdown bundles, frozen producer hashes,
explicit parent-segment rejection, a post-open terminal-type recheck, fail-closed output inventories, and a single-result CLI channel. The CLI has no implicit batch mode.

## Scientific and release boundary

No endpoint was recomputed and no historical output was rewritten. Scientific
fields, input checks, serializer choices, paths and producer failure behavior are
unchanged; D5 strengthens only publication ownership, durability and recovery.
Four producers import in the minimal Layer-A closure. Five depend on solver or owner-custody files that remain outside the rights-reviewed allowlist and are deferred to those layers; D5 does not vendor them. No API/model, solver, native evaluator or VM call was made, and no credential,
request/response body or evaluator-only answer was read. D1--D4 and D6--D8
remain open: this migration applies no license, publishes no repository and
reserves no DOI.
