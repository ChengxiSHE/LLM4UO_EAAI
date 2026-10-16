# Reconstruction publisher and solver boundary audit

Status: current behavior bound; replacement not authorized, 2026-10-15. The
machine-readable audit is
`experiments/reconstruction_publisher_solver_boundary_audit_20261015.json`,
SHA-256
`b5331ac3b605d153680becfa664910cfc00b93852c608986a7f144cf9bb8c22f`.

## Publisher result

All nine historical publishers now have a frozen description of their current
serialization, input-identity controls, path assumptions, temporary-file
behavior, durability and terminal-file ownership.

Three use compact canonical JSON, six use pretty JSON, and one of the canonical
JSON publishers also emits a Markdown summary. Three obtain a file `fsync`
through the shared `pipeline.write_json`; none fsyncs the containing directory.
None reserves the terminal output exclusively.

The current publication patterns are:

- existence precheck followed by direct text or byte write;
- a fixed sibling `.tmp` file followed by `replace`; or
- shared canonical JSON publication through a fixed `.tmp` followed by
  `replace`.

These patterns produce deterministic historical artifacts under cooperative
single-writer execution, but they do not prevent a second process from winning
between the precheck and write or from replacing a competing terminal result.
The nine scripts therefore remain valid provenance and cannot yet serve as the
publication layer of a concurrent clean-clone reconstruction command.

Any replacement must preserve, where applicable:

1. accepted input bytes, size limits, source hashes and path checks;
2. the exact field set and declared canonical or pretty serialization;
3. output SHA-256 identity for identical inputs;
4. fail-closed handling of missing, duplicate, invalid or mismatched inputs;
5. exclusive terminal ownership that never replaces a competing result; and
6. explicit recovery behavior for abandoned reservations and temporary files.

This is an equivalence requirement, not implementation approval.

## Solver boundary result

The two reviewed OR-Debug consumers share the pinned
`llm4or.or_debug_gurobi.solve_mps_text` wrapper. The frozen confirmation plan
uses one thread per solve, a 15-second solver limit and a 25-second wall limit;
the wrapper rejects MPS payloads above 1,000,000 bytes. The source dataset is
pinned to commit `c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010`.

The wrapper captures combined subprocess output, bounds wall time, and maps
timeouts and nonzero return codes to structured outcomes. The repository does
not supply the environment-specific Gurobi binary or user license.

`or_debug_static_public_runner.py` resolves the dataset root and model path and
checks containment before reading bytes. `or_debug_hidden_score.py` resolves
the row-provided model path but does not independently perform a local
containment check. The latter currently relies on the bound dataset and caller
contract; a future reconstruction boundary must make this reliance explicit or
strengthen it without changing endpoint semantics.

## Boundary

This audit freezes current behavior and exposes the exact remaining ownership,
durability, binary and path-contract gaps. It does not authorize a publisher
rewrite, redistribute Gurobi or its license, establish data rights, or prove a
clean-clone run. No network, model/API, solver, native evaluator or VM call was
made, and no request/response body, evaluator-only answer or credential was
read.
