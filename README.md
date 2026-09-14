# CMDO reproducibility

This repository contains the frozen reproducibility record for the current CMDO submission candidate.

## Reviewer scope

The reviewer-facing task is deliberately narrow:

1. verify the frozen submission-v2 scientific invariants;
2. regenerate the five manuscript figures and three Extended Data figures from tracked share-safe source data;
3. verify exactly 8 PNG and 8 PDF outputs;
4. verify that the Git worktree remains clean.

The reviewer pathway **does not require** reconstruction of the historical developmental DAG, full-claim replay, archival continuation, legacy Figure 5/6 renderers, the seven portable canonical-archive ZIPs, or restricted raw patient-level data.

Historical developmental code and provenance remain in the repository for transparency and maintainer audit, but they are not part of reviewer acceptance.

## One-command reviewer acceptance

From a fresh clone:

```powershell
python RUN_REVIEWER.py all
```

The command performs:

```text
submission-v2 static scientific-integrity check
        ↓
strict MATLAB rendering of the current 8 displays
        ↓
8 PNG + 8 PDF inventory check
        ↓
post-run Git cleanliness check
```

No network access is required.

If MATLAB is not on `PATH`, either set `CMDO_MATLAB` or pass it explicitly:

```powershell
python RUN_REVIEWER.py all --matlab "C:\Program Files\MATLAB\R2024b\bin\matlab.exe"
```

Generated reviewer figures are written outside the repository by default so a fresh clone remains clean. A custom external directory can be supplied with:

```powershell
python RUN_REVIEWER.py all --output-dir "C:\CMDO-REVIEWER-OUTPUT"
```

The individual gates are also available:

```powershell
python RUN_REVIEWER.py check
python RUN_REVIEWER.py figures
```

## Current submission architecture

The manuscript follows the non-propagating evidential order:

**IDENTIFY -> REUSE -> CERTIFY -> PRESERVE**

The active reviewer-facing displays are:

```text
Figure 1 — evidential order and information roles
Figure 2 — IDENTIFY
Figure 3 — REUSE
Figure 4 — CERTIFY
Figure 5 — PRESERVE
Extended Data Figure 1 — developmental falsification
Extended Data Figure 2 — role separation / locked U10 challenge
Extended Data Figure 3 — robustness-efficiency stress analysis
```

The active MATLAB renderers are:

```text
matlab/submission_figures/Figure1_Evidential_Order_PCC.m
matlab/submission_figures/Figure2_IDENTIFY_Validation.m
matlab/submission_figures/Figure3_REUSE_Refined.m
matlab/submission_figures/Figure4_CERTIFY.m
matlab/submission_figures/Figure5_PRESERVE_PCC.m
matlab/submission_figures/ED1_OutcomeFreeBoundary_v9.m
matlab/submission_figures/ED2_IntegrityControls_v2.m
matlab/submission_figures/ED3_RobustnessEfficiency_v1.m
```

They are orchestrated by:

```text
RUN_SUBMISSION_V2_FIGURES.m
```

A successful graphical gate reports:

```text
CMDO SUBMISSION V2 FIGURES COMPLETE: 8/8 PASS
```

## Frozen scientific constraints

The submission-v2 static verifier preserves the following scientific boundaries.

### 185-state synthesis

The post-completion synthesis is exactly:

```text
80 U6 + 80 U7 + 12 U8 + 9 U9A + 4 U9B = 185 states
```

The deferred eICU replication is separate and is not retrospectively added to this pool.

### Deferred eICU reserve

The reviewer-facing Figure 3 renderer reads only share-safe aggregate outputs under:

```text
source_data/figure3_eicu/
```

The frozen reserve contains 20 hospitals. Key results are:

- direct pooled MAE = 0.027772293
- CMDO pooled MAE = 0.026762245
- relative pooled MAE gain = +3.64%
- hospital breadth = 14/20 = 70%, below the prespecified 75% gate
- formal gates passed = 10/13
- PPI++-style pooled MAE = 0.016252
- canonical verdict = `INTEGRITY_SUPPORTED_EMPIRICAL_SAFETY_NOT_CONFIRMED`

Restricted eICU patient-level records are not redistributed.

### U10

The locked U10 prospective verdict remains:

```text
MECHANISM_NOT_CONFIRMED
```

Post-completion localization analyses do not overwrite this prospective verdict.

### PCC

Figure 4 reads:

```text
source_data/pcc/PCC_frontier_classified.csv
source_data/pcc/PCC_scaling_summary_v12.csv
source_data/pcc/CMDO_185_realized_projection.csv
```

Figure 5 additionally reads:

```text
source_data/pcc/CMDO_U9_REUSE_PRESERVE_bridge.csv
U10_Prospective_ECG/02_Posthoc_Diagnostics/U10_DEPENDENCE_DECOMPOSITION.csv
```

The retrospective completed-state PCC projection remains restricted to U6, U7, U8, U9A and U9B.

## Portable reviewer package

Maintainers can build the lean portable package with:

```powershell
python scripts/build_submission_candidate.py
```

The build:

- runs the submission-v2 static science gate;
- packages repository-tracked reviewer files only;
- excludes local caches, historical portable bootstraps, legacy canonical-archive bundles and restricted raw data;
- byte-verifies the portable ZIP;
- emits SHA-256 records.

The portable reviewer entrypoint remains:

```powershell
python RUN_REVIEWER.py all
```

## Maintainer clean-room acceptance

For final submission freeze testing:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_CLEANROOM_REVIEWER.ps1
```

This builds the lean reviewer package, creates a fresh clone of the exact candidate commit, runs the same submission-v2 reviewer acceptance and records the clean-room report.

## Historical/deep replay policy

The repository retains historical stage code, full-claim profiles, archival-continuation machinery and developmental provenance because failed, partial and negative analyses are part of the scientific record.

These materials are **maintainer/provenance resources**, not prerequisites for reproducing the manuscript tables, frozen source-data summaries or current submission figures. A reviewer is not expected to re-download every historical dataset or re-execute every developmental branch.

For the current submission, reviewer reproducibility means that the frozen share-safe scientific records support the manuscript quantities and regenerate the figures used in the paper while preserving the stated frozen verdicts and claim boundaries.

## Repository policy

- Frozen protocols, sealed execution records and locked prospective verdicts must not be overwritten.
- New post-completion analyses must remain explicitly labelled as such.
- Generated outputs, credentials, local caches and restricted patient data remain outside Git.
- Reviewer outputs must be written outside the repository.
- Final tagging occurs only after a fresh-clone `python RUN_REVIEWER.py all` acceptance passes and the worktree remains clean.

## Candidate branch

The reviewer-slim submission candidate is developed on:

```text
submission-v2.1.1-reviewer-slim
```

The existing v2.1.0 freeze/tag is not rewritten. A v2.1.1 tag should be created only after the lean reviewer workflow has passed the final clean-room test.
