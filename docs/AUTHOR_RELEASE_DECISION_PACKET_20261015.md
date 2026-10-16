# Author release decision packet — authorized 2026-10-16

Status: **D1–D8 approved; metadata and licenses may enter the verified
history-free candidate; public publication is authorized after mechanical
verification**. The machine-readable decision record is
`experiments/author_release_decision_packet_20261015.json`.

## Approved scope

The user confirmed licensing authority for the 792 first-party candidate paths
identified by the source-bound rights inventory and approved Apache-2.0 for
first-party software, tests, scripts, and machine-readable artifacts. The user
also approved CC BY 4.0 for explicitly marked author-owned aggregate Source
Data and documentation, the NOTICE policy, the completed D5 atomic publisher,
the disclosure text below, and publication of the final verified history-free
candidate with a later archival deposit.

These grants do not relicense upstream benchmark text or answers,
evaluator-only answers, private request or response bodies, credentials,
external submodule contents, third-party generated programs, CoE, or Gurobi.
`vendor/solver-in-the-loop` remains an external gitlink pinned at
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` under its upstream terms. CoE is
retrieved from its pinned upstream source without vendoring; Gurobi remains a
separately installed commercial dependency.

The authorization also covers the first-party release metadata, audits, tests,
and the body-free `llm4or/public_antchat_transport.py` surface added during the
final five-layer candidate audit. The experiment-private request-envelope
runtime and its untracked development closure are deliberately not published.

## Verified author metadata

- Author: Chengxi She
- Affiliation: School of Management & Engineering, Nanjing University
- Corresponding email: `522023150104@smail.nju.edu.cn`
- ORCID: omitted because it was not independently verified
- Target venue: undecided
- Funding: not declared

No DOI has been reserved or invented. Repository publication and archival
deposit must be recorded only after the external states are verified.

## Data Availability

> Author-owned aggregate data supporting the findings of this study, including
> endpoint summaries, paired correction and regression counts,
> structural-group summaries, routing-identity records and figure Source Data,
> accompany the versioned software release under CC BY 4.0. The archival DOI
> will be added after archival deposit. Reused benchmark sources are retrieved
> at pinned revisions listed in the release metadata and remain subject to
> their upstream terms. Where redistribution is not authorized, the release
> provides metadata-only identities, checksums and reconstruction instructions
> rather than upstream task text or evaluator-only answers. Private request and
> response bodies, credentials and evaluator-only answers are not released.

## Code availability

> First-party code, typed skill and library manifests, public-only routing and
> verification code, aggregate evidence, figure-generation scripts and
> deterministic reconstruction commands are publicly available at
> `https://github.com/ChengxiSHE/LLM4UO_EAAI` under Apache-2.0. The archival DOI
> will be added only after an external archival deposit is verified. The live
> `v1.0.0` repository and release are independently verified.
> The solver-in-the-loop dataset remains
> an external pinned submodule under its upstream terms. Gurobi 13.0.1 requires
> a separate user installation and licence. Provider replay requires a
> user-supplied account and credential; credential-free evidence reconstruction
> does not.

## AI-use disclosure

> Language models were used in the explicitly identified candidate-generation
> experiments, in software-development assistance and in manuscript drafting.
> Candidate knowledge, code changes, numerical results and prose were not
> accepted solely on model output. Human authors defined the research questions
> and frozen evaluation contracts, reviewed the outputs, and verified the
> reported evidence through deterministic checks, independent endpoint scoring,
> source and citation audits, and reproducible reconstruction. The human author
> remains accountable for all claims, analyses, citations and released
> artifacts.

This packet records the user's authorization and the repository's technical
scope; it is not legal advice.

## Post-publication addendum — 2026-10-16

The authorized history-free candidate is now public at
<https://github.com/ChengxiSHE/LLM4UO_EAAI>; release `v1.0.0` and all attached
asset digests have been independently verified. D1--D8 and all third-party
exclusions remain unchanged. No archival DOI is claimed until an external
deposit is verified.
