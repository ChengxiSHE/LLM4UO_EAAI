# Release readiness delta v4

Status: **not ready; the scientific surface is current, but release closure is
still open**.

## Current manifest surface

The post-G07/G08/G09 and final-figure paper manifest binds 69 unique existing
paths with no hash mismatch. Git currently tracks 34; 35 remain untracked. The
sorted path set has SHA-256
`420292bb6fb4e619ee7195f9f3f8ae4961aa79c07b636e68eb566a47e7d9ff9f`.

Relative to the frozen 46-path v3 surface, 23 paths were added and none was
removed. All 23 new paths are tracked. Four paths that were untracked in the
older snapshot are also now tracked: the figure plan, main draft, evidence
audit, and Source Data README. The unchanged 35 untracked paths are the legacy
release backlog; they must be reviewed and staged explicitly rather than
absorbed through a workspace-wide add.

## Content boundary

A key-aware scan of all 69 files found no bearer-token, OpenAI-style-key, or
quoted-secret-assignment literal. The 23 new paths did not trigger body or
secret fields. This is a mechanical redaction check, not a rights clearance.

One manifest-bound tracked file still embeds 140 upstream public task texts:
`experiments/mixed_skill_confirmation_bundle_20261014.json`. It must be
excluded or replaced by an identity/hash/routing projection with deterministic
upstream reconstruction. Two tracked files under `results/private` remain
outside the paper manifest and also require exclusion or replacement. No
private value, task text, request, response, reference answer, or credential
was displayed during this audit.

## What remains open

The repository still has no root license. The content-addressed skill/library
manifest contract is designed but has no validator, exclusive publisher,
materialized current manifests, or manifest-driven reconstruction. The
five-layer environment and command contract is not implemented, the pinned
solver submodule is uninitialized, Gurobi remains separately licensed, and no
credential-free recursive clean-clone rebuild exists. CoE remains upstream-
only because the inspected official repository exposes neither a verified root
license nor a release package.

The next safe sequence is:

1. keep the 69-path allowlist explicit and choose the first-party license and
   attribution policy;
2. replace body-bearing and private files with claim-complete safe projections;
3. review and explicitly integrate only the 35 remaining manifest paths;
4. implement canonical skill/library manifests and an exclusive publisher
   without altering frozen endpoints;
5. implement the layered reconstruction environment and run the recursive
   credential-free clean clone.

This v4 snapshot changes no runtime, endpoint, baseline, model, solver,
submodule, license, Git index, or history. It makes no API, model, solver,
native-evaluator, or VM call.
