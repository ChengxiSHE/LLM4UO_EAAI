# Content-addressed manifest implementation audit

Status: validator, publisher and semantic-length encoding implemented; current
TSP/OR-Debug manifest materialization and clean reconstruction remain open,
2026-10-15.

The two-level manifest design now has an offline implementation in
`llm4or/content_addressed_manifests.py`. A skill manifest binds the five
executable roles plus provenance, fallback behavior, direct semantic payload,
implementation closure and claim boundary. A library manifest binds sorted
skill identities, the exactly-one router, verifier closure, endpoint
identities, promotion decision, accepted and rejected ledgers, and parent and
rollback objects.

Validation occurs before import or execution. It rejects unknown fields,
duplicate JSON keys, non-finite numbers, absolute or parent-relative paths,
symlink components, closure hash drift, unvalidated bound skills, ledger byte
drift and missing successor ancestry. Request or response bodies,
evaluator/reference answers, credentials, problem text and solver
objective/point fields are forbidden recursively. Each semantic role must
contain direct knowledge; a path/hash/URI/reference-only object is rejected.

The operational complexity function implements the prospective prefix-free
encoding over skill semantic payloads and router semantic payload only. Paths,
reconstruction hashes, outcomes and machine metadata do not contribute. This
makes the theoretical object measurable, but does not retroactively establish
a complexity effect for a library whose outcomes were already exposed.

Publication uses the content digest as the filename, obtains terminal ownership
with exclusive creation, refuses replacement, and durably synchronizes both
the file and its directory. A crash-created partial terminal remains an
explicit abandoned reservation; it is never silently replaced. Loading checks
canonical bytes, filename/digest agreement, containment and all kind-specific
contracts again.

The verification command ran 35 tests covering the new implementation, the
existing verified skill library and the release-safe projection publisher. All
35 passed; bytecode compilation and whitespace checks also passed. The
implementation SHA-256 is
`77941ff32a3f1b9deb34d41c2975ece02ba49068db18d08d7c635ee8e242850f`;
the test SHA-256 is
`6c5a2143282b8db810d29e9c630cb61cdb34621c43a939ebbfb2cdc27e05fd6e`.

This step did not materialize current TSP or OR-Debug manifests, run a
manifest-driven reconstruction, import a manifest-selected module, or call an
API, model, solver, native evaluator or VM. It read no benchmark body, response
body, evaluator-only answer or credential. Root licensing, rights review,
fixed-prompt disclosure, layered environments, the external Gurobi contract,
history-safe publication and credential-free clean-clone reconstruction remain
G11 blockers.
