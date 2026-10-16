# Fresh common-38 current-method native plan

**Goal:** obtain the first prospective current-method accuracy row on the frozen 38-identity common protocol without an API call or answer leakage.

1. Freeze all packet, model, source-code, solver-binary and budget identities before reading evaluator endpoints.
2. Solve each admitted model once with Gurobi CLI, one process and one solver thread at a time, with a 20-second solver and 25-second wall cap.
3. Persist one exclusive private checkpoint per identity. Resume completed identities, continue after per-item timeout or failure, and never overwrite a terminal cell.
4. Score only after all 38 cells are terminal, using the frozen Text2Opt objective/status endpoint and rel=1e-5/abs=1e-6 tolerances.
5. Publish only aggregate family/status/accuracy counts and hashes. Keep objectives, points and reference values private.
