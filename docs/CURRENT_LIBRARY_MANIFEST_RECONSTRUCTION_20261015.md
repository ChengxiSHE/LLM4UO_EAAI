# Current library manifest reconstruction

Status: current TSP and OR-Debug manifests materialized; body-free direct and
mixed identity reconstruction passed, 2026-10-15.

The already frozen TSP constraint policy and OR-Debug typed repair policy now
have one answer-free content-addressed skill manifest each. A genesis library
manifest binds those skill identities, the exactly-one public router, verifier
closure, two frozen endpoint identities, aggregate accepted-ledger references,
release boundaries and claim boundaries.

The content identities are:

- OR-Debug skill:
  `68d5aed2794c5ccf381519f0a8ebc1c35da44a6f1fc749434f64491df49d9d39`;
- TSP skill:
  `cafdd1bb6429391f64aabd3b130d2028972b3f5f3dfb78d4609b2e7cd8fa87ff`;
- current genesis library:
  `1005544bd062b618f89c86a4e73707ea5dfd1daf267ddb29ac46b6c03a807116`.

These are hashes of the canonical body with `content_sha256` excluded. The
complete on-disk JSON files therefore have different ordinary file hashes:
`eab5e4db...e9b7`, `a89453ea...abfd` and `fc7194ef...61d5`, respectively.
The distinction prevents a self-referential digest while retaining normal file
integrity checks.

The measured prospective semantic envelope is 17,728 bits. It contains only
the direct TSP and OR-Debug semantic payloads and the router payload. Paths,
code hashes, endpoint outcomes, timestamps and machine metadata are excluded.
Because the current libraries were authored after development outcomes were
known, this number is an artifact measurement rather than retrospective
evidence that complexity control caused their benchmark gains.

The reconstruction audit first strictly reloads all three manifests, checks
every first-party code byte hash, validates ledger and endpoint bindings, and
then recomputes the public direct-versus-mixed identity comparison from six
metadata-only projections. It recovers 2,985/2,985 exact identities: 140 TSP
and 2,845 OR-Debug, with zero route, output, source, missing, duplicate,
invalid or terminal-failure discrepancies. Its five claim-bearing structures
are byte-equivalent as JSON values to the pre-existing public v3 audit. The
machine audit SHA-256 is
`af920f71608a46ce25fd5e8a54e88d1fe1f5ca351988b52546a83e1a3fbc6ce9`.

A clean-clone rehearsal exposed and corrected one closure error. The first
manifest version had included `or_debug_repair_dsl.py`, an evaluator-side
development parser that is not imported by the method runtime, and had required
seven untracked historical plan bodies. The corrected OR-Debug closure binds
the actual MPS patch transform only. Historical plan and decision identities
are preserved in the tracked, body-free
`reproduction/current_library_provenance_v1.json` registry. Thus every runtime
closure and accepted-ledger file required by the current library is tracked,
while non-release historical bodies are neither silently published nor needed
for reconstruction.

This closes the current-manifest and body-free identity-reconstruction part of
G11. It does not rerun the family solvers, rescore accuracy, create a new
promotion result, validate a retrospective complexity effect or establish a
new generalization claim. Root licensing, third-party attribution, fixed-prompt
disclosure, nine historical publisher replacements or wrappers, layered
environments, the external Gurobi binary/license contract, credential-free
recursive clean-clone reconstruction and history-safe public release remain
open.

No API, model, solver, native evaluator or VM was called. No benchmark body,
request or response body, evaluator-only answer or credential was read.
