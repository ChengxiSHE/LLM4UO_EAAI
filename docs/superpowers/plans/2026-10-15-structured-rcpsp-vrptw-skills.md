# Structured RCPSP/VRPTW skills implementation plan

**Goal:** Turn the fresh common-38 public structured packets into deterministic, typed, resource-bounded MILP artifacts without consulting evaluator answers or upstream model annotations.

1. Add failing tests for exact-one routing, strict schema validation, 38/38 compilation, source-count agreement, referential integrity, deterministic hashes, and malformed-packet rejection.
2. Implement two typed skills from the public benchmark semantics: multi-mode RCPSP with lag/deadline/budget/disjunctive resource obligations, and arc-flow VRPTW with visit, vehicle, MTZ-load, and time-link obligations.
3. Admit only models below frozen variable/constraint/nonzero/serialized-byte caps; reject zero or multiple route matches.
4. Publish a body-free readiness audit binding packet hashes, skill code hash, model hashes, resource metrics, and count agreement. Keep all packet bodies in the ignored private bundle.
5. Do not call an API or solver in this phase. Dispatch remains closed until budgets, custody, external serializers, and scoring are frozen.
