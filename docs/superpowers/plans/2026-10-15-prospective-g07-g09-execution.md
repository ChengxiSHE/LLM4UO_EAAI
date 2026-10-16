# G07--G09 Prospective Program Execution Plan

**Spec:** `experiments/prospective_research_program_decision_20261015.json`

**Approval:** The user approved Scheme A on 2026-10-15. This removes the
architecture gate, but every stage remains bound to its own immutable plan,
budgets, custody boundary, and terminal ledger.

## Global constraints

- Use AntChat `DeepSeek-V4-Flash`, concurrency 5, with credentials read only by
  the isolated transport child.
- Never publish request/response bodies, evaluator-only answers, solver points,
  or credentials.
- Preserve full denominators. Individual transport, compilation, or solver
  failures become unavailable cells and do not stop independent work.
- Authentication, model, ledger-integrity, token-budget, and repeated transport
  failures remain global halts.
- Use the pinned Text2Opt revision and official BIND/CoE prompt sources. Do not
  tune baseline prompts or rerun selectively for a favorable result.
- Report BIND round 1 separately from its answer-bearing repair endpoint.
- Keep method-native, equal-budget, and author-native views separate.

## Task 1: Fresh external AntChat ledger contract

Extend the existing durable formal ledger with a narrowly whitelisted
`fresh_common_external` plan kind. It must support three-call BIND and
eleven-call CoE trajectories, exact public-input hashes, plan-bound contexts,
resume-by-slot, at most three accounted attempts per request, concurrency 5,
and body-private persistence. Add a transport-neutral label to the BIND runtime
without changing the historical default.

Verification: focused unit tests must first fail, then pass for scope limits,
payload binding, slot binding, concurrent distinct requests, shared-fingerprint
single-send behavior, recovery, and transport labeling.

## Task 2: Frozen fresh-common BIND row

Build a content-addressed plan over the existing 38 fresh packets and pinned
source records. Freeze official prompt/code/solver hashes, logical and physical
request limits, model, endpoint, concurrency, timeouts, token caps, and private
run directory. Run official BIND with up to three rounds per item. Continue
after item-local failures and checkpoint every terminal item.

Publish only body-free aggregates and hashes. Report round-1 and final full-
denominator accuracy, corrections, regressions, unavailable cells, physical
attempts, retries, and provider tokens. Independently reconstruct the report
from the private ledger without new API calls.

## Task 3: Frozen fresh-common CoE-safe row

Freeze one official current-snapshot, forward-only CoE-safe plan over the same
38 identities. Use five collaborations plus one reducer (eleven calls per
item), the restricted code translator, and the same evaluator endpoint. Run
once under fixed seeds and budgets; do not optimize the baseline.

Publish a body-free full-denominator report and an independent no-API audit.
Keep license/release limitations explicit.

## Task 4: Base and common-protocol synthesis

Freeze and run the direct Base row under the same public information regime,
model, endpoint, solver-facing evaluator, and concurrency. Add an equal-budget
sensitivity view without replacing method-native primary rows. Produce paired
correction/regression tables for Base, BIND round 1, BIND final, CoE-safe, and
the proof-carrying current method. Do not claim broad superiority from 38
instances alone.

## Task 5: G09 component program

Create separate content-addressed plans for semantic admission, resource
admission, routing, and complexity. Use the units defined by the approved
decision packet: a shared prospective proposal pool for semantic/resource
contrasts, independent library episodes for complexity, and a separate
zero/unique/multiple plus shift envelope for routing. Retain hard parser,
resource, time, and memory caps in every arm. Apply Holm family-wise control.
If independent library episodes cannot be constructed, keep complexity as a
theory-only design principle.

## Task 6: Evidence and manuscript closure

Update the goal audit, evidence manifest, manuscript, figures, and release
artifacts only after their producing audits pass. Preserve negative G08
acquisition evidence and distinguish authored Abstract/Acquire steps from
validated Admit/Route/Promote steps.

## Review focus

- No evaluator-only value can reach a first-round BIND, Base, CoE, or current-
  method request.
- A resumed slot cannot change its request fingerprint.
- Provider/model/usage violations halt globally; item-local failures do not.
- Public reports contain no bodies, code, objectives, points, or answer values.
- Paired statistics use fixed identities and full denominators.
