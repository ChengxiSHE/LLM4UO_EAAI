# Offline analysis environment audit — 2026-10-15

## Decision

Layer B now has a passing, credential-free smoke test in a fresh temporary Python environment. The interpreter was exactly Python 3.11.16 and the installed analysis packages exactly matched `requirements-offline.txt`: NumPy 2.4.4, SciPy 1.17.1, jsonschema 4.26.0, and scikit-learn 1.9.0.

The machine-readable audit is `experiments/offline_analysis_environment_audit_20261015.json` (SHA-256 `0ce5e116043bab18c4852d0dde67adee3834fb1d6dc92f2c96983231576e8b7a`). The requirements file SHA-256 remains `6f359bfd71ebac9196dfb0c868f8279a4b3994c3f9b918372775feef41e030d3`.

## What was exercised

The verifier launches a child process with a new temporary home and an explicit minimal environment. It checks:

1. an exact deterministic NumPy operation;
2. a synthetic two-variable integer program through SciPy's internal MILP interface;
3. the frozen paired confirmatory statistics functions;
4. the public JSON Schema contract; and
5. synthetic public-text family grouping through scikit-learn.

All five checks passed. A separate standard-library-only preflight verifies that the requirements, verifier, tests, and directly exercised project modules are present, Git-tracked, and content hashed before any optional package is imported.

## Evidence boundary

This is an environment and code-path smoke test, not a rerun of a benchmark endpoint. It reads no benchmark instance, private evaluator answer, API request, API response, credential, or environment-secret value. It makes zero provider, external-solver, native-evaluator, or virtual-machine calls. The one MILP is an entirely synthetic program solved through SciPy's bundled interface and is recorded separately from the project's externally provisioned Gurobi layer.

Exact package versions are pinned, but the release does not yet bind distributable wheel hashes. Solver/native provisioning, provider replay, source rights, license selection, recursive-clone completeness, and history-safe publication remain separate release gates.
