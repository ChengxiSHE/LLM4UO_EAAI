# Goal-evidence Git-index closure audit

## Decision

The goal audit's Git-index backlog is closed. Before this step, 34 unique
project-authored audit and preflight files were present locally with correct
hashes but absent from the index. They were added through an exact allowlist;
no workspace-wide add was used.

The allowlist contains 16 JSON files and 18 Markdown reports, totalling 298,476
bytes before normalization. All 34 initially matched the hashes in the
pre-closure goal audit. Five Markdown date lines contained trailing spaces;
those spaces were removed, `git diff --check` was rerun, and the five final
hashes were rebound in the goal audit. The final sorted
`path + NUL + SHA-256` set has SHA-256
`69b19feb787e9b81149f77d7b5c71bdf12bb82494a27e50c0651d6e62d6ab0d0`.

## Safety checks

- All 16 JSON files parse.
- Bearer-token, OpenAI-style-key and quoted-secret-assignment scans have zero
  hits.
- Exact recursive JSON keys for task text, request/response bodies, repair,
  evaluator answers, solver objective/point and credentials have zero hits.
- The files are project-authored theory, experiment-design, release-audit and
  figure-preflight records; no model or solver output body is added.

After the commit, every goal-evidence path exists in the index with its
declared hash. The 69 paper-manifest paths also remain exact at index level.

## Boundary

This closes only evidence-file presence. It does not select a license, establish
third-party redistribution rights, make all historical producers runnable,
initialize the solver submodule, supply Gurobi, prove the layered environments,
run a clean-clone reconstruction or remove restricted blobs from local branch
history. G11 remains open.
