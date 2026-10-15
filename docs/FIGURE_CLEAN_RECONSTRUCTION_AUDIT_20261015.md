# Main-figure clean reconstruction audit

Date: 2026-10-15  
Status: **passed in a fresh temporary tree**

## Result

Both main figures were rebuilt with Python 3.10.1 and Matplotlib 3.10.7 from
repository-local rendering code and aggregate, body-free Source Data. The
rebuild started in a new temporary directory without any prior figure output.
It used only the eight declared environment variables needed for a blank home,
font cache, interpreter path and repository-local alignment gate.

For both figures:

- the repository-local 1.5 pt panel-alignment gate returned `PASS` with four
  comparisons and no failure or warning;
- the PDF contained one page, editable text and no glyph below 5 pt;
- the regenerated PNG and TIFF were byte-identical to the recorded artifacts;
- the PDF was byte-identical after removing only `CreationDate`;
- the SVG was byte-identical after canonicalizing only `dc:date` and
  self-consistent Matplotlib internal `m…`/`p…` identifier names.

The first failed attempt was retained diagnostically during execution: Figure
2 could not be rebuilt from a Git archive because four aggregate Source Data
tables were not tracked. Those tables contain only counts, rates and route
identity totals, with no task text, request/response body, evaluator-only
answer or credential. They are now part of the explicit figure reconstruction
closure, and the final clean-temporary-tree audit passed.

## Reproduction contract

The exact environment is recorded in `requirements-figures.txt`. Run:

```text
python -m pip install -r requirements-figures.txt
python scripts/reconstruct_figures.py --check
```

The renderer imports `scripts/audit_panel_alignment.py` through the documented
`FIGURE_QA_SCRIPTS` boundary. The reconstruction wrapper supplies that path
from the temporary repository tree, so no personal skill directory or external
QA checkout is needed.

## Evidence and limits

The machine-readable audit is
`experiments/figure_clean_reconstruction_audit_20261015.json` with SHA-256
`70c0132d51551ffad0038a3ffeaba9ed6b79d14424f15ca33b366e0c2c8949a2`.
Pixel identity allows the already recorded collision and final-size visual QA
to transfer to these exact regenerated pixels. It does not establish that
arbitrary future edits remain collision-free.

This audit made zero model, API, solver, native-evaluator or VM calls. It read
no request/response body, evaluator-only answer or credential. It closes the
figure-reconstruction layer only; provider replay, solver/native replay,
third-party rights, repository license, remote submodule acquisition and a
history-safe public snapshot remain separate release requirements.
