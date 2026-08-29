# CMDO reproducibility

This repository contains the frozen reproducibility record for the final CMDO manuscript.

## Final scientific architecture

The final manuscript is organized as:

**IDENTIFY -> REUSE -> PRESERVE**

with:

- Figure 1 — conceptual evidential order
- Figure 2 — ordered theory and mechanism
- Figure 3 — IDENTIFY
- Figure 4 — REUSE
- Figure 5 — PRESERVE
- Extended Data Figure 1 — developmental falsification of a universal outcome-free route
- Extended Data Figure 2 — role-separation and coupling-pathway diagnostics

The canonical MATLAB entry point is:

```matlab
SETUP_CMDO;
RUN_SUBMISSION_FIGURES('Strict', true);
```

The runner writes the final figure set and a machine-readable report under:

```text
outputs/submission_figures/
```

## Final source manifest

Exact final renderer paths and SHA-256 fingerprints are recorded in:

```text
provenance/final_submission_v1.3_manifest.json
```

The central stage inventory through U11 is:

```text
provenance/stage_registry.json
```

## Figure 1 frozen asset

Figure 1 is rendered from the tracked frozen asset:

```text
source_data/figure1_assets/Figure1_assets_selected_v1.mat
```

SHA-256:

```text
30490a2586a9394fad868159ccd1f0248b0d9afc17d9bc970456c425c63925e7
```

## Historical canonical reviewer assets

Seven historical U4C-U7 canonical archives remain outside Git and are distributed in the byte-verified companion bundle:

```text
CMDO-Reviewer-Assets-v1.0.zip
```

Their expected filenames, sizes and SHA-256 values are defined in:

```text
provenance/canonical_archives_manifest.csv
```

No raw PhysioNet patient waveforms are redistributed.

## Scientific interpretation boundaries

- U11 is a protocol-locked constructive information-closure witness, not an estimate of the real clinical performance of Georgia or CPSC 2018.
- U10 did not confirm shared-audit coupling as a general mechanism across both external ECG cohorts.
- Post-completion permutation and role-separation analyses are diagnostics and do not overwrite the locked U10 prospective verdict.
- U0-U5 are retained as developmental lineage and are not promoted into the final confirmatory chain.

## Historical routes

Older reviewer commands, legacy Figure 5/6 renderers and older Extended Data renderers are retained for provenance and historical reproducibility.

They do not define the final manuscript figure numbering.

The final manuscript figure route is exclusively:

```text
RUN_SUBMISSION_FIGURES.m
```

## Repository policy

- Frozen protocols and locked prospective verdicts must not be overwritten.
- New post-completion analyses must remain explicitly labelled as such.
- Generated outputs, local caches, raw patient data and binary reviewer bundles remain outside Git unless explicitly tracked by policy.
- The immutable submission tag is created only after a fresh-clone clean-room reproduction passes.
