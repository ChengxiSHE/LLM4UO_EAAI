# MIPLIB-NL answer-blind custodian design

**Date:** 2026-10-16  
**Status:** approved for implementation under the user's standing instruction to
self-confirm subsequent research work  
**Source identity:** `optsuite/MIPLIB-NL` commit
`9f14ad1782eaa547f7dad982d1edb186321ffd88`, dataset tree
`96132c089bbead0909c1ab9e55df59195ba8ec6f`

## Purpose

The prospective same-knowledge study needs a new benchmark lineage whose item
outcomes have not been opened. MIPLIB-NL is source-eligible, but its raw
`instance.json` co-locates the natural-language input with `optimal_value`, and
each instance directory also contains reference solver code and, for 180 of 223
items, `model.md`. Passing the raw directory to an inference worker would
invalidate answer blindness.

This subsystem creates a mechanically enforced custody boundary before any
model or solver dispatch. It must make it possible to prove which bytes an
inference worker can access without publishing task bodies or evaluator-only
answers.

## Non-goals

This implementation does not select the experimental cohort, derive modeling
facts, define the same-knowledge serializers, execute reference solver code,
score a candidate, or run an API/model/solver experiment. It does not resolve
all CC BY-SA or upstream MIPLIB redistribution questions. Those remain separate
gates.

## Considered approaches

1. **Manual redaction.** Copy files and remove visible answer fields by hand.
   This is rejected because it is not deterministic, auditable, or fail-closed.
2. **One output directory with permissions.** Keep inputs and references in one
   tree and rely on runtime file permissions. This is rejected because an
   incorrectly configured worker can regain reference access.
3. **Three disjoint projections with a hash ledger.** A trusted offline process
   validates the raw snapshot once, then materializes separate inference,
   resource-metadata, and evaluator roots. This is selected because the
   inference root is safe by construction and can be mounted alone.

## Trust boundary and data flow

The custodian is a local, standard-library-only process. It may read the fixed
raw snapshot. It never invokes a provider, model, solver, native evaluator, VM,
or third-party program. It writes to a new, empty custody root and publishes all
terminal files without replacement.

```text
fixed raw snapshot
       |
       v
strict schema + path + content checks
       |
       +--> inference/     task text + parameters + declared data only
       +--> metadata/      answer-free size/capacity descriptors only
       +--> evaluator/     optimal value + reference model/code only
       +--> private ledger cross-binding every source and output hash
       +--> public audit   counts, identities, hashes, gates; no bodies/answers
```

An inference worker receives only the `inference/` root. The evaluator receives
the frozen candidate output plus the `evaluator/` root and, when necessary, a
read-only view of the corresponding inference data. The two roots have no
relative links and contain no symlinks.

## Input contract

The raw root must contain `dataset/<instance>/` directories from the fixed Git
tree. Every instance must contain regular, non-symlink `instance.json` and
`solve.py`; `model.md` is optional because the frozen tree contains only 180.
Only data files declared by `instance.json` may enter the inference projection.

The initial strict top-level JSON contract accepts exactly:

- `abstract_problem`
- `parameters`
- `files`
- `optimal_value`

JSON is parsed with duplicate-key and non-finite-number rejection. Unknown
top-level fields fail closed. If the real snapshot contains additional fields,
a schema-census mode may report only field paths, JSON types, occurrence
counts, and source hashes. No value is emitted. Extending the allowlist then
requires an explicit contract version change; the implementation must not
silently copy unknown content.

Each `files` entry must resolve beneath the same instance's `data/` directory.
Absolute paths, `..`, empty components, duplicate normalized paths, links,
devices, sockets, FIFOs, and undeclared files fail. Version 1 admits UTF-8 CSV
data only. Declared CSVs are opaque inputs: empty, headerless, ragged, and
rectangular files are all valid source shapes and are never rewritten. When a
first row exists, its cells are also screened as possible field names and are
rejected if their normalized text implies solutions, answers, optimal values,
objectives, incumbents, bounds, gaps, or reference outputs. The scan is a guard
in addition to the source contract, not a claim that a deny-list proves
semantic safety.

## Outputs

### Inference projection

For each instance, `inference/<opaque_id>/instance.json` contains only
`abstract_problem`, `parameters`, and `files`. It preserves their values and
canonicalizes JSON deterministically. The directory contains byte-identical
copies of the declared data files and nothing else. It never contains
`optimal_value`, `model.md`, `solve.py`, raw `instance.json`, or a path to the
evaluator root.

### Answer-free metadata projection

`metadata/<opaque_id>.json` contains source/output hashes, byte counts, declared
file counts, CSV row and column counts, parameter-key/type structure, whether a
reference model exists, and the source commit/tree identity. It contains no
task prose, parameter values, data values, optimal value, model text, or code.
This is the only material a later resource selector may inspect before cohort
freeze.

### Evaluator projection

`evaluator/<opaque_id>/reference.json` contains the exact parsed
`optimal_value`, its canonical hash, and source bindings. `solve.py` and the
optional `model.md` are copied byte-identically into this root. They are data,
never imported or executed by the custodian.

### Private ledger and public audit

The private ledger maps source directory identities to opaque IDs and binds
every source and projected file by SHA-256. It remains outside the public
release. The public audit contains only aggregate counts, source commit/tree,
directory-name-set hash, schema fingerprints, terminal bundle hashes, failure
counts, and explicit execution/privacy fields. It must pass a recursive
forbidden-key check and contain no task body, data value, code body, objective
value, credential, request, or response.

## Failure and publication semantics

The custodian validates the entire source before terminal publication. It
writes to a fresh staging directory beneath the custody root, fsyncs files and
directories, and atomically reserves the final bundle. An existing
byte-identical terminal bundle is an idempotent success; any differing terminal
or reservation is a conflict. A failed validation publishes no partial
inference or evaluator root. Recovery never uses a time-to-live assumption.

Errors identify only the instance's opaque hash and a reason code. They must
not echo JSON values, task text, CSV rows, reference code, model text, or the
optimal value.

## Interfaces

The module `llm4or.miplib_nl_custody` exposes pure validators and one projection
builder. The CLI `scripts/build_miplib_nl_custody.py` has three explicit modes:

- `--schema-census`: body-free field/type census; no projections;
- `--write`: validate and publish into an absent custody root; and
- `--check`: reconstruct hashes in memory and require byte-identical terminals.

The CLI requires an explicit raw root, custody root, fixed commit, and dataset
tree. It does not read credentials or ambient provider configuration.

## Verification

Synthetic fixtures must prove:

- `optimal_value`, `model.md`, and `solve.py` never appear in inference;
- inference bytes and evaluator bytes are deterministically hash-bound;
- duplicate JSON keys, NaN/Infinity, unknown keys, nested sensitive keys,
  undeclared data, unsafe CSV headers, path escapes, symlinks, special files,
  duplicate identities, and terminal collisions fail closed;
- optional absence of `model.md` remains explicit and accepted;
- errors contain no source values;
- schema-census and public-audit outputs are body-free;
- reruns are deterministic and `--check` detects any drift; and
- the complete operation records zero API/model/solver/native/VM calls and no
  credential access.

After synthetic tests pass, a zero-model/zero-solver rehearsal on the fixed
snapshot may run. The rehearsal is successful only if all 223 source
directories are terminal, the inference/evaluator separation checks pass, no
raw or reference file is reachable from the inference root, and a body-free
audit reproduces exactly. It still does not authorize experimental dispatch.

## Acceptance boundary

Passing this design closes only the answer-blind custody implementation and
packet-completeness inventory. Rights review, resource-bounded selection,
endpoint/evaluator validation, atomic-fact identity, and experiment freeze
remain open. No formulation-accuracy or mechanism claim follows from the
custodian.

## Fixed-source rehearsal outcome

The 2026-10-16 rehearsal against source commit
`9f14ad1782eaa547f7dad982d1edb186321ffd88` closed the implementation check but
did not publish a custody bundle. Of 223 source directories, 220 had exact
declared-versus-materialized data identity and three did not; the mismatches
contained five missing declared paths and five undeclared materialized paths.
One of the missing files is independently recorded in the upstream issue
tracker. Because the reference programs name the declared paths, the custodian
does not infer aliases, drop records, or construct a post-audit subset.

The fixed release therefore fails the source-materialization and packet-
completeness gates. No API, model, solver, native evaluator, or VM call was
made, and no terminal inference or evaluator bundle was published. A future
rehearsal requires an upstream-complete snapshot or a separately frozen source
whose path identities pass the same whole-source check.
