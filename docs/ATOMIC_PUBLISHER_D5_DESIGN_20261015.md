# D5 shared atomic publisher design

Status: author-approved architecture, implementation pending, 2026-10-15.

## Scope

D5 replaces the unsafe terminal-write boundary of the nine publishers listed in
`experiments/reconstruction_publisher_solver_boundary_audit_20261015.json`.
It does not change their scientific computation, accepted inputs, serializers,
output paths, or failure checks. The historical producer files remain byte
identical so their self-hashes and frozen plan bindings remain valid. Nine thin
adapters invoke those producers through their existing publication seams and
send the already serialized bytes to one shared publisher.

## Shared publisher contract

The shared publisher accepts a repository root and a non-empty mapping of
terminal paths to bytes. It must:

1. reject absolute path escape, `..`, symlinks in existing path components,
   symlink terminals, non-regular terminals, and duplicate normalized paths;
2. serialize no scientific value itself;
3. create a content-bound transaction journal and one reservation per terminal
   by exclusive no-clobber hard-link publication from an `fsync`ed unique
   temporary file;
4. reserve every terminal before publishing any terminal payload;
5. publish each payload by an atomic no-clobber hard link, then `fsync` every
   containing directory;
6. return success for an existing byte-identical regular terminal and reject a
   different terminal without changing it;
7. support replay after interruption at any phase by deriving the same
   transaction identity from normalized paths, payload lengths, and SHA-256
   digests; no elapsed-time lease or stale-owner takeover is permitted; and
8. remove the transaction journal and reservations only after every terminal is
   durable. Unique abandoned temporary files are inert and never treated as
   terminal results.

For a cross-directory JSON/Markdown pair, the transaction is recoverable rather
than instantaneously visible as an all-or-none filesystem snapshot. A crash may
leave one terminal visible, but the durable transaction journal and reservations
permit only the byte-identical replay to finish the pair; a competing payload is
rejected.

## Adapter contract

Each adapter binds one audited historical producer. It verifies the producer
source SHA-256 recorded in the boundary audit before importing it. It captures
only the producer's final serialized output at the existing narrow publication
seam, verifies the expected output inventory, and submits those bytes to the
shared publisher. It never decodes request or response bodies, reads credentials,
or changes API/model/solver behavior.

The adapters preserve these serializer families exactly:

- compact canonical JSON plus newline for BIND, CoE, and the common-40 summary;
- sorted two-space pretty JSON plus newline for the six pretty publishers; and
- the existing deterministic Markdown rendering for the common-40 summary.

The adapter layer is intentionally separate from the historical files. Editing
those files would invalidate source pins and, for three publishers, would also
change a self-hash embedded in the scientific output.

## Failure and recovery boundary

Missing or drifted producer source, an unexpected output path/count, path escape,
symlink, non-regular existing terminal, conflicting reservation, conflicting
terminal bytes, incomplete captured output, and malformed transaction metadata
all fail closed. Recovery is an explicit replay with the same producer and input
state. The publisher never steals an abandoned transaction, uses a TTL, replaces
a terminal, or silently chooses between differing bytes.

## Non-goals

D5 does not authorize a software/data license, publish the repository, reserve a
DOI, redistribute third-party inputs, run an API/model, run a solver, or alter a
paper endpoint. Those remain separate D1--D4 and D6--D8 decisions.
