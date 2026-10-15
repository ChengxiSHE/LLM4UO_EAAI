# Disposition of the 35 untracked manifest paths

Status: **34 ready for explicit local-history integration; one requires a safe
projection**.

The v4 release snapshot leaves 35 paper-manifest paths untracked. This audit
recomputes every byte identity and gives each path one disposition. It does not
equate Git tracking with public-release or license clearance.

Thirty-four paths are project-authored manuscript material, aggregate Source
Data, body-free experiment records, evidence audits, or answer-free
certificates. Their current hashes match the paper manifest. A key-aware scan
finds no benchmark/request body value, repair object, repair identity,
credential literal, or reference-answer value in this 34-file set. They may be
added to local version history through the exact allowlist in the machine
audit, while retaining the explicit boundary that a root license and final
rights review remain open.

`results/or_debug_confirmation_evaluation_20261014.json` is different. It is a
3.58 MB full evaluation record with per-instance repair identity. It remains
untracked and must not be added as a public artifact. The paper needs a safe
projection that preserves denominator, group membership hash, corrected and
released endpoints, correction/regression cells, terminal-status counts, and
the source-record hash, while omitting repair identity, repair objects, task
text, solver points, and evaluator-only values.

This decision authorizes only an explicit local commit of the 34 named files.
It does not authorize a workspace-wide add, remote push, public release, root
license choice, or publication of the full OR-Debug evaluation record. No API,
model, solver, native-evaluator, or VM call was made, and no restricted value
was displayed.
