# History-free mechanical release candidate — 2026-10-15

## Decision

A deterministic one-commit candidate was built from the current Git tree and verified successfully. Its commit `347977e4535737829b4f3883055c4b581fd62530` has zero parents and is the only reachable commit. Its tree `fa8f3665ea239ab2ade4e6744fe2373dc70698aa` exactly matches source commit `df0ef6428bd2b7cf4991698b7f0e2c465b9a9c8b`.

The machine-readable audit is `experiments/history_free_release_candidate_audit_20261015.json`. The temporary bundle SHA-256 was `d94ecdddc57f14ba676e53b850183b4864d88761ec8d8cefde2cdaff800c21ad`; the bundle itself was deliberately not retained as a publishable artifact because licensing and rights review remain open.

## Safety and reconstruction

All six declared restricted paths are absent from the candidate tree, and no path containing a `private` directory is tracked. The temporary release ref was deleted after bundle creation, and no public push occurred.

The candidate was cloned again with `--no-local`, paired with the pinned complete local solver submodule snapshot, and checked in a blank non-secret environment. Fifty-three tests passed. Current skill/library manifest checks, 2,985-record body-free identity reconstruction, and release-evidence reconstruction all passed. The submodule had zero missing reachable objects and passed `git fsck --full`. No model, API, solver, native evaluator or virtual-machine call was made.

## Remaining boundary

The candidate contains no root `LICENSE`, `COPYING`, or `NOTICE`. No author-selected license, per-file rights decision, third-party attribution policy, or public-release authorization exists yet. The construction proves that restricted ancestry can be removed mechanically; it does not establish redistribution rights. The final fresh remote submodule clone also remains dependent on GitHub availability, and the nine historical result publishers still need an approved exclusive-write replacement or wrapper.
