# Local acceptance checklist before any Drive cleanup

1. Put the complete portable bundle, or a Git clone plus its local data mount, on the intended machine.
2. For a Git clone, create `config/local_paths.json` from the example. The complete portable bundle needs no path file.
3. Run `RUN_ALL_CMDO`. This performs the environment check, non-data unit tests and all current figure builds, but never re-executes U8 or unseals U9.
4. Confirm imported-source hashes are 20/20, canonical archives are 7/7 and `Ready for all figures` is 1.
5. Inspect `outputs/reports/test_run_report.csv`; every test must have `passed=true`, `failed=false` and `incomplete=false`.
6. Inspect `outputs/reports/figure_run_report.csv`; every requested figure must be `PASS`. This is an automated generation result, not a visual publication-readiness decision.
7. Inspect the exported main and Extended Data PNG/TIFF files under `outputs/figures/`; the `visualReview` field remains `PENDING_EXTERNAL_QA` until this review is completed.
8. Inspect `outputs/reports/pdf_compatibility_report.csv`. Every row must be `PASS`. The ordinary PDF remains the editable vector export; `*_compat.pdf` is the renderer-safe, image-only companion used when a PDF previewer changes font spacing.
9. Inspect `outputs/reports/local_acceptance_summary.json`; test, figure-generation and compatibility-PDF failure counts must all be zero.
10. Run only the explicitly authorized U8/U9 phase(s), preserving their console output and work directories.
11. Hash the final canonical outputs and compare them to the accepted records.
12. Keep two independent recoverable copies (for example local SSD plus a second external/off-site backup).
13. Produce a Drive cleanup manifest listing each proposed deletion, its local replacement path and hash.

No Drive deletion is authorized by the repository build itself.
