# Indexed MILP IR v3 design

## Purpose

Replace the unbounded expanded `milp-v1` response in the compact
OptiTrust-style sensitivity with a bounded parametric representation.  The
language model states modeling knowledge once as indexed variable families and
constraint generators.  A trusted deterministic interpreter expands the IR
against the public `instance_data`, validates the resulting sparse MILP and
passes it to the existing solver endpoint.

This is a prospective v3 representation.  The stopped v2 common-38 run is not
resumed and none of its endpoint outcomes may tune the v3 semantics.

## Knowledge-separation rule

The interpreter is benchmark agnostic.  Its implementation may contain only:

- finite integer ranges and public-data record sets;
- Cartesian binding over declared finite sets;
- guarded arithmetic, comparisons and finite aggregates;
- indexed variable references and linear term accumulation;
- deterministic identifier construction; and
- syntax, numerical and resource validation.

It must not contain the strings `rcpsp` or `vrptw`, recognize their field
signatures, choose a formulation family, inject a constraint, or call the
current authored skills.  All formulation semantics in the sensitivity row
must appear in the model-produced IR and remain inspectable in its private
trajectory.

## IR contract

An `indexed-milp-ir-v1` object contains exactly:

1. `data_parameter`, fixed to `instance_data`;
2. ordered finite `sets`, each either a bounded integer range or records read
   from an explicit public-data path;
3. indexed `variables` with declared domains, bounds and guards;
4. indexed `constraints` containing finite linear-term generators; and
5. one linear `objective`.

Bindings range only over declared sets.  A record binding must explicitly
unpack its arity.  Numeric expressions can read public data, binding values,
finite arithmetic, conditionals and finite sum/min/max aggregates.  Predicates
can use comparisons, Boolean connectives and finite any/all aggregates.  There
is no recursion, dynamic code, string evaluation, implicit data lookup,
mutation or generated Python.

Variable and row identifiers are generated from a declared base plus
nonnegative integer indices.  The interpreter rejects duplicate identifiers,
unknown variable-family references, invalid paths, nonfinite arithmetic,
division by zero, empty min/max aggregates, unsupported key sets and excessive
expansion.  Zero coefficients are removed before strict `milp-v1` validation.

## Proof obligations

For public data `D`, admitted IR `q` and deterministic compiler `E`, admission
produces a certificate containing `H(D)`, `H(q)`, `H(E(D,q))`, exact resource
counts and the frozen interpreter identity.  Admission proves only:

- total termination within the declared expansion budget;
- every emitted coefficient and bound is finite;
- every linear reference resolves to one emitted variable;
- the expanded object satisfies the strict `milp-v1` schema; and
- declared resource limits hold.

It does not prove that the model matches the natural-language problem.  That
semantic claim remains measured by the frozen solver-facing benchmark endpoint
and protected by answer-blind inference.

## Transport and reliability contract

The candidate response is capped at a capacity-gated completion limit and 32
KiB of canonical JSON.  The first frozen worst-shape gate showed that 2,048
tokens truncates all three candidates after their constraint section; the clean
v2 gate therefore tests 3,072 tokens without reusing any v1 response.  Expanded
`milp-v1` bytes never traverse the provider.  Every canonical request must
terminate under the non-streaming transport bound before common-38 dispatch.

The user-provided `.venv-preparation` OpenAI/httpx stack is used for transport
consistency.  Streaming remains disabled for claim-bearing runs until partial
chunk durability and total wall-time semantics have a separate audited
contract.  A missing review becomes an abstention; it cannot erase a valid
canonical IR.  A missing canonical IR remains infrastructure unavailable.

The capacity gate tests only complete bounded envelope delivery.  Nested IR
compilation is reported diagnostically because the five review stages are the
method component responsible for repairing a surface-valid proposal.  No
candidate or patched candidate reaches the solver unless strict compilation
and resource admission succeeds.

## Scientific boundary

The resulting row remains an OptiTrust-style paper-structure sensitivity, not
an official reproduction, native five-language execution or equal-budget
leaderboard.  The generic interpreter is also a reusable method component for
the paper's knowledge-compilation story: authored skills, learned skills and
paper-inspired proposal trajectories can share the same proof-carrying
admission boundary without sharing benchmark-specific compiler code.
