# MIPLIB-NL same-knowledge source gate

**Status:** current official release fails source integrity and is not
dispatch-ready. No API, model, solver, native evaluator, or VM call was made.

## Decision

MIPLIB-NL remains a relevant, distinct source lineage for the prospective
same-knowledge study, but the current release cannot supply a complete frozen
cohort. The official `main` head checked on 2026-10-16 is still commit
`9f14ad1782eaa547f7dad982d1edb186321ffd88`, with dataset tree
`96132c089bbead0909c1ab9e55df59195ba8ec6f`.

The zero-model custodian rehearsal covered all 223 directories. It confirmed
223 metadata files, 223 reference programs, 180 reference models, 43 explicit
model absences, and 809 declared data files. The full materialization gate then
found that only 220 instances have identical declared and actual data-path
sets. Three instances mismatch: five declared files are absent and five
materialized files are undeclared. Equal aggregate totals do not establish a
valid mapping.

The official repository's open
[Issue #2](https://github.com/optsuite/MIPLIB-NL/issues/2) confirms one missing
declared file. It does not supply mappings or corrections for the complete set
found by this audit. The custodian therefore stopped before publication; both
attempted destination roots contain zero terminal files.

## Custody boundary

The implemented custodian mechanically separates:

1. inference input containing the task, parameters, declared file schema, and
   exact declared data bytes;
2. answer-free structural metadata; and
3. evaluator-only optimal values, reference formulations when present, and
   reference programs.

Thirty-eight focused tests prove synthetic separation, path confinement,
symlink rejection, duplicate-key and non-finite JSON rejection, recursive
sensitive-key rejection, exact-byte data preservation, opaque string reference
handling, atomic publication, replay, and drift detection. Fourteen publisher
tests also pass. These tests establish implementation behavior; they cannot
turn an incomplete upstream source into a complete 223-item bundle.

Reference values were read only by the trusted custodian and were never
rendered, scored, used for selection, or exposed to inference. No item was
excluded after this audit.

## Gate table

| Gate | State | Evidence or required closure |
|---|---|---|
| New source lineage | Passed | Fixed official commit and tree remain distinct from prior cohorts. |
| Trusted outcome isolation | Passed | Zero reference values reached public evidence, selection, or inference. |
| Source materialization | **Failed** | 220/223 exact; 3 mismatched; 5 missing declared and 5 undeclared actual files. |
| Answer-blind full-source custody | Open | Implementation passes tests, but no complete fixed-source bundle exists. |
| Packet completeness | **Failed** | Missing data paths prevent a 223-item inference/evaluator packet. |
| Rights-safe public-input route | Open | Attribution, share-alike, and upstream-file treatment still require review. |
| Resource contract | Open | No cohort may be selected from an incomplete source. |
| Scoreable endpoint | Open | No complete evaluator bundle or frozen endpoint contract exists. |
| Reference-access contract | Open | Evaluator separation exists in code but cannot be frozen for all 223 items. |
| Same-knowledge serializer | Open | Requires a complete canonical inference packet first. |
| Frozen selector | Open | The 220 exact items cannot be adopted after observing this audit. |

## Dispatch rule

No MIPLIB-NL inference or solver experiment may start from this fixed release.
We will not rename files, infer mappings, download guessed replacements, remove
the three affected instances, or claim the remaining 220 as a prospectively
frozen cohort. Dispatch can reopen only after an official hash-bound correction
passes the same zero-model custody rehearsal, or after a different untouched
benchmark passes every gate.

Machine evidence is in
`experiments/miplib_nl_custody_rehearsal_20261016.json`; the detailed human
audit is `docs/MIPLIB_NL_CUSTODY_REHEARSAL_20261016.md`.
