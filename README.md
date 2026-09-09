# CMDO reproducibility

This repository contains the frozen reproducibility record for the CMDO submission candidate.

## Scientific architecture

The manuscript is organized as the non-propagating evidential order:

**IDENTIFY -> REUSE -> CERTIFY -> PRESERVE**

with:

- Figure 1 — evidential order and information roles.
- Figure 2 — IDENTIFY: outcome-free non-identifiability and restoration by representative current outcomes.
- Figure 3 — REUSE: frozen U6/U7 confirmation, mismatch sensing, the frozen 185-state post-completion geometry, and a deferred sealed 20-hospital eICU replication.
- Figure 4 — CERTIFY: prospective composability certification (PCC), exact finite-sample certification cost, information-cost scaling, and retrospective projection of the completed 185-state CMDO pool.
- Figure 5 — PRESERVE: fixed-use value versus adaptive implementation, matched fixed/adaptive risk on Georgia and CPSC 2018, and the adaptation frontier.
- Extended Data Figure 1 — developmental falsification of a universal outcome-free route.
- Extended Data Figure 2 — role separation and the locked U10 mechanism challenge.
- Extended Data Figure 3 — controlled robustness-efficiency operating region under historical misspecification.

## Submission-v2 reviewer figure pathway

From a fresh clone of the exact candidate commit, run:

```matlab
RUN_SUBMISSION_V2_FIGURES('RepoRoot',pwd,'Strict',true)
```

The submission-v2 runner renders eight displays:

```text
Figure1
Figure2_IDENTIFY
Figure3_REUSE
Figure4_CERTIFY
Figure5_PRESERVE
ED1
ED2
ED3
```

A freeze candidate is not accepted until this reports `8/8 PASS` from a fresh clone and the Git worktree remains clean.

Before the graphical run, the static scientific-integrity gate is:

```powershell
python scripts/verify_submission_v2_science.py
```

This gate does not re-run any sealed prospective stage. It verifies frozen scientific invariants and claim boundaries only.

## Frozen scientific constraints

The following are immutable for the submission-v2 freeze:

1. The post-completion synthesis remains exactly:

```text
80 U6 + 80 U7 + 12 U8 + 9 U9A + 4 U9B = 185 states
```

2. The deferred eICU replication is separate from that pool. It must not be added to the 185-state synthesis and must not revise the retrospective PCC projection.
3. The locked U10 prospective verdict remains `MECHANISM_NOT_CONFIRMED`. Post-completion localization does not overwrite that verdict.
4. The eICU canonical shareable execution record is immutable. Its canonical ZIP SHA-256 is:

```text
815bbc9a575a3e2eca5e227ad24d6d4f4e210eedac086f09287dac22c950b701
```

5. The executed eICU Amendment A1 code SHA-256 is:

```text
5f72a5aba7650bc7ac51ac48c72db8e5d7ede19d856a75d29b8367387da43352
```

Amendment A1 changed only official-field matching and Windows case-insensitive duplicate-path handling before reserve-outcome access; no scientific estimand, threshold, budget, seed, borrowing rule or gate was changed.
6. No raw credentialed eICU/PhysioNet patient-level records are redistributed in the default reviewer pathway.
7. The PPI++-style method is retained as an auxiliary point-estimation comparator. Its lower eICU pooled MAE is not converted into an estimator-superiority claim for CMDO.

## Deferred sealed eICU replication

The reviewer-facing Figure 3 renderer reads only share-safe aggregate outputs under:

```text
source_data/figure3_eicu/
```

The frozen reserve contains 20 hospitals. The one-shot verdict is:

```text
INTEGRITY_SUPPORTED_EMPIRICAL_SAFETY_NOT_CONFIRMED
```

Key frozen results include:

- direct pooled MAE = 0.027772293
- CMDO pooled MAE = 0.026762245
- relative pooled MAE gain = +3.64%
- hospital breadth = 14/20 = 70%, below the prespecified 75% gate
- formal gates passed = 10/13
- PPI++-style pooled MAE = 0.016252
- matched outcome-free telemetry witness maximum later true-accuracy gap = 0.08053

The eICU blockwise/covered-event certificate diagnostics are implementation diagnostics and are distinct from the manuscript's PCC prospective-certification analysis.

## PCC source data

Figure 4 reads the frozen PCC products under:

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

The retrospective completed-state PCC projection contains exactly 185 rows and remains restricted to U6, U7, U8, U9A and U9B.

## Submission-v2 figure renderers

The active reviewer-facing renderers are:

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

Figure 5 panel B is frozen to the four audit budgets `128, 256, 512, 1024` in each of Georgia and CPSC 2018.

## Restricted and sealed data

The default reviewer pathway consumes tracked frozen derived records and does not re-run sealed patient-level analyses. Authorized stage-specific reruns, where legally and scientifically permitted, remain separate from the portable submission pathway.

This separation is deliberate: a post-completion rerun must not silently replace the result of a locked prospective or sealed one-shot stage.

## Repository policy

- Frozen protocols, sealed execution records and locked prospective verdicts must not be overwritten.
- New post-completion analyses must remain explicitly labelled as such.
- Generated outputs, local caches, credentials and raw patient data remain outside Git unless explicitly permitted by policy.
- The eICU canonical ZIP must never be rebuilt merely to satisfy repository packaging.
- Final submission tagging occurs only after all submission-v2 sources/renderers are frozen, a final SHA-256 manifest is committed, CI is green, and an exact fresh clone passes the eight-display MATLAB acceptance run while remaining Git-clean.

## Submission-v2 freeze status

The working freeze branch is:

```text
submission-v2-freeze-20260909
```

The intended immutable submission tag is:

```text
cmdo-submission-v2.0.0
```

That tag must point to the exact commit that passes the final fresh-clone acceptance gate. Until that acceptance is recorded, the branch is a candidate freeze rather than the final tagged submission record.
