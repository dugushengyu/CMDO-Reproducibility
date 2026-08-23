# CMDO U10 PRESEAL pipeline v0.2 CPUFAST

Run only after the FAST downloader ends with `DONE`.

## 1. Confirm download status

```powershell
$root = "$HOME\CMDO-U10-ECG"
$fast = "$HOME\CMDO-U10-FAST-v0.2.1\CMDO_U10_ECG_FAST_v0.2.1"
Set-Location $fast

powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_FAST.ps1" `
  -Phase status `
  -Root $root
```

Required:
- PTB-XL: 21837 `.mat`, 21837 `.hea`
- Georgia: 10344 `.mat`, 0 `.hea`
- CPSC: 6877 `.mat`, 0 `.hea`

## 2. Run PRESEAL

```powershell
$root = "$HOME\CMDO-U10-ECG"
$pkg = "$HOME\CMDO-U10-PRESEAL-v0.2 CPUFAST\CMDO_U10_PRESEAL_PIPELINE_v0.2 CPUFAST"
Set-Location $pkg

powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_PRESEAL.ps1" `
  -Root $root `
  -Workers 8
```

This creates source-only development artifacts, frozen Georgia/CPSC waveform-only scores,
and `SEALS/U10_PREOUTCOME_SEAL.json`.

Stop after the seal. Do not manually obtain target `.hea` files yet.


## CPUFAST change

This version changes only execution strategy, not the scientific feature definition:
- joblib backend: processes instead of threads
- default workers: 16
- batch size: 16
- progress messages enabled

The GPU is intentionally not used in this PRESEAL extractor. The workload is dominated by
thousands of small MATLAB-file reads plus SciPy signal/statistical operations. Moving this
stage to CUDA would require a different implementation and would change the computational
path without adding scientific value. GPU use can be considered later for a deep ECG model
only if scientifically justified.

If the v0.1 run was interrupted before `FEATURES_ptb-xl.npz` was written, that unfinished
PTB-XL feature pass cannot be resumed and v0.2 will recompute PTB-XL from the beginning.


## v0.3 LABELFIX

The waveform features produced by v0.2 are reused exactly; they are **not recomputed**.

The only scientific repair is in SOURCE-ONLY PTB-XL diagnosis parsing:
- accepts `#Dx:`, `# Dx :`, `Dx:` and leading-whitespace variants;
- extracts integer SNOMED-CT tokens robustly;
- audits and prints the PTB-XL diagnosis distribution before training;
- writes `PRESEAL/SOURCE_DIAGNOSIS_AUDIT_ptb-xl.json`;
- refuses to continue if AF (`164889003`) is still absent.

No Georgia/CPSC header is read. The target pre-outcome boundary is unchanged.


## v0.3.1 LABELFIX+QC

Adds an outcome-blind exclusion audit before the source model is trained or any seal is written.

The existing v0.2 feature files are reused exactly.

Accepted exclusion reasons are only those implied by the already-frozen eligibility rule:
- fewer/more than 12 leads;
- waveform shorter than 6 seconds.

Any other extraction exception stops the pipeline before sealing.

The audit is saved to `PRESEAL/FEATURE_EXCLUSION_AUDIT.json`.


## v0.3.2 patch

Fixes a bookkeeping-only bug in v0.3.1 QC:

- v0.2 wrote a zero-byte `FEATURE_ERRORS_<dataset>.csv` when a dataset had zero exclusions.
- pandas therefore raised `EmptyDataError` before the label audit could run.
- v0.3.2 treats a zero-byte error file as exactly zero exclusions.
- future zero-exclusion error files are written with CSV headers (`record_id,error`).

No waveform feature, roster, source label, model, target score, protocol choice, or target-outcome boundary is changed.
Existing v0.2 feature artifacts are reused exactly.
