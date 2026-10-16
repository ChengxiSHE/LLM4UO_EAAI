# FormulationBench answer-blind custody audit

**Status:** complete fixed-source custody passed; same-fact serialization and
capacity gates remain open; no experiment was dispatched.

The custodian rebuilt the complete FormulationBench snapshot fixed at commit
`6f37a71e6251b11599ef42869e4268882985a8a7` and dataset tree
`793db197693fac5446fe1bd39aaf178fea437822`. The source first passed the strict
20-problem, 109-formulation, 89-pair and 63-proof structural census. It then
produced one atomic generation with three separated projections.

The inference projection contains exactly one canonical record for each of the
89 opaque pair identities. Each record contains the problem description,
answer-free parameter schema, two structured formulations and the official
parameter map. The custodian removes source metadata, source names, executable
code, imports, concrete data values and the upstream `valid` field before the
record is serialized. That last removal is essential because the candidate
formulation's `valid` field is a direct pair-level answer.

The metadata projection contains exactly one same-shape record per opaque pair.
It binds only the sanitized inference hash, byte count and generic structural
counts. It contains no pair label, proof-presence flag, evaluator path, raw
source hash, solution, code or data value. A synthetic counterfactual test
changes only the candidate answer and proof file, then verifies that every
inference and metadata byte remains identical.

The evaluator projection separately preserves exact problem data, solution,
full source formulations, parameter generators, Lean formulations, pair map
and any reformulation certificate. Its label is derived from the candidate's
boolean answer field. The custodian requires the source formulation to be
valid and requires the candidate answer to agree with certificate presence;
the fixed source passed this relation for all 89 pairs. Inference workers will
receive only the inference root and never the evaluator or private-ledger root.

Publication stages all files under a hidden generation directory, verifies the
complete path and byte set, and only then atomically renames the generation to
its terminal root. Synthetic interruption before the rename leaves no visible
custody root; byte-identical replay succeeds; drift, unsafe links, missing
files, collisions and unknown entries fail closed.

The machine-readable public audit is
`experiments/formulationbench_custody_audit_20261016.json`, SHA-256
`f2583a812259db6d0ae4cee63eea5b59804242ee4e9d1e75d3e5b380abb49e93`.
It binds the public inference/metadata projection, private evaluator projection
and private ledger only through aggregate hashes. It contains no problem body,
formulation algebra, code, data value, label, solution, proof, request,
response or credential.

This result proves deterministic answer-blind custody and atomic publication.
It does not yet prove that Flat-K and PCK-K contain identical semantic facts,
authorize a provider call, or support any mechanism or accuracy claim.
