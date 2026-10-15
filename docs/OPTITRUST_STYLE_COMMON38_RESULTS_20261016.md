# OptiTrust-style common-38 sensitivity result

Status: **complete but unscoreable because the safe adapter exhausted its
transport budget on all 38 identities**.

This experiment is a paper-structure sensitivity named
`OptiTrust-style-safe-sidecar`. It is not an official OptiTrust reproduction:
the inspected official arXiv v1 source and bounded public recheck did not yield
a verified runnable author implementation, native five-language runtimes,
fine-tuned checkpoint, or complete prompts.

## Result

The frozen run planned 38 RCPSP/VRPTW identities. It produced zero scoreable
method outcomes and 38 `infrastructure_unavailable` outcomes. The controller
recorded 199 logical requests, 282 physical attempts, 83 retries, 121 failed
physical attempts, 161 complete provider responses, and 7,608,756 reserved or
reported tokens. The independent audit reconstructed all 38 terminal cells,
verified every complete response hash, and reproduced the public result without
new provider or solver calls.

Failure was concentrated when the paper-derived five-role trajectory asked the
provider to emit repeated full `milp-v1` sidecars. Thirty-five identities
terminated after five logical slots, one after six, and two after nine. Each of
the 38 terminal request fingerprints exhausted the frozen three-attempt cap;
the recorded transport class was `transport_RemoteDisconnected`.

The mechanical `accuracy: 0.0` field in the low-level result is therefore not
an accuracy estimate. There are no scoreable OptiTrust-style outcomes, so
paired corrections, regressions, accuracy deltas, and significance tests
against the current method are not estimable. The existing current/Base/BIND/
CoE-safe common-38 rows remain unchanged and were not retuned after this run.

## Interpretation and next adapter

The run identifies an adapter-capacity mismatch: serializing five complete
candidate models per identity made the provider interaction too large and too
fragile for the bounded transport. It does not show that OptiTrust or the
paper-level multi-language idea has 0% formulation accuracy.

A new outcome-blind adapter must be frozen before any further dispatch. It
will generate one canonical `milp-v1` candidate, bind it by hash, and obtain
five compact language-conditioned reviews that can emit only typed bounded
deltas or abstentions. A trusted composer, schema validator, semantic checker,
resource checker, solver endpoint, canary progression gate, and corrected
three-attempt resume rule remain outside the model. The redesign may not use
the v1 benchmark answers to tune its representation or prompts.

## Claim boundary

This is an audited infrastructure and representation result, not an accuracy
estimate, official reproduction, equal-budget leaderboard row, or evidence of
broad superiority. Published OptiTrust scores are not substituted for a local
run. Official reproduction remains externally blocked until an author- or
venue-linked runnable artifact becomes available.
