# D5 credential-free clean-clone Layer A audit

Status: **passed with a complete pinned local submodule snapshot**, 2026-10-15.
Machine-readable audit: `experiments/clean_clone_layer_a_d5_audit_20261015.json`,
SHA-256 `bf582f84c34aea9a34afaa08a8ca969cfaa7c4fe73743b305a0d6ca08e3d5e1b`.

A fresh `git clone --no-local` of commit `888593d565ede68e466d76024a5c7b0e92629cca` was clean before
and after execution. The local fallback re-cloned the solver submodule instead
of copying its worktree `.git` pointer, checked out the pinned
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` commit, verified zero missing reachable
objects and a full `git fsck`, and did not execute the solver.

The credential-free Layer A command ran 79 tests, now including the
shared atomic publisher and all nine reconstruction-adapter tests. It also
rechecked current content-addressed manifests, all 2,985 public routing
identities and the release evidence report. No inherited environment values,
credential, API/model, solver, native evaluator or VM call was available or
used. No request/response body or evaluator-only answer was read.

This local complete-snapshot run proves D5 is present in a clean committed
checkout. It does not replace the earlier remote HTTP/1.1 acquisition audit,
apply a license, establish redistribution rights, publish the repository or
reserve a DOI.
