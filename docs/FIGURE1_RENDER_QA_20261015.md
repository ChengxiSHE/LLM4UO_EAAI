# Figure 1 render and final-size QA

Status: **passed** on 2026-10-15.

Figure 1 is rendered with the saved Python/Matplotlib backend at 180 × 135.89
mm. PDF and SVG preserve editable text, and the PNG and TIFF companions are
exported at 600 dpi.

The strict plotting-source preflight reports 21 passes, zero warnings and zero
failures. The final PDF contains 78 auditable text runs, with a 5.0 pt minimum
against the 5.0 pt requirement. The rendered collision audit and all four
panel-alignment comparisons pass with zero warnings or failures at the 1.5 pt
alignment tolerance. Missing Unicode subscript glyphs found in the first render
were replaced by explicit ASCII mathematical labels before the audited render.
An initial collision audit then identified crowded labels and an overlapping
footer; boxes, line breaks, arrow labels and reserved footer space were revised
before the complete audit was repeated.

Final-size visual inspection confirms that the untrusted proposer is outside
the trusted library boundary; witness rejection and exhausted-grammar paths
terminate; zero, multiple and rejected execution paths return the previous
output; and the promotion panel distinguishes an immutable successor from an
unchanged state. The figure labels finite-domain software guarantees,
conditional accepted-path correctness, exact fallback and empirical benchmark
utility separately. It also states that the canonical loadable manifest is now
implemented as a retrospective artifact measurement, while complexity-weighted
promotion remains prospective, cumulative bounds require one fixed target, and
no universal language proof or unrestricted recursive self-improvement is
claimed.

The authoritative machine record is
[`figure1_render_qa_20261015.json`](../experiments/figure1_render_qa_20261015.json).
The render made no model, API, solver, native-evaluator or VM call, exposed no
request or response body, answer or credential, and added no empirical result.
