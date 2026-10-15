# Proposal provenance inventory

## Question

Can the existing repository supply a real matched population for testing
flat feedback against interaction-aware separating-witness feedback during
automatic skill construction?

## Result

No.  Proposal identities are abundant, but they belong to three different
statistical objects.  Only one historical episode is a reusable skill proposal
inside the frozen typed finite grammar required by the current causal claim.

| Class | Observed identities | What the unit is | Eligible for the current matched study? |
|---|---:|---|---|
| Current DCP acquisition episodes | 5 | A proposed reusable rule or skill | One of five |
| Packing development trajectories | 132 source identities across 229 records | A per-instance formulation output | No |
| Legacy VERA development records inspected | 6 | A skill-lineage proposal under an older protocol | No |

This inventory is metadata-only.  It did not read or reproduce request bodies,
response bodies, proposal text, credentials or reference answers.

## Current DCP acquisition episodes

The repository contains five distinct proposal identities from the current DCP
research sequence:

1. an initial pair-spacing free-text proposal;
2. its counterexample-conditioned free-text revision;
3. an initial finite-count free-text proposal;
4. its counterexample-conditioned free-text revision; and
5. one finite-count proposal in the frozen 64-member typed grammar.

All five were sent once with DeepSeek-V4-Flash and none was promoted.  The
first four cannot be treated as exchangeable observations in the proposed
matched study.  They differ in family, prompt history, representation and
available verifier state; the two revisions also depend on their preceding
proposals.  They remain useful qualitative evidence for the failure taxonomy.

The fifth episode is the only strict historical unit.  Its candidate passed
20,977 semantic assignments before failing resource admission.  The frozen
grammar and verifier make a matched feedback comparison well-defined for this
state, but a single unit cannot establish a population-level causal effect.

## Why the 229 packing trajectories are not 229 skill-construction trials

`results/packing_reference_candidate_coverage.json` covers 229 exposed
development trajectories and 132 distinct source proposal hashes.  Ninety-four
original formulations mechanically compile.  The metadata-only reference
coverage analysis found 217 records with no structurally eligible reference,
11 requiring semantic review and one candidate that did not compile.

These records concern per-instance formulation outputs.  The acquisition claim
in the current paper concerns construction of a reusable skill under a common
skill grammar and verifier.  Re-labelling the 229 trajectories as skill
proposals would change the experimental unit after observing the data and would
inflate the effective sample size.

They may still serve a legitimate earlier stage of the methodology: clustering
benchmark failures to define candidate skill families.  That use must remain
separate from evaluating whether a feedback policy improves skill acquisition.

## Why legacy VERA proposals cannot fill the gap

The three inspected VERA development records expose six distinct proposal
identities.  They were produced under older task-specific protocols, their
development or promotion outcomes are already open, and they do not share the
current typed-count grammar, verifier or endpoint.  Pooling them with the typed
count episode would confound feedback policy with task family, representation,
history and evaluator.

They can be cited as historical design evidence, but not as matched observations
for the current automatic-acquisition claim.

## Consequence for the next experiment

The matched acquisition study needs a prospective population of independent
rejected typed skill proposals generated under one frozen grammar, verifier,
endpoint and custody protocol.  Only after those units exist should flat versus
separating-witness feedback be randomized or paired.  The existing four
free-text episodes may inform the preregistered failure taxonomy, the packing
trajectories may inform failure clustering, and the VERA records may motivate
design choices; none may be counted as a replacement observation.

The machine-readable inventory is
`experiments/proposal_provenance_inventory_20261015.json`.
