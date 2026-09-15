# CMDO reviewer: start here

This is the shortest end-to-end reviewer route for the current CMDO submission.

## What this command rebuilds

The reviewer run starts from a clean generated-output state and performs:

1. frozen submission manifest and scientific-integrity checks;
2. public CIFAR data verification/reuse (download only when missing);
3. fresh 12-epoch model training;
4. fresh prediction on all 38 U2 targets;
5. fresh metric and current-outcome-audit source-data generation;
6. comparison with the frozen U2 reference metrics;
7. strict regeneration of all 5 main + 3 Extended Data displays;
8. final 8 PNG + 8 PDF inventory check;
9. clean-worktree verification; and
10. creation of a results ZIP and SHA-256 sidecar.

Historical developmental T2/T3 replay is intentionally not part of the reviewer path.

## Windows: one command

Open Command Prompt or PowerShell in the repository root and run:

~~~text
RUN_REVIEWER_FROM_ZERO.cmd -FreshEnvironment
~~~

The CMD launcher uses a process-local PowerShell execution-policy bypass for this run only. It does not change the machine-wide or user-wide PowerShell execution policy.

If PowerShell scripts are already allowed, this direct form is equivalent:

~~~powershell
.\RUN_REVIEWER_FROM_ZERO.ps1 -FreshEnvironment
~~~

The script automatically:

- locates Python 3.11;
- creates a reviewer-only virtual environment outside the repository;
- selects a compatible PyTorch build for the detected NVIDIA driver when possible, otherwise CPU;
- installs the remaining pinned dependencies;
- detects MATLAB from PATH or a standard Windows MATLAB installation;
- uses a persistent public-data cache; and
- rebuilds every generated reviewer result from scratch; and
- automatically runs an independent no-retrain final verification before reporting the final reviewer status.

Default persistent public-data cache:

~~~text
%USERPROFILE%\.cmdo\public_data
~~~

Default generated-output directory:

~~~text
%USERPROFILE%\CMDO_REVIEWER_RUN
~~~

The generated-output directory is deleted and rebuilt on every run. The public-data cache is not.

## Reuse an existing public-data cache

If CIFAR-10, CIFAR-10.1 v6 and the selected CIFAR-10-C arrays already exist, point the runner at that directory:

~~~powershell
RUN_REVIEWER_FROM_ZERO.cmd -FreshEnvironment -DataRoot "D:\path\to\existing\CIFAR_External_v0.1"
~~~

Existing data are checked and reused. Missing data are downloaded. Model checkpoints, predictions, metrics, audit tables and manuscript figures are never reused from a previous WorkRoot.

The cache can also be set once:

~~~powershell
$env:CMDO_DATA_ROOT = "D:\path\to\existing\CIFAR_External_v0.1"
.\RUN_REVIEWER_FROM_ZERO.cmd -FreshEnvironment
~~~

## Optional explicit locations

~~~powershell
.\RUN_REVIEWER_FROM_ZERO.cmd `
    -FreshEnvironment `
    -DataRoot "D:\CMDO_PUBLIC_DATA" `
    -WorkRoot "D:\CMDO_REVIEWER_RUN" `
    -Device auto `
    -Epochs 12 `
    -WitnessReps 100 `
    -Matlab "C:\Program Files\MATLAB\R2024b\bin\matlab.exe"
~~~

## How to read the final status

The final report separates three concepts:

- **Execution**: whether the complete data/training/inference/audit/figure pipeline finished successfully.
- **Reviewer readiness**: whether the complete reviewer artifact is available. Log-loss-only deviations and operating-threshold sensitivity are labeled separately from unexplained core-metric failures.
- **U2 numeric comparison**: whether every fresh metric falls inside the predeclared platform-tolerant replay tolerance.

The runner does not silently relax numeric tolerances. Strict native-threshold replay remains REVIEW_REQUIRED whenever any original comparison exceeds the predeclared tolerance.

If the only non-log-loss deviation is balanced accuracy, the runner performs an additional diagnostic using the pre-existing frozen U2 operating threshold already stored in provenance. No threshold is re-optimized after seeing the fresh run. If AUC, AUPRC and Brier remain within tolerance and balanced accuracy at that frozen threshold is within tolerance for all 38 targets, the package is labeled READY_WITH_THRESHOLD_SELECTION_ADVISORY. This label explains the deviation; it does not convert the strict replay to PASS.

If the only deviations are log-loss, the package is labeled READY_WITH_LOGLOSS_ADVISORY. Any unexplained AUC, AUPRC, Brier, or balanced-accuracy deviation remains READY_WITH_CORE_NUMERIC_ADVISORY. Structural mismatches remain failures. The original tolerance itself is never changed after seeing a fresh run.

Exact deviations are written to:

~~~text
<WorkRoot>\u2_fresh\u2_metric_comparison.csv
<WorkRoot>\u2_fresh\fresh_u2_report.json
<WorkRoot>\u2_fresh\frozen_threshold_balanced_accuracy.csv
~~~

For a completed run, the no-retrain final verifier can be used to rebuild the advisory/report/package without repeating training:

~~~powershell
python .\scripts\finalize_existing_e2e_reviewer.py --work-root "D:\CMDO_REVIEWER_RUN"
~~~

## Required final artifacts

A successful complete execution produces:

~~~text
<WorkRoot>\
  u2_fresh\
    training_history.csv
    checkpoint_latest.pt
    validation_metrics.json
    predictions\                 # 38 fresh prediction files
    StageU2_External_Target_True_Metrics_v0.1.csv
    u2_metric_comparison.csv
    fresh_current_outcome_audit.csv
    Fresh_U2_Training_Audit.png
    Fresh_U2_Training_Audit.pdf
    fresh_u2_report.json
    frozen_threshold_balanced_accuracy.csv
    NUMERIC_REPLAY_ADVISORY.md

  submission_v2_figures\
    8 PNG
    8 PDF

  CMDO_E2E_REVIEWER_REPORT.json
  CMDO_E2E_REVIEWER_RESULTS.zip
  CMDO_E2E_REVIEWER_RESULTS.zip.sha256.txt
~~~

The manuscript continues to use the frozen authoritative records. Fresh training is an additional reviewer replay and does not rewrite sealed prospective results.
