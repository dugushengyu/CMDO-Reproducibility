# CMDO reviewer-facing GitHub-native submission pathway v4

This branch is designed so a reviewer can reproduce the manuscript figure pathway
and the exact finite-cohort U10 Supplementary diagnostic from the Git repository alone.

## Reviewer use

Clone the frozen submission branch/tag, open MATLAB at repository root, and run the
combined submission check:

```matlab
RUN_SUBMISSION_REPRO_CHECKS('Strict',true)
```

This command runs:

1. all seven manuscript/Extended Data figure renderers through
   `RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true)`; and
2. the exact finite-cohort U10 check reported in Supplementary Note 6 through
   `RUN_U10_EXACT_FINITE_COHORT_CHECK('VerifyOnly',true,'Strict',true)`.

The pathway reads only repository-relative tracked records and does not require an
author-machine data path or network access during rendering/checking.

## Figure 4 empirical-risk and exact-U10 records

The corrected empirical Figure 4 source and provenance are tracked in:

- `source_data/figure4_submission/CMDO_Figure4_PRESERVE_Source_v1.csv`
- `source_data/figure4_submission/CMDO_Figure4_PRESERVE_Source_v1_provenance.json`

The exact finite-cohort U10 Supplementary diagnostic is tracked in:

- `source_data/figure4_submission/U10_ExactFiniteCohort_Check_v1.csv`
- `source_data/figure4_submission/U10_ExactFiniteCohort_Check_v1_provenance.json`

The exact check is conditional on the frozen U10 binary correctness rosters and locked
scalar shared-audit rule. It is a post-completion diagnostic and does not change the
prespecified U10 mechanism verdict.

## Figure 5 source roles

The manuscript Figure 5 is rendered from the tracked frozen state-summary CSV in:

`source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv`

The reconstructed dense-Lambda stress generator under `scripts/stress_replay/` is a
post-completion replay diagnostic. It is not byte-identical recovery of the lost
original generator and it does not overwrite or define the manuscript Figure 5.

## Restricted data

This pathway reproduces the final manuscript figures and the stated reviewer-facing
diagnostics from frozen derived records. It is not a fresh raw-to-science replay of
every historical/credentialed analysis, and restricted patient-level records are not
redistributed.
