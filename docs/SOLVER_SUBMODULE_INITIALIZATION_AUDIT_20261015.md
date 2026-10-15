# Solver submodule initialization audit

The current checkout now initializes `vendor/solver-in-the-loop` at the exact
superproject gitlink `c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010`. The
submodule worktree is clean, contains 4,962 OR-Debug MPS files and has no
uninitialized nested submodule.

The reproducible command is:

```sh
git submodule update --init --recursive vendor/solver-in-the-loop
```

This closes only the current-checkout initialization gap. A fresh clone still
needs network access to acquire the pinned upstream repository. Gurobi, its
license and binary identity remain external, and no solver or benchmark body
was opened during this audit. The credential-free recursive clean-clone
reconstruction remains open.
