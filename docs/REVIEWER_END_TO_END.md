# Reviewer end-to-end reproducibility

## Recommended reviewer commands

For exact submitted figures from a fresh clone:

```matlab
RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true)
```

For the broader portability/engineering audit:

```matlab
RUN_REVIEWER_E2E
```

The end-to-end audit creates all runtime outputs outside the Git checkout and performs:

1. repository-relative input and author-path isolation checks;
2. the existing repository engineering acceptance checks;
3. a public UCI-296 download -> preprocessing -> logistic-regression fit -> AUC evaluation -> ROC figure;
4. a reconstructed dense-Lambda stress replay as a diagnostic only;
5. the exact seven manuscript/Extended-Data figures from tracked frozen submission records;
6. the historical full-claim execution plan; and
7. a Git-clean audit.

Use the offline form when only the exact manuscript route and path isolation need to be checked:

```matlab
RUN_REVIEWER_E2E('Offline',true)
```

## Claim separation

### Exact manuscript reproduction

`RUN_SUBMISSION_FIGURES` is the manuscript-defining route. It uses only repository-tracked frozen derived records, including the frozen Figure-5 state-summary CSV. No author-machine repository path, external data mount, or network access is required during rendering.

### Public raw-data engineering loop

The UCI-296 smoke route genuinely performs download -> preprocessing -> model fitting -> evaluation -> ROC figure. Its purpose is to verify that a new machine can execute a complete public-data computation chain. It is explicitly an engineering smoke test, not a manuscript estimate.

### Reconstructed dense-Lambda stress replay

The stress generator under `scripts/stress_replay/` is a post-completion diagnostic reconstruction. The lost original generator's exact random-number trajectory cannot be certified, so the replay does not overwrite or define manuscript Figure 5. The tracked frozen CSV remains authoritative.

### Historical raw-to-science reconstruction

The repository retains a separate `full-claim` retrospective replay for provenance. That route can require public-provider availability, network access, GPU acceleration, manual or credentialed assets, and hours to days of runtime. It also contains a disclosed historical scientific-divergence boundary. Consequently, it is not a universal prerequisite for reproducing the submitted figures.

## Portability envelope

The standard reviewer route is designed for Windows, macOS and Linux with:

- Git;
- Python 3.10 or newer;
- internet access for first-time Python package installation and the public smoke test; and
- MATLAB capable of running the tracked renderers.

A GitHub Actions matrix runs the standard-library static portability audit on all three operating systems. MATLAB figure rendering is additionally checked by a fresh-clone clean-room run. Exact cross-OS pixel hashes are not required because fonts and rendering backends can vary; numerical fingerprints and expected output files define acceptance.
