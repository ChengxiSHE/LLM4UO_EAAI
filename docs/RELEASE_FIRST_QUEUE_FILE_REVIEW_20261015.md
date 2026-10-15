# File review of the first Python release queue

Status: mechanical file review complete; rights and release clearance open,
2026-10-15. The machine-readable audit is
`experiments/release_first_queue_file_review_20261015.json`, SHA-256
`f9c8dc2a99b07f572f8550b7f5450c4790260f799c08f1ff1f42c7dc3fd523b6`.
No file is authorized for release by this review.

## Result

All 28 files in the first source-review queue now have per-file byte identity,
semantic role, top-level definition inventory, direct local and third-party
imports, bounded content and execution risk signals, and a release disposition.

| Review outcome | Files |
| --- | ---: |
| Frozen-evidence-bound | 23 |
| External record reconstruction | 5 |
| No high-risk literal signal in the mechanical content screen | 17 |
| Manual projection review required | 11 |
| Manual execution review required | 14 |
| Ordinary code candidates with neither review trigger | 13 |
| Release-cleared | 0 |

The content and execution queues overlap. A signal indicates where a reviewer
must look; it does not establish that a credential, private answer, network
transmission or unsafe write exists.

## Why the 28 files are not a runnable allowlist

Direct imports from the queue reach 18 other queue files, ten already tracked
files and two incidental untracked files. The two direct cut points are:

1. `scripts/prepare_tsp_constraint_confirmation.py` imports
   `llm4or/object_feedback_pilot_inputs.py`, pulling the historical provider,
   reviewer and packing stack into TSP preparation.
2. `llm4or/or_debug_hidden_score.py` imports
   `llm4or/or_debug_development_eval.py`, adding development-evaluation code to
   confirmation scoring.

Starting from the 28 files, conservative static recursion reaches 102 local
Python files. It also finds `cpmpy`, `jsonschema`, `numpy`, `psutil`, `pytest`,
`scipy` and `yaml` imports. The tracked offline requirements fix `numpy`,
`scipy` and `jsonschema`, but do not fix `cpmpy`, `psutil`, `pytest` or
`PyYAML`. Because several of these imports belong to incidental branches, the
correct response is to establish layer-specific runtime necessity before
adding packages, rather than expanding the environment blindly.

## Content boundary

The audit did not emit any literal value. The only first-queue file with long
literal assignments is `llm4or/finite_count_public.py`; the report records only
the declared constant names, character counts and hashes. Files with
private/evaluator terms remain in manual projection review even when the term
may refer only to a field name, path or scorer interface. This preserves the
rule that evaluator-only answers and benchmark bodies cannot be opened merely
to simplify release review.

## Rights and provenance boundary

All 28 files remain blocked by the missing root license, unresolved attribution
policy and absence of a reachable same-path/same-blob commit for the current
bytes. A mechanically clean file is not necessarily first-party or
redistributable. Conversely, a review signal does not mean the file must be
excluded; it may be publishable after an explicit safe projection and rights
decision.

## Next release actions

1. Select the repository license and attribution policy.
2. Review the eleven projection-triggered and fourteen execution-triggered files,
   without opening evaluator-only answer values.
3. Specify behavior-equivalence tests for the two dependency cut points before
   proposing any implementation refactor.
4. Freeze the actual non-Python inputs, binaries and per-layer environment.
5. Reconstruct the headline evidence from a recursive credential-free clean
   clone.

This review does not establish an executable or rights-safe allowlist. It makes
the remaining decisions file-specific and prevents the 28-file review queue
from being mistaken for a complete runtime closure. No network, model/API,
solver, native evaluator or VM call was made; no request/response body,
evaluator-only answer or credential was read; and the Git index and history
were not modified.
