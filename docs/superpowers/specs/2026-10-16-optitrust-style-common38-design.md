# OptiTrust-style Common-38 Sensitivity Design

## Purpose

Close the scientific gap between an artifact-availability audit and an
executed OptiTrust comparison. The authors have not released a verified
runnable package for arXiv:2508.03117v1, so this study is a paper-based
sensitivity analysis. It must never be described as an official-code
reproduction, a fine-tuned OptiTrust checkpoint result, or a replacement for
the unavailable official artifact.

The study reuses the frozen 38-problem RCPSP/VRPTW cohort, DeepSeek-V4-Flash
provider, trusted Gurobi endpoint, full denominator, retry ledger, concurrency
five, and post-inference evaluator boundary used by the existing common
protocol. It adds only the method structure recoverable from the paper.

## Method boundary

The paper describes decomposition, one decomposition reflection, formulation,
one formulation reflection, five modeling-language-conditioned code paths,
solver validation, and solution voting. Its released source contains partial
prompt structures but no runnable code, complete prompts, demonstrations,
15,000-sample training data, fine-tuned Granite checkpoint, or inference
configuration.

The design is grounded in the inspected arXiv v1 source archive
`2508.03117v1` (SHA-256
`c550894d070b32877713053b0fc87e8df1b4e864a1055c2b71071d9c35123c7e`)
and the repository's static and public-artifact audits. A later official
artifact supersedes this sensitivity for any official-reproduction claim.

The sensitivity therefore freezes nine model calls per problem:

1. decomposition;
2. decomposition reflection;
3. formulation;
4. formulation reflection; and
5. one candidate for each of Pyomo, Gurobipy, DOcplex, CVXPY and PySCIPOpt.

Prompts are first-party paraphrases of the published stage responsibilities,
not copied prompt text. Every stage receives the original public problem. The
candidate stages also receive the reflected components and formulation.

## Safe execution adaptation

Executing arbitrary generated Python is prohibited. Each language-conditioned
candidate must return the repository's strict `milp-v1` sidecar instead of
executable code. This keeps the paper's five language-conditioned views while
making all candidates pass through the same schema, resource caps and trusted
Gurobi CLI. The adaptation is part of the method label:
`OptiTrust-style-safe-sidecar`; it is not native five-library execution.

Each candidate is independently validated and solved. Only optimal candidates
participate in voting. Objectives are grouped with the frozen endpoint
tolerances (`rtol=1e-5`, `atol=1e-6`). A strict majority of at least three of
five candidates is required. Multiple strict majorities are impossible; no
majority, all-invalid, non-optimal and tied outputs fail closed. The selected
objective is compared with the evaluator-only reference only after all nine
responses have been durably recorded and no further model request is possible.

## Components

- `llm4or/optitrust_style_runtime.py`: pure prompt construction, response
  parsing, candidate solving, strict-majority selection and post-inference
  scoring.
- `llm4or/fresh_common38_optitrust_style.py`: frozen plan, authorization,
  checkpointing, concurrent execution, body-free public result and ledger
  summary.
- `scripts/freeze_fresh_common38_optitrust_style.py`: exclusive plan and
  authorization publisher.
- `scripts/run_fresh_common38_optitrust_style.py`: resumable live controller.
- `scripts/score_fresh_common38_optitrust_style.py`: body-free result
  publisher.
- `scripts/audit_fresh_common38_optitrust_style.py`: independent plan, cell,
  ledger, denominator and result reconstruction without new provider calls.
- `tests/test_optitrust_style_runtime.py` and
  `tests/test_fresh_common38_optitrust_style.py`: pure runtime, gateway and
  controller contracts.

## Data and privacy flow

The public request contains the frozen natural-language description and public
structured instance data. Private source files remain ignored. Request and
response bodies stay in `results/private`. Public artifacts contain only
problem identity, family, terminal status, candidate status counts, consensus
presence, correctness flags, model hashes and aggregate accounting. They omit
problem text, generated reasoning, formulations, model bodies, objective
values, solution points, reference values and credentials.

## Failure and recovery

The existing formal gateway reserves every physical attempt before dispatch,
deduplicates request fingerprints, allows at most three recorded attempts per
request, continues after per-request exhaustion, and halts only on global
authentication, model, accounting, budget or repeated transport failures.
Every problem has an exclusive terminal cell. A restart reuses completed
responses by fingerprint and never silently changes a slot's request.

## Evaluation and claims

The primary endpoint is full-denominator objective/status accuracy on the same
38 identities. Report RCPSP and VRPTW separately, terminal/infrastructure
counts, strict-majority coverage, valid candidate counts, physical attempts,
retries and tokens. Add paired corrections/regressions against the current
method and other common-protocol rows, but preserve the existing unequal-call
and unequal-construction-cost boundary.

Permitted claim: a paper-structure OptiTrust-style sensitivity was locally
executed under the common endpoint.

Prohibited claims: official OptiTrust reproduction; evaluation of the
fine-tuned Granite checkpoint or synthetic-data contribution; native execution
of five modeling libraries; equal-budget leaderboard; broad benchmark
superiority.

## Acceptance criteria

1. All prompt, parser, voting and gateway contracts are covered by tests that
   fail before implementation and pass afterward.
2. The frozen plan reconstructs byte-for-byte and binds 38 identities, nine
   calls, concurrency five, DeepSeek-V4-Flash and the trusted solver.
3. A no-network offline simulation proves restart, terminal-cell, privacy and
   score behavior.
4. The live run reaches 38 terminal cells without excluding failures.
5. An independent read-only audit exactly reconstructs the public result and
   accounting with zero new provider calls.
6. The manuscript and evidence manifest label the row as paper-based and bind
   all limitations above.

## Autonomous approval record

The user explicitly instructed the agent to confirm and approve subsequent
work autonomously. Under that standing instruction, this design is approved
for implementation without a separate confirmation turn.
