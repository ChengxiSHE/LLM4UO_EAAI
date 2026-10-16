# RetailOpt-190 prospective short-decision protocol

## Purpose

This experiment asks whether benchmark-grounded, proof-carrying knowledge improves direct optimization-modeling accuracy on a source that is independent of the earlier TSP, OR-Debug, Text2Opt, FormulationBench, and NLEquiv evaluations. The endpoint is the public ReLoop implementation's objective-error rule: relative objective error strictly below 1%.

## Matched comparison

The unit sent to the model is one public archetype description. Each archetype has five numerical variants. Both arms use DeepSeek-V4-Flash, the same public description, the same typed questions, the same response schema, the same deterministic compiler, and the same Gurobi configuration. The only designed difference is that `knowledge_short` receives at most three routed knowledge cards containing a formulation obligation and a counterexample witness; `base_short` receives no card content.

One short decision is compiled and solved on all five variants. This yields 38 paired archetypes and 190 scored instances per arm while avoiding a separate language-model call for every numerical variant. Missing, malformed, or unsolved records count as incorrect on the full denominator.

## Frozen knowledge compiler

The library contains ten typed cards covering core inventory flow, substitution, lead time, minimum-order/fixed-cost activation, pack size, transshipment, returns, labor, budget, and sustainability constraints. A deterministic structural router selects one to three cards. Across the frozen source, the route is invariant over the five variants of every archetype. The model returns only enumerated semantic decisions; a shared first-party compiler converts those decisions into a solver model.

Before model inference, the admitted decision was replayed on all 190 records. It achieved 190/190 endpoint correctness and 38/38 fully correct archetypes, so downstream failures can be attributed to inference decisions or declared infrastructure failures rather than an unvalidated compiler endpoint.

## Capacity and resilience

The first capacity plan exposed a local admission bug: the token reserve used inner-payload bytes while the gateway checks the larger serialized provider envelope. That immutable failed attempt is retained. Version 2 binds the exact maximum wire-envelope size. Its two synthetic cells completed with zero retry, zero failure, and zero additional sends on restart.

The formal plan permits concurrent execution of five distinct fingerprints, at most three charged attempts per fingerprint, a persistent limit of 40 logical starts per 60 seconds, checkpointed cells, and idempotent restart. The independent evaluator and its endpoint implementation were hashed into the full plan before inference.

## Confirmation rule

The primary paired unit is an archetype that is correct on all five variants. Confirmation requires all of the following:

- instance accuracy gain of at least 5 percentage points;
- at least six corrected archetypes and at most two regressed archetypes;
- correction-to-regression ratio of at least 2;
- one-sided exact McNemar p-value below 0.05;
- at least 99% valid inference completion in each arm.

The result supports a prospective RetailOpt-190 accuracy claim only under the frozen source, endpoint, model, authored benchmark-specific library, and shared compiler. It does not by itself establish universal optimization-modeling superiority or automatic skill acquisition.
