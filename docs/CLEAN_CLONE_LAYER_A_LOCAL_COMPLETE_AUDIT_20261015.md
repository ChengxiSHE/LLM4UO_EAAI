# Clean-clone Layer A with complete local submodule snapshot — 2026-10-15

## Decision

A new no-local main-repository clone at commit `cbd41fbef24d2b55524b01842c65b4f424c38962` passed the credential-free Layer A suite using a copied local solver submodule whose complete reachable object graph was independently verified. The machine-readable audit is `experiments/clean_clone_layer_a_local_complete_audit_20261015.json` (SHA-256 `181d44f01c9eb1c1338660f8b827ad4cdada35810a804784a06a37e8c1c75e37`).

The clone was clean before and after reconstruction. Fifty-three tests passed, followed by successful current-library manifest rebuilding, body-free identity reconstruction, and paper-evidence reconstruction. The commands ran in a blank home with eight explicitly named non-secret environment variables and made no model, API, solver, native-evaluator or virtual-machine call.

## Submodule improvement

The copied submodule is exactly commit `c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010`. Unlike the earlier partial-snapshot audit, the runner now executes `git rev-list --objects --all --missing=print` and `git fsck --full` inside the cloned submodule. It found zero missing reachable objects and passed the full object check.

Earlier on the same date, the configured GitHub remote returned the same pinned `main` commit and supplied the four objects missing from the original partial checkout. A later fresh recursive clone attempt failed before object validation because two HTTPS connections to GitHub each timed out after about 75 seconds; a subsequent short reachability check failed the same way. Therefore this artifact closes local complete-object reconstruction but deliberately leaves current-run remote acquisition false. Internet availability remains an external prerequisite for a new machine.

## Boundary

This audit does not supply Gurobi or a license, does not close repository licensing or source rights, and does not make the current Git history safe for public push. Separate audits now close the local solver smoke test, offline analysis smoke test, provider transport preflight, and figure reconstruction, each under its own stated boundary. Historical publisher exclusivity and the history-free rights-reviewed release remain open.
