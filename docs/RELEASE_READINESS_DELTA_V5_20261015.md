# Release readiness delta v5

Status: **68 of 69 manifest paths tracked; projection and architecture gates
remain open**.

The exact 34-file allowlist from the v4 backlog has been integrated into local
Git history without changing any bound byte or paper result. The current
69-path manifest now has 68 tracked paths, one deliberately untracked path, and
no missing path. The only untracked path is the 3.58 MB full OR-Debug
confirmation evaluation, which remains outside Git because it contains
per-instance repair identity.

Tracking coverage is no longer the main release problem. Four existing
manifest bindings still require claim-complete safe projections:

1. the mixed confirmation bundle embeds 140 upstream public texts;
2. the full OR-Debug evaluation contains corrected/released repair identity;
3. the OR-Debug method-output record contains static/evolved repair objects;
4. the mixed-output record contains OR-Debug repair objects.

The projection designs preserve the quantities used by the paper: identity or
membership hashes, source revision, family and order, route and terminal
status, endpoint aggregates, correction/regression cells, direct/mixed output
hashes, and exact-equivalence decisions. They omit task text, repair identity,
repair objects, solver points, request/response bodies, evaluator-only values,
and credentials.

Two tracked files under `results/private` also remain outside the paper
manifest and must be removed from a public release or replaced. Root-license
selection, third-party attribution, fixed-prompt disclosure, canonical
skill/library manifests, exclusive terminal publication, the five-layer
environment, pinned submodule initialization and a credential-free recursive
clean-clone rebuild are still open.

This update made no API, model, solver, native-evaluator, or VM call and did not
push to a remote.
