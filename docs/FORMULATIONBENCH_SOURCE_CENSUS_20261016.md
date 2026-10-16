# FormulationBench fixed-source census

**Status:** passed the fixed-source body-free census; no experiment was
dispatched.

The official FormulationBench snapshot was fixed at commit
`6f37a71e6251b11599ef42869e4268882985a8a7` and dataset tree
`793db197693fac5446fe1bd39aaf178fea437822`. Its archive was downloaded from
the commit-specific GitHub endpoint, checked for path confinement and unsafe
archive member types, and extracted into a private temporary directory. The
archive has SHA-256
`78c9c4cf6e665cc4739482d634580a1a55a5476b0c786830a8f367914c3d4bf3`.

The source validator inspected directory entries with no-follow metadata calls.
It never opened a problem, data, solution, formulation, map or Lean file. The
validator requires the complete declared schema, rejects unknown entries,
missing required entries, links, special files, duplicate canonical problem or
formulation identities, and reformulation sides absent from the matching
problem.

The real fixed source passed with:

| Structural unit | Count |
|---|---:|
| problems | 20 |
| formulations | 109 |
| reformulation pairs | 89 |
| reformulation proof files | 63 |

The opaque pair-identity set hash is
`87f530293d915896248d141367a90047ca23fb7146d1eb33f02c844fcd5e565a`.
The path/type/size structure hash is
`03eacaa4bae8eebc90cf2beb59c3efd20a0dc6bca88fac90d01944fe4f67a14d`.
Neither hash reveals a pair identity or whether any particular pair has a proof.

The machine-readable audit is
`experiments/formulationbench_source_census_20261016.json`, SHA-256
`e5fda4361c4faefa90034d09d457c6da9932f788ff01df74672f49998a27fd78`.
It contains no problem body, data value, label, solution, formulation body,
proof body, request, response or credential.

This closes only fixed-source materialization and structural identity. It does
not create inference or evaluator projections, prove answer-blind worker
isolation, establish same-fact serialization, authorize provider calls, or
support any accuracy claim. Those gates remain prospective.
