# Local acceptance fixes — 2026-08-10

The first Windows MATLAB R2024b portable run completed all automated tests and
generated all 13 figures, but external visual QA found that generation success
did not guarantee publication-ready layout.

## Visual issues corrected

- Figure 1: inset/body collision, clipped panel letters and footer/x-axis overlap.
- Figure 4: panel-b legend/residual collision and overlapping panel-c/d labels.
- Figure 5: clipped panel letters and missing bottom audit margin.
- Figure 6: dense panel-b label collisions and panel-d exponent/title collision.
- Extended Data 1: unnamed parity line rendered as `data1`.
- Extended Data 4: fallback-residual annotation collided with the legend.
- Extended Data 6: the negative AUC regret label collided with the category label.

No canonical record, estimator, gate, metric definition, numerical result or
frozen source file was changed.

## Independent numerical spot checks

- U6: 16/16 targets improved; pooled reduction 3.053756144742%.
- U7 AUC: 16/16 strata improved; pooled reduction 3.744089549358%.
- U8: 12/12 states improved; pooled reduction 10.072784761268%; mean/minimum
  coverage 0.968333333333/0.940000000000; certificate violations 0; maximum
  fallback residual 0.
- U7 metric gains: sensitivity 4.917295%, specificity 3.870081%, AUC 3.744299%,
  balanced accuracy 3.243585%, Brier utility 0.518519%.
- Root-budget slopes: AUC U-statistic -0.501416300281; Bernoulli accuracy
  -0.491763617848; bounded Brier utility -0.500923061039; bounded sensitivity
  -0.510028368051.

## Acceptance-report hardening

- `RUN_CMDO_TESTS` now writes `outputs/reports/test_run_report.csv`.
- `RUN_ALL_FIGURES` explicitly marks visual review as `PENDING_EXTERNAL_QA`.
- `RUN_ALL_CMDO` writes `outputs/reports/local_acceptance_summary.json`.

## R4.1 acceptance-summary hotfix

- `RUN_ALL_FIGURES` now returns the compatibility-PDF report as a second
  output, so the top-level runner no longer writes a CSV and immediately
  reimports it using release-dependent table variable names.
- `FINALIZE_EXISTING_CMDO_RUN` validates the existing environment, test,
  figure and compatibility-PDF reports by stable column position and writes
  the missing acceptance summary without rerendering.
- `RUN_ALL_CMDO('Mode','finalize')` exposes that recovery path. It never
  re-executes U8 and never accesses U9 outcomes.
- The environment check resolves callable functions with `which`, avoiding a
  false negative for `exportgraphics` on the accepted Windows installation.

## R4.2 compatibility-PDF canvas hotfix

- External rendering of the R4 compatibility PDFs found that the hidden-axes
  export path could tighten the canvas at the right or lower boundary.  The
  source PNG/TIFF files and all numerical results were unaffected.
- `cmdo_png_to_pdf` now embeds each accepted 8-bit true-colour PNG losslessly
  as a single 600-dpi PDF image.  The PDF MediaBox is calculated directly from
  the source pixel dimensions, so every source pixel and the full canvas are
  retained and no live fonts remain.
- `REBUILD_COMPATIBILITY_PDFS` replaces only the compatibility PDFs and their
  report.  It does not redraw figures, rerun U8 or access U9 outcomes.

## R3 external visual-QA follow-up

The R3 rerun preserved every numerical result and passed 10/10 tests and 13/13
figure-generation actions.  External inspection of the actual PNG, TIFF and PDF
files nevertheless found residual presentation defects:

- Figure 1: the root-budget inset still crowded its footer, and panel-c result
  annotations sat on the bars and x-axis.
- Figure 4: the residual-audit inset obscured the panel-b title; two panel-c
  worst-regret labels and three near-zero panel-d labels remained crowded.
- Figure 5: the panel-a summary sat on the lower axis.
- Figure 6: the panel-d letter collided with the top y tick and the weight inset
  obscured the main x-axis labels.
- MATLAB's vector PDFs rendered normally in Ghostscript but showed expanded
  character spacing in Poppler.  R4 therefore preserves each vector PDF and
  additionally creates a 600-dpi, image-only `*_compat.pdf` companion from the
  pixel-identical accepted PNG/TIFF render.

These R4 changes affect layout and export compatibility only.  Canonical
records, SourceData, estimators, gates, statistics and conclusions are unchanged.
