# Exact power analysis for matched skill acquisition

## Purpose

The proposed eight-pair acquisition canary is useful for engineering, but it
cannot support a publication-level causal claim.  This note converts the open
instruction to “expand the sample” into explicit sample-size requirements.

The calculation is entirely offline.  It does not estimate an effect from the
current repository, authorize new model calls, or change the experiment.

## Primary statistical object

Each independent unit is a rejected typed skill proposal together with its
frozen version-space state.  The two outcomes are whether fact-equivalent flat
feedback and separating-witness feedback respectively produce an admitted
candidate within the same request and resource budget.

Let

- `r` be the probability that the two arms have different binary outcomes;
- `q` be the probability that the separating-witness arm wins, conditional on
  the pair being discordant.

The full-denominator accuracy difference is `r(2q-1)`.  The primary test is a
one-sided exact conditional McNemar, equivalently a sign test on discordant
pairs, at alpha 0.05.  Under the null, a discordant pair favors treatment with
probability at most 0.5.

For every proposed total sample size `N`, the calculation integrates the exact
conditional rejection probability over `D ~ Binomial(N,r)`.  For each realized
discordant count `D`, rejection uses the smallest integer threshold `k` such
that `P[Binomial(D,0.5) >= k] <= 0.05`.

## Required total proposal pairs

The columns give `q`; rows give `r`.

### At least 80% power

| `r` | `q=.65` | `q=.70` | `q=.75` | `q=.80` |
|---:|---:|---:|---:|---:|
| .20 | 369 | 208 | 134 | 92 |
| .30 | 246 | 138 | 89 | 61 |
| .40 | 185 | 104 | 67 | 46 |
| .50 | 148 | 83 | 53 | 37 |

### At least 90% power

| `r` | `q=.65` | `q=.70` | `q=.75` | `q=.80` |
|---:|---:|---:|---:|---:|
| .20 | 498 | 279 | 177 | 122 |
| .30 | 332 | 186 | 118 | 81 |
| .40 | 249 | 139 | 88 | 60 |
| .50 | 199 | 111 | 70 | 48 |

For interpretation, `r=.30, q=.70` corresponds to a 12 percentage-point
success difference.  Detecting that alternative requires 138 independent
proposal pairs for 80% power or 186 pairs for 90% power.  Even the very large
alternative `r=.50, q=.80`, a 30-point difference, requires 37 or 48 pairs.

Conditioning directly on the observed discordant count, 80% power requires
69, 37, 23 or 18 discordant pairs for `q=.65, .70, .75, .80`; 90% power requires
93, 53, 33 or 23.

## Role of the eight-pair canary

With only eight total pairs, unconditional power ranges from approximately
0.1% to 10.9% across the displayed scenarios.  The canary must therefore be
limited to four purposes:

1. verify that flat and separating packets contain the same atomic facts;
2. verify deterministic teacher and tie-breaking behavior;
3. validate request, retry, missingness and resource accounting; and
4. obtain a planning estimate of the discordance rate.

It must not decide the paper's efficacy claim.  If the canary is inspected for
efficacy, either its alpha must be charged through the predeclared alpha-spending
mechanism or the expansion must be fully independent.

## Recommended expansion rule

The cleanest design is a two-stage protocol.  First, generate eight prospective
typed pairs solely as an engineering and variance-estimation pilot.  Then freeze
the relevant `r` and `q` alternative and collect an independent expansion with
the table-defined sample size.  A conservative illustrative target is 138
independent proposal pairs for 80% power, or 186 for 90%, under `r=.30, q=.70`.

These numbers do not solve the remaining design issues.  The proposal units
must still be exchangeable, all facts must be content-addressed before outcome
generation, and both arms must share grammar, verifier, endpoint, model, call
count, token ceiling and stopping rule.  Sequential monitoring requires a new
power calculation consistent with the paper's alpha-spending mechanism.

The machine-readable table is
`experiments/matched_acquisition_power_analysis_20261015.json`.
