# FormulationBench source qualification

**Status:** fixed source passed body-free census, answer-blind custody and
full-population same-fact serialization; the capacity gate remains open; no
experiment is authorized or dispatched.

## Decision

[FormulationBench](https://github.com/henryrobbins/formulation-bench) is the
preferred replacement for the incomplete MIPLIB-NL release in the G09
same-knowledge mechanism study. The official source was fixed before any task,
label, solution, formulation, or proof body was opened:

- commit `6f37a71e6251b11599ef42869e4268882985a8a7`;
- tree `793db197693fac5446fe1bd39aaf178fea437822`;
- explicit [MIT license](https://raw.githubusercontent.com/henryrobbins/formulation-bench/main/LICENSE.md);
- official paper [FLARE](https://arxiv.org/abs/2608.25220); and
- complete GitHub tree metadata, 947 entries and 665 blobs, with no truncated
  response.

The official aggregate description reports 20 optimization problems, 109 MILP
formulations, and 89 reformulation pairs: 63 positive and 26 negative. The
body-free tree census independently recovers 20 descriptions, problem schemas,
data files and solutions; 109 structured formulations, parameter generators
and Lean formulations; 89 pair maps; and 63 Lean reformulation proofs. The
counts agree without identifying which pair carries which label or proof.

The fixed-commit archive was subsequently materialized in a private temporary
directory. A strict source validator inspected only file types, paths and byte
sizes; it did not open any benchmark file body. It rejected undeclared files,
missing required files, links, special files, duplicate canonical identities
and pair sides absent from the corresponding problem. The real source passed
with the same 20/109/89/63 counts. The body-free audit is
`experiments/formulationbench_source_census_20261016.json` (SHA-256
`e5fda4361c4faefa90034d09d457c6da9932f788ff01df74672f49998a27fd78`).

## Why this source fits the research question

The current paper already establishes complete-system formulation-accuracy
gains, but the successful methods change both knowledge content and
architecture. FormulationBench supplies an external, recent, formally grounded
task where the same two formulation facts can be serialized in a flat view or
a proof-obligation view. Pair validity remains an evaluator-only label. This
allows a paired, full-denominator test of representation and verification
without claiming that it re-estimates TSP or OR-Debug generation accuracy.

Its role is therefore narrow and useful: external task-level evidence for G09,
combined with the existing finite routing and complexity censuses. It does not
replace the benchmark-generation accuracy results.

## Alternatives considered

| Source | Disposition | Reason |
|---|---|---|
| MIPLIB-NL | Rejected for current release | Three of 223 directories fail declared-versus-materialized path identity. |
| OR-Bench and the assortment contribution | Not selected now | Promising modeling endpoints, but no explicit repository license was observed at qualification time and the answer/input custody surface is less mature. |
| ProOPF | Not selected now | No explicit repository license was observed and the official evaluator requires MATLAB/MATPOWER. |
| FrontierOR | Out of scope for G09 | Its primary estimand is efficient algorithm design rather than formulation equivalence under fixed knowledge. |
| FormulationBench | Selected in principle | Explicit MIT license, path-separated answers and proofs, machine-checked positive certificates, and an exact 89-pair full denominator. |

Absence of an observed license is not a permanent legal conclusion; it is a
fail-closed release decision for the current study.

## Remaining gates

The complete fixed source now has a verified three-projection custody bundle.
Inference records remove the upstream candidate `valid` answer, source
metadata, executable code, concrete data and proof-presence signals; evaluator
material remains in a separate private root. The public audit is documented in
`docs/FORMULATIONBENCH_CUSTODY_AUDIT_20261016.md`.

The dual-view serializer now verifies all 89 pairs: Flat-K and PCK-K contain
the same 4,935 content-addressed semantic facts and the same six fixed generic
checks, with zero fact or guidance mismatch. The public audit is documented in
`docs/FORMULATIONBENCH_SAME_FACT_AUDIT_20261016.md`.

No model or solver call may start until a synthetic capacity canary
demonstrates typed, bounded responses below the known non-streaming transport
cutoff across the observed input-size envelope. Only after that gate passes may
the 89-pair full-denominator plan be frozen.

The machine-readable audit is
`experiments/formulationbench_source_qualification_20261016.json`. It records
zero API, model, solver, native or VM calls and zero benchmark bodies, labels,
solutions or proof bodies opened.
