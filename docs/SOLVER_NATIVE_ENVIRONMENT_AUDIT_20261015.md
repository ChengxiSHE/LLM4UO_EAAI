# Solver/native environment audit — 2026-10-15

## Decision

The machine-local solver/native layer passes a synthetic smoke test under its frozen external-dependency contract. The result is deliberately labeled `passed_local_solver_native_smoke_external_license`: it confirms this machine's runtime, not credential-free portability.

The machine-readable audit is `experiments/solver_native_environment_audit_20261015.json` (SHA-256 `3476e963a270f19756fe7147e92bb50b5b895f8ead1aa950c02c411b42b445b0`).

## Bound identities

- Gurobi CLI: version 13.0.1 at `/usr/local/bin/gurobi_cl`; resolved binary SHA-256 `306eb8c94fd58fec71817db556d0c022bda7657df46c4f62772dad7258a3171e`.
- OR-Debug submodule: `vendor/solver-in-the-loop` at commit `c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010`, clean working tree.
- Submodule inventory: 4,962 tracked MPS models plus tracked dataset, README, and LICENSE paths.
- Frozen OR-Debug limits: one thread, 15-second solver timeout, 25-second wall timeout, and 1,000,000-byte MPS cap.

## Synthetic checks

Three local solver invocations were made. First, the declarative MILP adapter solved a two-variable mixed-integer model and independently rechecked the returned primal point and objective. Second, the OR-Debug adapter computed a fresh IIS for a small contradictory system. Third, the generic IIS repair was applied and the repaired MPS solved to the expected optimum. Every check passed.

The verifier initially failed before any solver invocation because a clean interpreter did not place the repository root on its module path. The launcher was corrected to bind that root explicitly, after which the same tests passed.

## Evidence boundary

The verifier does not locate, read, hash, copy, or report a solver-license file. The vendor binary may resolve a user-provisioned license internally. The verifier also does not read the OR-Debug dataset contents, benchmark models, hidden answers, model/API request or response bodies, or credentials. No provider or virtual-machine call is made.

This layer therefore supports a precise local-runtime statement only. Public credential-free reconstruction still rests on Layer A and frozen projections; release rights, license selection, wheel artifacts, provider replay, and history-safe publication remain independent gates.
