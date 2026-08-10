# CMDO U8 complete package v1.1.0

This package replaces the manual v1.0.1 + v1.0.2 folder-merging workflow with one clean folder and one MATLAB entry script.

## Before removing the old folder

Compress the entire original `CMDO_U8_NHANES_PreOutcome_MATLAB_v1_0_1` folder into one archival ZIP and retain that ZIP unchanged. After the archive exists, the expanded old working folder may be removed from your computer. Do not permanently erase the only copy of the original seal, outcome-access record, analysis-start marker, reserve truth, or console history.

## Run

1. Extract this ZIP into a new empty folder.
2. Open MATLAB in the extracted `CMDO_U8_NHANES_PostUnseal_Complete_v1_1_0` folder.
3. Run only `RUN_COMPLETE_POST_UNSEAL_RERUN.m`.
4. Do not run files inside `evidence`.

Required MATLAB component: Statistics and Machine Learning Toolbox.

The package downloads official CDC NHANES files automatically. It first reproduces the frozen pre-outcome assets and requires the 19,097-row target-score hash to match the reviewed seal exactly. It then runs the corrected, disclosed post-unseal reconstruction.

Success ends with:

```text
================ CMDO U8 COMPLETE ================
Execution status: DISCLOSED POST-UNSEAL RECONSTRUCTION v1.1.0
```

Upload the complete MATLAB console output and:

- `CMDO_U8_NHANES_PostUnseal_Workdir_v1_1_0/05_Canonical/StageU8_Canonical_Records_v1_1_0.zip`
- `CMDO_U8_NHANES_PostUnseal_Workdir_v1_1_0/05_Canonical/StageU8_Complete_v1_1_0.json`

If an error appears after the reconstruction-start marker has been written, do not delete the Workdir or improvise a rerun. Preserve the console and folder and report the exact error.

