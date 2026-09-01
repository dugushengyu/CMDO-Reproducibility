# Submission-ready Code Availability wording

Recommended manuscript text:

> **Code availability.** Code and reviewer-facing frozen derived records required to reproduce all main and Extended Data figures are provided in the CMDO-Reproducibility repository. From a fresh clone, the complete reviewer evidence-to-figure audit can be run with `RUN_REVIEWER_END_TO_END('Strict',true,'RunStressReplay',true)`, which verifies tracked frozen inputs by SHA-256, regenerates the deterministic synthetic stress-test diagnostic, renders Figures 1–5 and Extended Data Figures 1–2, and checks for author-specific paths and Git cleanliness. The authoritative manuscript Figure 5 is rendered from the tracked frozen stress-test record; the reconstructed executable stress test is retained separately as a diagnostic replay and does not overwrite that record. Raw controlled-access patient-level data are not redistributed. For sealed or restricted prospective stages, the repository provides the frozen derived evidence used by the manuscript together with a machine-readable re-execution contract. The final submission should cite the immutable repository tag/commit created after the clean-room audit.

## Reviewer commands

Strongest portable audit:

```matlab
RUN_REVIEWER_END_TO_END('Strict',true,'RunStressReplay',true)
```

Figures only:

```matlab
RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true)
```

## Validation record

The first recorded fresh-clone portability acceptance test is stored at:

```text
provenance/reviewer_end_to_end_validation_windows_r2024b_20260901.json
```

The final manuscript should replace generic repository wording with the journal's private-review link or immutable public URL/tag as appropriate at submission.
