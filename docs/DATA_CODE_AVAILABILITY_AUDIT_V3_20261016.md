# Data and code availability audit v3 — 2026-10-16

> **Superseded historical snapshot.** This document records the final
> pre-publication gate. Current availability is reported in
> [`DATA_CODE_AVAILABILITY_AUDIT_V4_20261016.md`](DATA_CODE_AVAILABILITY_AUDIT_V4_20261016.md);
> the history-free public repository and `v1.0.0` release are verified, while
> the archival DOI remains pending.


## Current status

The author-controlled release decisions are closed. The author confirmed
authority for the scoped first-party material, approved Apache-2.0 for the
first-party software and machine-readable artifacts, approved CC BY 4.0 for
explicitly marked author-owned aggregate Source Data and documentation,
approved the NOTICE and third-party exclusions, and authorized publication of
a verified history-free candidate. Verified author metadata records Chengxi
She, School of Management & Engineering, Nanjing University, and the
institutional corresponding email. Unverified ORCID is omitted, funding is not
declared, and venue selection remains open.

All 70 paths in the paper evidence manifest are tracked and hash verified. Six
task-text, repair-object and evaluator-only sources are represented by
metadata-only projections; restricted paths and paths below a private directory
are absent from the release tree. One shared exclusive durable publisher wraps
all nine historical producers without changing their frozen schemas, paths or
output bytes.

The final provider audit exposed a release-closure defect: the historical
preflight imported untracked private experiment modules. The public release now
uses a body-free transport surface that binds only the AntChat endpoint,
DeepSeek-V4-Flash model, concurrency five, CA identity and TLS-context
construction. It imports no request construction, prompt, response or
credential material. The provider preflight makes zero API calls.

## Environment and dependency boundaries

The five environments remain separate. Layer A is credential-free and verifies
the evidence chain, current content-addressed library and public identity
reconstruction. Layer B fixes the offline Python analysis dependencies. Layer C
uses the separately installed Gurobi 13.0.1 binary and user-held license. Layer
D is the zero-call public provider transport preflight. Layer E reconstructs
the two main figures in the exact declared figure environment. Passing one
layer does not imply another.

The solver-in-the-loop dependency remains an external gitlink pinned to
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` under its upstream terms. CoE is
retrieved from pinned upstream code and is not vendored or relicensed. No
official runnable OptiTrust artifact was verified, so OptiTrust remains an
artifact-availability comparison rather than a scored local reproduction.

## Remaining release gates

1. Rebuild the zero-parent candidate from the final provider-corrected commit.
2. Verify the new candidate has one reachable commit, no restricted/private
   paths, complete pinned dependencies, and a passing credential-free Layer A.
3. Re-run or hash-bind Layers B–E against the final release inputs.
4. Publish that exact immutable candidate and verify its public URL.
5. Archive the exact release, record its DOI, and run a post-publication
   independent claim and clean-clone audit.

The earlier local one-commit bundle proves the history-removal mechanism but is
superseded and must not be published because it predates the provider-surface
correction. No public repository availability or DOI is claimed by this audit.

## Manuscript-ready bounded statement

First-party code, typed skill and library manifests, public-only routing and
verification code, aggregate evidence, figure Source Data and deterministic
reconstruction commands are authorized for release under Apache-2.0, with
explicitly marked author-owned aggregate Source Data and documentation under CC
BY 4.0. Reused benchmark sources are retrieved at pinned revisions and remain
subject to upstream terms. Where redistribution is not authorized, the release
provides metadata-only identities, checksums and reconstruction instructions
rather than upstream task text or evaluator-only answers. Gurobi 13.0.1 and
provider credentials remain external. Private request and response bodies,
credentials, evaluator-only answers and restricted upstream task text are not
released. The live repository URL and archival DOI will be added only after
external verification.
