# MIPLIB-NL custody rehearsal

**Status:** failed source-materialization gate; no private bundle was published
and no experiment was dispatched.

## Result

The fixed official snapshot was inspected by the fail-closed custodian at
commit `9f14ad1782eaa547f7dad982d1edb186321ffd88` and dataset tree
`96132c089bbead0909c1ab9e55df59195ba8ec6f`. The schema census covered all
223 instance directories without making an API, model, solver, native, or VM
call. It found 223 `instance.json` files, 223 reference programs, 180 reference
models, 43 explicit model absences, and 809 declared data files. Reference
values remained evaluator-only and were never rendered.

The terminal materialization check did not pass:

| Check | Count |
|---|---:|
| Instances with exact declared/actual data-path sets | 220 |
| Instances with a path-set mismatch | 3 |
| Declared files absent from the snapshot | 5 |
| Materialized files not declared by `instance.json` | 5 |
| Published custody files | 0 |

Declared and actual file totals are both 809, but equality of totals does not
repair the five path-identity mismatches. The missing declared names are used
by the corresponding upstream reference programs, while the undeclared names
cannot be substituted without an upstream mapping. The official repository's
open [Issue #2](https://github.com/optsuite/MIPLIB-NL/issues/2) independently
confirms one missing declared file; it does not explain or authorize repairs
for the full set found here. The official `main` head remained the fixed commit
when checked on 2026-10-16.

## Custodian behavior

The implementation now accepts the two observed top-level schemas, preserves
numeric and opaque-string reference values only in the evaluator projection,
and treats empty, ragged, or headerless declared CSV files as exact opaque input
data. It still rejects path escape, links, undeclared files, missing declared
files, sensitive first-row fields, malformed UTF-8, duplicate JSON keys,
non-finite JSON, and projection drift. Thirty-eight focused custody tests and
fourteen atomic-publisher tests pass.

The full-source write stopped before publication with a source-materialization
error. Both attempted private destination roots remained empty. This is the
intended fail-closed behavior, not an infrastructure failure.

## Decision

The current MIPLIB-NL release is not eligible for the prospective
same-knowledge experiment. We do not silently rename files, download guessed
replacements, remove the three affected instances, or promote the 220 exact
instances after seeing this audit. Dispatch remains closed until the official
source supplies a hash-bound correction or a different untouched benchmark is
qualified under the same custody rules.

The machine-readable evidence is
`experiments/miplib_nl_custody_rehearsal_20261016.json`. It contains no task,
data, model, reference-program, answer, request, response, or credential body.
