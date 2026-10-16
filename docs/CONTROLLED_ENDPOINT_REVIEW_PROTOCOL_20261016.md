# Controlled endpoint review protocol — 2026-10-16

## Purpose

The public `v1.0.0` package is an integrity/audit release. It intentionally
excludes upstream task bodies that are not authorized for redistribution,
evaluator-only answers, private request/response bodies and credentials. This
protocol lets a conference artifact chair or designated independent reviewer
recompute the central endpoint claims without making those materials public.

## Custody and separation

The reviewer receives a read-only encrypted volume containing only the
hash-bound inputs listed in the machine protocol. The reviewer uses a fresh
checkout of the public code, verifies every input and code hash before scoring,
disables network access, and writes only an aggregate attestation. Problem text,
reference objectives, points, repair objects and per-instance outputs never
enter the attestation. No author process may edit the method, router, compiler,
endpoint or denominator after the volume is opened.

## Required checks

1. **TSP sealed confirmation:** reconstruct references from the pinned upstream
   source, score both frozen 140-row candidate arms with the frozen evaluator,
   and reproduce 54/140 versus 100/140, 46 corrections and zero regressions.
2. **OR-Debug confirmation:** score both frozen terminal arms on all 2,845 held
   out records in a temporary workspace, retain evaluator failures in the full
   denominator, and reproduce both released-label and source-corrected endpoints
   plus the prespecified 100-group inference.
3. **Fresh common-38:** rebuild the four independent method audits, verify all
   38 aligned identities, and regenerate method counts, paired corrections and
   regressions, and Holm-adjusted tests from the frozen result rows.
4. Verify zero model/API calls during review, report solver calls, preserve the
   fixed denominator and destroy the decrypted review volume after signing the
   aggregate attestation.

## Claim boundary

A passing controlled review supports independent endpoint recomputation under
restricted-data custody. It does not make the private material redistributable,
prove equal construction cost for common-38, establish broad benchmark
superiority, or replace a future rights-safe public scoring bundle.
