# Optional end-to-end reviewer audit

This audit supplements the frozen `cmdo-submission-v2.1.1` reviewer package. It does **not** replace frozen manuscript records or sealed prospective verdicts.

## Recommended reviewer entry point

For a from-zero reviewer run on Windows, use the root-level wrapper:

~~~text
RUN_REVIEWER_FROM_ZERO.cmd -FreshEnvironment
~~~

This creates the reviewer Python environment, selects a compatible PyTorch build, reuses verified public-data caches when available, runs fresh training/inference/audit generation, regenerates all eight manuscript displays, and packages the final results. See START_HERE_REVIEWER.md.

## Scope

The optional E2E route executes:

```text
public CIFAR data acquisition
        ->
fresh 12-epoch U2 CNN training
        ->
38 external target predictions
        ->
fresh U2 metric/source-data generation
        ->
declared tolerance comparison with frozen U2 metrics
        ->
fresh current-outcome audit table
        ->
strict regeneration of the current 5 main + 3 Extended Data figures
        ->
clean-worktree verification
```

Historical T2/T3 developmental replay, full-claim replay and archival continuation are excluded.

## Scientific fidelity

The fresh training preserves the original U2 configuration:

- seed: `20260724`
- positive CIFAR classes: `{2,3,4,5,6,7}`
- train/validation split: 45,000 / 5,000
- optimizer: AdamW, learning rate `2e-3`, weight decay `1e-4`
- cosine learning-rate schedule
- batch size: 256
- epochs: 12
- same frozen CNN architecture
- evaluation targets: CIFAR-10 clean, CIFAR-10.1 v6, and 12 CIFAR-10-C corruptions at severities 1/3/5 = 38 targets

The repository's existing replay rule is used: checkpoint byte identity is not required, and fresh metrics pass when the declared absolute or relative tolerance is satisfied.

## Environment

Use Python 3.11.

Install the platform-appropriate current stable PyTorch + torchvision build first, then:

```powershell
python -m pip install -r environment/requirements-reviewer-e2e-core.txt
```

For NVIDIA Blackwell GPUs, use a current PyTorch build with Blackwell-capable CUDA support. Do not use the formal historical CPU-only torch 2.6 replay environment as the GPU E2E environment.

## One command

From a clean clone of the E2E branch:

```powershell
python RUN_REVIEWER_E2E.py `
    --work-root "F:\CMDO audit\E2E_REVIEWER" `
    --data-root "F:\CMDO audit\E2E_PUBLIC_DATA" `
    --device cuda `
    --matlab "C:\Program Files\MATLAB\R2024b\bin\matlab.exe"
```

The public data directory is reusable across reruns.

## Expected outputs

```text
<work-root>/
  u2_fresh/
    acquisition.json
    environment.json
    training_history.csv
    checkpoint_latest.pt
    validation_metrics.json
    StageU2_External_Target_True_Metrics_v0.1.csv
    u2_metric_comparison.csv
    fresh_current_outcome_audit.csv
    predictions/*.npz
    Fresh_U2_Training_Audit.png
    Fresh_U2_Training_Audit.pdf
    fresh_u2_report.json
    NUMERIC_REPLAY_ADVISORY.md
  submission_v2_figures/
    8 PNG
    8 PDF
    optional MATLAB .fig files
  CMDO_E2E_REVIEWER_REPORT.json
```

A complete execution requires:

1. frozen submission-v2 manifest and science checks pass;
2. fresh U2 training finishes all 12 epochs;
3. all 38 target identities match structurally;
4. the fresh metric comparison grid contains all 190 target-by-metric comparisons;
5. the fresh current-outcome audit source table is generated;
6. current manuscript figures render 8/8;
7. exactly 8 PNG and 8 PDF manuscript displays exist; and
8. the Git worktree remains clean.

Numeric replay is reported separately without changing the predeclared tolerance. A run with all comparisons inside tolerance is READY. A run whose only out-of-tolerance comparisons are log-loss is READY_WITH_LOGLOSS_ADVISORY. Any AUC, AUPRC, balanced-accuracy or Brier deviation outside tolerance is surfaced as a core numeric advisory. Structural mismatches remain failures.

## Claim boundary

Fresh U2 training is a platform-tolerant engineering/scientific replay of a public-data training component. The manuscript continues to cite the frozen authoritative records. A successful E2E audit demonstrates that the raw/public-data-to-training-to-prediction path remains executable and quantitatively compatible; it does not retroactively redefine locked prospective results.


## No-retrain final verification

After a completed E2E run, the existing artifacts can be independently rechecked and repackaged without training again:

~~~powershell
python .\scripts\finalize_existing_e2e_reviewer.py --work-root "D:\CMDO_REVIEWER_RUN"
~~~

This verifies the 38-target structural roster, all 190 metric comparisons, 38 prediction artifacts, the 8 PNG + 8 PDF display inventory, Git cleanliness, and the final ZIP SHA-256. It also refreshes the numeric advisory and final machine-readable report.
