# Post-publication release closure — 2026-10-16

## Verified public state

The history-free repository is publicly available at
<https://github.com/ChengxiSHE/LLM4UO_EAAI>. Its default `main` branch points to
commit `3b870323935fa0a00ffd3fe9d1dc3512323beacf`, whose tree is
`3c90e562c0f3f228c2a1a031320dd75b80257304`. The commit has no parent and is
the only commit reachable from the `v1.0.0` release tag. The previous repository
was renamed to a private legacy backup before the public repository was created;
the public Git object store therefore never received its earlier history.

The public release is available at
<https://github.com/ChengxiSHE/LLM4UO_EAAI/releases/tag/v1.0.0>. Eleven release
assets are public. GitHub's server-reported SHA-256 digest and size match the
local source for every asset, including the exact 6,540,184-byte candidate
bundle with SHA-256
`bc8b817fddf8844bafe468b33860355b4bd2d2dfc2c699ea74e204f24530c658`.

## Independent public clean clone

An unauthenticated recursive clone retrieved both the public main repository and
the pinned solver-in-the-loop submodule at
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010`. Full Git object checks passed for
both repositories. In that fresh clone, 79 credential-free Layer-A tests and 12
additional release/provider tests passed with zero failures. Six deterministic
reconstruction and preflight commands also passed, and the checkout remained
clean. These commands made no API/model, benchmark-solver, native-evaluator or
VM call and read no credential, private request/response body or evaluator-only
answer.

The separate local B--E audits also pass for the identical release tree: exact
offline analysis, external-license Gurobi synthetic checks, the zero-call
DeepSeek-V4-Flash transport preflight at concurrency five, and exact main-figure
reconstruction.

The public checks establish release integrity and aggregate-evidence
reconstruction. They deliberately do not rerun provider inference or rescore
restricted benchmark endpoints from evaluator-only answers. A separate frozen
controlled-review protocol covers that endpoint-recomputation claim under
non-redistributive reviewer custody.
The controlled reviewer subsequently reproduced all three central endpoint
families exactly; that aggregate audit is separate from the immutable public
release and does not add restricted materials to it.

## Remaining archival boundary

No archival DOI has been verified. The GitHub Release is public and immutable
by tag, but the manuscript must continue to mark the DOI as pending until an
external archival service records the deposit. No DOI is inferred or invented.
