# Figure 2 backend-independent preflight

Status: **passed for evidence architecture and source data; rendering remains
pending because no Python/R backend preference is selected.**

This preflight freezes the argument and traceability of the planned main
endpoint figure before any plotting code is written. It does not create a
figure or claim publication readiness.

## Figure-level argument

The figure asks whether admitted benchmark-grounded knowledge improves each
frozen endpoint relative to its strong control and whether public-only
composition preserves pinned direct-family behavior. The defensible conclusion
is that the two separately frozen studies show large within-study gains made
entirely of observed corrections, with no observed paired regressions, and
that the retrospective mixed router reproduces all direct-family outputs.

The two endpoint definitions remain separate. They must not be pooled into one
effect estimate. TSP size strata share template lineage and are descriptive;
OR-Debug inference uses the 100 disclosed structural groups.

## Evidence architecture

| Panel | Inferential role | Source | Claim boundary |
| --- | --- | --- | --- |
| a | Hero: full-denominator endpoint accuracy | `figure2_endpoint_summary.csv` | Within-study comparison only; no TSP item-level significance |
| b | Paired correction/regression mechanism | `figure2_endpoint_summary.csv` | Zero observed regressions is not a future guarantee |
| c | Size/group consistency | `figure2_tsp_by_size.csv`; `figure2_group_summary.csv` | TSP strata are descriptive; the OR structural key is not complete lineage proof |
| d | Composition-preservation audit | `figure2_router_identity.csv` | Retrospective identity, not a new accuracy estimate or shift study |

Panel a should dominate the page. Panel b is the main control, panel c shows
where the effect appears, and panel d is visually subordinate because it tests
interface preservation rather than endpoint superiority.

## Arithmetic and privacy preflight

All frozen aggregate tables match their recorded hashes. The two endpoint
partitions sum to their full denominators, and their accuracy and delta columns
recompute from the integer counts. The seven TSP size rows cover sizes 13--19
exactly and sum to 140 records, 54 control successes, 100 method successes, 46
corrections and zero regressions. Router family rows sum to 2,985 records and
2,985 exact matches; every recorded mismatch or terminal-failure count is zero.

The plotted tables contain aggregate fields only. They contain no task text,
request or response body, evaluator-only answer, reference repair, or
credential.

## Blocking render-time requirements

Rendering still requires one persisted backend choice. After that choice, the
final PDF and SVG must be exported at 180 mm width with editable text and a
5 pt minimum glyph size. The final layout must pass the 1.5 pt panel-alignment
gate, plotting-source validation, PDF text audit, and collision audit. Every
panel and the complete figure must be inspected at final physical size.

The render must keep a visible zero-regression label even though the segment
height is zero, mark panel d as `accuracy not rescored`, and record the intended
alignment exemption if the hero panel uses an unequal span.

Machine-readable preflight:
`experiments/figure2_backend_independent_preflight_20261015.json`.

No model/API, solver, native evaluator, VM, or plotting call was made.
