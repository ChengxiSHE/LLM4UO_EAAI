# Data and code availability audit v2 — 2026-10-15

## Current status

The scientific evidence is locally reconstructable, but the project is not yet
an author-approved public release. All 70 paths in the paper evidence manifest
are Git tracked and hash verified. Six task-text, repair-object and
evaluator-only sources have been replaced in the public evidence chain by
metadata-only projections; none of those restricted paths, and no path below a
`private` directory, is tracked in the current candidate tree.

The five environment layers are separated explicitly. Credential-free Layer A
retrieves the exact pinned solver-in-the-loop gitlink over Git HTTPS forced to
HTTP/1.1, then rebuilds the evidence chain and the current content-addressed
skill library.
The exact Python 3.11.16 offline-analysis environment, the local Gurobi 13.0.1
solver boundary, the AntChat transport preflight, and both main-figure builds
have independent passing audits. Gurobi remains a separately licensed local
dependency, and real provider replay remains account, credential, network and
authorization dependent.

A deterministic history-free candidate has one reachable commit, no parent,
an exact identity to its bound source tree, no restricted or private paths, and
a passing 53-test Layer-A reconstruction. This proves that restricted ancestry
can be removed mechanically. It does not claim identity to every later working
commit and does not grant redistribution rights.

## Rights inventory

At source commit `87668c7806f8b9aea48494cddb9a8bc96277ddac`, the 825
tracked entries are partitioned into 792 first-party candidates, 21
generated manuscript artifacts, 11 source-metadata manifests, and one external
git submodule. The main repository has no root license. The authors must
confirm ownership or permission for the first-party candidates, select a root
license, approve a third-party attribution/NOTICE policy, and authorize the
release. Source manifests preserve provenance but do not grant rights to
upstream material.

The solver-in-the-loop dependency remains a gitlink at commit
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` under its upstream terms. The
local object graph is complete and passes `git fsck --full`. The final fresh
recursive acquisition succeeded after forcing Git HTTPS to HTTP/1.1: the exact
pinned commit was retrieved in a new checkout, had zero missing reachable
objects, passed full `fsck`, and supported all 53 credential-free Layer-A
tests. CoE remains an upstream-only reconstruction source because no verified
root license or release package was found. OptiTrust remains an artifact-
availability row because no verified runnable official artifact was found.

## Remaining release gates

1. Authors confirm the 792 first-party candidates and select the root license.
2. Authors approve the third-party attribution/NOTICE, fixed-prompt, and AI-use
   disclosure policies.
3. The nine historical nonexclusive result publishers are replaced or wrapped
   by an approved exclusive, durable publisher while preserving frozen bytes,
   hashes, schemas, and failure behavior.
4. The licensed one-commit candidate is rebuilt, all five layers are rerun, and
   the final independent claim audit is executed.
5. Only then may the repository be pushed or archived and assigned a DOI.

## Manuscript-ready bounded statement

The experiments use publicly obtainable benchmark sources at pinned revisions.
The release will contain first-party code, typed skill and library manifests,
public-only routing and verification code, metadata-only benchmark identities,
aggregate endpoint evidence, figure Source Data, and deterministic
reconstruction commands. Upstream content without verified redistribution
rights will be retrieved from its pinned source rather than vendored. The
solver-in-the-loop dependency is a pinned external submodule, and Gurobi 13.0.1
requires a separate user installation and license. Credentials, private
request and response bodies, evaluator-only answers, and restricted upstream
task text will not be released. The final repository URL, DOI, root license,
author metadata, and approved AI-use disclosure remain author inputs.
