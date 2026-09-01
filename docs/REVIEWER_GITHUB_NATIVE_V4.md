# CMDO reviewer-facing GitHub-native figure pathway v4

This branch is designed so a reviewer can reproduce the manuscript figure pathway
from the Git repository alone.

## Reviewer use

Clone the frozen submission branch/tag, open MATLAB at repository root, and run:

```matlab
RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true)
```

The renderer reads only repository-relative tracked frozen records.

## Figure 5 source roles

The manuscript Figure 5 is rendered from the tracked frozen state-summary CSV in:

`source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv`

The reconstructed dense-Lambda stress generator under `scripts/stress_replay/` is a
post-completion replay diagnostic. It is not byte-identical recovery of the lost
original generator and it does not overwrite or define the manuscript Figure 5.

## Restricted data

This pathway reproduces the final manuscript figures from frozen derived records.
It is not a fresh raw-to-science replay of every historical/credentialed analysis,
and restricted patient-level records are not redistributed.
