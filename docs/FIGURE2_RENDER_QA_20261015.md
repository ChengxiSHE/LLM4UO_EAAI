# Figure 2 render and final-size QA

Status: **passed** on 2026-10-15.

Figure 2 is now rendered from the aggregate, answer-free Source Data package
with the Python/Matplotlib backend. The final canvas is 180 × 122 mm. PDF and
SVG preserve editable text, while the PNG and TIFF companions are exported at
600 dpi.

The strict source preflight reports 21 passes, zero warnings and zero failures.
The PDF contains 71 auditable text runs; its smallest glyph is 5.5 pt against a
5 pt requirement. The rendered collision audit reports zero failures and zero
warnings. The four panel-alignment comparisons pass at the prespecified 1.5 pt
tolerance. Final-size visual inspection confirms that all panel titles, labels,
counts, legends and boundary notes are readable. One initial visual-only issue
in panel c was repaired by removing a redundant axis title and shortening the
group-test note; the final PDF was then fully re-audited.

Panel a retains the two endpoint contrasts as separate rows and reports no
pooled effect. Panel b keeps a visible red regression category and explicit
zero-regression annotations. Panel c labels TSP size strata as descriptive and
attaches the prespecified sign test only to the 100 OR-Debug groups. Panel d
states that 2,985 direct outputs are preserved exactly and that accuracy was not
rescored.

The authoritative machine record is
[`figure2_render_qa_20261015.json`](../experiments/figure2_render_qa_20261015.json).
It binds the plotting source, three Source Data tables, four final outputs,
alignment report and collision report by SHA-256. The figure contains no task
text, request or response body, evaluator-only answer or credential. Rendering
made no model, API, solver, native-evaluator or VM call and added no new
benchmark result.
