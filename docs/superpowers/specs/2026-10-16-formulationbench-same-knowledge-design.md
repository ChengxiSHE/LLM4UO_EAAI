# FormulationBench same-knowledge mechanism study design

**Status:** architectural design approved under the user's standing instruction
to self-confirm subsequent research work. Implementation and dispatch remain
separate gated stages.

**Source:** `henryrobbins/formulation-bench` commit
`6f37a71e6251b11599ef42869e4268882985a8a7`, tree
`793db197693fac5446fe1bd39aaf178fea437822`.

## Purpose and estimand

The study isolates whether a proof-obligation representation improves an LLM's
ability to judge whether two MILP formulations are equivalent when the factual
content, model, budget, prompt goal, and evaluator are held fixed. The unit is
one of the official 89 reformulation pairs. The primary endpoint is exact pair
validity classification on the full denominator.

This is a mechanism study for representation and admission. It is not a new
formulation-generation benchmark and cannot by itself explain all TSP or
OR-Debug gains. Those benchmarks remain the evidence for final modeling
accuracy; the existing finite censuses remain the evidence for routing and
description-length selection.

## Source custody

The source is materialized at the fixed commit in a private root. A custodian
creates three disjoint projections:

1. **Inference facts:** problem description, parameter schema, the two
   structured formulations, and the official parameter map. No solution,
   validity label, Lean proof, proof-presence flag, reference code body, or
   source path is included.
2. **Answer-free metadata:** opaque pair ID, input hashes, token/byte/structural
   counts, source identities, and serializer hashes. It contains no prose,
   values, algebra, labels, solutions, code, or proof text.
3. **Evaluator:** pair label, solution material needed by the official package,
   and any Lean certificate. This root is never mounted or passed to inference
   workers.

The publisher validates all 89 pairs before atomic publication. Missing,
duplicate, unknown, linked, escaping, or inconsistent files fail the whole
source. The study never reduces the denominator after seeing labels or model
outputs.

## Same-fact dual views

A canonical semantic fact graph is deterministically parsed from each pair's
public inference facts. Its nodes bind parameter domains, variables, bounds,
integrality, objectives, indexed constraints and the supplied parameter map.
Every node and edge receives a content hash.

Two serializers consume exactly that graph:

- **Flat-K:** canonical prose/JSON listing of the graph facts and a neutral
  equivalence checklist.
- **PCK-K:** the identical fact hashes arranged under typed obligations for
  parameter compatibility, forward feasibility, backward feasibility,
  integrality and bounds, index/quantifier coverage, and objective
  preservation.

Neither view contains a validity label, proof, solution, source formulation
name, pair-level proof-presence signal, or extra domain fact. A verifier rejects
either view if its fact-hash multiset differs from the canonical graph or from
the other arm. This is the operational same-knowledge guarantee.

## Model contract

Each arm makes one independent request per pair. The frozen model must return
strict JSON containing `equivalent`, `confidence`, six obligation statuses and
opaque evidence references that can point only to supplied fact hashes. Free
text, code, algebra not present in the facts, unknown hashes and missing fields
fail as method errors and count as incorrect.

Responses are intentionally short. Before the benchmark run, four synthetic
nonbenchmark pairs exercise positive, negative, mapping and index-scope cases.
The capacity gate requires all eight arm requests to complete, zero transport
failures, zero restarts, valid typed JSON and a 1,024-token completion ceiling.
The preparation OpenAI/httpx environment is the transport worker; the Python
3.11 fresh controller remains responsible for ledger, custody and validation.

## Freeze and evaluation

The full experiment contains 178 logical requests: 89 pairs times two arms,
concurrency five, one physical send per fingerprint, and at most three
ledgered attempts for retryable transport or invalid-JSON failures. Per-item
exhaustion continues; authentication, model, budget, ledger and repeated
transport failures halt globally. No solver or Lean process runs during model
inference.

After all terminal states are fixed, an evaluator-only process joins predictions
to labels. The primary contrast is paired full-denominator accuracy. The
prespecified success gate requires:

- PCK-K accuracy minus Flat-K accuracy at least five percentage points;
- more PCK-K corrections than regressions;
- one-sided exact paired McNemar probability at most 0.05; and
- no more than five percentage points of accuracy loss in either the positive
  or negative label subgroup.

Wilson intervals, corrections/regressions, abstentions, method errors,
infrastructure outcomes and subgroup results are reported separately. Missing
predictions count as incorrect in the full denominator. There is one primary
contrast and no post-hoc prompt, threshold or cohort tuning.

## Claim boundary

If the gate passes, the permitted claim is that proof-obligation serialization
improves FormulationBench pair-validity accuracy over a same-fact flat
serialization under the frozen model and budget. If it fails, the result is a
negative mechanism experiment. Neither outcome changes prior benchmark scores,
proves unrestricted self-improvement, or establishes that every knowledge
library should use this representation.
