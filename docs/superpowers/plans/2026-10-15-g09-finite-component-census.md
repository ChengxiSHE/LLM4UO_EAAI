# G09 finite component census execution plan

**Approval:** Scheme A was approved on 2026-10-15. This is the bounded offline
Stage 3 implementation after the negative Stage 1 acquisition canary. It does
not reopen Stage 2.

## Estimands

1. **Semantic/resource admission census.** Enumerate all 64 members of the
   frozen typed-count candidate grammar. Compare full admission,
   no-semantic-gate admission, and no-resource-gate admission using the same
   verifier outputs. This is an exact finite-population decision census, not a
   sample from a proposer distribution.
2. **Selective-routing census.** Freeze a finite key-transformation grammar over
   the RCPSP and VRPTW typed interfaces. Enumerate zero-, unique-, and
   multiple-match envelopes under exact, additive, missing-key, renamed-key,
   partial-cross-family, unrelated, and new-family shifts. Compare exactly-one
   routing with a forced-first policy.
3. **Complexity control.** Report no empirical causal estimate because the
   repository contains zero independent common-pool library-selection episodes.
   Prefix-code/MDL control remains a theory and protocol component.

## Safety and claim boundaries

- No API, credential, solver, native evaluator, VM, benchmark answer, request
  body, or response body is used.
- Unsafe arms are scored offline only. They never publish a skill, execute a
  candidate, or change the current library.
- The semantic/resource result is exact only for the 64-member grammar. If the
  resource gate subsumes the semantic gate on this population, semantic
  necessity remains unidentified rather than being declared absent.
- The routing result is exact only for the frozen envelope grammar. It supports
  a bounded ambiguity/shift guarantee, not unrestricted distribution-shift
  robustness.
- No p-value or Holm claim is attached to a complete deterministic census.
  Generalization beyond the enumerated populations remains open.

## Implementation

1. Add a pure census module with deterministic population builders and scorers.
2. Test exact population uniqueness, full coverage, arm behavior, privacy, and
   deterministic reconstruction before publishing evidence.
3. Publish a canonical machine-readable result and a concise human-readable
   report with exclusive creation.
4. Update the G09 evidence boundary only after the focused tests and independent
   reconstruction pass.
