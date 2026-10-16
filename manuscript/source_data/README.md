# Main-figure source data

These aggregate tables support the rendered Figure 2 and its contract in
[`FIGURE_PLAN.md`](../FIGURE_PLAN.md). They contain no task text, request or
response body, evaluator-only answer or credential. Render and final-size QA
are recorded in
[`figure2_render_qa_20261015.json`](../../experiments/figure2_render_qa_20261015.json).

## Tables

- `figure2_endpoint_summary.csv`: full-denominator correctness and paired
  outcome decomposition for TSP and OR-Debug.
- `figure2_tsp_by_size.csv`: TSP results for every frozen confirmation size.
- `figure2_group_summary.csv`: direction of the effect at the valid grouped
  inference level.
- `figure2_router_identity.csv`: mixed-router identity audit by family.
- `or_debug_endpoint_sensitivity.csv`: corrected-primary and unmodified
  released-primary OR-Debug confirmation outcomes for the same frozen outputs.
- `or_debug_group_endpoint_sensitivity.csv`: all 100 confirmation structural
  groups, group sizes, reconstructable membership hashes, error-type counts and
  paired outcomes under both endpoint definitions.

## Authoritative inputs

| Input | SHA-256 |
| --- | --- |
| `results/tsp_constraint_confirmation_root_closure_20261014.json` | `0a0aef6aad14e720f537c3201b5cc585b0177c0a05150a18d0300f3e498c437d` |
| `results/tsp_constraint_confirmation_evaluation_20261014.json` | `184d05aa1ff0857e9577fa239c4aed230d021e7404b865c340020c93f7757082` |
| `results/or_debug_confirmation_evaluation_20261014.json` | `04342d960613c01d3e354d742e39eec5949a90a53ca06fe0c6e30b6be057b66e` |
| `results/mixed_skill_confirmation_public_audit_v3_20261015.json` | `3c9b8700639cfe5599fc76b18cca4318b14d4b0865fb5bd343f5c0d26fead08f` |

Accuracy columns are exact ratios from the frozen finite cohorts. TSP size
rows share template lineage and are descriptive strata rather than independent
replicates. OR-Debug inference uses 100 structural groups. Router identity is a
retrospective behavior-preservation result; it is not a new accuracy estimate.
The OR-Debug sensitivity table makes endpoint-definition dependence explicit
and is not an additional model run.
The group table contains no problem identifier, task text, reference repair,
repair identity or evaluator-only answer. Its membership hash is computed from
the sorted public problem identifiers joined by newline, allowing an authorized
copy of the pinned upstream dataset to reconstruct group membership. It shows
that all 2,845 records are covered, group sizes range from 1 to 126, and the 516
endpoint-divergent evolved outcomes occur across 20 structural groups. The
aggregate audit is
[`or_debug_group_endpoint_sensitivity_audit_20261015.json`](../../results/or_debug_group_endpoint_sensitivity_audit_20261015.json).

## Figure 3 tables

- `figure3_retailopt_summary.csv`: prospective and post hoc label-blind
  instance and archetype totals, correct counts and complete paired outcome
  decompositions.
- `figure3_retailopt_diagnostics.csv`: two aggregate prospective decision-card
  diagnostics used only for post hoc error localization.

The summary rows are reconstructed exactly from the two public RetailOpt
evaluation projections, and the diagnostic rows from the public aggregate
decision audit. The machine-readable check is
[`manuscript_figure3_source_data_audit_20261017.json`](../../results/manuscript_figure3_source_data_audit_20261017.json).
The label-blind rows are same-benchmark robustness evidence, not a second
independent confirmation. Diagnostic rows do not causally decompose the effect
of formulation obligations and witnesses.

